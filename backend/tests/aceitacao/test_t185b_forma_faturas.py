"""T-185 (parte 2) · Forma de pagamento e faturas da assinatura (`docs/api/assinatura.md`;
PLT-02, PLT-13, PLT-14; ADR 0023).

Mais os requisitos 4 a 8 que a segurança deixou para a T-185 na revisão da T-189: token fora da
API (4), trocar de forma apaga o token (5), `pagar/` com `meio` não troca a forma (6), faturas
sempre da empresa da requisição (7) e os dados para pagar fora da auditoria (8). Os requisitos 1 a
3 estão em `test_t185_assinatura.py`, que também traz a empresa de teste.
"""

from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import transaction
from django_tenants.utils import schema_context

from apps.auditoria.models import EventoAuditoria
from apps.plataforma import services
from apps.plataforma.models import (
    FaturaAssinatura,
    FormaPagamentoAssinatura,
    StatusFormaPagamento,
)
from comum.models import WebhookRecebido
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.base import CartaoGuardado, EventoWebhook, ParceiroIndisponivel

from .test_t185_assinatura import (
    ASSINATURA,
    MotoRapida,
    _erro,
    _mudar,
    _rotas_que_escrevem_na_suspensa,
)

FORMA = "/api/assinatura/forma-pagamento/"
FATURAS = "/api/assinatura/faturas/"
FUSO = ZoneInfo("America/Sao_Paulo")
SUPORTE_NAO_MEXE = {"codigo": "PLT-07", "mensagem": "O suporte não mexe na assinatura da empresa"}
SO_ADMINISTRADOR = {"codigo": "permissao", "mensagem": "Só o administrador mexe na assinatura"}


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    yield MotoRapida(criar_empresa())
    pagamentos.limpar()


def _pagar(api: Any, codigo: str = "FAT-0001", meio: str | None = None) -> Any:
    corpo = {"meio": meio} if meio else {}
    return api.post(f"{FATURAS}{codigo}/pagar/", corpo, format="json")


def _forma(moto: MotoRapida) -> FormaPagamentoAssinatura:
    return FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)


def _baixar(cobranca_id: str, evento_id: str) -> str:
    """O pagamento no parceiro e o aviso da conta principal, como o webhook faz (T-184)."""
    pagamentos.simular_pagamento(cobranca_id)
    aviso = services.registrar_webhook_principal(
        EventoWebhook("asaas", evento_id, "PAYMENT_RECEIVED", cobranca_id, "", ""), {}
    )
    assert aviso is not None
    return services.processar_webhook_fatura(aviso.pk)


def _textos_da_auditoria(schema: str) -> str:
    with schema_context(schema):
        return " ".join(str(e.antes) + str(e.depois) for e in EventoAuditoria.objects.all())


# --- PUT /api/assinatura/forma-pagamento/ (PLT-13) ---


