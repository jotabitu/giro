"""T-029 · `asaas.py` contra as respostas gravadas do Asaas (docs/qa/criterios/T-029.md).

Testes de contrato: sem rede, sem chave e sem banco; rodam no CI. Os mesmos casos contra o
sandbox ficam em `test_t029_asaas_sandbox.py` (só local, com a chave no ambiente).
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from integracoes.pagamentos import CABECALHO_DO_TOKEN
from integracoes.pagamentos.asaas import EVENTOS_DO_WEBHOOK, _para_json, centavos, reais
from integracoes.pagamentos.base import (
    ContaPagamentoRef,
    DadosEmpresa,
    Pagador,
    ParceiroIndisponivel,
    ParceiroRecusou,
    PedidoCobranca,
    PedidoRecorrencia,
    StatusDesconhecido,
)

from .gravacao import CHAVE_DA_SUBCONTA, CHAVE_PRINCIPAL, asaas

FUSO = ZoneInfo("America/Sao_Paulo")
SUBCONTA = ContaPagamentoRef("4f468235-0000-4000-8000-000000000001", lambda: CHAVE_DA_SUBCONTA)
CARLOS = Pagador("Carlos Menezes", "25890144227", "85985554433", "")
RAFAEL = Pagador("Rafael Sousa", "32137710587", "85987651234", "")


def _pix_carlos(referencia: str = "9001") -> PedidoCobranca:
    return PedidoCobranca("pix", 30609, date(2026, 10, 7), referencia, CARLOS)


# --- Centavos exatos (CA-029-05) ---


@pytest.mark.parametrize(
    ("valor_centavos", "texto"),
    [(1, "0.01"), (10, "0.10"), (99, "0.99"), (30609, "306.09"), (134700, "1347.00")],
)
def test_fin_04_asaas_centavos_vao_e_voltam_sem_float(valor_centavos, texto):
    assert reais(valor_centavos) == Decimal(texto)
    enviado = _para_json({"value": reais(valor_centavos)}).decode()
    assert enviado == f'{{"value": {texto}}}'
    lido = json.loads(enviado, parse_float=Decimal)["value"]
    assert isinstance(lido, Decimal)
    assert centavos(lido) == valor_centavos


def test_fin_04_asaas_recusa_fracao_de_centavo():
    with pytest.raises(ValueError, match="fração"):
        centavos(Decimal("306.095"))


# --- Cobrança Pix e boleto (FIN-04) ---


def test_fin_04_asaas_pix_do_carlos_cria_o_pagador_sem_notificacoes(relogio):
    """CA-029-04 e CA-029-03: Pix de R$ 306,09 para 07 out, com o id da conta como referência;
    o Carlos é criado na subconta com as notificações do Asaas desligadas."""
    parceiro, gravacao = asaas("pix_carlos_cliente_novo")
    cobranca = parceiro.criar_cobranca(SUBCONTA, _pix_carlos())
    gravacao.conferir_fim()

    assert (cobranca.id, cobranca.tipo, cobranca.valor_centavos) == (
        "pay_t029carlos0001",
        "pix",
        30609,
    )
    assert cobranca.vencimento == date(2026, 10, 7)
    assert cobranca.pix_copia_e_cola.startswith("000201")
    assert (cobranca.linha_digitavel, cobranca.boleto_url) == ("", "")
    pagador = gravacao.corpo("POST", "/customers")
    assert pagador == {
        "name": "Carlos Menezes",
        "cpfCnpj": "25890144227",
        "mobilePhone": "85985554433",
        "notificationDisabled": True,
    }
    assert gravacao.feitas[0]["consulta"] == {"cpfCnpj": "25890144227"}
    pedido = gravacao.corpo("POST", "/payments")
    assert pedido == {
        "customer": "cus_000000000841",
        "billingType": "PIX",
        "value": Decimal("306.09"),
        "dueDate": "2026-10-07",
        "externalReference": "9001",
    }
    # Toda chamada da cobrança usa a chave da subconta, nunca a da conta principal.
    assert {f["chave"] for f in gravacao.feitas} == {CHAVE_DA_SUBCONTA}


def test_fin_04_asaas_pagador_reaproveitado_e_cobranca_anterior_cancelada(relogio):
    """CA-029-04 (o Carlos achado pelo CPF) e CA-029-16 (a cobrança aberta que ficou de uma
    tentativa anterior é cancelada antes da nova)."""
    parceiro, gravacao = asaas("pix_carlos_cliente_existente")
    cobranca = parceiro.criar_cobranca(SUBCONTA, _pix_carlos())
    gravacao.conferir_fim()
    assert cobranca.id == "pay_t029carlos0002"
    assert [f["metodo"] for f in gravacao.feitas] == ["GET", "GET", "DELETE", "POST", "GET"]
    assert gravacao.feitas[1]["consulta"] == {"externalReference": "9001", "status": "PENDING"}


def test_fin_04_asaas_boleto_do_rafael(relogio):
    """CA-029-06: boleto de 138517 com vencimento em 10 out, linha digitável e link."""
    parceiro, gravacao = asaas("boleto_rafael")
    pedido = PedidoCobranca("boleto", 138517, date(2026, 10, 10), "9002", RAFAEL)
    cobranca = parceiro.criar_cobranca(SUBCONTA, pedido)
    gravacao.conferir_fim()
    assert cobranca.linha_digitavel == "00190000090000000000000000000000100000000138517"
    assert cobranca.boleto_url.endswith("t029rafael0001")
    assert cobranca.pix_copia_e_cola == ""
    assert gravacao.corpo("POST", "/payments")["billingType"] == "BOLETO"
    assert gravacao.corpo("POST", "/payments")["value"] == Decimal("1385.17")


def test_fin_04_asaas_sem_pix_copia_e_cola_cancela_a_cobranca(relogio):
    """CA-029-16: nada fica pela metade no parceiro."""
    parceiro, gravacao = asaas("pix_qr_falha")
    with pytest.raises(ParceiroIndisponivel):
        parceiro.criar_cobranca(SUBCONTA, _pix_carlos())
    gravacao.conferir_fim()
    assert gravacao.feitas[-1]["metodo"] == "DELETE"


def test_fin_04_asaas_fora_do_ar(relogio):
    parceiro, gravacao = asaas("fora_do_ar")
    with pytest.raises(ParceiroIndisponivel):
        parceiro.criar_cobranca(SUBCONTA, _pix_carlos())
    gravacao.conferir_fim()


def test_fin_04_asaas_tempo_limite(relogio):
    """CA-029-16: sem resposta em 10 s vira `ParceiroIndisponivel`."""
    from integracoes.pagamentos import asaas as modulo

    assert modulo.TEMPO_LIMITE_SEGUNDOS <= 10

    def sem_resposta(*_):
        raise ParceiroIndisponivel("TimeoutError")

    parceiro = modulo.Asaas(url_base="https://asaas.teste/v3", transporte=sem_resposta)
    with pytest.raises(ParceiroIndisponivel):
        parceiro.consultar_cobranca(SUBCONTA, "pay_t029carlos0001")


def test_fin_04_asaas_cancelar_cobranca_ja_paga_nao_trava(caplog):
    """CA-029-07: o parceiro recusa cancelar a que foi paga; o webhook dela vira pendência."""
    parceiro, gravacao = asaas("cancelar_ja_paga")
    parceiro.cancelar_cobranca(SUBCONTA, "pay_t029carlos0001")
    gravacao.conferir_fim()


# --- Consultar (CA-029-08) ---


def test_fin_04_asaas_consultar_pix_pago_hoje(relogio):
    parceiro, _ = asaas("consultar_pix_pago")
    situacao = parceiro.consultar_cobranca(SUBCONTA, "pay_t029carlos0001")
    assert (situacao.status, situacao.valor_pago_centavos, situacao.forma) == ("paga", 30609, "pix")
    assert situacao.pago_em == relogio.agora


def test_fin_04_asaas_consultar_boleto_confirmado_ontem(relogio):
    parceiro, _ = asaas("consultar_boleto_confirmado_ontem")
    situacao = parceiro.consultar_cobranca(SUBCONTA, "pay_t029rafael0001")
    assert (situacao.status, situacao.valor_pago_centavos, situacao.forma) == (
        "paga",
        138517,
        "boleto",
    )
    assert situacao.pago_em == datetime(2026, 10, 6, tzinfo=FUSO)


@pytest.mark.parametrize(
    ("caso", "cobranca_id", "status"),
    [
        ("consultar_aguardando", "pay_t029carlos0001", "aguardando"),
        ("consultar_vencida", "pay_t029rafael0001", "vencida"),
        ("consultar_estornada", "pay_t029carlos0001", "estornada"),
        ("consultar_removida", "pay_t029carlos0001", "cancelada"),
    ],
)
def test_fin_04_asaas_consultar_situacoes(relogio, caso, cobranca_id, status):
    parceiro, _ = asaas(caso)
    assert parceiro.consultar_cobranca(SUBCONTA, cobranca_id).status == status


def test_fin_04_asaas_valor_pago_diferente_volta_como_pago(relogio):
    """CA-029-13: quem decide é o financeiro; a interface só diz o valor pago."""
    parceiro, _ = asaas("consultar_pago_300")
    situacao = parceiro.consultar_cobranca(SUBCONTA, "pay_t029carlos0001")
    assert (situacao.status, situacao.valor_pago_centavos) == ("paga", 30000)


def test_fin_04_asaas_status_desconhecido_e_erro(relogio):
    parceiro, _ = asaas("consultar_status_desconhecido")
    with pytest.raises(StatusDesconhecido):
        parceiro.consultar_cobranca(SUBCONTA, "pay_t029carlos0001")


# --- Subconta (CA-029-01, CA-029-02) ---


def _dados_moto_rapida(token: str = "t" * 43) -> DadosEmpresa:
    return DadosEmpresa(
        nome="Moto Rápida Locações Ltda",
        documento="12345678000195",
        email="financeiro@motorapida.exemplo",
        celular="85999990000",
        logradouro="Avenida Exemplo",
        numero="100",
        bairro="Centro",
        cep="60000000",
        faturamento_mensal_centavos=7420000,
        webhook_url="https://admin.giro.teste/api/webhooks/pagamentos/asaas/",
        webhook_token=token,
        tipo_empresa="limitada",
    )


def test_fin_04_asaas_criar_subconta_com_o_webhook():
    parceiro, gravacao = asaas("subconta_moto_rapida")
    token = "x" * 43
    subconta = parceiro.criar_subconta(_dados_moto_rapida(token))
    gravacao.conferir_fim()
    assert subconta.conta_externa_id == "4f468235-0000-4000-8000-000000000001"
    assert subconta.carteira_id == "c0c1688f-0000-4000-8000-000000000001"
    assert subconta.chave_api == "chave-ficticia-da-subconta-t029"
    assert subconta.chave_api not in repr(subconta)
    # A subconta é aberta pela conta principal.
    assert gravacao.feitas[0]["chave"] == CHAVE_PRINCIPAL
    corpo = gravacao.corpo("POST", "/accounts")
    assert corpo["cpfCnpj"] == "12345678000195"
    assert corpo["companyType"] == "LIMITED"
    assert corpo["incomeValue"] == Decimal("74200.00")
    (webhook,) = corpo["webhooks"]
    assert webhook["url"] == "https://admin.giro.teste/api/webhooks/pagamentos/asaas/"
    assert webhook["authToken"] == token
    assert len(webhook["authToken"]) >= 32
    assert webhook["events"] == EVENTOS_DO_WEBHOOK
    assert webhook["enabled"] is True


def test_fin_04_asaas_subconta_recusada_traz_o_motivo():
    parceiro, _ = asaas("subconta_recusada")
    with pytest.raises(ParceiroRecusou) as erro:
        parceiro.criar_subconta(_dados_moto_rapida())
    assert erro.value.mensagem == "O CPF/CNPJ informado é inválido."


@pytest.mark.parametrize(
    ("caso", "status"), [("subconta_aprovada", "aprovada"), ("subconta_em_analise", "pendente")]
)
def test_fin_04_asaas_situacao_da_subconta(caso, status):
    parceiro, gravacao = asaas(caso)
    assert parceiro.consultar_subconta(SUBCONTA) == status
    assert gravacao.feitas[0]["chave"] == CHAVE_DA_SUBCONTA


# --- Pix Automático (AUT-04, CA-029-09) ---


def test_aut_04_asaas_autorizacao_semanal_do_carlos(relogio):
    parceiro, gravacao = asaas("autorizacao_carlos")
    pedido = PedidoRecorrencia(
        referencia_externa="2841",
        frequencia="semanal",
        inicio=date(2026, 10, 14),
        valor_centavos=32900,
        primeira_cobranca_centavos=32900,
        pagador=CARLOS,
        descricao="Locação LOC-2841",
    )
    autorizacao = parceiro.criar_autorizacao_recorrente(SUBCONTA, pedido)
    gravacao.conferir_fim()
    assert (autorizacao.id, autorizacao.status) == (
        "a33047b1-0000-4000-8000-000000002841",
        "pendente",
    )
    assert autorizacao.pix_copia_e_cola.startswith("000201")
    corpo = gravacao.corpo("POST", "/pix/automatic/authorizations")
    assert corpo["frequency"] == "WEEKLY"
    assert corpo["value"] == Decimal("329.00")
    assert corpo["paymentCreationMode"] == "MANUAL"
    assert corpo["immediateQrCode"]["originalValue"] == Decimal("329.00")
    assert corpo["customerId"] == "cus_000000000841"


def test_aut_04_asaas_cobra_a_parcela_pela_autorizacao(relogio):
    parceiro, gravacao = asaas("cobrar_com_autorizacao")
    pedido = PedidoCobranca("pix", 32900, date(2026, 10, 21), "9010", CARLOS)
    cobranca = parceiro.cobrar_com_autorizacao(
        SUBCONTA, "a33047b1-0000-4000-8000-000000002841", pedido
    )
    gravacao.conferir_fim()
    assert (cobranca.id, cobranca.valor_centavos) == ("pay_t029carlos0010", 32900)
    corpo = gravacao.corpo("POST", "/payments")
    assert corpo["pixAutomaticAuthorizationId"] == "a33047b1-0000-4000-8000-000000002841"
    assert corpo["externalReference"] == "9010"


def test_aut_04_asaas_cancelar_autorizacao():
    parceiro, gravacao = asaas("cancelar_autorizacao")
    parceiro.cancelar_autorizacao(SUBCONTA, "a33047b1-0000-4000-8000-000000002841")
    gravacao.conferir_fim()


# --- Webhook (S-14) ---


def test_fin_04_asaas_webhook_le_o_evento_e_o_token():
    parceiro, _ = asaas()
    corpo = {
        "id": "evt_05b708f961d739ea7eba7e4db318f621&368604920",
        "event": "PAYMENT_RECEIVED",
        "dateCreated": "2026-10-07 10:05:00",
        "payment": {"id": "pay_t029carlos0001", "externalReference": "9001", "value": 306.09},
    }
    evento = parceiro.validar_webhook({CABECALHO_DO_TOKEN: "tok"}, json.dumps(corpo).encode())
    assert evento is not None
    assert (evento.provedor, evento.evento_id, evento.tipo) == (
        "asaas",
        "evt_05b708f961d739ea7eba7e4db318f621&368604920",
        "PAYMENT_RECEIVED",
    )
    assert (evento.cobranca_id, evento.referencia_externa, evento.token) == (
        "pay_t029carlos0001",
        "9001",
        "tok",
    )


@pytest.mark.parametrize("corpo", [b"", b"nao-e-json", b"{}", b'{"id": "evt_1", "event": "X"}'])
def test_fin_04_asaas_webhook_que_nao_e_aviso(corpo):
    parceiro, _ = asaas()
    assert parceiro.validar_webhook({CABECALHO_DO_TOKEN: "tok"}, corpo) is None


# --- Segredos (S-05) ---


def test_s_05_asaas_chave_e_cpf_fora_do_log(relogio, caplog):
    caplog.set_level(logging.DEBUG, logger="integracoes.pagamentos.asaas")
    parceiro, _ = asaas("pix_carlos_cliente_novo")
    parceiro.criar_cobranca(SUBCONTA, _pix_carlos())
    texto = caplog.text
    assert "/v3/customers" in texto
    assert CHAVE_DA_SUBCONTA not in texto
    assert "25890144227" not in texto
    assert CHAVE_DA_SUBCONTA not in repr(SUBCONTA)
    assert CHAVE_DA_SUBCONTA not in repr(parceiro)


def test_s_05_asaas_so_por_https():
    from integracoes.pagamentos.asaas import transporte_urllib

    with pytest.raises(ValueError, match="HTTPS"):
        transporte_urllib("GET", "http://asaas.teste/v3/payments", None, {})
