"""T-366 · Rota de recebimentos e marcação dos passos (`plataforma.md`, "Recebimentos da empresa"
e "Quando cada passo conta como feito"; FIN-04, IMP-07, PLT-07, PLT-12; achados M-01 e B-01 a
B-03 da T-384).

Roda na Moto Rápida da T-181 (Profissional, em teste, 07 out 2026), com o parceiro de mentira.
"""

import logging
import threading
import time
from contextlib import nullcontext
from datetime import date
from typing import Any

import pytest
from django.db import connection, connections

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.plataforma import services as plataforma
from apps.plataforma.models import ContaPagamento, Empresa, Plano, UsoEmpresa
from apps.veiculos.models import Categoria, PrecoCategoria
from integracoes.pagamentos import falso
from integracoes.pagamentos.base import ParceiroIndisponivel, ParceiroRecusou

from .test_t012_filiais import HORARIO_CENTRO
from .test_t014_clientes import _suporte
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t181_configuracoes import moto_rapida  # noqa: F401 - fixture

URL = "/api/recebimentos/"
IMPLANTACAO = "/api/implantacao/"
CORPO = {
    "nome": "Moto Rápida Locadora LTDA",
    "documento": "12.345.678/0001-95",
    "email": "financeiro@motorapida.com.br",
    "celular": "(85) 99812-4410",
    "cep": "60110-000",
    "logradouro": "Av. Santos Dumont",
    "numero": "1500",
    "complemento": "",
    "bairro": "Aldeota",
    "faturamento_mensal_centavos": 5000000,
    "tipo_empresa": "LIMITED",
}
PRECO = {
    "diaria_centavos": 5490,
    "semanal_centavos": 32900,
    "mensal_centavos": 119000,
    "caucao_centavos": 30000,
}


def _passos(moto, *feitos: str) -> None:
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(
        passos_implantacao={p: "2026-10-07" for p in feitos}
    )


def _feitos(moto) -> dict[str, str]:
    return dict(UsoEmpresa.objects.get(empresa=moto.empresa).passos_implantacao)


def _conectar(moto, quem: str = "Mariana", **mudancas: Any):
    return moto.api(quem).post(URL, {**CORPO, **mudancas}, format="json")


def _conta(moto) -> ContaPagamento:
    return ContaPagamento.objects.get(empresa=moto.empresa)


@pytest.fixture
def essencial(moto_rapida):  # noqa: F811
    """A Moto Rápida no Essencial, sem `recebimento_parceiro` (PLT-12, ADR 0024)."""
    Empresa._base_manager.filter(pk=moto_rapida.moto.empresa.pk).update(
        plano=Plano.objects.get(nome="Essencial")
    )
    return moto_rapida


# --- GET e POST (FIN-04) ---


