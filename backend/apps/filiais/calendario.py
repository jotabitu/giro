"""Feriados nacionais sugeridos e cálculo de horário da filial (FIL-03, LOC-11). Sem banco.

Nacionais de lei: datas fixas (Lei 662/1949 e alterações, Lei 6.802/1980, Lei 14.759/2023) e
a Sexta-feira Santa, calculada pela Páscoa. Carnaval e Corpus Christi são ponto facultativo e
entram como feriado local, se a filial fechar.
"""

import re
from datetime import date, datetime, time, timedelta
from typing import Any

FERIADOS_FIXOS = [
    ((1, 1), "Confraternização Universal"),
    ((4, 21), "Tiradentes"),
    ((5, 1), "Dia do Trabalho"),
    ((9, 7), "Independência do Brasil"),
    ((10, 12), "Nossa Senhora Aparecida"),
    ((11, 2), "Finados"),
    ((11, 15), "Proclamação da República"),
    ((11, 20), "Dia Nacional de Zumbi e da Consciência Negra"),
    ((12, 25), "Natal"),
]
DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
ROTULO_DIA = {
    "seg": "seg",
    "ter": "ter",
    "qua": "qua",
    "qui": "qui",
    "sex": "sex",
    "sab": "sáb",
    "dom": "dom",
}
MAXIMO_DE_INTERVALOS = 2
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def pascoa(ano: int) -> date:
    """Algoritmo de Meeus/Jones/Butcher (calendário gregoriano)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mes = (h + m - 7 * n + 114) // 31
    dia = (h + m - 7 * n + 114) % 31 + 1
    return date(ano, mes, dia)


def feriados_nacionais(ano: int) -> list[tuple[date, str]]:
    feriados = [(date(ano, mes, dia), nome) for (mes, dia), nome in FERIADOS_FIXOS]
    feriados.append((pascoa(ano) - timedelta(days=2), "Sexta-feira Santa"))
    return sorted(feriados)


# --- Horário ---


def validar_horario(horario: Any) -> list[str]:
    """Erros do horário (vazio = válido): 7 dias, até 2 intervalos, fecha > abre, sem sobrepor."""
    if not isinstance(horario, dict) or set(horario) != set(DIAS):
        return ["Informe o horário dos 7 dias da semana (seg a dom)."]
    erros: list[str] = []
    for dia in DIAS:
        intervalos = horario[dia]
        if not isinstance(intervalos, list):
            erros.append(f"{ROTULO_DIA[dia]}: use uma lista de intervalos.")
            continue
        if len(intervalos) > MAXIMO_DE_INTERVALOS:
            erros.append(f"{ROTULO_DIA[dia]}: no máximo 2 intervalos por dia.")
            continue
        faixas = []
        for intervalo in intervalos:
            abre = intervalo.get("abre") if isinstance(intervalo, dict) else None
            fecha = intervalo.get("fecha") if isinstance(intervalo, dict) else None
            if not (isinstance(abre, str) and _HORA.match(abre)) or not (
                isinstance(fecha, str) and _HORA.match(fecha)
            ):
                erros.append(f"{ROTULO_DIA[dia]}: use horas no formato HH:MM.")
                break
            if fecha <= abre:
                erros.append(f"{ROTULO_DIA[dia]}: o fechamento precisa ser depois da abertura.")
                break
            faixas.append((abre, fecha))
        else:
            faixas.sort()
            if any(faixas[i][1] > faixas[i + 1][0] for i in range(len(faixas) - 1)):
                erros.append(f"{ROTULO_DIA[dia]}: os intervalos não podem se sobrepor.")
    return erros


def _hora_curta(texto: str) -> str:
    hora, minuto = texto.split(":")
    return f"{int(hora)}h" if minuto == "00" else f"{int(hora)}h{minuto}"


def _faixas_do_dia(intervalos: list[dict[str, str]]) -> str:
    return " e ".join(
        f"{_hora_curta(i['abre'])}–{_hora_curta(i['fecha'])}"
        for i in sorted(intervalos, key=lambda i: i["abre"])
    )


def resumo_do_horario(horario: dict[str, list[dict[str, str]]]) -> str:
    """`seg a sex 8h–18h · sáb 8h–12h`: dias seguidos com o mesmo horário juntos; fechado some."""
    grupos: list[tuple[list[str], str]] = []
    for dia in DIAS:
        faixas = _faixas_do_dia(horario.get(dia, []))
        if (
            grupos
            and grupos[-1][1] == faixas
            and DIAS.index(grupos[-1][0][-1]) + 1 == DIAS.index(dia)
        ):
            grupos[-1][0].append(dia)
        else:
            grupos.append(([dia], faixas))
    partes = []
    for dias, faixas in grupos:
        if not faixas:
            continue
        if len(dias) == 1:
            rotulo = ROTULO_DIA[dias[0]]
        elif len(dias) == 2:
            rotulo = f"{ROTULO_DIA[dias[0]]} e {ROTULO_DIA[dias[1]]}"
        else:
            rotulo = f"{ROTULO_DIA[dias[0]]} a {ROTULO_DIA[dias[-1]]}"
        partes.append(f"{rotulo} {faixas}")
    return " · ".join(partes)


def intervalos_do_dia(
    horario: dict[str, list[dict[str, str]]], dia: date
) -> list[tuple[time, time]]:
    return sorted(
        (time.fromisoformat(i["abre"]), time.fromisoformat(i["fecha"]))
        for i in horario.get(DIAS[dia.weekday()], [])
    )


def aberta_em(
    horario: dict[str, list[dict[str, str]]], feriados: set[date], momento_local: datetime
) -> bool:
    dia = momento_local.date()
    if dia in feriados:
        return False
    agora = momento_local.time()
    return any(abre <= agora < fecha for abre, fecha in intervalos_do_dia(horario, dia))


def proxima_abertura_em(
    horario: dict[str, list[dict[str, str]]],
    feriados: set[date],
    momento_local: datetime,
    dias_procurados: int = 400,
) -> datetime | None:
    """O próprio momento, se aberta; senão a próxima abertura. `None` se nunca abre."""
    for passo in range(dias_procurados):
        dia = momento_local.date() + timedelta(days=passo)
        if dia in feriados:
            continue
        for abre, fecha in intervalos_do_dia(horario, dia):
            inicio = datetime.combine(dia, abre, tzinfo=momento_local.tzinfo)
            fim = datetime.combine(dia, fecha, tzinfo=momento_local.tzinfo)
            if momento_local < fim:
                return max(inicio, momento_local)
    return None
