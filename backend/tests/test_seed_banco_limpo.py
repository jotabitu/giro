"""T-281: o seed roda do zero, num banco novo, com as configurações de teste.

Com `CELERY_TASK_ALWAYS_EAGER`, o convite agendado no commit roda na conexão do seed. O sinal
de limpeza do worker (S-11, ADR 0012) devolvia essa conexão ao public e o seed falhava com
`veiculos_veiculo does not exist` (`comum.worker`). O teste cria um banco só dele, migra o
public e roda o comando de verdade em outro processo, já que o seed grava e confirma (commit).
"""

import os
import subprocess
import sys
from collections.abc import Iterator
from urllib.parse import quote

import psycopg
import pytest
from django.conf import settings
from psycopg import sql

BANCO = "giro_seed_t281"


def _banco() -> dict[str, str]:
    return settings.DATABASES["default"]


def _conectar(nome: str) -> psycopg.Connection:
    d = _banco()
    return psycopg.connect(
        dbname=nome,
        user=d["USER"],
        password=d["PASSWORD"],
        host=d["HOST"],
        port=d["PORT"] or 5432,
        autocommit=True,
    )


def _url(nome: str) -> str:
    d = _banco()
    porta = d["PORT"] or 5432
    return f"postgres://{quote(d['USER'])}:{quote(d['PASSWORD'])}@{d['HOST']}:{porta}/{nome}"


def _manage(*args: str) -> subprocess.CompletedProcess[str]:
    ambiente = {
        **os.environ,
        "DATABASE_URL": _url(BANCO),
        "DJANGO_SETTINGS_MODULE": "config.settings.test",
    }
    return subprocess.run(  # noqa: S603 (argumentos fixos, sem entrada externa)
        [sys.executable, "manage.py", *args],
        cwd=settings.BASE_DIR,
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def banco_novo() -> Iterator[None]:
    with _conectar("postgres") as con:
        con.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(BANCO)))
        con.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(BANCO)))
    yield
    with _conectar("postgres") as con:
        con.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(BANCO))
        )


def test_seed_roda_em_banco_novo_com_as_configuracoes_de_teste(banco_novo):
    migrado = _manage("migrate_schemas", "--shared")
    assert migrado.returncode == 0, migrado.stderr[-2000:]

    semeado = _manage("seed_moto_rapida")
    assert semeado.returncode == 0, semeado.stderr[-2000:]
    assert "veiculos_veiculo" not in semeado.stderr

    with _conectar(BANCO) as con:
        empresas = con.execute("SELECT subdominio FROM plataforma_empresa ORDER BY 1").fetchall()
        veiculos = con.execute("SELECT count(*) FROM motorapida.veiculos_veiculo").fetchone()
    assert ("motorapida",) in empresas
    assert veiculos is not None and veiculos[0] > 0

    de_novo = _manage("seed_moto_rapida")
    assert de_novo.returncode == 0, de_novo.stderr[-2000:]
