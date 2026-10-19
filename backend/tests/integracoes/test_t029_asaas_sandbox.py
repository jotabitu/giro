"""T-029 · `asaas.py` contra o sandbox do Asaas: só local, nunca no CI.

Pulam sem `GIRO_ASAAS_SANDBOX_CHAVE` no ambiente (a chave de uma conta de sandbox, que faz o
papel da subconta). A chave nunca entra em commit, log ou handoff. Para rodar:

    GIRO_ASAAS_SANDBOX_CHAVE=... pytest tests/integracoes/test_t029_asaas_sandbox.py -v

A abertura de subconta cria uma conta de verdade no sandbox: só com `GIRO_ASAAS_SANDBOX_SUBCONTA=1`
e a chave da conta principal do sandbox em `GIRO_ASAAS_SANDBOX_CHAVE_PRINCIPAL`.
"""

import os
import secrets
from datetime import date, timedelta

import pytest

from integracoes.pagamentos.asaas import URL_SANDBOX, Asaas
from integracoes.pagamentos.base import (
    ContaPagamentoRef,
    DadosEmpresa,
    Pagador,
    ParceiroRecusou,
    PedidoCobranca,
)

CHAVE = os.environ.get("GIRO_ASAAS_SANDBOX_CHAVE", "")
pytestmark = pytest.mark.skipif(not CHAVE, reason="sem GIRO_ASAAS_SANDBOX_CHAVE: só local")

# Dados fictícios do seed (CPFs com dígito válido, que não são de ninguém).
CARLOS = Pagador("Carlos Menezes", "25890144227", "85985554433", "")
RAFAEL = Pagador("Rafael Sousa", "32137710587", "85987651234", "")


@pytest.fixture
def parceiro() -> Asaas:
    return Asaas(url_base=os.environ.get("GIRO_ASAAS_URL", URL_SANDBOX), chave_principal="")


@pytest.fixture
def subconta() -> ContaPagamentoRef:
    return ContaPagamentoRef("sandbox", lambda: CHAVE)


def _referencia() -> str:
    return f"t029-{secrets.token_hex(4)}"


def test_fin_04_sandbox_pix_consultar_e_cancelar(parceiro, subconta):
    """CA-029-04, CA-029-05, CA-029-07, CA-029-08."""
    hoje = date.today()
    pedido = PedidoCobranca("pix", 30609, hoje, _referencia(), CARLOS)
    cobranca = parceiro.criar_cobranca(subconta, pedido)
    assert cobranca.valor_centavos == 30609
    assert cobranca.pix_copia_e_cola.startswith("000201")
    assert parceiro.consultar_cobranca(subconta, cobranca.id).status == "aguardando"

    # O mesmo pagador é reaproveitado pelo CPF, e a nova cobrança da mesma conta cancela a outra.
    segunda = parceiro.criar_cobranca(subconta, pedido)
    assert segunda.id != cobranca.id
    assert parceiro.consultar_cobranca(subconta, cobranca.id).status == "cancelada"
    parceiro.cancelar_cobranca(subconta, segunda.id)
    assert parceiro.consultar_cobranca(subconta, segunda.id).status == "cancelada"


@pytest.mark.parametrize("valor_centavos", [10, 99, 134700])
def test_fin_04_sandbox_centavos_exatos(parceiro, subconta, valor_centavos):
    # O Asaas pode recusar valores pequenos demais para boleto; Pix aceita a partir de centavos.
    pedido = PedidoCobranca("pix", valor_centavos, date.today(), _referencia(), CARLOS)
    try:
        cobranca = parceiro.criar_cobranca(subconta, pedido)
    except ParceiroRecusou as erro:
        pytest.skip(f"sandbox recusou o valor: {erro.mensagem}")
    assert cobranca.valor_centavos == valor_centavos
    parceiro.cancelar_cobranca(subconta, cobranca.id)


def test_fin_04_sandbox_boleto(parceiro, subconta):
    """CA-029-06."""
    vencimento = date.today() + timedelta(days=3)
    pedido = PedidoCobranca("boleto", 138517, vencimento, _referencia(), RAFAEL)
    cobranca = parceiro.criar_cobranca(subconta, pedido)
    assert cobranca.linha_digitavel
    assert cobranca.boleto_url.startswith("https://")
    assert cobranca.vencimento == vencimento
    parceiro.cancelar_cobranca(subconta, cobranca.id)


def test_fin_04_sandbox_boleto_com_o_pix(parceiro, subconta):
    """T-307, pontos 1 e 2 da T-305: o boleto traz o Pix pelo `pixQrCode` quando a conta tem
    chave Pix; sem chave, o parceiro recusa e o boleto sai sem ele, sem ser cancelado."""
    vencimento = date.today() + timedelta(days=5)
    pedido = PedidoCobranca("boleto", 138517, vencimento, _referencia(), RAFAEL)
    cobranca = parceiro.criar_cobranca(subconta, pedido)
    try:
        assert cobranca.linha_digitavel
        if not cobranca.pix_copia_e_cola:
            pytest.skip("a conta do sandbox não tem chave Pix: o boleto saiu sem o Pix")
        assert cobranca.pix_copia_e_cola.startswith("000201")
        _, qr = parceiro._chamar("GET", f"/payments/{cobranca.id}/pixQrCode", conta=subconta)
        # Com chave Pix, vale até depois do vencimento (não só até 23:59 do dia da emissão).
        assert str(qr["expirationDate"])[:10] >= vencimento.isoformat()
    finally:
        parceiro.cancelar_cobranca(subconta, cobranca.id)


@pytest.mark.skipif(
    os.environ.get("GIRO_ASAAS_SANDBOX_SUBCONTA") != "1", reason="cria uma conta no sandbox"
)
def test_fin_04_sandbox_criar_subconta():
    """CA-029-01. Dados fictícios; o CNPJ da Moto Rápida pode já existir no sandbox."""
    principal = Asaas(
        url_base=os.environ.get("GIRO_ASAAS_URL", URL_SANDBOX),
        chave_principal=os.environ["GIRO_ASAAS_SANDBOX_CHAVE_PRINCIPAL"],
    )
    dados = DadosEmpresa(
        nome="Moto Rápida Locações Ltda",
        documento="12345678000195",
        email=f"t029-{secrets.token_hex(4)}@motorapida.exemplo",
        celular="85999990000",
        logradouro="Avenida Exemplo",
        numero="100",
        bairro="Centro",
        cep="60110000",
        faturamento_mensal_centavos=7420000,
        webhook_url="https://admin.giro.exemplo/api/webhooks/pagamentos/asaas/",
        webhook_token=secrets.token_urlsafe(32),
        tipo_empresa="limitada",
    )
    try:
        subconta = principal.criar_subconta(dados)
    except ParceiroRecusou as erro:
        pytest.skip(f"sandbox recusou: {erro.mensagem}")
    assert subconta.conta_externa_id and subconta.chave_api
