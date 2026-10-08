"""Feriados nacionais e horário da filial, sem banco (FIL-03, LOC-11)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from apps.filiais.calendario import (
    feriados_nacionais,
    pascoa,
    proxima_abertura_em,
    resumo_do_horario,
    validar_horario,
)

SP = ZoneInfo("America/Sao_Paulo")
FECHADO: dict[str, list[dict[str, str]]] = {
    dia: [] for dia in ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
}


@pytest.mark.parametrize(
    ("ano", "esperada"),
    [(2026, date(2026, 4, 5)), (2027, date(2027, 3, 28)), (2024, date(2024, 3, 31))],
)
def test_fil_03_pascoa(ano, esperada):
    assert pascoa(ano) == esperada


def test_fil_03_nacionais_de_2026():
    feriados = dict(feriados_nacionais(2026))
    assert len(feriados) == 10
    assert feriados[date(2026, 4, 3)] == "Sexta-feira Santa"
    assert feriados[date(2026, 11, 20)] == "Dia Nacional de Zumbi e da Consciência Negra"


def test_fil_01_resumo_com_almoco_e_dias_soltos():
    horario = {
        **FECHADO,
        "seg": [{"abre": "08:00", "fecha": "12:00"}, {"abre": "13:30", "fecha": "18:00"}],
        "ter": [{"abre": "08:00", "fecha": "12:00"}, {"abre": "13:30", "fecha": "18:00"}],
        "qui": [{"abre": "09:00", "fecha": "17:00"}],
    }
    assert resumo_do_horario(horario) == "seg e ter 8h–12h e 13h30–18h · qui 9h–17h"


def test_fil_01_horario_valido():
    assert validar_horario({**FECHADO, "seg": [{"abre": "08:00", "fecha": "18:00"}]}) == []


@pytest.mark.parametrize(
    "intervalo", [{"abre": "8:00", "fecha": "18:00"}, {"abre": "08:00", "fecha": "24:00"}, "x"]
)
def test_fil_01_horario_com_hora_invalida(intervalo):
    assert validar_horario({**FECHADO, "seg": [intervalo]})


def test_loc_11_filial_sempre_fechada_nao_tem_proxima_abertura():
    momento = datetime(2026, 10, 7, 10, 0, tzinfo=SP)
    assert proxima_abertura_em(FECHADO, set(), momento, dias_procurados=10) is None


def test_loc_11_almoco_conta_como_fechado():
    horario = {
        **FECHADO,
        "qua": [{"abre": "08:00", "fecha": "12:00"}, {"abre": "14:00", "fecha": "18:00"}],
    }
    momento = datetime(2026, 10, 7, 12, 30, tzinfo=SP)
    assert proxima_abertura_em(horario, set(), momento) == datetime(2026, 10, 7, 14, 0, tzinfo=SP)
