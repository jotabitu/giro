"""T-517, parte B: ressalvas baixas da Segurança no Excluir (#679).

- B1: a lista de categorias não conta o veículo excluído (VEI-22).
- B2: criar locação, venda e conta trava a linha do cliente contra o excluir (CLI-13).
- B3: a remoção dos arquivos vai para a tarefa com nova tentativa, fora da resposta (AUD-06).
- B4: o excluir e a anonimização limpam a linha da importação do cliente (CLI-13, AUD-06).
"""

from datetime import date
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.clientes import services as clientes_services
from apps.clientes import titular
from apps.clientes.models import Cliente, DocumentoCliente
from apps.contas.models import Usuario
from apps.financeiro import services as financeiro
from apps.importacao.models import Importacao, LinhaImportacao
from apps.plataforma.models import Empresa
from comum import arquivos
from comum import tasks as tarefas_comuns
from comum.erros import ErroDeValidacao

from .test_t014_clientes import DOCUMENTOS, _enviar
from .test_t015_locacoes import Cenario
from .test_t015_locacoes import cenario as cenario
from .test_t502_fluxo_de_venda import VEN_0177, _criar

CLIENTES = "/api/clientes/"


def _excluir_cliente(cenario: Cenario, cliente_id: int) -> Any:
    return cenario.moto.api("Mariana").post(f"{CLIENTES}{cliente_id}/excluir/", {}, format="json")


def _paula() -> Cliente:
    return clientes_services.cadastrar(
        {
            "tipo": "pf",
            "nome": "Paula Souza",
            "documento": "52998224725",
            "celular": "85988880000",
            "email": "paula@exemplo.test",
        }
    )


def _venda(cenario: Cenario, cliente_id: int) -> Any:
    return _criar(
        cenario, "interessado", **{**VEN_0177, "desconto_pct": "5.00", "cliente_id": cliente_id}
    )


def _avulsa(cenario: Cenario, cliente_id: int) -> Any:
    return financeiro.lancar_avulsa(
        filial_id=cenario.frota.centro.pk,
        cliente_id=cliente_id,
        tipo="outro",
        descricao="Multa de trânsito",
        vencimento=date(2026, 10, 20),
        valor_centavos=19500,
    )


# --- B1 ---


