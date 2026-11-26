"""T-515 · Excluir o veículo e o cliente sem histórico (VEI-22, CLI-13; padrão A nos três pontos).

Moto Rápida, Filial Centro, 07 out 2026, com a frota e os clientes da T-015. O SAK-1D39 (Street,
`disponivel`) e a Juliana Rocha não têm nada além do cadastro. Excluir guarda o registro, marcado,
e ele some de tudo para a locadora (listas, busca, contagens, Nova locação, ficha 404); a placa e
o chassi, ou o CPF, ficam livres. No cliente, os dados pessoais e os arquivos saem na hora, como
na AUD-06. Com histórico, a API recusa com 409 e a lista do que achou, e a ficha manda o aviso
pronto (`acoes.excluir`).
"""

from datetime import date
from typing import Any

import pytest

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.clientes import exclusao as exclusao_cliente
from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente, DocumentoCliente
from apps.financeiro import services as financeiro
from apps.plataforma.models import UsoEmpresa
from apps.veiculos import exclusao as exclusao_veiculo
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import DocumentoVeiculo, FotoVeiculo, PlanoVeiculo, Veiculo
from apps.veiculos.selectors import contar_veiculos_do_plano, frota_ativa_em
from comum import arquivos, leituras
from comum.auditoria import Ator, TipoAtor, usar_ator
from comum.erros import NaoEncontrado

from .test_t013_veiculos import _caucaia
from .test_t014_clientes import DOCUMENTOS, JULIANA, _enviar, _suporte
from .test_t015_locacoes import Cenario
from .test_t015_locacoes import cenario as cenario
from .test_t178_despesas import frota_com_historico as frota_com_historico

VEICULOS = "/api/veiculos/"
CLIENTES = "/api/clientes/"
CHASSI_SAK = "9C2KC2210RR004417"


def _ficha_veiculo(cenario: Cenario, veiculo: Veiculo, quem: str = "Mariana") -> Any:
    return cenario.moto.api(quem).get(f"{VEICULOS}{veiculo.pk}/")


def _excluir_veiculo(cenario: Cenario, veiculo: Veiculo, quem: str = "Mariana") -> Any:
    return cenario.moto.api(quem).post(f"{VEICULOS}{veiculo.pk}/excluir/", {}, format="json")


def _ficha_cliente(cenario: Cenario, cliente_id: int, quem: str = "Mariana") -> Any:
    return cenario.moto.api(quem).get(f"{CLIENTES}{cliente_id}/")


def _excluir_cliente(cenario: Cenario, cliente_id: int, quem: str = "Mariana") -> Any:
    return cenario.moto.api(quem).post(f"{CLIENTES}{cliente_id}/excluir/", {}, format="json")


def _juliana(cenario: Cenario) -> int:
    """A Juliana da T-015 com os 4 documentos enviados (CLI-03)."""
    juliana = cenario.cliente("Juliana")
    for tipo in DOCUMENTOS:
        assert _enviar(cenario.moto, juliana.pk, tipo).status_code == 201
    return int(juliana.pk)


def _placas(cenario: Cenario, **parametros: str) -> set[str]:
    resposta = cenario.moto.api().get(VEICULOS, {"tamanho": "200", **parametros})
    return {v["placa"] for v in resposta.json()["resultados"]}


def _como(cenario: Cenario, quem: str) -> Any:
    pessoa = cenario.pessoas[quem]
    return usar_ator(Ator(tipo=TipoAtor.USUARIO, nome=pessoa.nome, id=pessoa.pk))


# --- Veículo sem histórico (VEI-22) ---


def test_vei_22_ficha_manda_a_confirmacao_pronta(cenario: Cenario) -> None:
    excluir = _ficha_veiculo(cenario, cenario.sak).json()["acoes"]["excluir"]
    assert excluir == {
        "permitido": True,
        "titulo": "Excluir a SAK-1D39?",
        "texto": (
            "Use só para um cadastro feito por engano. A moto sai da frota e de todas as listas,"
            " com as fotos, os documentos e os preços. A placa e o chassi ficam livres para um"
            " novo cadastro. Não dá para desfazer."
        ),
        "motivo": None,
        "caminho": None,
        "historico": [],
    }


