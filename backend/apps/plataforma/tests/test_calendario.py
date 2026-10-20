"""Calendário das faturas da assinatura (PLT-01, PLT-14) e do cancelamento e da pausa (PLT-06,
AUD-08): funções puras, sem banco."""

from datetime import date, timedelta

import pytest

from apps.plataforma.calendario import (
    DIAS_ATE_APAGAR,
    DIAS_DO_AVISO_DO_APAGAMENTO,
    datas_do_cancelamento,
    descricao_da_fatura,
    periodo_da_pausa,
    proximo_periodo,
    vencimento_seguinte,
)


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


# --- Cancelar e pausar (PLT-06, AUD-08; cancelamento.md) ---


@pytest.mark.parametrize(
    ("caso", "hoje", "status", "fim_pago", "acesso_ate", "cancelada_em", "apagar_em"),
    [
        # (a) em teste, 1ª fatura em aberto, cancela em 10 out
        ("a", date(2026, 10, 10), "em_teste", None, date(2026, 10, 21), date(2026, 10, 22),
         date(2027, 1, 20)),
        # (b) ativa, FAT-0001 paga, cancela em 05 nov
        ("b", date(2026, 11, 5), "ativa", date(2026, 11, 21), date(2026, 11, 21),
         date(2026, 11, 22), date(2027, 2, 20)),
        # (c) inadimplente com a FAT-0001 atrasada, cancela em 25 out: na hora
        ("c", date(2026, 10, 25), "inadimplente", None, None, date(2026, 10, 25),
         date(2027, 1, 23)),
        # (d) em teste com a FAT-0001 paga em 12 out, cancela em 15 out: o período pago vence
        ("d", date(2026, 10, 15), "em_teste", date(2026, 11, 21), date(2026, 11, 21),
         date(2026, 11, 22), date(2027, 2, 20)),
    ],
)  # fmt: skip
def test_plt_06_datas_do_cancelamento_da_moto_rapida(
    caso, hoje, status, fim_pago, acesso_ate, cancelada_em, apagar_em
):
    datas = datas_do_cancelamento(hoje, status, date(2026, 10, 21), fim_pago)
    assert (datas.acesso_ate, datas.cancelada_em, datas.apagar_em) == (
        acesso_ate,
        cancelada_em,
        apagar_em,
    ), caso


def test_plt_06_cancelar_anual_sem_devolucao_vai_ate_o_fim_do_ano_pago():
    """CA-ASS-33: anual de 22 out 2026 a 21 out 2027, cancela em 05 nov 2026."""
    datas = datas_do_cancelamento(date(2026, 11, 5), "ativa", None, date(2027, 10, 21))
    assert datas.acesso_ate == date(2027, 10, 21)
    assert datas.cancelada_em == date(2027, 10, 22)


@pytest.mark.parametrize("status", ["suspensa", "pausada"])
def test_plt_06_suspensa_e_pausada_cancelam_na_hora(status):
    datas = datas_do_cancelamento(date(2026, 12, 10), status, None, date(2026, 11, 21))
    assert datas.acesso_ate is None
    assert datas.cancelada_em == date(2026, 12, 10)


def test_plt_06_acesso_que_ja_acabou_termina_agora():
    """Ativa no dia do vencimento, com a fatura do período ainda sem pagar: o período pago acabou
    ontem, então o acesso termina agora (vira `cancelada` hoje, como a tela diz)."""
    datas = datas_do_cancelamento(date(2026, 11, 22), "ativa", None, date(2026, 11, 21))
    assert (datas.acesso_ate, datas.cancelada_em) == (None, date(2026, 11, 22))


def test_aud_08_aviso_7_dias_antes_e_apagamento_no_90_dia():
    assert DIAS_ATE_APAGAR == 90
    datas = datas_do_cancelamento(date(2026, 10, 10), "em_teste", date(2026, 10, 21), None)
    assert datas.apagar_em - timedelta(days=DIAS_DO_AVISO_DO_APAGAMENTO) == date(2027, 1, 13)


@pytest.mark.parametrize(
    ("inicio", "meses", "ate"),
    [
        (date(2026, 11, 22), 2, date(2027, 1, 21)),  # Pausa da Moto Rápida
        (date(2026, 11, 22), 1, date(2026, 12, 21)),
        (date(2026, 11, 22), 3, date(2027, 2, 21)),
        (date(2027, 1, 31), 1, date(2027, 2, 27)),  # fevereiro sem o dia 31 (PLT-01)
    ],
)
def test_plt_06_periodo_da_pausa(inicio, meses, ate):
    periodo = periodo_da_pausa(inicio, meses)
    assert (periodo.inicio, periodo.fim) == (inicio, ate)


@pytest.mark.parametrize("meses", [0, 4])
def test_plt_06_pausar_por_ate_3_meses(meses):
    with pytest.raises(ValueError):
        periodo_da_pausa(date(2026, 11, 22), meses)
