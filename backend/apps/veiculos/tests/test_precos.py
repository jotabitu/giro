"""Cálculo dos preços do veículo, sem banco (VEI-13, VEI-16; ADR 0041, item 4).

Os casos são os de `docs/regras/dados-de-teste.md`: "Locação com compra da Pop 110i TBC-5H21",
"Parcela da Pop 110i nas 4 periodicidades", "Parcela digitada da Pop 110i" e "Locação com compra
da CG QXA-4B21". O "recebe pela moto" usa a parcela arredondada (padrão A do ponto em aberto
"Arredondamento do recebe pela moto": Pop R$ 17.768,96).
"""

from decimal import Decimal

import pytest

from apps.veiculos import precos

POP = {
    "valor_venda": 1590000,
    "entrada": 100000,
    "parcelas": 104,
    "periodicidade": "semanal",
    "modo": "calcular",
    "juros_mes_pct": Decimal("1.00"),
    "parcela_digitada": 0,
    "adicional": 2977,  # R$ 129,00 por mês × 24 ÷ 104
    "pago_na_moto": 1380000,  # compra 13.490,00 + despesas 310,00
}


def test_vei_16_pop_semanal_104() -> None:
    resultado = precos.simular_compra(**POP)  # type: ignore[arg-type]
    assert resultado.financiado_centavos == 1490000
    assert resultado.meses_do_prazo == Decimal("24.00")
    assert resultado.taxa_periodo_pct == Decimal("0.23")
    assert resultado.parcela_moto_centavos == 16124
    assert resultado.parcela_cliente_centavos == 19101
    assert resultado.recebe_pela_moto_centavos == 1776896
    assert resultado.lucro_centavos == 396896
    assert resultado.juros_no_prazo_centavos == 186896
    assert resultado.margem_sobre_pago_pct == Decimal("28.76")  # 28,8% na tela
    # A barra do recebe pela moto: 13.800,00 ÷ 17.768,96 = 77,66% pago e 22,34% lucro.
    assert resultado.pago_sobre_recebe_pct == Decimal("77.66")
    assert resultado.lucro_sobre_recebe_pct == Decimal("22.34")
    assert resultado.venda_abaixo_do_pago is False
    assert resultado.pede_confirmacao_juros is False


def test_vei_16_parcela_nas_4_periodicidades_pop() -> None:
    resultado = precos.simular_compra(**POP)  # type: ignore[arg-type]
    assert [
        (p.periodicidade, p.parcelas, p.parcela_cliente_centavos)
        for p in resultado.nas_periodicidades
    ] == [
        ("diaria", 730, 2719),
        ("semanal", 104, 19101),
        ("quinzenal", 52, 38239),
        ("mensal", 24, 83039),
    ]


def test_vei_16_digitar_170_acha_1_46() -> None:
    resultado = precos.simular_compra(**{**POP, "modo": "digitar", "parcela_digitada": 17000})  # type: ignore[arg-type]
    assert resultado.juros_mes_pct == Decimal("1.46")
    assert resultado.parcela_moto_centavos == 17000
    assert resultado.pede_confirmacao_juros is True


def test_vei_16_digitar_parcela_que_nao_cobre_a_venda() -> None:
    with pytest.raises(precos.ParcelaNaoCobre, match=r"A parcela não cobre o valor de venda\."):
        precos.simular_compra(**{**POP, "modo": "digitar", "parcela_digitada": 14000})  # type: ignore[arg-type]


def test_vei_16_cg_venda_abaixo_do_pago() -> None:
    resultado = precos.simular_compra(
        valor_venda=1248000,
        entrada=0,
        parcelas=104,
        periodicidade="semanal",
        modo="calcular",
        juros_mes_pct=Decimal("1.00"),
        parcela_digitada=0,
        adicional=0,
        pago_na_moto=1390000,
    )
    assert resultado.parcela_moto_centavos == 13505
    assert resultado.recebe_pela_moto_centavos == 1404520
    assert resultado.lucro_centavos == 14520
    assert resultado.margem_sobre_pago_pct == Decimal("1.04")  # 1,0% na tela
    assert resultado.venda_abaixo_do_pago is True


def test_vei_16_juros_zero_divide_o_financiado() -> None:
    resultado = precos.simular_compra(**{**POP, "juros_mes_pct": Decimal("0")})  # type: ignore[arg-type]
    assert resultado.parcela_moto_centavos == 14327  # 14.900,00 ÷ 104 = 143,269...


def test_vei_16_meses_do_prazo_iguais() -> None:
    for parcelas, periodicidade in ((104, "semanal"), (52, "quinzenal"), (730, "diaria")):
        assert precos.meses_do_prazo(parcelas, periodicidade) == Decimal(24)
    assert precos.meses_do_prazo(24, "mensal") == Decimal(24)


def test_vei_16_simular_alerta_da_venda_e_dos_juros() -> None:
    entrada = precos.Entrada(
        valor_venda=1248000,
        pago_na_moto=1390000,
        custos=precos.Custos(),
        planos=[],
        compra=precos.Compra(
            ligado=True,
            periodicidade="semanal",
            parcelas=104,
            entrada=0,
            juros_mes_pct=Decimal("1.50"),
            modo="calcular",
            parcela_digitada=0,
            adicional=0,
        ),
    )
    resultado = precos.simular(entrada)
    assert [a["codigo"] for a in resultado.alertas] == ["venda_abaixo_do_pago", "VEI-16"]
    assert resultado.alertas[0]["mensagem"] == precos.ALERTA_VENDA_ABAIXO
    assert resultado.pede_confirmacao_juros is True


def test_vei_13_custo_receita_e_margem() -> None:
    """Custo: 100 + 80 + 1.200 ÷ 12 + 50 + (13.800 − 9.000) ÷ 24 = R$ 530,00 por mês. Semanal
    R$ 329,00 a 85%: 329 × 52 ÷ 12 × 0,85 = R$ 1.211,82; lucro R$ 681,82; margem 56,26%."""
    custo = precos.custo_mes(
        manutencao_mes=10000,
        seguro_mes=8000,
        rastreador_mes=5000,
        ipva_ano=120000,
        pago_na_moto=1380000,
        revenda_estimada=900000,
    )
    assert custo == Decimal(53000)
    margem = precos.margem(32900, "semana", Decimal("85.00"), custo, Decimal("60.00"))
    assert margem is not None
    assert margem.receita_mes_centavos == 121182
    assert margem.lucro_mes_centavos == 68182
    assert margem.margem_pct == Decimal("56.26")
    assert margem.abaixo_da_minima is True


def test_vei_13_sem_ocupacao_nao_calcula_margem() -> None:
    assert precos.margem(32900, "semana", None, Decimal(0)) is None


def test_vei_13_sem_revenda_sem_desvalorizacao() -> None:
    custo = precos.custo_mes(
        manutencao_mes=0,
        seguro_mes=0,
        rastreador_mes=0,
        ipva_ano=0,
        pago_na_moto=1380000,
        revenda_estimada=None,
    )
    assert custo == 0


def test_vei_13_valor_em_mes_por_periodo() -> None:
    assert precos.receita_mes(4490, "dia", Decimal(100)) == Decimal(134700)
    assert precos.receita_mes(99000, "mes", Decimal(50)) == Decimal(49500)