def test_vei_22_sem_historico_exclui_e_some_das_listas_e_da_busca(cenario: Cenario) -> None:
    sak = cenario.sak
    antes = cenario.moto.api().get(VEICULOS).json()["contagens"]
    assert "SAK1D39" in _placas(cenario, busca="SAK1D39")

    resposta = _excluir_veiculo(cenario, sak)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {"id": sak.pk, "mensagem": "Veículo SAK-1D39 excluído."}

    # Sai da Frota, da busca e das contagens; a ficha responde 404, como um que não existe.
    assert "SAK1D39" not in _placas(cenario)
    assert _placas(cenario, busca="SAK1D39") == set()
    depois = cenario.moto.api().get(VEICULOS).json()["contagens"]
    assert (depois["todos"], depois["disponivel"]) == (antes["todos"] - 1, antes["disponivel"] - 1)
    assert _ficha_veiculo(cenario, sak).status_code == 404
    assert not Veiculo.objects.filter(pk=sak.pk).exists()
    # Nova locação: o veículo não existe mais para a locadora.
    simulada = cenario.simular(veiculo=sak)
    assert simulada.status_code == 400
    assert simulada.json()["campos"]["veiculo_id"] == ["Veículo não encontrado."]
    # Já excluído: 404.
    assert _excluir_veiculo(cenario, sak).status_code == 404

    # Guardado no banco, marcado, com quem excluiu; o status não muda.
    guardado = Veiculo.todos.get(pk=sak.pk)
    assert guardado.excluido_em is not None
    assert guardado.excluido_por_id == cenario.pessoas["Mariana"].pk
    assert guardado.status == "disponivel"
    # Planos e preços desligam; documentos e fotos ficam guardados inativos.
    assert not PlanoVeiculo.objects.filter(veiculo_id=sak.pk, ativo=True).exists()
    assert not PlanoVeiculo.objects.filter(veiculo_id=sak.pk, ligado=True).exists()
    assert not DocumentoVeiculo.ativos.filter(veiculo_id=sak.pk).exists()
    assert not FotoVeiculo.ativos.filter(veiculo_id=sak.pk).exists()


def test_vei_22_vei_01_placa_e_chassi_livres_para_um_cadastro_novo(cenario: Cenario) -> None:
    sak = cenario.sak
    novo = {
        "placa": "SAK1D39",
        "chassi": CHASSI_SAK,
        "marca": "Honda",
        "modelo": "CG 160 Start",
        "ano_fabricacao": 2026,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "km_atual": 0,
        "categoria_id": sak.categoria_id,
        "filial_id": sak.filial_id,
    }
    repetido = cenario.moto.api().post(VEICULOS, novo, format="json")
    assert (repetido.status_code, repetido.json()["codigo"]) == (409, "VEI-01")

    assert _excluir_veiculo(cenario, sak).status_code == 200
    criado = cenario.moto.api().post(VEICULOS, novo, format="json")
    assert criado.status_code == 201, criado.json()
    assert criado.json()["id"] != sak.pk
    assert Veiculo.todos.filter(placa="SAK1D39").count() == 2
    assert Veiculo.objects.get(placa="SAK1D39").pk == criado.json()["id"]


def test_vei_22_plt_03_o_excluido_nao_conta_no_limite_do_plano(cenario: Cenario) -> None:
    uso = UsoEmpresa.objects.get(empresa=cenario.moto.empresa)
    usados, contados = uso.veiculos, contar_veiculos_do_plano()
    assert _excluir_veiculo(cenario, cenario.sak).status_code == 200
    uso.refresh_from_db()
    assert (uso.veiculos, contar_veiculos_do_plano()) == (usados - 1, contados - 1)


# --- Veículo com histórico (VEI-22) ---


