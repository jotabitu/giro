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


def dia_mes_e_ano(dia: date) -> str:
    """21 out 2027 (o anual leva o ano, PLT-14)."""
    return f"{dia_e_mes(dia)} {dia.year}"


# --- Cancelar e pausar (PLT-06, AUD-08; `cancelamento.md`) ---

DIAS_ATE_APAGAR = 90  # AUD-08: a partir do dia em que a empresa vira `cancelada`
DIAS_DO_AVISO_DO_APAGAMENTO = 7  # AUD-08: o aviso sai 7 dias antes
MESES_DE_PAUSA = (1, 2, 3)  # PLT-06
CANCELA_DEPOIS_DO_ACESSO = frozenset({"em_teste", "ativa"})


@dataclass(frozen=True)
class DatasDoCancelamento:
    acesso_ate: date | None  # último dia de acesso; nulo quando o acesso termina agora
    cancelada_em: date  # o dia em que a empresa vira `cancelada`
    apagar_em: date


def datas_do_cancelamento(
    hoje: date, status: str, teste_fim: date | None, fim_do_periodo_pago: date | None
) -> DatasDoCancelamento:
    """Cancelando hoje (PLT-06, AUD-08): o último dia de acesso, o dia em que a empresa vira
    `cancelada` e o do apagamento (+90 dias).

    - `em_teste`: até o fim do período pago, se a 1ª fatura já foi paga (caso (d)); senão, até o
      fim do teste (caso (a)).
    - `ativa`: até o fim do período pago, mensal ou anual, sem devolução (casos (b) e CA-ASS-33).
    - `inadimplente`, `suspensa`, `pausada`: termina agora (caso (c)).

    O acesso que já acabou (o fim do período pago ficou para trás) também termina agora."""
    acesso_ate: date | None = None
    if status in CANCELA_DEPOIS_DO_ACESSO:
        acesso_ate = fim_do_periodo_pago or (teste_fim if status == "em_teste" else None)
    if acesso_ate is not None and acesso_ate < hoje:
        acesso_ate = None
    cancelada_em = acesso_ate + timedelta(days=1) if acesso_ate is not None else hoje
    return DatasDoCancelamento(
        acesso_ate, cancelada_em, cancelada_em + timedelta(days=DIAS_ATE_APAGAR)
    )


def periodo_da_pausa(inicio: date, meses: int) -> Periodo:
    """De `inicio` (o dia seguinte ao fim do período pago) até a véspera do mesmo dia `meses`
    meses depois, com a regra do mês sem o dia da PLT-01 (22 nov + 2 meses: até 21 jan)."""
    if meses not in MESES_DE_PAUSA:
        raise ValueError(f"Pausa fora de 1 a 3 meses: {meses}")
    indice = inicio.year * 12 + inicio.month - 1 + meses
    volta = vencimento_no_mes(indice // 12, indice % 12 + 1, inicio.day)
    return Periodo(inicio, volta - timedelta(days=1))


def vencimento_da_reativacao(
    hoje: date, ultimo_periodo_pago_fim: date | None, dia_vencimento: int
) -> tuple[date, int]:
    """A reativação da `cancelada` pela equipe (PLT-06, decisão de 14 out 2026, T-216): o
    vencimento da fatura nova e o `dia_vencimento` dali em diante.

    - Período pago ainda correndo: vence no dia seguinte ao fim dele, e o dia não muda (CA-ASS-49).
    - Já acabou, ou nenhum pago: vence hoje, e o dia passa a ser o de hoje, como na volta da pausa
      (CA-ASS-46)."""
    if ultimo_periodo_pago_fim is not None and ultimo_periodo_pago_fim >= hoje:
        return ultimo_periodo_pago_fim + timedelta(days=1), dia_vencimento
    return hoje, hoje.day


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