def test_fin_04_recebimentos_desconectado_com_sugestao(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    Empresa._base_manager.filter(pk=moto.empresa.pk).update(
        razao_social="Moto Rápida Locadora LTDA", cnpj="12345678000195"
    )
    Usuario.objects.filter(pk=moto.pessoas["Mariana"].pk).update(celular="85998124410")
    resposta = moto.api("Mariana").get(URL)
    assert resposta.status_code == 200, resposta.json()
    centro = moto_rapida.frota.centro
    assert resposta.json() == {
        "situacao": "desconectado",
        "rotulo": "Não conectado",
        "mensagem": "Conecte para gerar Pix e boleto e dar baixa sozinho.",
        "conectado_em": None,
        "sugestao": {
            "nome": "Moto Rápida Locadora LTDA",
            "documento": "12345678000195",
            "email": "mariana@motorapida.com.br",
            "celular": "85998124410",
            "cep": centro.cep,
            "logradouro": centro.logradouro,
            "numero": centro.numero,
            "complemento": centro.complemento,
            "bairro": centro.bairro,
        },
        "acoes": {"conectar": True},
    }


def test_fin_04_sugestao_do_administrador_logado(moto_rapida):  # noqa: F811
    # B-03 da T-384: com dois administradores, cada um vê o próprio e-mail e celular.
    moto = moto_rapida.moto
    Usuario.objects.filter(pk=moto.pessoas["Rodrigo"].pk).update(
        perfil="administrador", celular="85991112222"
    )
    sugestao = moto.api("Rodrigo").get(URL).json()["sugestao"]
    assert (sugestao["email"], sugestao["celular"]) == ("rodrigo@motorapida.com.br", "85991112222")


def test_fin_04_conectar_recebimentos(moto_rapida, caplog):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    with caplog.at_level(logging.DEBUG):
        resposta = _conectar(moto)
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    assert (corpo["situacao"], corpo["rotulo"]) == ("pendente", "Em análise pelo parceiro")
    assert corpo["mensagem"] == (
        "O parceiro está conferindo o cadastro. Enquanto isso, registre os pagamentos à mão em "
        "Contas a receber."
    )
    assert corpo["sugestao"] is None and corpo["acoes"] == {"conectar": False}
    assert corpo["conectado_em"] is not None
    conta = _conta(moto)
    assert conta.status == "pendente"
    # A chave e o token do webhook nunca saem (S-05, S-14).
    texto = resposta.content.decode()
    assert conta.chave_api_cifrada_claro() not in texto
    assert conta.webhook_token_hash not in texto
    # Não marca o passo: só a aprovação conta (IMP-07).
    assert "recebimentos" not in _feitos(moto)
    # B-02: o corpo vai só ao parceiro, fora da auditoria e do log.
    evento = EventoAuditoria.objects.get(acao="conta_pagamento.criar")
    gravado = f"{evento.antes}{evento.depois}{evento.motivo}"
    for valor in ("12345678000195", "financeiro@motorapida.com.br", "85998124410", "Aldeota"):
        assert valor not in gravado
        assert valor not in caplog.text


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("documento", "12345678000100"),
        ("documento", "123.456.789-00"),
        ("cep", "6011000"),
        ("celular", "859981244"),
        ("faturamento_mensal_centavos", 0),
        ("tipo_empresa", "SA"),
    ],
)
def test_fin_04_conectar_validacao(moto_rapida, campo, valor):  # noqa: F811
    resposta = _conectar(moto_rapida.moto, **{campo: valor})
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "validacao"
    assert campo in resposta.json()["campos"]
    assert not ContaPagamento.objects.exists()


def test_fin_04_conectar_com_cpf_do_mei(moto_rapida):  # noqa: F811
    resposta = _conectar(moto_rapida.moto, documento="529.982.247-25", tipo_empresa="MEI")
    assert resposta.status_code == 201, resposta.json()