def test_vei_22_com_locacao_em_rascunho_recusa(cenario: Cenario) -> None:
    sak = cenario.sak
    cenario.criar(veiculo=sak)  # rascunho: já é histórico
    resposta = _excluir_veiculo(cenario, sak)
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "VEI-22",
        "mensagem": "Este veículo já tem locação. Ele fica guardado e não pode ser excluído.",
        "detalhes": {"historico": ["locacao"]},
    }
    assert Veiculo.objects.filter(pk=sak.pk).exists()
    excluir = _ficha_veiculo(cenario, sak).json()["acoes"]["excluir"]
    assert excluir["permitido"] is False
    assert excluir["titulo"] == "Este veículo não pode ser excluído"
    assert excluir["motivo"] == resposta.json()["mensagem"]
    assert excluir["caminho"] == (
        "Para tirar a moto da frota, coloque à venda ou faça a baixa (perda total, roubo ou"
        " sucata)."
    )
    assert excluir["historico"] == ["locacao"]
    # O gerente pede a baixa ao administrador.
    do_gerente = _ficha_veiculo(cenario, sak, "Rodrigo").json()["acoes"]["excluir"]
    assert do_gerente["caminho"] == (
        "Para tirar a moto da frota, coloque à venda ou peça a baixa ao administrador (perda"
        " total, roubo ou sucata)."
    )


def test_vei_22_com_transferencia_e_despesa_recusa(cenario: Cenario) -> None:
    sak = cenario.sak
    caucaia = _caucaia(cenario.moto, "Rodrigo")
    with _como(cenario, "Mariana"):
        veiculos_services.transferir(sak, caucaia.pk)
    resposta = _excluir_veiculo(cenario, sak)
    assert (resposta.status_code, resposta.json()["detalhes"]) == (
        409,
        {"historico": ["transferencia"]},
    )
    assert resposta.json()["mensagem"] == (
        "Este veículo já tem transferência. Ele fica guardado e não pode ser excluído."
    )
    # A despesa conta em qualquer situação (FIN-17).
    financeiro.lancar_despesa(
        filial=caucaia,
        usuario=cenario.pessoas["Mariana"],
        descricao="Troca de óleo",
        valor_centavos=8000,
        data=date(2026, 10, 7),
        vencimento=date(2026, 10, 7),
        categoria="manutencao",
        veiculo_id=sak.pk,
    )
    resposta = _excluir_veiculo(cenario, sak)
    assert resposta.json()["detalhes"] == {"historico": ["despesa", "transferencia"]}
    assert resposta.json()["mensagem"] == (
        "Este veículo já tem despesa e transferência. Ele fica guardado e não pode ser excluído."
    )


def test_vei_22_cada_tipo_de_historico_tem_fornecedor() -> None:
    """Cada tipo da VEI-22 tem o contador registrado pelo app dono, sem o recurso do plano. A
    ordem de serviço ainda não existe (fase 2): sem fornecedor, vale 0."""
    registrados = set(leituras._contadores[exclusao_veiculo.ALVO])
    faltando = {
        tipo
        for tipo, _ in exclusao_veiculo.HISTORICO
        if exclusao_veiculo.contador(tipo) not in registrados
    }
    assert faltando == {"ordem_servico"}
    assert not any(
        ("contador", exclusao_veiculo.ALVO, exclusao_veiculo.contador(tipo)) in leituras._recurso_do
        for tipo, _ in exclusao_veiculo.HISTORICO
    )


@pytest.mark.parametrize(
    ("achados", "frase"),
    [
        (["locacao"], "locação"),
        (["venda", "despesa"], "venda e despesa"),
        (["vistoria", "despesa", "transferencia"], "vistoria, despesa e transferência"),
        (
            ["troca", "ordem_servico", "movimentacao"],
            "troca de veículo, ordem de serviço e movimentação",
        ),
    ],
)
def test_vei_22_frase_com_os_tipos_achados_na_ordem(achados: list[str], frase: str) -> None:
    assert exclusao_veiculo.motivo(achados) == (
        f"Este veículo já tem {frase}. Ele fica guardado e não pode ser excluído."
    )


