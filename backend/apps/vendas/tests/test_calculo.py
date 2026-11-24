"""Contas da venda, sem banco (`vendas.calculo`, ADR 0042, item 4).

Os números são os da VEN-0177 (`docs/regras/dados-de-teste.md`): CB 300F, tabela R$ 22.900,00,
desconto de 8%, entrada R$ 5.000,00 e 12 parcelas.
"""

from datetime import date
from decimal import Decimal

from apps.vendas import calculo

VEN_0177 = calculo.Entrada(
    preco_tabela_centavos=2290000,
    desconto_pct=Decimal("8.00"),
    forma="entrada_parcelas",
    entrada_centavos=500000,
    num_parcelas=12,
)


def test_ven_02_ven_0177_8_pct_21068():
    conta = calculo.calcular(VEN_0177)
    assert conta.desconto_centavos == 183200
    assert conta.preco_final_centavos == 2106800
    assert conta.precisa_aprovacao is True
    assert conta.erros == {}


def test_ven_04_ven_0177_12_x_1339():
    conta = calculo.calcular(VEN_0177)
    assert conta.saldo_centavos == 1606800
    assert (conta.parcela_centavos, conta.ultima_parcela_centavos) == (133900, 133900)
    assert conta.total_parcelas_centavos == 1606800


def test_fin_09_ven_0177_comissao_63204():
    assert calculo.calcular(VEN_0177).comissao_centavos == 63204


def test_ven_02_ate_5_pct_sem_aprovacao_e_desconto_aprovado_vira_o_limite():
    assert not calculo.calcular(calculo.Entrada(2290000, Decimal("5.00"))).precisa_aprovacao
    assert calculo.calcular(calculo.Entrada(2290000, Decimal("5.01"))).precisa_aprovacao
    aprovado = calculo.Entrada(2290000, Decimal("8.00"), desconto_aprovado_pct=Decimal("8.00"))
    assert not calculo.calcular(aprovado).precisa_aprovacao
    assert calculo.limite_efetivo(Decimal("3.00")) == Decimal("5.00")


def test_ven_02_desconto_arredonda_meio_centavo_para_cima():
    # 12.345 × 2,5% = 308,625 → 309
    assert calculo.calcular(calculo.Entrada(12345, Decimal("2.50"))).desconto_centavos == 309


def test_ven_04_diferenca_dos_centavos_na_ultima_parcela():
    conta = calculo.calcular(
        calculo.Entrada(1000000, forma="entrada_parcelas", entrada_centavos=0, num_parcelas=3)
    )
    assert (conta.parcela_centavos, conta.ultima_parcela_centavos) == (333333, 333334)
    assert conta.total_parcelas_centavos == 1000000


def test_ven_04_com_juros_a_parcela_da_tabela_price():
    conta = calculo.calcular(
        calculo.Entrada(
            2290000,
            Decimal("8.00"),
            forma="entrada_parcelas",
            entrada_centavos=500000,
            num_parcelas=12,
            juros_pct=Decimal("1.00"),
        )
    )
    # 16.068,00 × 0,01 ÷ (1 − 1,01^−12) = 1.427,622... → 1.427,62, igual nas 12
    assert (conta.parcela_centavos, conta.ultima_parcela_centavos) == (142762, 142762)
    assert conta.total_parcelas_centavos == 142762 * 12


def test_ven_03_a_vista_entrada_e_o_preco_final():
    conta = calculo.calcular(calculo.Entrada(2290000, Decimal("2.00"), forma="a_vista"))
    assert conta.entrada_centavos == conta.preco_final_centavos == 2244200
    assert (conta.saldo_centavos, conta.num_parcelas, conta.parcela_centavos) == (0, None, None)
    assert conta.completo


def test_ven_04_parcelas_de_2_a_24_e_entrada_menor_que_o_preco():
    erros = calculo.calcular(
        calculo.Entrada(2290000, forma="entrada_parcelas", entrada_centavos=500000, num_parcelas=25)
    ).erros
    assert erros == {"num_parcelas": ["Escolha de 2 a 24 parcelas."]}
    erros = calculo.calcular(
        calculo.Entrada(2290000, forma="entrada_parcelas", entrada_centavos=2290000, num_parcelas=2)
    ).erros
    assert erros == {"entrada_centavos": ["A entrada tem que ser menor que o preço final."]}


def test_ven_18_financiamento_recusado():
    conta = calculo.calcular(calculo.Entrada(2290000, forma="financiamento"))
    assert conta.erros == {"forma": ["O financiamento ainda não está disponível."]}
    assert not conta.completo


def test_ven_04_vencimentos_no_mesmo_dia_e_no_fim_do_mes():
    assert calculo.vencimentos(date(2026, 10, 7), 2) == [date(2026, 11, 7), date(2026, 12, 7)]
    assert calculo.vencimentos(date(2026, 1, 31), 3) == [
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]
    assert calculo.vencimentos(date(2026, 11, 30), 2)[-1] == date(2027, 1, 30)