def test_vei_22_categorias_nao_contam_o_excluido(cenario: Cenario) -> None:
    """A lista conta os veículos pelo join, que não passa pelo manager. A categoria é dado
    antigo (ADR 0043), gravada aqui à mão; a rota sai na T-522 B2."""
    from apps.veiculos.models import Categoria, Veiculo

    antiga = Categoria.objects.create(nome="Street antiga", tipo_veiculo="moto")
    Veiculo.objects.filter(pk=cenario.sak.pk).update(categoria=antiga)

    def contagem() -> int:
        corpo = cenario.moto.api("Mariana").get("/api/categorias/").json()
        lista = corpo["resultados"] if isinstance(corpo, dict) else corpo
        return int(next(c["veiculos"] for c in lista if c["id"] == antiga.pk))

    antes = contagem()
    resposta = cenario.moto.api("Mariana").post(
        f"/api/veiculos/{cenario.sak.pk}/excluir/", {}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    assert contagem() == antes - 1


# --- B2 ---


def test_cli_13_criar_trava_o_cliente(cenario: Cenario, monkeypatch) -> None:
    """Locação, venda e conta travam a linha do cliente dentro da transação do criar: o
    `FOR NO KEY UPDATE` espera o `FOR UPDATE` do excluir e relê pelo manager, que tira o
    excluído. Quem chega depois do excluir não acha o cliente."""
    original = clientes_services.travar_para_vincular
    travados: list[tuple[int, bool]] = []

    def espiao(cliente_id: Any) -> Cliente:
        travados.append((int(cliente_id), connection.in_atomic_block))
        return original(cliente_id)

    monkeypatch.setattr(clientes_services, "travar_para_vincular", espiao)
    lucas = cenario.cliente("Lucas")
    cenario.criar(cliente="Lucas")
    assert (lucas.pk, True) in travados

    travados.clear()
    venda = _venda(cenario, lucas.pk)
    assert venda.status_code == 201, venda.json()
    assert (lucas.pk, True) in travados

    travados.clear()
    _avulsa(cenario, lucas.pk)
    assert travados == [(lucas.pk, True)]


def test_cli_13_cliente_excluido_nao_recebe_conta_nem_venda(cenario: Cenario) -> None:
    juliana = cenario.cliente("Juliana")
    assert _excluir_cliente(cenario, juliana.pk).status_code == 200
    with pytest.raises(ErroDeValidacao) as erro:
        _avulsa(cenario, juliana.pk)
    assert erro.value.campos == {"cliente_id": ["Cliente não encontrado."]}
    venda = _venda(cenario, juliana.pk)
    assert venda.status_code == 400
    assert venda.json()["campos"]["cliente_id"] == ["Cliente não encontrado."]


# --- B3 ---


def test_cli_13_aud_06_excluir_com_o_armazenamento_fora_responde_200(
    cenario: Cenario,
    monkeypatch,
    django_capture_on_commit_callbacks,
) -> None:
    """A remoção dos documentos vai para a tarefa depois do commit: o armazenamento fora do ar
    não dá 500 nem desfaz o excluir, e a nova tentativa apaga os arquivos."""
    juliana = cenario.cliente("Juliana")
    for tipo in DOCUMENTOS:
        assert _enviar(cenario.moto, juliana.pk, tipo).status_code == 201
    caminhos = [
        d.arquivo.name for d in DocumentoCliente.objects.filter(cliente=juliana) if d.arquivo
    ]
    assert len(caminhos) == 4
    provedor = arquivos.provedor()
    original = type(provedor).apagar

    def fora_do_ar(self: Any, caminho: str) -> None:
        raise OSError("armazenamento fora do ar")

    monkeypatch.setattr(type(provedor), "apagar", fora_do_ar)
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _excluir_cliente(cenario, juliana.pk)
    assert resposta.status_code == 200, resposta.json()
    assert Cliente.todos.get(pk=juliana.pk).excluido_em is not None
    assert all(provedor.existe(c) for c in caminhos)  # a tarefa ficou para tentar de novo

    monkeypatch.setattr(type(provedor), "apagar", original)
    argumentos: tuple[str, list[str], list[str]] = ("empresa_a", sorted(caminhos), [])
    assert tarefas_comuns.arquivos_apagar.apply(args=argumentos).get() == 4
    assert not any(provedor.existe(c) for c in caminhos)


def test_aud_06_anonimizar_agenda_a_remocao_depois_do_commit(
    cenario: Cenario,
    monkeypatch,
    django_capture_on_commit_callbacks,
) -> None:
    paula = _paula()
    assert _enviar(cenario.moto, paula.pk, DOCUMENTOS[0]).status_code == 201
    agendadas: list[tuple[Any, ...]] = []
    monkeypatch.setattr(
        tarefas_comuns.arquivos_apagar, "delay", lambda *args: agendadas.append(args)
    )
    with django_capture_on_commit_callbacks(execute=True):
        assert _anonimizar(paula) == 1
    assert len(agendadas) == 1
    schema, caminhos, pastas, antes_de = agendadas[0]
    assert (schema, len(caminhos), pastas, antes_de) == ("empresa_a", 1, [], None)


# --- B4 ---


def _linhas_importadas(cliente: Cliente) -> tuple[LinhaImportacao, LinhaImportacao]:
    importacao = Importacao.objects.create(
        tipo="clientes",
        status="concluida",
        arquivo_nome="clientes.xlsx",
        enviada_em=timezone.now(),
        apagar_em=date(2026, 10, 14),
    )
    linhas = []
    for numero, objeto_id, dados in (
        (2, cliente.pk, '{"documento": "52998224725", "nome": "Paula Souza"}'),
        (3, cliente.pk + 1000, '{"documento": "11144477735"}'),
    ):
        linha = LinhaImportacao(
            importacao=importacao,
            numero=numero,
            status="importada",
            chave_documento=f"hash-{numero}",
            objeto_tipo="cliente",
            objeto_id=objeto_id,
        )
        linha.definir_dados_cifrados(dados)
        linha.save()
        linhas.append(linha)
    return linhas[0], linhas[1]


def _anonimizar(cliente: Cliente) -> int:
    with schema_context("public"):
        dono = Usuario.objects.create_user(
            "dono-t517@giro.test",
            "senha-longa-2026",
            nome="Ana Dono",
            funcao_plataforma="dono",
            status="ativo",
        )
    empresa = Empresa.objects.get(schema_name="empresa_a")
    pedido = titular.Pedido(dono=dono, motivo="Chamado 4600: pedido da titular")
    try:
        return titular.anonimizar(empresa, cliente.pk, pedido, cliente.nome)
    finally:
        connection.set_tenant(empresa)


def test_cli_13_excluir_limpa_a_linha_da_importacao(cenario: Cenario) -> None:
    paula = _paula()
    linha, outra = _linhas_importadas(paula)
    assert _excluir_cliente(cenario, paula.pk).status_code == 200
    linha.refresh_from_db()
    outra.refresh_from_db()
    assert (linha.dados_cifrados_claro(), linha.chave_documento) == ("", "")
    assert outra.dados_cifrados_claro() and outra.chave_documento == "hash-3"


def test_aud_06_anonimizar_limpa_a_linha_da_importacao(cenario: Cenario) -> None:
    paula = _paula()
    linha, outra = _linhas_importadas(paula)
    _anonimizar(paula)
    linha.refresh_from_db()
    outra.refresh_from_db()
    assert (linha.dados_cifrados_claro(), linha.chave_documento) == ("", "")
    assert outra.dados_cifrados_claro() and outra.chave_documento == "hash-3"