@pytest.mark.parametrize("tipo", [tipo for tipo, _ in exclusao_veiculo.HISTORICO])
def test_vei_22_com_cada_tipo_de_historico_recusa(cenario: Cenario, monkeypatch, tipo) -> None:
    contadores = dict(leituras._contadores[exclusao_veiculo.ALVO])
    contadores[exclusao_veiculo.contador(tipo)] = lambda _id: 1
    monkeypatch.setitem(leituras._contadores, exclusao_veiculo.ALVO, contadores)
    resposta = _excluir_veiculo(cenario, cenario.sak)
    assert (resposta.status_code, resposta.json()["detalhes"]) == (409, {"historico": [tipo]})
    assert Veiculo.objects.filter(pk=cenario.sak.pk).exists()


# --- Veículo: perfis, filial e suporte (VEI-22, USR-07, PLT-07) ---


def test_vei_22_perfis_e_filial(cenario: Cenario) -> None:
    sak = cenario.sak
    for quem in ("Bruna", "João", "Lúcia"):
        assert _excluir_veiculo(cenario, sak, quem).status_code == 403
    assert _ficha_veiculo(cenario, sak, "Bruna").json()["acoes"]["excluir"] is None
    # O gerente só nas filiais dele: fora delas, o veículo não existe (404).
    caucaia = _caucaia(cenario.moto)
    with _como(cenario, "Mariana"):
        veiculos_services.transferir(cenario.frota.veiculos["SAK1D39"], caucaia.pk)
    outro = Veiculo.objects.filter(filial=cenario.frota.centro, status="disponivel").first()
    assert outro is not None
    assert _excluir_veiculo(cenario, sak, "Rodrigo").status_code == 404
    assert _excluir_veiculo(cenario, outro, "Rodrigo").status_code == 200


@pytest.mark.parametrize("permissao", ["ver", "ver_editar"])
def test_vei_22_plt_07_suporte_nao_exclui(cenario: Cenario, relogio_jwt, permissao) -> None:
    api = _suporte(cenario.moto, permissao)
    resposta = api.post(f"{VEICULOS}{cenario.sak.pk}/excluir/", {}, format="json")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "PLT-07")
    assert Veiculo.objects.filter(pk=cenario.sak.pk).exists()
    ficha = api.get(f"{VEICULOS}{cenario.sak.pk}/")
    assert ficha.status_code == 200
    assert ficha.json()["acoes"]["excluir"] is None


def test_vei_22_auditoria_com_os_dados_do_veiculo(cenario: Cenario) -> None:
    sak = cenario.sak
    assert _excluir_veiculo(cenario, sak, "Rodrigo").status_code == 200
    evento = EventoAuditoria.objects.get(acao="veiculo.excluir")
    assert (evento.objeto_tipo, evento.objeto_id, evento.objeto_codigo) == (
        "veiculo",
        sak.pk,
        "SAK-1D39",
    )
    assert evento.ator_id == cenario.pessoas["Rodrigo"].pk
    assert evento.regra == "VEI-22"
    assert evento.filial_id == sak.filial_id
    assert evento.antes == {
        "placa": "SAK1D39",
        "chassi": CHASSI_SAK,
        "marca": sak.marca,
        "modelo": sak.modelo,
        "ano_fabricacao": sak.ano_fabricacao,
        "ano_modelo": sak.ano_modelo,
        "filial_id": sak.filial_id,
        "status": "disponivel",
    }
    assert evento.depois["excluido_por"] == cenario.pessoas["Rodrigo"].pk


# --- Cliente sem histórico (CLI-13) ---


