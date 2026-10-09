"""Momentos saem em UTC com `Z`, sem fração de segundo, por um ponto só (ADR 0020).

O ponto é o renderizador JSON de `comum` com `DATETIME_FORMAT = None` no DRF: o
`DateTimeField` devolve o `datetime` cru e quem formata é o encoder, também para valores
soltos na resposta (`detalhes.tentar_de_novo_em`). Nenhum serializer escolhe fuso ou formato.
"""

import ast
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from rest_framework import serializers
from rest_framework.settings import api_settings

RAIZ = Path(__file__).resolve().parent.parent

T089 = pytest.mark.xfail(strict=True, reason="T-089 liga o renderizador de comum (ADR 0020)")

# 09:12:00,123456 em São Paulo = 12:12:00 UTC; a fração cai.
MOMENTO = datetime(2026, 10, 7, 9, 12, 0, 123456, tzinfo=ZoneInfo("America/Sao_Paulo"))
ESPERADO = "2026-10-07T12:12:00Z"

# O formato mora aqui, e só aqui.
RENDERIZADOR = "comum/renderizacao.py"

# Quem ainda formata momento por conta própria. A T-089 esvazia; ninguém entra.
PENDENTES_T089 = {
    "apps/clientes/api/serializers.py",  # _momento com default_timezone=UTC
    "apps/contas/dois_fatores.py",  # tentar_de_novo_em montado com strftime
}


def _renderizar(corpo: Any) -> Any:
    classe: Any = api_settings.DEFAULT_RENDERER_CLASSES[0]
    return json.loads(classe().render(corpo))


class _ComMomento(serializers.Serializer[Any]):
    em = serializers.DateTimeField()


@T089
def test_adr_0020_campo_de_serializer_sai_em_utc_com_z():
    assert api_settings.DATETIME_FORMAT is None
    assert _renderizar(_ComMomento({"em": MOMENTO}).data) == {"em": ESPERADO}


@T089
def test_adr_0020_valor_solto_na_resposta_sai_em_utc_com_z():
    corpo = {"detalhes": {"tentar_de_novo_em": MOMENTO}, "lista": [MOMENTO.astimezone(UTC)]}
    assert _renderizar(corpo) == {"detalhes": {"tentar_de_novo_em": ESPERADO}, "lista": [ESPERADO]}


@T089
def test_adr_0020_momento_sem_fuso_e_erro():
    with pytest.raises(TypeError):
        _renderizar({"em": datetime(2026, 10, 7, 9, 12)})


def _formata_momento(arquivo: Path) -> bool:
    """`DateTimeField(format=...)`, `DateTimeField(default_timezone=...)` ou um `"%Y-%m-%dT..."`."""
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        if isinstance(no, ast.Call):
            nome = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
            if nome == "DateTimeField" and any(
                k.arg in {"format", "default_timezone"} for k in no.keywords
            ):
                return True
        if isinstance(no, ast.Constant) and isinstance(no.value, str) and "%Y-%m-%dT" in no.value:
            return True
        if isinstance(no, ast.keyword) and no.arg == "renderer_classes":
            return True
        if isinstance(no, ast.Assign) and any(
            getattr(alvo, "id", None) == "renderer_classes" for alvo in no.targets
        ):
            return True
    return False


def test_adr_0020_ninguem_formata_momento_por_conta_propria():
    """O formato é do renderizador de `comum`; app nenhum troca fuso, formato ou renderizador."""
    arquivos = [
        a
        for pasta in ("apps", "comum")
        for a in (RAIZ / pasta).rglob("*.py")
        if "tests" not in a.parts and "migrations" not in a.parts
    ]
    achados = {a.relative_to(RAIZ).as_posix() for a in arquivos if _formata_momento(a)}
    achados.discard(RENDERIZADOR)
    assert achados == PENDENTES_T089
