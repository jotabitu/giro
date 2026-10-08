"""Endurecimento de produção (T-035): S-16, S-17, S-18, C-04. Cada caso sobe um processo limpo."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
AMBIENTE_PROD = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "segredo-django-de-teste",
    "JWT_SIGNING_KEY": "segredo-dos-tokens-de-teste",
    "DATABASE_URL": "postgres://u:p@db:5432/giro",
    "GIRO_REDES_PROXY": "10.0.0.0/8",
}


def rodar(codigo: str, **variaveis: str | None) -> subprocess.CompletedProcess[str]:
    ambiente = {k: v for k, v in os.environ.items() if k not in AMBIENTE_PROD}
    ambiente.update({k: v for k, v in {**AMBIENTE_PROD, **variaveis}.items() if v is not None})
    return subprocess.run(  # noqa: S603 (argumentos fixos, sem entrada externa)
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )


def configuracao_de_prod(**variaveis: str | None) -> dict[str, Any]:
    resultado = rodar(
        "import json; from django.conf import settings as s;"
        "print(json.dumps({k: getattr(s, k) for k in ("
        "'SHOW_PUBLIC_IF_NO_TENANT_FOUND','SECURE_HSTS_SECONDS','SECURE_HSTS_PRELOAD',"
        "'SECURE_HSTS_INCLUDE_SUBDOMAINS','SECURE_REFERRER_POLICY','X_FRAME_OPTIONS',"
        "'EXPOR_DOCUMENTACAO_DA_API')}))",
        **variaveis,
    )
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def test_s16_prod_nao_serve_o_public_em_host_desconhecido():
    assert configuracao_de_prod()["SHOW_PUBLIC_IF_NO_TENANT_FOUND"] is False


def test_s17_prod_fecha_schema_e_docs_por_padrao():
    assert configuracao_de_prod()["EXPOR_DOCUMENTACAO_DA_API"] is False
    assert configuracao_de_prod(GIRO_EXPOR_DOCUMENTACAO_DA_API="1")["EXPOR_DOCUMENTACAO_DA_API"]


def test_s18_prod_hsts_com_preload_e_cabecalhos():
    cfg = configuracao_de_prod()
    assert cfg["SECURE_HSTS_SECONDS"] >= 31536000
    assert cfg["SECURE_HSTS_PRELOAD"] is True
    assert cfg["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert cfg["SECURE_REFERRER_POLICY"] == "same-origin"
    assert cfg["X_FRAME_OPTIONS"] == "DENY"


def test_s18_prod_recusa_chave_dos_tokens_igual_a_chave_do_django():
    resultado = rodar("import django.conf as c; c.settings.DEBUG", JWT_SIGNING_KEY=None)
    assert resultado.returncode != 0
    assert "JWT_SIGNING_KEY" in resultado.stderr


def test_prod_recusa_subir_sem_rede_de_proxy():
    resultado = rodar("import django.conf as c; c.settings.DEBUG", GIRO_REDES_PROXY=None)
    assert resultado.returncode != 0
    assert "GIRO_REDES_PROXY" in resultado.stderr


@pytest.mark.parametrize("modulo", ["config.wsgi", "config.asgi", "config.celery"])
def test_c04_sem_padrao_dev_quando_a_variavel_falta(modulo):
    resultado = rodar(f"import {modulo}", DJANGO_SETTINGS_MODULE=None)
    assert resultado.returncode != 0
    assert "DJANGO_SETTINGS_MODULE" in resultado.stderr