def test_cli_13_ficha_manda_a_confirmacao_pronta(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    excluir = _ficha_cliente(cenario, juliana).json()["acoes"]["excluir"]
    assert excluir == {
        "permitido": True,
        "titulo": "Excluir o cadastro de Juliana Rocha?",
        "texto": (
            "Use só para um cadastro feito por engano. O cliente sai da lista, os dados pessoais"
            " e os documentos enviados são apagados, e o CPF fica livre para um novo cadastro."
            " Não dá para desfazer."
        ),
        "motivo": None,
        "caminho": None,
        "inativar": False,
        "historico": [],
    }


def test_cli_13_sem_historico_exclui_apaga_os_dados_e_some(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    caminhos: list[str] = [
        str(caminho)
        for caminho in DocumentoCliente.objects.filter(cliente_id=juliana).values_list(
            "arquivo", flat=True
        )
        if caminho
    ]
    assert len(caminhos) == 4
    antes = cenario.moto.api().get(CLIENTES).json()["contagens"]

    resposta = _excluir_cliente(cenario, juliana)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {"id": juliana, "mensagem": "Cliente excluído."}

    # Some da lista, da busca e das contagens; a ficha responde 404.
    lista = cenario.moto.api().get(CLIENTES, {"busca": "Juliana"}).json()
    assert lista["resultados"] == []
    assert (
        cenario.moto.api().get(CLIENTES, {"busca": JULIANA["documento"]}).json()["resultados"] == []
    )
    depois = cenario.moto.api().get(CLIENTES).json()["contagens"]
    assert depois["todos"] == antes["todos"] - 1
    assert _ficha_cliente(cenario, juliana).status_code == 404
    assert _excluir_cliente(cenario, juliana).status_code == 404
    simulada = cenario.simular(cliente="Juliana")
    assert simulada.status_code == 400

    # Guardado, marcado, sem os dados pessoais (como na AUD-06) e sem os arquivos.
    guardado = Cliente.todos.get(pk=juliana)
    assert guardado.excluido_em is not None
    assert guardado.excluido_por_id == cenario.pessoas["Mariana"].pk
    assert guardado.nome == "Cliente excluído"
    assert (guardado.documento_claro(), guardado.cnh_numero_claro()) == ("", "")
    assert (guardado.celular, guardado.email, guardado.nascimento) == ("", "", None)
    assert (guardado.logradouro, guardado.cidade, guardado.referencia_nome) == ("", "", "")
    documentos = DocumentoCliente.objects.filter(cliente_id=juliana)
    assert {(d.ativo, bool(d.arquivo)) for d in documentos} == {(False, False)}
    for caminho in caminhos:
        assert not arquivos.provedor().existe(caminho)


def test_cli_13_cli_01_cpf_livre_para_um_cadastro_novo(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    repetido = cenario.moto.api("Bruna").post(CLIENTES, JULIANA, format="json")
    assert (repetido.status_code, repetido.json()["codigo"]) == (409, "CLI-01")
    assert _excluir_cliente(cenario, juliana).status_code == 200
    novo = cenario.moto.api("Bruna").post(CLIENTES, JULIANA, format="json")
    assert novo.status_code == 201, novo.json()
    assert novo.json()["id"] != juliana


# --- Cliente com histórico (CLI-13) ---


def test_cli_13_com_locacao_recusa(cenario: Cenario) -> None:
    lucas = cenario.cliente("Lucas")
    cenario.criar(cliente="Lucas")  # rascunho: já é histórico
    resposta = _excluir_cliente(cenario, lucas.pk)
    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["codigo"] == "CLI-13"
    assert corpo["detalhes"]["historico"][0] == "locacao"
    assert corpo["mensagem"] == exclusao_cliente.motivo(corpo["detalhes"]["historico"])
    assert Cliente.objects.filter(pk=lucas.pk).exists()
    excluir = _ficha_cliente(cenario, lucas.pk).json()["acoes"]["excluir"]
    assert excluir["permitido"] is False
    assert excluir["titulo"] == "Este cliente não pode ser excluído"
    assert excluir["motivo"] == corpo["mensagem"]
    assert excluir["inativar"] is True
    assert excluir["caminho"] == (
        "Para ele não fazer novas locações nem compras, inative o cadastro. Se o cliente pediu"
        " para apagar os dados dele, peça à equipe Giro para anonimizar o cadastro."
    )
    do_gerente = _ficha_cliente(cenario, lucas.pk, "Rodrigo").json()["acoes"]["excluir"]
    assert do_gerente["caminho"] == (
        "Para ele não fazer novas locações nem compras, inative o cadastro."
    )


def test_cli_13_com_pedido_de_aprovacao_recusa_e_inativo_ja_esta_inativo(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    api = cenario.moto.api
    assert (
        api()
        .post(f"{CLIENTES}{juliana}/bloquear/", {"motivo": "Conferido"}, format="json")
        .status_code
        == 200
    )
    pedido = api("Bruna").post(
        f"{CLIENTES}{juliana}/desbloquear/", {"motivo": "Pagou"}, format="json"
    )
    assert pedido.status_code == 202, pedido.json()
    assert (
        api()
        .post(f"{CLIENTES}{juliana}/desbloquear/", {"motivo": "Pagou"}, format="json")
        .status_code
        == 200
    )
    resposta = _excluir_cliente(cenario, juliana)
    assert (resposta.status_code, resposta.json()["detalhes"]) == (
        409,
        {"historico": ["aprovacao"]},
    )
    assert resposta.json()["mensagem"] == (
        "Este cliente já tem pedido de aprovação na empresa. O cadastro fica guardado e não pode"
        " ser excluído."
    )
    assert (
        api().post(f"{CLIENTES}{juliana}/inativar/", {"motivo": "Mudou"}, format="json").status_code
        == 200
    )
    excluir = _ficha_cliente(cenario, juliana, "Rodrigo").json()["acoes"]["excluir"]
    assert (excluir["caminho"], excluir["inativar"]) == ("O cadastro já está inativo.", False)


def test_cli_13_bloqueado_recusa(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    with _como(cenario, "Mariana"):
        clientes_services.bloquear(Cliente.objects.get(pk=juliana), "Conferido")
    resposta = _excluir_cliente(cenario, juliana)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "transicao_cliente")
    assert resposta.json()["mensagem"] == "Desbloqueie o cliente antes de excluir."
    excluir = _ficha_cliente(cenario, juliana).json()["acoes"]["excluir"]
    assert (excluir["permitido"], excluir["motivo"]) == (
        False,
        "Desbloqueie o cliente antes de excluir.",
    )


def test_cli_13_cada_tipo_de_historico_tem_fornecedor() -> None:
    registrados = set(leituras._contadores[exclusao_cliente.ALVO])
    assert {
        exclusao_cliente.contador(tipo) for tipo, _ in exclusao_cliente.HISTORICO
    } <= registrados
    assert not any(
        ("contador", exclusao_cliente.ALVO, exclusao_cliente.contador(tipo)) in leituras._recurso_do
        for tipo, _ in exclusao_cliente.HISTORICO
    )


def test_cli_13_frase_com_os_tipos_achados_na_ordem() -> None:
    assert exclusao_cliente.motivo(["venda"]) == (
        "Este cliente já tem venda na empresa. O cadastro fica guardado e não pode ser excluído."
    )
    assert exclusao_cliente.motivo(["locacao", "conta", "contrato"]) == (
        "Este cliente já tem locação, conta e contrato na empresa. O cadastro fica guardado e não"
        " pode ser excluído."
    )


@pytest.mark.parametrize("tipo", [tipo for tipo, _ in exclusao_cliente.HISTORICO])
def test_cli_13_com_cada_tipo_de_historico_recusa(cenario: Cenario, monkeypatch, tipo) -> None:
    juliana = cenario.cliente("Juliana")
    contadores = dict(leituras._contadores[exclusao_cliente.ALVO])
    contadores[exclusao_cliente.contador(tipo)] = lambda _id: 1
    monkeypatch.setitem(leituras._contadores, exclusao_cliente.ALVO, contadores)
    resposta = _excluir_cliente(cenario, juliana.pk)
    assert (resposta.status_code, resposta.json()["detalhes"]) == (409, {"historico": [tipo]})
    assert Cliente.objects.filter(pk=juliana.pk).exists()


# --- Cliente: perfis e suporte (CLI-13, PLT-07) ---


def test_cli_13_perfis(cenario: Cenario) -> None:
    juliana = cenario.cliente("Juliana")
    for quem in ("Bruna", "João", "Lúcia"):
        assert _excluir_cliente(cenario, juliana.pk, quem).status_code == 403
    # O vendedor vê a ficha completa, mas não exclui: o botão não aparece.
    assert _ficha_cliente(cenario, juliana.pk, "Bruna").json()["acoes"]["excluir"] is None
    assert _excluir_cliente(cenario, juliana.pk, "Rodrigo").status_code == 200


@pytest.mark.parametrize("permissao", ["ver", "ver_editar"])
def test_cli_13_plt_07_suporte_nao_exclui(cenario: Cenario, relogio_jwt, permissao) -> None:
    juliana = cenario.cliente("Juliana")
    api = _suporte(cenario.moto, permissao)
    resposta = api.post(f"{CLIENTES}{juliana.pk}/excluir/", {}, format="json")
    assert (resposta.status_code, resposta.json()["codigo"]) == (403, "PLT-07")
    assert Cliente.objects.filter(pk=juliana.pk).exists()


def test_cli_13_auditoria_com_o_nome_mascarado_e_sem_documento(cenario: Cenario) -> None:
    juliana = _juliana(cenario)
    assert _excluir_cliente(cenario, juliana, "Rodrigo").status_code == 200
    evento = EventoAuditoria.objects.get(acao="cliente.excluir")
    assert (evento.objeto_tipo, evento.objeto_id, evento.regra) == ("cliente", juliana, "CLI-13")
    assert evento.ator_id == cenario.pessoas["Rodrigo"].pk
    # O nome e o tipo no momento; o nome mascarado, como em todo evento do cliente (ADR 0014).
    assert evento.antes == {"nome": "J. R.", "tipo": "pf", "status": "ativo"}
    texto = str(evento.antes) + str(evento.depois)
    assert "05221833018" not in texto
    assert "Juliana" not in texto
    documentos = EventoAuditoria.objects.filter(acao="documento_cliente.excluir")
    assert documentos.count() == 4


# --- Revisão da segurança no #679 (M1, M2) ---


def test_vei_22_apr_06_excluir_cancela_o_pedido_de_correcao_de_km(cenario: Cenario) -> None:
    """M1: o pedido APR-06 pendente sai da caixa do gerente; aprovar depois não dá 500."""
    sak = cenario.sak
    api = cenario.moto.api
    assert (
        api("João").post(f"{VEICULOS}{sak.pk}/km/", {"km": 3500}, format="json").status_code == 200
    )
    pedido = api("João").post(
        f"{VEICULOS}{sak.pk}/corrigir-km/",
        {"km": 3400, "motivo": "Erro de digitação"},
        format="json",
    )
    assert pedido.status_code == 202, pedido.json()
    pedido_id = pedido.json()["pedido_aprovacao"]["id"]

    assert _excluir_veiculo(cenario, sak).status_code == 200
    cancelado = PedidoAprovacao.objects.get(pk=pedido_id)
    assert cancelado.status == "cancelado"
    # Mesmo chamado direto, o assinante da aprovação responde 404, e não 500.
    with pytest.raises(NaoEncontrado):
        veiculos_services.aplicar_correcao_aprovada(sak.pk, 3400, 3500, "Erro", pedido_id)


def test_vei_22_fin_16_o_excluido_nao_entra_no_rateio_da_frota(
    cenario: Cenario, frota_com_historico: int
) -> None:
    """M2: a frota ativa do rateio (FIN-16) lê o histórico de status e não conta o excluído."""
    dia, filiais = date(2026, 10, 7), [cenario.frota.centro.pk]
    antes = frota_ativa_em(dia, filiais)
    assert antes > 0
    assert _excluir_veiculo(cenario, cenario.sak).status_code == 200
    assert frota_ativa_em(dia, filiais) == antes - 1