def test_plt_13_ca_ass_02_escolher_boleto_nao_muda_o_estado(moto):
    resposta = moto.api().put(FORMA, {"forma": "boleto"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {
        "forma_pagamento": {
            "forma": "boleto",
            "situacao": {
                "codigo": "ativa",
                "rotulo": "Boleto enviado por e-mail 5 dias antes",
                "tom": "sucesso",
            },
            "cartao": None,
            "prazo": None,
        },
        "proximo_passo": None,
    }
    corpo = moto.api().get(ASSINATURA).json()
    assert corpo["status"] == "em_teste"  # a forma não ativa a empresa (U1)
    assert corpo["teste"]["fim"] == "2026-10-21"
    for schema in ("public", moto.empresa.schema_name):
        with schema_context(schema):
            evento = EventoAuditoria.objects.get(acao="assinatura.forma_pagamento")
            assert (evento.antes, evento.depois) == ({"forma": None}, {"forma": "boleto"})


def test_plt_13_pix_automatico_e_a_troca_cancela_a_autorizacao(moto, relogio):
    api = moto.api()
    resposta = api.put(FORMA, {"forma": "pix_automatico"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["forma_pagamento"]["situacao"]["codigo"] == "aguardando_autorizacao"
    expira = datetime.fromisoformat(corpo["proximo_passo"]["expira_em"])
    assert corpo["proximo_passo"]["tipo"] == "autorizar_pix"
    assert corpo["proximo_passo"]["pix_copia_e_cola"].startswith("00020126")
    assert expira == relogio.agora + timedelta(hours=24)
    autorizacao = _forma(moto).autorizacao_externa_id
    assert pagamentos.autorizacoes[autorizacao].status == "pendente"
    assert len(pagamentos.pagadores) == 1  # o pagador nasce na conta principal

    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    assert pagamentos.autorizacoes[autorizacao].status == "cancelada"
    assert _forma(moto).autorizacao_externa_id == ""


def test_plt_13_ca_ass_11_cartao_na_primeira_fatura(moto):
    resposta = moto.api().put(FORMA, {"forma": "cartao"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["proximo_passo"] is None  # a 1ª fatura ainda sem cobrança
    situacao = resposta.json()["forma_pagamento"]["situacao"]
    assert situacao["rotulo"] == "Você cadastra o cartão ao pagar a primeira fatura."
    assert not pagamentos.cobrancas


def test_plt_13_ca_ass_26_troca_com_cobranca_emitida(moto, relogio):
    """A cobrança viva de outra forma é cancelada; com o cartão, volta a página dele."""
    api = moto.api()
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    relogio.em("2026-10-17 06:00")
    api = moto.api()
    boleto = _pagar(api).json()
    assert boleto["forma"] == "boleto"
    boleto_id = moto.fatura("FAT-0001").cobranca_externa_id
    resposta = api.put(FORMA, {"forma": "cartao"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    proximo = resposta.json()["proximo_passo"]
    assert proximo["tipo"] == "pagina_parceiro"
    assert proximo["fatura"] == "FAT-0001"
    assert proximo["url"].startswith("https://pagamentos.falso/pagar/")
    assert pagamentos.cobrancas[boleto_id].situacao.status == "cancelada"
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "cartao_link"
    assert fatura.cobranca_linha_digitavel == ""


def test_adr_0023_trocar_de_forma_apaga_o_token(moto):
    """Requisito 5: trocar de forma esquece o token, a bandeira e o final; um aviso atrasado
    do parceiro não regrava o cartão. Auditoria só com a forma antiga e a nova."""
    api = moto.api()
    assert api.put(FORMA, {"forma": "cartao"}, format="json").status_code == 200
    with transaction.atomic():
        services._guardar_cartao(moto.recarregar(), CartaoGuardado("tok_t185", "visa", "4242"))
    assert _forma(moto).cartao_token_cifrado_claro() == "tok_t185"
    corpo = api.get(ASSINATURA).json()["forma_pagamento"]
    assert corpo["cartao"] == {"bandeira": "visa", "final": "4242"}  # requisito 4
    assert "tok_t185" not in str(api.get(ASSINATURA).json())

    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    forma = _forma(moto)
    assert (forma.cartao_token_cifrado_claro(), forma.cartao_bandeira, forma.cartao_final) == (
        "",
        "",
        "",
    )
    with transaction.atomic():
        services._guardar_cartao(moto.recarregar(), CartaoGuardado("tok_atrasado", "visa", "1111"))
    assert _forma(moto).cartao_token_cifrado_claro() == ""
    for schema in ("public", moto.empresa.schema_name):
        assert "tok_" not in _textos_da_auditoria(schema)


def test_plt_13_forma_invalida_e_parceiro_fora(moto, monkeypatch):
    api = moto.api()
    assert api.put(FORMA, {"forma": "dinheiro"}, format="json").status_code == 400

    def fora(*_: Any) -> None:
        raise ParceiroIndisponivel()

    monkeypatch.setattr(pagamentos.PagamentosFalso, "criar_autorizacao_recorrente", fora)
    resposta = api.put(FORMA, {"forma": "pix_automatico"}, format="json")
    assert resposta.status_code == 503
    assert resposta.json()["codigo"] == "parceiro_indisponivel"
    assert _forma(moto).forma == ""  # nada gravado


# --- Faturas (PLT-14) ---


def test_plt_14_ca_ass_01_lista_da_moto_rapida_em_07_out(moto):
    resposta = moto.api().get(FATURAS)
    assert resposta.status_code == 200, resposta.json()
    fatura, teste = resposta.json()["resultados"]
    assert fatura == {
        "tipo": "fatura",
        "codigo": "FAT-0001",
        "vencimento": "2026-10-22",
        "descricao": "Plano Profissional · 22 out a 21 nov",
        "periodo": {"inicio": "2026-10-22", "fim": "2026-11-21"},
        "valor_centavos": 44900,
        "status": "aberta",
        "forma": None,
        "pago_em": None,
        "situacao": {"codigo": "sem_forma", "rotulo": "Sem forma de pagamento", "tom": "alerta"},
        "acoes": {"pagar": False, "recibo": False, "nota_fiscal": False},
    }
    assert teste == {
        "tipo": "teste",
        "codigo": None,
        "vencimento": "2026-10-07",
        "descricao": "Teste grátis de 14 dias",
        "periodo": {"inicio": "2026-10-07", "fim": "2026-10-21"},
        "valor_centavos": 0,
        "status": None,
        "forma": None,
        "pago_em": None,
        "situacao": {"codigo": "teste_ativo", "rotulo": "Ativo", "tom": "info"},
        "acoes": {"pagar": False, "recibo": False, "nota_fiscal": False},
    }
    assert resposta.json()["proximo"] is None
    so_abertas = moto.api().get(FATURAS, {"status": "aberta"}).json()["resultados"]
    assert [f["codigo"] for f in so_abertas] == ["FAT-0001"]  # sem a linha do teste
    assert moto.api().get(FATURAS, {"status": "vencida"}).status_code == 400


def test_plt_14_ca_ass_28_lista_depois_do_upgrade(moto, relogio):
    """FAT-0001 paga em 22 out pelo webhook (com o recibo do parceiro); upgrade em 01 nov; a
    lista de 05 nov traz a diferença em aberto e a FAT-0001 paga."""
    api = moto.api()
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    relogio.em("2026-10-17 06:00")
    _pagar(moto.api())
    relogio.em("2026-10-22 10:00")
    assert _baixar(moto.fatura("FAT-0001").cobranca_externa_id, "evt_t185_1") == "baixada"
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    assert _mudar(moto.api(), "Completo", valor=30484).status_code == 200
    relogio.em("2026-11-05 09:00")
    api = moto.api()
    diferenca, paga, teste = api.get(FATURAS).json()["resultados"]
    assert (diferenca["codigo"], diferenca["valor_centavos"], diferenca["status"]) == (
        "FAT-0002",
        30484,
        "aberta",
    )
    assert diferenca["descricao"] == "Mudança para o plano Completo · 01 a 21 nov"
    assert diferenca["acoes"]["pagar"] is True
    assert paga["situacao"] == {"codigo": "paga", "rotulo": "Paga em 22 out", "tom": "sucesso"}
    assert paga["forma"] == "boleto"
    assert paga["acoes"] == {"pagar": False, "recibo": True, "nota_fiscal": False}
    assert teste["situacao"]["codigo"] == "teste_concluido"
    detalhe = api.get(f"{FATURAS}FAT-0001/").json()
    assert detalhe["recibo_url"].startswith("https://pagamentos.falso/recibo/")
    assert detalhe["nota_fiscal"] is None  # emissão desligada até a T-197
    assert detalhe["cobranca"]["forma"] == "boleto"


def test_plt_02_situacao_do_cartao_recusado_e_da_atrasada(moto, relogio):
    FaturaAssinatura.objects.filter(empresa=moto.empresa).update(
        cartao_recusado_em=datetime(2026, 10, 22, 6, tzinfo=FUSO), tentativas_cartao=1
    )
    situacao = moto.api().get(FATURAS).json()["resultados"][0]["situacao"]
    assert situacao["rotulo"] == "Cartão recusado · nova tentativa amanhã"
    FaturaAssinatura.objects.filter(empresa=moto.empresa).update(
        tentativas_cartao=2, cartao_recusado_em=None
    )
    FaturaAssinatura._base_manager.filter(empresa=moto.empresa).update(status="atrasada")
    relogio.em("2026-11-03 09:00")
    item = moto.api().get(FATURAS).json()["resultados"][0]
    assert item["situacao"] == {"codigo": "atrasada", "rotulo": "12 dias atrasada", "tom": "perigo"}
    assert item["acoes"]["pagar"] is True  # atrasada sem forma: o corpo escolhe o meio


# --- POST /api/assinatura/faturas/{codigo}/pagar/ (PLT-14) ---


def test_plt_14_pagar_pela_forma_e_por_outro_meio(moto, relogio):
    api = moto.api()
    sem_forma = _pagar(api)
    assert sem_forma.status_code == 422
    assert _erro(sem_forma) == {
        "codigo": "sem_forma_pagamento",
        "mensagem": "Escolha a forma de pagamento antes.",
    }
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    boleto = _pagar(api)
    assert boleto.status_code == 200, boleto.json()
    assert boleto.json()["forma"] == "boleto"
    assert boleto.json()["linha_digitavel"]
    assert boleto.json()["vencimento"] == "2026-10-22"
    assert _pagar(api).json() == boleto.json()  # a mesma cobrança, não duas
    assert len(pagamentos.cobrancas) == 1
    # Requisito 6: pagar por outro meio não troca a forma; a antiga é cancelada.
    pix = _pagar(api, meio="pix")
    assert pix.status_code == 200
    assert pix.json()["pix_copia_e_cola"].startswith("00020126")
    assert [c.situacao.status for c in pagamentos.cobrancas.values()] == ["cancelada", "aguardando"]
    assert _forma(moto).forma == "boleto"
    assert _forma(moto).cartao_token_cifrado_claro() == ""


def test_plt_14_fatura_paga_nao_se_paga_de_novo(moto):
    api = moto.api()
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    _pagar(api)
    assert _baixar(moto.fatura("FAT-0001").cobranca_externa_id, "evt_t185_2") == "baixada"
    resposta = _pagar(api)
    assert resposta.status_code == 409
    assert _erro(resposta) == {
        "codigo": "fatura_nao_pagavel",
        "mensagem": "Esta fatura já foi paga ou cancelada.",
    }
    assert _pagar(api, meio="banana").status_code == 400


def test_plt_14_faturas_sempre_da_empresa_da_requisicao(moto, criar_empresa):
    """Requisito 7: `FAT-0001` existe nas duas; a rota só enxerga a da requisição."""
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81", nome_exibicao="Outra")
    api = moto.api()
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    assert _pagar(api).status_code == 200
    assert (
        FaturaAssinatura.objects.get(empresa=outra, codigo="FAT-0001").cobranca_externa_id is None
    )
    assert api.get(f"{FATURAS}FAT-0002/").status_code == 404
    assert _pagar(api, "FAT-0002").status_code == 404
    assert [f["codigo"] for f in api.get(FATURAS).json()["resultados"]] == ["FAT-0001", None]


def test_plt_14_dados_para_pagar_fora_da_auditoria(moto, relogio):
    """Requisito 8: linha digitável, Pix e página do parceiro só na resposta ao administrador."""
    api = moto.api()
    assert api.put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    boleto = _pagar(api).json()
    pix = _pagar(api, meio="pix").json()
    assert api.put(FORMA, {"forma": "cartao"}, format="json").status_code == 200
    pagina = moto.fatura("FAT-0001").cobranca_url_pagina
    for schema in ("public", moto.empresa.schema_name):
        textos = _textos_da_auditoria(schema)
        for segredo in (boleto["linha_digitavel"], pix["pix_copia_e_cola"], pagina):
            assert segredo and segredo not in textos
    assert moto.api("Rodrigo").get(FATURAS).status_code == 403


# --- Suspensa, suporte e perfis (requisitos 1 a 3 nas rotas da parte 2) ---


def test_plt_13_ca_ass_27_suspensa_escolhe_a_forma_e_paga(moto):
    moto.estado(status="suspensa")
    api = moto.api()
    assert api.get(FATURAS).json()["resultados"][0]["acoes"]["pagar"] is True
    assert _pagar(api, meio="pix").status_code == 200  # sem forma, pelo meio
    resposta = api.put(FORMA, {"forma": "boleto"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert _pagar(api).status_code == 200
    assert moto.recarregar().status == "suspensa"  # volta a ativa só com a baixa


@pytest.mark.parametrize("status", ["pausada", "cancelada"])
def test_plt_13_pausada_e_cancelada_nao_pagam_pela_tela(moto, status):
    moto.estado(status=status)
    api = moto.api()
    for resposta in (api.put(FORMA, {"forma": "boleto"}, format="json"), _pagar(api, meio="pix")):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "empresa_sem_operacao"
    assert not api.get(FATURAS).json()["resultados"][0]["acoes"]["pagar"]


def test_plt_13_excecao_da_suspensa_com_as_tres_rotas():
    """Requisito 2: a lista é exatamente a do contrato."""
    assert _rotas_que_escrevem_na_suspensa() == {
        ("api/assinatura/dados-fiscais/", "PATCH"),
        ("api/assinatura/forma-pagamento/", "PUT"),
        ("api/assinatura/faturas/<str:codigo>/pagar/", "POST"),
    }


@pytest.mark.parametrize("permissao", ["ver", "ver_editar"])
def test_plt_07_ca_ass_19_suporte_nao_paga_nem_troca_a_forma(moto, permissao):
    suporte = moto.suporte(permissao)
    for resposta in (
        suporte.put(FORMA, {"forma": "boleto"}, format="json"),
        suporte.post(f"{FATURAS}FAT-0001/pagar/", {"meio": "pix"}, format="json"),
    ):
        assert resposta.status_code == 403
        assert _erro(resposta) == SUPORTE_NAO_MEXE
    assert _forma(moto).forma == ""
    assert not pagamentos.cobrancas and not pagamentos.autorizacoes
    leitura = suporte.get(FATURAS)
    assert leitura.status_code == 200
    assert not leitura.json()["resultados"][0]["acoes"]["pagar"]
    assert suporte.get(f"{FATURAS}FAT-0001/").status_code == 200


@pytest.mark.parametrize("nome", ["Rodrigo", "Lúcia"])
def test_plt_13_ca_ass_19_forma_e_faturas_so_do_administrador(moto, nome):
    api = moto.api(nome)
    for resposta in (
        api.put(FORMA, {"forma": "boleto"}, format="json"),
        api.get(FATURAS),
        api.get(f"{FATURAS}FAT-0001/"),
        _pagar(api, meio="pix"),
    ):
        assert resposta.status_code == 403
        assert _erro(resposta) == SO_ADMINISTRADOR
    assert _forma(moto).status == StatusFormaPagamento.PENDENTE
    assert not WebhookRecebido.objects.exists()
