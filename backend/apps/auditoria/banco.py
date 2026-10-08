"""Permissões dos papéis de banco em cada schema (ADR 0016, S-10).

`giro_app` atende requisições e roda o Celery: lê e grava nas tabelas de negócio, mas na
auditoria só `SELECT` e `INSERT`. `giro_expurgo` é dono da função `auditoria_expurgar`, a única
que apaga evento (com mais de 5 anos). Os papéis são criados pelo devops
(`infra/postgres/01-papeis.sh`); papel que não existe é ignorado, então em dev com um papel só
nada muda.

Roda depois de toda migração do schema (`post_migrate`) e pode rodar de novo sem efeito.
"""

from django.db.backends.utils import CursorWrapper

PAPEL_APP = "giro_app"
PAPEL_EXPURGO = "giro_expurgo"
TABELA = "auditoria_eventoauditoria"


def _papel_existe(cursor: CursorWrapper, papel: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
    return cursor.fetchone() is not None


def _sem_aspas(nome: str) -> str:
    """Schema e papel vêm do banco, mas entram no SQL: só aceita identificador simples."""
    if not nome.replace("_", "").isalnum() or not nome.isascii():
        raise ValueError(f"Identificador inesperado: {nome!r}")
    return f'"{nome}"'


def aplicar_permissoes(cursor: CursorWrapper, schema: str) -> None:
    s = _sem_aspas(schema)
    funcao = f"{s}.auditoria_expurgar(date)"
    cursor.execute("SELECT to_regprocedure(%s)", [funcao])
    linha = cursor.fetchone()
    if linha is None or linha[0] is None:
        return  # migração da auditoria ainda não chegou à 0003 neste schema
    tem_app = _papel_existe(cursor, PAPEL_APP)
    tem_expurgo = _papel_existe(cursor, PAPEL_EXPURGO)

    cursor.execute(f"REVOKE EXECUTE ON FUNCTION {funcao} FROM PUBLIC")
    if tem_expurgo:
        cursor.execute(f"GRANT USAGE ON SCHEMA {s} TO {PAPEL_EXPURGO}")
        cursor.execute(f"GRANT SELECT, DELETE ON {s}.{TABELA} TO {PAPEL_EXPURGO}")
        cursor.execute(f"ALTER FUNCTION {funcao} OWNER TO {PAPEL_EXPURGO}")

    if tem_app:
        cursor.execute(f"GRANT USAGE ON SCHEMA {s} TO {PAPEL_APP}")
        cursor.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {s} TO {PAPEL_APP}"
        )
        cursor.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {s} TO {PAPEL_APP}")
        cursor.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {s} "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {PAPEL_APP}"
        )
        cursor.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {s} "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {PAPEL_APP}"
        )
        # Depois do GRANT geral: na auditoria, só SELECT e INSERT.
        cursor.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {s}.{TABELA} FROM {PAPEL_APP}")
        cursor.execute(f"GRANT EXECUTE ON FUNCTION {funcao} TO {PAPEL_APP}")
