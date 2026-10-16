"""T-276 · Migração com os papéis de banco separados (ADR 0016).

Em homologação e produção, a migração roda como `giro_migracao`, sem superusuário, e é dona dos
schemas. `aplicar_permissoes` (post_migrate) passa a função `auditoria_expurgar` para
`giro_expurgo`, e o PostgreSQL só aceita a troca de dono se o dono novo tiver `CREATE` no schema.
Aqui o teste roda como `giro_migracao` (`SET ROLE`), num schema dele, como no deploy: o banco de
teste usa o superusuário, que não pega o erro (T-264).
"""

import contextlib
from collections.abc import Iterator
from importlib import import_module
from typing import Any

import pytest
from django.db import DatabaseError, connection

from apps.auditoria.banco import PAPEL_APP, PAPEL_EXPURGO, aplicar_permissoes

PAPEL_MIGRACAO = "giro_migracao"
SCHEMA = "t276_papeis"
CRIAR_FUNCAO = import_module("apps.auditoria.migrations.0003_truncate_e_expurgo").CRIAR


def _criar_papel(cursor: Any, papel: str) -> None:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
    if cursor.fetchone() is None:
        cursor.execute(f"CREATE ROLE {papel} NOLOGIN NOSUPERUSER")


@pytest.fixture
def como_migracao(db) -> Iterator[Any]:
    """Os papéis como em `infra/postgres/01-papeis.sh`, um schema de `giro_migracao` com a tabela
    de eventos e a função da migração 0003, e a sessão já como `giro_migracao`. Tudo dentro da
    transação do teste, desfeito no fim."""
    with connection.cursor() as cursor:
        for papel in (PAPEL_MIGRACAO, PAPEL_APP, PAPEL_EXPURGO):
            _criar_papel(cursor, papel)
        cursor.execute(f"GRANT {PAPEL_EXPURGO} TO {PAPEL_MIGRACAO}")
        cursor.execute(f"CREATE SCHEMA {SCHEMA} AUTHORIZATION {PAPEL_MIGRACAO}")
        cursor.execute(f"SET ROLE {PAPEL_MIGRACAO}")
        cursor.execute(f"SET search_path TO {SCHEMA}")
        cursor.execute(
            "CREATE TABLE auditoria_eventoauditoria "
            "(id bigserial PRIMARY KEY, ocorrido_em timestamptz NOT NULL)"
        )
        cursor.execute(CRIAR_FUNCAO)
        try:
            yield cursor
        finally:
            # Com a transação abortada por um erro, o rollback do teste já desfaz o SET ROLE.
            with contextlib.suppress(DatabaseError):
                cursor.execute("RESET ROLE")
                cursor.execute("SET search_path TO public")


def _dono_da_funcao(cursor: Any) -> str:
    cursor.execute(
        "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE oid = to_regprocedure(%s)",
        [f"{SCHEMA}.auditoria_expurgar(date)"],
    )
    return str(cursor.fetchone()[0])


def _pode(cursor: Any, sql: str, *args: str) -> bool:
    cursor.execute(f"SELECT {sql}", list(args))
    return bool(cursor.fetchone()[0])


def test_adr_0016_migracao_sem_superusuario_passa_a_funcao_ao_expurgo(como_migracao):
    cursor = como_migracao
    cursor.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    assert cursor.fetchone()[0] is False  # é mesmo o papel da migração, sem superusuário

    aplicar_permissoes(cursor, SCHEMA)
    aplicar_permissoes(cursor, SCHEMA)  # o post_migrate roda de novo a cada migração

    assert _dono_da_funcao(cursor) == PAPEL_EXPURGO
    funcao = f"{SCHEMA}.auditoria_expurgar(date)"
    assert _pode(cursor, "has_function_privilege(%s, %s, 'EXECUTE')", PAPEL_APP, funcao)
    assert not _pode(cursor, "has_function_privilege('public', %s, 'EXECUTE')", funcao)


def test_adr_0016_expurgo_nao_fica_com_create_no_schema(como_migracao):
    """O `CREATE` que a troca de dono pede é temporário: o expurgo não cria nada no schema."""
    cursor = como_migracao
    aplicar_permissoes(cursor, SCHEMA)
    assert not _pode(cursor, "has_schema_privilege(%s, %s, 'CREATE')", PAPEL_EXPURGO, SCHEMA)
    assert not _pode(cursor, "has_schema_privilege(%s, %s, 'CREATE')", PAPEL_APP, SCHEMA)
