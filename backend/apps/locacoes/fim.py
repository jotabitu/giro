"""Fim da locação, sem banco: atraso (LOC-10, LOC-11, FIL-03) e encerramento antecipado (LOC-12,
LOC-13).

Os selectors leem a filial, a configuração e as contas e chamam estas funções. Cada valor é
arredondado no centavo por `comum.dinheiro`.

**Atraso.** O prazo é o fim previsto mais a tolerância. Se a filial está fechada no fim previsto
(fora do horário ou em feriado), ou fecha antes de a tolerância acabar, o prazo passa para a
abertura seguinte mais a tolerância (LOC-11: a devolução prevista para um feriado pode ser feita
na abertura seguinte sem atraso). A devolução fora do horário conta como feita na abertura
seguinte. Passado o prazo, cada 24 h (ou fração) a partir do fim previsto cobra 1 diária, sem
contar as horas dos feriados da filial (FIL-03). Filial sem horário cadastrado conta como aberta
o dia todo, menos nos feriados.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from math import ceil
from typing import Any
from zoneinfo import ZoneInfo

from apps.filiais.calendario import intervalos_do_dia, proxima_abertura_em
from comum.dinheiro import aplicar_percentual, proporcional

from .calculo import fim_dos_periodos
from .models import Periodicidade

P = Periodicidade
UM_DIA = timedelta(days=1)
MULTA_ENCERRAMENTO_PCT = 20  # LOC-12
DIAS_DO_MES = 30  # LOC-13: 7 × preço mensal ÷ 30 por semana


# --- Atraso (LOC-10, LOC-11, FIL-03) ---


@dataclass(frozen=True)
class Atraso:
    dias: int
    valor_centavos: int
    devolucao_considerada_em: datetime


def _tem_horario(horario: dict[str, Any]) -> bool:
    return any(horario.get(dia) for dia in horario)


def _abertura(horario: dict[str, Any], feriados: set[date], momento: datetime) -> datetime:
    """O próprio momento, se a filial está aberta; senão a abertura seguinte."""
    if _tem_horario(horario):
        return proxima_abertura_em(horario, feriados, momento) or momento
    while momento.date() in feriados:
        momento = datetime.combine(momento.date() + UM_DIA, time.min, tzinfo=momento.tzinfo)
    return momento


def _fechamento(horario: dict[str, Any], momento: datetime) -> datetime | None:
    """Quando fecha o intervalo aberto que contém `momento` (sem horário: nunca fecha)."""
    for abre, fecha in intervalos_do_dia(horario, momento.date()):
        if abre <= momento.time() < fecha:
            return datetime.combine(momento.date(), fecha, tzinfo=momento.tzinfo)
    return None


def _horas_de_feriado(feriados: set[date], de: datetime, ate: datetime) -> timedelta:
    total = timedelta()
    dia = de.date()
    while dia <= ate.date():
        if dia in feriados:
            comeco = datetime.combine(dia, time.min, tzinfo=de.tzinfo)
            total += max(timedelta(), min(ate, comeco + UM_DIA) - max(de, comeco))
        dia += UM_DIA
    return total


def prazo_da_devolucao(
    fim_previsto: datetime,
    *,
    tolerancia: timedelta,
    horario: dict[str, Any],
    feriados: set[date],
    fuso: str,
) -> tuple[datetime, datetime]:
    """(de onde o atraso conta, até quando a devolução não tem atraso)."""
    fim = fim_previsto.astimezone(ZoneInfo(fuso))
    aberta = _abertura(horario, feriados, fim) == fim
    if not aberta:
        fim = _abertura(horario, feriados, fim)
    elif _tem_horario(horario):
        fecha = _fechamento(horario, fim)
        if fecha is not None and fecha < fim + tolerancia:
            fim = _abertura(horario, feriados, fecha)
    return fim, fim + tolerancia


def calcular_atraso(
    fim_previsto: datetime,
    devolucao: datetime,
    *,
    tolerancia: timedelta,
    horario: dict[str, Any],
    feriados: set[date],
    fuso: str,
    diaria_centavos: int,
) -> Atraso:
    conta_de, prazo = prazo_da_devolucao(
        fim_previsto, tolerancia=tolerancia, horario=horario, feriados=feriados, fuso=fuso
    )
    considerada = _abertura(horario, feriados, devolucao.astimezone(ZoneInfo(fuso)))
    if considerada <= prazo:
        return Atraso(0, 0, considerada)
    horas = considerada - conta_de - _horas_de_feriado(feriados, conta_de, considerada)
    dias = max(1, ceil(horas / UM_DIA))
    return Atraso(dias, dias * diaria_centavos, considerada)


# --- Encerramento antecipado (LOC-12, LOC-13) ---


@dataclass
class Encerramento:
    antes_da_retirada: bool
    periodo_atual: dict[str, Any] | None = None
    dias_restantes: int = 0
    valor_restante_centavos: int = 0
    multa_centavos: int = 0
    credito_semanas: dict[str, int] = field(
        default_factory=lambda: {"semanas": 0, "valor_centavos": 0}
    )
    credito_dias: dict[str, int] = field(default_factory=lambda: {"dias": 0, "valor_centavos": 0})
    devolver_centavos: int = 0
    cobrar_centavos: int = 0

    def como_dict(self) -> dict[str, Any]:
        return {
            "antes_da_retirada": self.antes_da_retirada,
            "periodo_atual": self.periodo_atual,
            "dias_restantes": self.dias_restantes,
            "valor_restante_centavos": self.valor_restante_centavos,
            "multa_centavos": self.multa_centavos,
            "credito_semanas": self.credito_semanas,
            "credito_dias": self.credito_dias,
            "devolver_centavos": self.devolver_centavos,
            "cobrar_centavos": self.cobrar_centavos,
        }


def antes_da_retirada(pago_centavos: int) -> Encerramento:
    """LOC-12: sem multa, devolve tudo o que foi pago (parcelas e caução)."""
    return Encerramento(antes_da_retirada=True, devolver_centavos=pago_centavos)


def periodo_em(
    periodicidade: str, inicio: datetime, periodos: int, dia: date
) -> tuple[int, date, date] | None:
    """O período (número, início, fim) que contém `dia`, em datas locais."""
    for k in range(1, periodos + 1):
        comeco = fim_dos_periodos(periodicidade, inicio, k - 1).date()
        fim = fim_dos_periodos(periodicidade, inicio, k).date()
        if comeco <= dia < fim:
            return k, comeco, fim
    return None


def depois_da_retirada(
    *,
    periodicidade: str,
    inicio: datetime,
    fim_previsto: datetime,
    periodos: int,
    fuso: str,
    dia: date,
    preco_do_periodo: Any,  # (k) -> centavos do período k, com os descontos
    diaria_centavos: int,
    nao_pagas_do_periodo_centavos: int = 0,
) -> Encerramento | None:
    """LOC-12 e LOC-13 no `dia`. `None` quando não sobra dia nenhum (é uma devolução).

    `nao_pagas_do_periodo_centavos`: no mensal em 4 semanais, as parcelas do mês em curso que
    o encerramento cancela; o crédito das semanas não devolve o que não foi pago."""
    tz = ZoneInfo(fuso)
    inicio_local = inicio.astimezone(tz)
    fim_local = fim_previsto.astimezone(tz).date()
    if dia >= fim_local:
        return None
    if periodicidade == P.DIARIA:
        # Sem multa: cobra só os dias usados. A diária é paga toda na retirada.
        restantes = (fim_local - dia).days
        valor = restantes * preco_do_periodo(1)
        return Encerramento(
            antes_da_retirada=False,
            periodo_atual={"inicio": inicio_local.date(), "fim": fim_local, "dias": periodos},
            dias_restantes=restantes,
            credito_dias={"dias": restantes, "valor_centavos": valor},
            devolver_centavos=valor,
        )
    achado = periodo_em(periodicidade, inicio_local, periodos, dia)
    if achado is None:
        return None
    k, comeco, fim = achado
    dias_do_periodo = (fim - comeco).days
    restantes = (fim - dia).days
    preco = preco_do_periodo(k)
    restante = proporcional(preco, restantes, dias_do_periodo)
    multa = max(aplicar_percentual(restante, MULTA_ENCERRAMENTO_PCT), diaria_centavos)
    credito = 0
    semanas = 0
    if periodicidade == P.MENSAL:
        semanas = restantes // 7
        credito = proporcional(preco, 7 * semanas, DIAS_DO_MES)
        credito = max(0, credito - nao_pagas_do_periodo_centavos)
    saldo = credito - multa
    return Encerramento(
        antes_da_retirada=False,
        periodo_atual={"inicio": comeco, "fim": fim, "dias": dias_do_periodo},
        dias_restantes=restantes,
        valor_restante_centavos=restante,
        multa_centavos=multa,
        credito_semanas={"semanas": semanas, "valor_centavos": credito},
        devolver_centavos=max(0, saldo),
        cobrar_centavos=max(0, -saldo),
    )
