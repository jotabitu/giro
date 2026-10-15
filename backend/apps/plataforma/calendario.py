"""Datas e descrições das faturas da assinatura (PLT-01, PLT-14). Funções puras, sem banco.

- Cada fatura cobre do vencimento até a véspera do vencimento seguinte; o anual, do vencimento até
  a véspera do mesmo dia no ano seguinte.
- `dia_vencimento` (1 a 31) é o da empresa. Em mês sem esse dia, vence no último dia do mês, e no
  mês seguinte volta ao `dia_vencimento` (CA-ASS-08: 31 jan, 28 fev, 31 mar).
- `competencia` é o dia 1 do mês do início do período.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
MENSAL = "mensal"
ANUAL = "anual"


@dataclass(frozen=True)
class Periodo:
    inicio: date  # = vencimento da fatura
    fim: date

    @property
    def competencia(self) -> date:
        return self.inicio.replace(day=1)


def vencimento_no_mes(ano: int, mes: int, dia_vencimento: int) -> date:
    """O `dia_vencimento` naquele mês, ou o último dia do mês se ele não tiver esse dia."""
    return date(ano, mes, min(dia_vencimento, calendar.monthrange(ano, mes)[1]))


def vencimento_seguinte(dia_vencimento: int, ciclo: str, vencimento: date) -> date:
    meses = 12 if ciclo == ANUAL else 1
    indice = vencimento.year * 12 + vencimento.month - 1 + meses
    return vencimento_no_mes(indice // 12, indice % 12 + 1, dia_vencimento)


def proximo_periodo(dia_vencimento: int, ciclo: str, inicio: date) -> Periodo:
    """O período da fatura que vence em `inicio` (PLT-01)."""
    if not 1 <= dia_vencimento <= 31:
        raise ValueError(f"Dia de vencimento fora de 1 a 31: {dia_vencimento}")
    return Periodo(inicio, vencimento_seguinte(dia_vencimento, ciclo, inicio) - timedelta(days=1))


def dia_e_mes(dia: date) -> str:
    """22 out."""
    return f"{dia.day:02d} {MESES[dia.month - 1]}"


def intervalo(inicio: date, fim: date) -> str:
    """ "22 out a 21 nov"; no mesmo mês, "01 a 21 nov". Sem o ano (PLT-14)."""
    if (inicio.year, inicio.month) == (fim.year, fim.month):
        return f"{inicio.day:02d} a {dia_e_mes(fim)}"
    return f"{dia_e_mes(inicio)} a {dia_e_mes(fim)}"


def descricao_da_fatura(tipo: str, plano: str, ciclo: str, inicio: date, fim: date) -> str:
    """A descrição da fatura na tabela da `Admin-Assinatura` (PLT-14)."""
    if tipo == "diferenca_plano":
        return f"Mudança para o plano {plano} · {intervalo(inicio, fim)}"
    if ciclo == ANUAL:
        de = f"{MESES[inicio.month - 1]} {inicio.year}"
        ate = f"{MESES[fim.month - 1]} {fim.year}"
        return f"Plano {plano} anual · {de} a {ate}"
    return f"Plano {plano} · {intervalo(inicio, fim)}"
