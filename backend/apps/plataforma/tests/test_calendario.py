"""Calendário das faturas da assinatura (PLT-01, PLT-14): funções puras, sem banco."""

from datetime import date

import pytest

from apps.plataforma.calendario import descricao_da_fatura, proximo_periodo, vencimento_seguinte


def test_plt_01_periodo_da_primeira_fatura_da_moto_rapida():
    periodo = proximo_periodo(22, "mensal", date(2026, 10, 22))
    assert (periodo.inicio, periodo.fim, periodo.competencia) == (
        date(2026, 10, 22),
        date(2026, 11, 21),
        date(2026, 10, 1),
    )


def test_plt_01_mes_sem_o_dia_vence_no_ultimo_e_volta():
    """CA-ASS-08: dia 31 → 31 jan, 28 fev, 31 mar."""
    assert vencimento_seguinte(31, "mensal", date(2027, 1, 31)) == date(2027, 2, 28)
    assert vencimento_seguinte(31, "mensal", date(2027, 2, 28)) == date(2027, 3, 31)
    assert proximo_periodo(31, "mensal", date(2027, 2, 28)).fim == date(2027, 3, 30)
    assert vencimento_seguinte(31, "mensal", date(2028, 1, 31)) == date(2028, 2, 29)


def test_plt_01_virada_do_ano():
    assert proximo_periodo(22, "mensal", date(2026, 12, 22)).fim == date(2027, 1, 21)


def test_plt_01_anual_ate_a_vespera_do_mesmo_dia():
    """CA-ASS-09: o anual cobre do vencimento até a véspera do mesmo dia no ano seguinte."""
    periodo = proximo_periodo(22, "anual", date(2026, 10, 22))
    assert periodo.fim == date(2027, 10, 21)
    assert proximo_periodo(29, "anual", date(2028, 2, 29)).fim == date(2029, 2, 27)


def test_plt_01_dia_de_vencimento_fora_de_1_a_31():
    with pytest.raises(ValueError):
        proximo_periodo(0, "mensal", date(2026, 10, 22))


@pytest.mark.parametrize(
    ("tipo", "ciclo", "inicio", "fim", "texto"),
    [
        (
            "mensalidade",
            "mensal",
            date(2026, 10, 22),
            date(2026, 11, 21),
            "Plano Profissional · 22 out a 21 nov",
        ),
        (
            "mensalidade",
            "mensal",
            date(2026, 12, 22),
            date(2027, 1, 21),
            "Plano Profissional · 22 dez a 21 jan",
        ),
        (
            "mensalidade",
            "anual",
            date(2026, 10, 22),
            date(2027, 10, 21),
            "Plano Profissional anual · out 2026 a out 2027",
        ),
        (
            "diferenca_plano",
            "mensal",
            date(2026, 11, 1),
            date(2026, 11, 21),
            "Mudança para o plano Profissional · 01 a 21 nov",
        ),
    ],
)
def test_plt_14_descricao_da_fatura(tipo, ciclo, inicio, fim, texto):
    assert descricao_da_fatura(tipo, "Profissional", ciclo, inicio, fim) == texto
