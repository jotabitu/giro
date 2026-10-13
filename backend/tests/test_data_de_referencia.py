"""ADR 0021 (T-142): data de referência do relógio no desenvolvimento.

O dia fica parado na data de `GIRO_DATA_REFERENCIA` e a hora é a real de São Paulo. Só
`dev.py` lê a variável; `prod.py` recusa subir com ela; os testes ligam por `override_settings`.
"""

import logging
from datetime import UTC, date, datetime

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from comum import relogio
from comum.ambiente import CABECALHO, avisar_ao_subir, conferir_data_de_referencia

from .test_producao import rodar

DATA = date(2026, 10, 7)
LIGADA = override_settings(GIRO_DATA_REFERENCIA=DATA)
HOST_EMPRESA = "empresa-a.localhost"
HOST_PLATAFORMA = "admin.localhost"
# 12 out 2026, 14:30 em São Paulo (17:30 UTC).
REAL = datetime(2026, 10, 12, 17, 30, 15, tzinfo=UTC)


@pytest.fixture
def relogio_real(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: REAL)


def _dev(valor: str | None) -> tuple[int, str]:
    resultado = rodar(
        "from django.conf import settings as s; print(s.GIRO_DATA_REFERENCIA)",
        DJANGO_SETTINGS_MODULE="config.settings.dev",
        GIRO_DATA_REFERENCIA=valor,
    )
    return resultado.returncode, (resultado.stdout + resultado.stderr).strip()


def test_adr_0021_ligada_dia_de_referencia_com_a_hora_real(relogio_real):
    with LIGADA:
        agora = relogio.agora()
        assert relogio.hoje() == DATA
        local = timezone.localtime(agora)
        assert (local.date(), local.hour, local.minute, local.second) == (DATA, 14, 30, 15)
        assert str(local.tzinfo) == "America/Sao_Paulo"


def test_adr_0021_desligada_relogio_real(relogio_real):
    assert relogio.data_de_referencia() is None
    assert relogio.agora() == REAL
    assert relogio.hoje() == date(2026, 10, 12)


def test_adr_0021_dev_le_a_variavel_vazia_desliga_e_formato_errado_nao_sobe():
    assert _dev("2026-10-07") == (0, "2026-10-07")
    assert _dev("") == (0, "None")
    assert _dev("   ") == (0, "None")
    assert _dev(None) == (0, "None")
    codigo, saida = _dev("07/10/2026")
    assert codigo != 0
    assert "GIRO_DATA_REFERENCIA fora do formato AAAA-MM-DD" in saida


def test_adr_0021_producao_recusa_subir_com_a_data():
    resultado = rodar(
        "from django.conf import settings as s; print(s.GIRO_DATA_REFERENCIA)",
        GIRO_DATA_REFERENCIA="2026-10-07",
    )
    assert resultado.returncode != 0
    assert "GIRO_DATA_REFERENCIA só vale no desenvolvimento." in resultado.stderr
    vazia = rodar(
        "from django.conf import settings as s; print(s.GIRO_DATA_REFERENCIA)",
        GIRO_DATA_REFERENCIA="",
    )
    assert vazia.returncode == 0, vazia.stderr
    assert vazia.stdout.strip() == "None"


def test_adr_0021_testes_nao_leem_a_variavel():
    from django.conf import settings

    assert settings.GIRO_DATA_REFERENCIA is None


def test_adr_0021_aviso_no_check_e_ao_subir(caplog):
    assert conferir_data_de_referencia() == []
    with LIGADA:
        avisos = conferir_data_de_referencia()
        assert [(a.id, a.msg) for a in avisos] == [
            ("giro.W001", "Data de referência ligada: 2026-10-07")
        ]
        with caplog.at_level(logging.WARNING, logger="giro.relogio"):
            avisar_ao_subir()
    assert "Data de referência ligada: 2026-10-07" in caplog.text


@pytest.mark.parametrize(
    ("host", "rota"),
    [(HOST_EMPRESA, "/api/ambiente/"), (HOST_PLATAFORMA, "/api/plataforma/ambiente/")],
)
def test_adr_0021_rota_e_cabecalho_nos_dois_urlconfs(empresa_a, relogio_real, host, rota):
    api = APIClient(HTTP_HOST=host)
    desligada = api.get(rota)
    assert desligada.status_code == 200
    assert desligada.json() == {"hoje": "2026-10-12", "data_simulada": False}
    assert desligada["Cache-Control"] == "no-store"
    assert CABECALHO not in desligada

    with LIGADA:
        ligada = api.get(rota)
        assert ligada.json() == {"hoje": "2026-10-07", "data_simulada": True}
        assert ligada[CABECALHO] == "2026-10-07"
        # Pública: um token qualquer não muda a resposta.
        com_token = APIClient(HTTP_HOST=host, HTTP_AUTHORIZATION="Bearer invalido")
        assert com_token.get(rota).status_code == 200
        # O cabeçalho vai em toda resposta da API, inclusive nas recusas.
        assert api.get("/api/auth/eu/" if host == HOST_EMPRESA else rota)[CABECALHO] == (
            "2026-10-07"
        )