def test_fin_04_recebimentos_conectados_409(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    segundo = _conectar(moto)
    assert segundo.status_code == 409
    assert segundo.json()["codigo"] == "recebimentos_conectados"
    assert ContaPagamento.objects.filter(empresa=moto.empresa).count() == 1


def test_fin_04_parceiro_recusou_nada_gravado(moto_rapida, monkeypatch):  # noqa: F811
    def recusar(self, empresa):
        raise ParceiroRecusou("O CPF/CNPJ informado é inválido.")

    monkeypatch.setattr(falso.PagamentosFalso, "criar_subconta", recusar)
    resposta = _conectar(moto_rapida.moto)
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "parceiro_recusou"
    assert resposta.json()["mensagem"] == "O CPF/CNPJ informado é inválido."
    assert not ContaPagamento.objects.exists()
    assert not EventoAuditoria.objects.filter(acao="conta_pagamento.criar").exists()


def test_fin_04_parceiro_fora_do_ar_503(moto_rapida, monkeypatch):  # noqa: F811
    def fora(self, empresa):
        raise ParceiroIndisponivel("timeout")

    monkeypatch.setattr(falso.PagamentosFalso, "criar_subconta", fora)
    resposta = _conectar(moto_rapida.moto)
    assert resposta.status_code == 503
    assert resposta.json()["codigo"] == "parceiro_indisponivel"
    assert not ContaPagamento.objects.exists()


def test_fin_04_conectar_no_maximo_10_por_hora(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    for _ in range(10):
        assert _conectar(moto, cep="1").status_code == 400
    acima = _conectar(moto)
    assert acima.status_code == 429
    assert acima.json()["codigo"] == "muitas_requisicoes"
    # A leitura não conta no limite.
    assert moto.api("Mariana").get(URL).status_code == 200


def test_fin_04_recebimentos_aprovada_liga_a_cobranca(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    falso.subcontas[_conta(moto).conta_externa_id] = "aprovada"
    corpo = moto.api("Mariana").get(URL).json()
    assert (corpo["situacao"], corpo["rotulo"]) == ("aprovada", "Recebimentos ligados")
    assert corpo["mensagem"] == "Pix e boleto saem pelo parceiro, e a baixa é feita sozinha."
    assert corpo["acoes"] == {"conectar": False}
    evento = EventoAuditoria.objects.get(acao="conta_pagamento.aprovada")
    assert (evento.categoria, evento.regra) == ("configuracoes", "FIN-04")


def test_fin_04_recebimentos_recusada(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    falso.subcontas[_conta(moto).conta_externa_id] = "recusada"
    corpo = moto.api("Mariana").get(URL).json()
    assert (corpo["situacao"], corpo["rotulo"]) == ("recusada", "Cadastro recusado")
    assert corpo["mensagem"] == "O parceiro recusou o cadastro. Fale com a equipe Giro."
    assert corpo["acoes"] == {"conectar": False}
    assert EventoAuditoria.objects.filter(acao="conta_pagamento.recusada").count() == 1
    assert "recebimentos" not in _feitos(moto)


def test_fin_04_consulta_ao_parceiro_uma_vez_por_minuto(moto_rapida, monkeypatch):  # noqa: F811
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    consultas: list[str] = []
    original = falso.PagamentosFalso.consultar_subconta

    def contar(self, conta):
        consultas.append(conta.conta_externa_id)
        return original(self, conta)

    monkeypatch.setattr(falso.PagamentosFalso, "consultar_subconta", contar)
    api = moto.api("Mariana")
    for _ in range(3):
        assert api.get(URL).json()["situacao"] == "pendente"
    assert len(consultas) == 1


def test_fin_04_consulta_sem_trava_responde_a_gravada(moto_rapida, monkeypatch):  # noqa: F811
    # B-01: outra consulta já pegou a trava do minuto; esta não chama o parceiro.
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    falso.subcontas[_conta(moto).conta_externa_id] = "aprovada"
    monkeypatch.setattr(plataforma.cache, "add", lambda *args, **kwargs: False)
    assert moto.api("Mariana").get(URL).json()["situacao"] == "pendente"


def test_fin_04_transicao_feita_por_outra_consulta_nao_da_409(moto_rapida, monkeypatch):  # noqa: F811
    # B-01: as duas viram `pendente`; a outra transicionou antes desta pegar a linha.
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201
    falso.subcontas[_conta(moto).conta_externa_id] = "aprovada"
    original = falso.PagamentosFalso.consultar_subconta

    def a_outra_chegou_antes(self, conta):
        situacao = original(self, conta)
        plataforma.transicionar(
            ContaPagamento.objects.get(pk=_conta(moto).pk), situacao, regra="FIN-04"
        )
        return situacao

    monkeypatch.setattr(falso.PagamentosFalso, "consultar_subconta", a_outra_chegou_antes)
    resposta = moto.api("Mariana").get(URL)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["situacao"] == "aprovada"


def test_fin_04_parceiro_fora_do_ar_na_consulta(moto_rapida, monkeypatch):  # noqa: F811
    moto = moto_rapida.moto
    assert _conectar(moto).status_code == 201

    def fora(self, conta):
        raise ParceiroIndisponivel("timeout")

    monkeypatch.setattr(falso.PagamentosFalso, "consultar_subconta", fora)
    resposta = moto.api("Mariana").get(URL)
    assert resposta.status_code == 200
    assert resposta.json()["situacao"] == "pendente"


def _em_outra_conexao(funcao):
    erros: list[BaseException] = []

    def rodar() -> None:
        try:
            connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
            funcao()
        except BaseException as erro:  # devolvido ao teste
            erros.append(erro)
        finally:
            connections.close_all()

    thread = threading.Thread(target=rodar)
    thread.start()
    return thread, erros


def test_fin_04_conectar_em_paralelo_cria_uma_subconta(empresa_a, monkeypatch):
    """M-01 da T-384. Conexões próprias, fora da transação do teste; a subconta criada aqui é
    apagada no fim. A auditoria (imutável) fica de fora: o teste é da trava."""
    chamadas: list[str] = []
    original = falso.PagamentosFalso.criar_subconta

    def devagar(self, empresa):
        chamadas.append(empresa.documento)
        time.sleep(0.5)  # a outra requisição chega com esta no meio do parceiro
        return original(self, empresa)

    monkeypatch.setattr(falso.PagamentosFalso, "criar_subconta", devagar)
    monkeypatch.setattr(plataforma, "auditar", lambda *args, **kwargs: nullcontext())
    dados: dict[str, Any] = {**CORPO, "documento": "12345678000195", "tipo_empresa": "limitada"}
    if ContaPagamento.objects.filter(empresa__schema_name="empresa_a").exists():
        pytest.skip("empresa_a precisa começar sem subconta gravada")

    def conectar() -> None:
        plataforma.conectar_recebimentos(**dados)

    try:
        corridas = [_em_outra_conexao(conectar), _em_outra_conexao(conectar)]
        for corrida, _ in corridas:
            corrida.join(timeout=20)
        erros = [e for _, lista in corridas for e in lista]
    finally:

        def apagar() -> None:
            ContaPagamento.objects.filter(empresa__schema_name="empresa_a").delete()

        thread, sobra = _em_outra_conexao(apagar)
        thread.join(timeout=20)
        assert not sobra, sobra
    assert len(chamadas) == 1
    assert [getattr(e, "codigo", repr(e)) for e in erros] == ["recebimentos_conectados"]


# --- Quem pode (PLT-07, PLT-12) ---


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna", "João", "Lúcia"])
def test_fin_04_recebimentos_so_do_administrador(moto_rapida, quem):  # noqa: F811
    moto = moto_rapida.moto
    for resposta in (moto.api(quem).get(URL), _conectar(moto, quem)):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "permissao"


@pytest.mark.parametrize("permissao", ["ver", "ver_editar"])
def test_plt_07_recebimentos_recusa_suporte(moto_rapida, relogio_jwt, permissao):  # noqa: F811
    api = _suporte(moto_rapida.moto, permissao)
    for resposta in (api.get(URL), api.post(URL, CORPO, format="json")):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "PLT-07"
    assert not ContaPagamento.objects.exists()


@pytest.mark.parametrize("quem", ["Mariana", "Bruna"])
def test_plt_12_recebimentos_essencial_403(essencial, quem):
    moto = essencial.moto
    for resposta in (moto.api(quem).get(URL), _conectar(moto, quem)):
        assert resposta.status_code == 403
        assert resposta.json() == {
            "codigo": "PLT-12",
            "mensagem": "Seu plano não inclui Pix e boleto automáticos. Para usar, mude de plano.",
            "detalhes": {"recurso": "recebimento_parceiro", "motivo": "plano"},
        }
    assert not ContaPagamento.objects.exists()


# --- Quando cada passo conta como feito (IMP-07) ---


def test_imp_07_recebimentos_so_com_a_subconta_aprovada(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    api = moto.api("Mariana")
    assert _conectar(moto).status_code == 201
    assert api.get(URL).json()["situacao"] == "pendente"
    assert "recebimentos" not in _feitos(moto)

    falso.subcontas[_conta(moto).conta_externa_id] = "aprovada"
    plataforma.cache.clear()  # passou o minuto da consulta
    assert api.get(URL).json()["situacao"] == "aprovada"
    assert _feitos(moto)["recebimentos"] == "2026-10-07"
    passo = next(p for p in api.get(IMPLANTACAO).json()["passos"] if p["passo"] == "recebimentos")
    assert passo["feito"] is True


def test_imp_07_precos_marca_com_preco_vigente(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    api = moto.api("Mariana")
    so_caucao = {**PRECO, "diaria_centavos": 0, "semanal_centavos": 0, "mensal_centavos": 0}
    zerada = {"nome": "Sem preço", "tipo_veiculo": "moto", "preco": so_caucao}
    assert api.post("/api/categorias/", zerada, format="json").status_code == 201
    assert "precos" not in _feitos(moto)  # só a caução não é preço de plano

    nova = {"nome": "Trilha 250", "tipo_veiculo": "moto", "preco": PRECO}
    assert api.post("/api/categorias/", nova, format="json").status_code == 201
    assert _feitos(moto)["precos"] == "2026-10-07"


def _so_preco_agendado() -> None:
    """As categorias do seed saem; fica uma só, com preço a partir de 01 nov."""
    Categoria.objects.update(ativo=False)
    trilha = Categoria.objects.create(nome="Trilha 250", tipo_veiculo="moto")
    PrecoCategoria.objects.create(categoria=trilha, vigente_desde=date(2026, 11, 1), **PRECO)


def test_imp_07_precos_agendado_marca_na_data(moto_rapida, relogio):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    _so_preco_agendado()
    api = moto.api("Mariana")
    assert api.get(IMPLANTACAO).status_code == 200
    assert api.get("/api/configuracoes/").status_code == 200
    assert "precos" not in _feitos(moto)

    relogio.em("2026-11-01 08:00")
    moto._tokens.clear()
    passos = moto.api("Mariana").get(IMPLANTACAO).json()["passos"]
    assert next(p for p in passos if p["passo"] == "precos")["feito_em"] == "2026-11-01"


def test_imp_07_precos_agendado_marca_pela_configuracoes(moto_rapida, relogio):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    _so_preco_agendado()
    relogio.em("2026-11-01 08:00")
    moto._tokens.clear()
    assert moto.api("Mariana").get("/api/configuracoes/").status_code == 200
    assert _feitos(moto)["precos"] == "2026-11-01"


def test_imp_07_precos_de_categoria_inativa_nao_marca(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    Categoria.objects.update(ativo=False)
    assert moto.api("Mariana").get(IMPLANTACAO).status_code == 200
    assert "precos" not in _feitos(moto)


def test_imp_07_equipe_marca_no_primeiro_convite(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    centro = moto_rapida.frota.centro
    corpo = {"email": "novo@motorapida.com.br", "perfil": "vendedor", "filiais": [centro.pk]}
    resposta = moto.api("Mariana").post("/api/usuarios/convites/", corpo, format="json")
    assert resposta.status_code == 201, resposta.json()
    assert _feitos(moto)["equipe"] == "2026-10-07"  # mesmo sem aceite


def test_imp_07_convite_do_administrador_da_compra_nao_marca_equipe(moto_rapida):  # noqa: F811
    from apps.contas import services as contas

    moto = moto_rapida.moto
    _passos(moto, "conta")
    contas.convidar_administrador("Dona Nova", "dona@motorapida.com.br")
    assert "equipe" not in _feitos(moto)


def test_imp_07_filial_marca_na_matriz(moto_rapida):  # noqa: F811
    from apps.filiais import services as filiais

    moto = moto_rapida.moto
    _passos(moto, "conta")
    campos = {
        "nome": "Filial Caucaia",
        "endereco": {
            "cep": "61600000",
            "logradouro": "Rua A",
            "numero": "1",
            "bairro": "Centro",
            "cidade": "Caucaia",
            "uf": "CE",
        },
        "horario": HORARIO_CENTRO,
    }
    mariana = moto.pessoas["Mariana"]
    filiais.criar_filial(campos, mariana)
    assert "filial" not in _feitos(moto)  # já há matriz: a nova não é a primeira filial

    filiais.criar_filial({**campos, "nome": "Filial Maracanaú", "matriz": True}, mariana)
    assert "filial" in _feitos(moto)


def test_imp_07_desfazer_nao_desmarca(moto_rapida):  # noqa: F811
    moto = moto_rapida.moto
    _passos(moto, "conta")
    api = moto.api("Mariana")
    nova = {"nome": "Trilha 250", "tipo_veiculo": "moto", "preco": PRECO}
    assert api.post("/api/categorias/", nova, format="json").status_code == 201
    Categoria.objects.update(ativo=False)  # inativar depois não desmarca
    assert api.get(IMPLANTACAO).status_code == 200
    assert "precos" in _feitos(moto)
