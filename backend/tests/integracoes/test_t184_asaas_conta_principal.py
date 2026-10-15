"""T-184 · `asaas.py` na conta principal (assinatura, ADR 0023), contra respostas gravadas.

Sem rede, sem chave e sem banco. O formato do `creditCard` na consulta da cobrança paga na
página do parceiro segue a documentação do Asaas e ainda precisa ser conferido no sandbox
(ADR 0023, item 4).
"""

from datetime import date

import pytest

from integracoes.pagamentos import conta_principal
from integracoes.pagamentos.base import CartaoRecusado, Endereco, Pagador, PedidoCobranca

from .gravacao import CHAVE_PRINCIPAL, asaas

CENTRO = Endereco("60325000", "Av. Bezerra de Menezes", "1200", "São Gerardo", "Fortaleza", "CE")
MOTO_RAPIDA = Pagador(
    "Moto Rápida Locações Ltda",
    "12345678000195",
    email="mariana@motorapida.com.br",
    endereco=CENTRO,
)


def test_plt_15_asaas_pagador_da_empresa_na_conta_principal():
    provedor, gravacao = asaas("t184_pagador_novo")
    assert provedor.criar_ou_atualizar_pagador(conta_principal(), MOTO_RAPIDA) == (
        "cus_000000000901"
    )
    corpo = gravacao.corpo("POST", "/customers")
    assert corpo["notificationDisabled"] is True  # as mensagens da assinatura são do Giro
    assert (corpo["cpfCnpj"], corpo["email"], corpo["postalCode"], corpo["province"]) == (
        "12345678000195",
        "mariana@motorapida.com.br",
        "60325000",
        "São Gerardo",
    )
    # Conta principal: a chave do ambiente, nunca a de uma subconta.
    assert gravacao.feitas[0]["chave"] == CHAVE_PRINCIPAL
    gravacao.conferir_fim()


def test_plt_15_asaas_pagador_atualizado_pelo_id():
    provedor, gravacao = asaas("t184_pagador_atualizado")
    pagador = Pagador(
        "Moto Rápida Locações Ltda",
        "12345678000195",
        email="financeiro@motorapida.com.br",
        id_externo="cus_000000000901",
    )
    assert provedor.criar_ou_atualizar_pagador(conta_principal(), pagador) == "cus_000000000901"
    assert gravacao.corpo("POST", "/customers/cus_000000000901")["email"] == (
        "financeiro@motorapida.com.br"
    )
    gravacao.conferir_fim()


def test_plt_13_asaas_cartao_so_na_pagina_do_parceiro(relogio):
    provedor, gravacao = asaas("t184_fatura_no_cartao_pela_pagina")
    pedido = PedidoCobranca(
        "cartao_link",
        44900,
        date(2026, 10, 22),
        "fatura-1",
        Pagador("Moto Rápida Locações Ltda", id_externo="cus_000000000901"),
    )
    cobranca = provedor.criar_cobranca(conta_principal(), pedido)
    assert cobranca.url_pagina == "https://sandbox.asaas.com/i/t184fat0001"
    corpo = gravacao.corpo("POST", "/payments")
    assert corpo["billingType"] == "CREDIT_CARD"
    assert corpo["customer"] == "cus_000000000901"  # o pagador já criado, sem procurar de novo
    # ADR 0023: nenhum dado de cartão sai do Giro.
    assert not {"creditCard", "creditCardHolderInfo", "creditCardToken"} & set(corpo)
    gravacao.conferir_fim()


def test_plt_13_asaas_pago_na_pagina_devolve_o_cartao_guardado(relogio):
    provedor, gravacao = asaas("t184_fatura_paga_no_cartao")
    situacao = provedor.consultar_cobranca(conta_principal(), "pay_t184fat0001")
    assert (situacao.status, situacao.forma, situacao.valor_pago_centavos) == (
        "paga",
        "cartao",
        44900,
    )
    assert situacao.cartao is not None
    assert (situacao.cartao.bandeira, situacao.cartao.final) == ("visa", "4242")
    assert situacao.cartao.token == "tok-ficticio-0000-t184"
    assert "tok-ficticio" not in repr(situacao)  # o token não aparece em log nem em repr
    gravacao.conferir_fim()


def test_plt_02_asaas_cobra_no_cartao_salvo(relogio):
    provedor, gravacao = asaas("t184_cartao_salvo_cobrado")
    pedido = PedidoCobranca(
        "cartao",
        44900,
        date(2026, 11, 22),
        "fatura-2",
        Pagador("Moto Rápida Locações Ltda", id_externo="cus_000000000901"),
    )
    cobranca = provedor.cobrar_cartao_salvo(conta_principal(), "tok-ficticio-0000-t184", pedido)
    assert (cobranca.id, cobranca.tipo, cobranca.valor_centavos) == (
        "pay_t184fat0002",
        "cartao",
        44900,
    )
    corpo = gravacao.corpo("POST", "/payments")
    assert (corpo["billingType"], corpo["creditCardToken"]) == (
        "CREDIT_CARD",
        "tok-ficticio-0000-t184",
    )
    gravacao.conferir_fim()


def test_plt_02_asaas_cartao_salvo_recusado(relogio):
    provedor, gravacao = asaas("t184_cartao_salvo_recusado")
    pedido = PedidoCobranca(
        "cartao",
        44900,
        date(2026, 11, 22),
        "fatura-2",
        Pagador("Moto Rápida Locações Ltda", id_externo="cus_000000000901"),
    )
    with pytest.raises(CartaoRecusado, match="não autorizada"):
        provedor.cobrar_cartao_salvo(conta_principal(), "tok-ficticio-0000-t184", pedido)
    gravacao.conferir_fim()
