"""Concessão e conferência dos privilégios por schema de empresa (ADR 0040, itens 2, 5 e 11).

`conceder(schema)` roda `auditoria.banco.aplicar_permissoes` pelo alias de migração e diz se algo
mudou (compara as ACLs antes e depois). `problemas(schema)` lista o que falta e o que sobra para o
`giro_app`, o `giro_expurgo` e o `PUBLIC`; o deploy roda os dois depois do `migrate_schemas`.
"""

from typing import Any

from django.db import connections, transaction
from django_tenants.utils import get_public_schema_name, schema_context

from apps.auditoria.banco import (
    PAPEL_APP,
    PAPEL_EXPURGO,
    PAPEL_MIGRACAO,
    TABELA,
    aplicar_permissoes,
)

from .banco import alias_de_migracao, schema_apagavel
from .models import Empresa

DML = ("SELECT", "INSERT", "UPDATE", "DELETE")
SO_NA_AUDITORIA = ("UPDATE", "DELETE", "TRUNCATE")
FUNCAO = "auditoria_expurgar(date)"

_ACLS = """
SELECT 'schema', n.nspname, coalesce(n.nspacl::text, ''), pg_get_userbyid(n.nspowner)
  FROM pg_namespace n WHERE n.nspname = %(s)s
UNION ALL
SELECT 'rel', c.relname, coalesce(c.relacl::text, ''), pg_get_userbyid(c.relowner)
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = %(s)s AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
UNION ALL
SELECT 'func', p.proname, coalesce(p.proacl::text, ''), pg_get_userbyid(p.proowner)
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = %(s)s
UNION ALL
SELECT 'padrao', d.defaclobjtype::text, coalesce(d.defaclacl::text, ''),
       pg_get_userbyid(d.defaclrole)
  FROM pg_default_acl d JOIN pg_namespace n ON n.oid = d.defaclnamespace
 WHERE n.nspname = %(s)s
ORDER BY 1, 2, 4
"""


def schemas_de_empresa(schema: str | None = None) -> list[str]:
    """Os schemas das empresas prontas e não apagadas (ou só o pedido, se for uma delas)."""
    with schema_context(get_public_schema_name()):
        empresas = (
            Empresa.objects.prontas()
            .exclude(schema_name=get_public_schema_name())
            .filter(apagada_em__isnull=True)
        )
        if schema is not None:
            empresas = empresas.filter(schema_name=schema)
        nomes = [
            str(nome)
            for nome in empresas.order_by("schema_name").values_list("schema_name", flat=True)
        ]
    return [nome for nome in nomes if schema_apagavel(nome)]


def _acls(cursor: Any, schema: str) -> list[tuple[Any, ...]]:
    cursor.execute(_ACLS, {"s": schema})
    return list(cursor.fetchall())


def conceder(schema: str) -> bool:
    """Aplica as concessões no schema. Devolve se alguma ACL mudou."""
    alias = alias_de_migracao()
    conexao: Any = connections[alias]
    with transaction.atomic(using=alias), conexao.cursor() as cursor:
        antes = _acls(cursor, schema)
        aplicar_permissoes(cursor, schema)
        depois = _acls(cursor, schema)
    return antes != depois


def _papel_existe(cursor: Any, papel: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
    return cursor.fetchone() is not None


def _pode(cursor: Any, consulta: str, *args: Any) -> bool:
    cursor.execute(f"SELECT {consulta}", list(args))
    return bool(cursor.fetchone()[0])


def problemas(schema: str) -> list[str]:
    """O que falta ou sobra no schema. Vazio = nada a mudar."""
    erros: list[str] = []
    with connections["default"].cursor() as cursor:
        if not _papel_existe(cursor, PAPEL_APP):
            return []  # desenvolvimento com um papel só: nada a conferir
        tem_migracao = _papel_existe(cursor, PAPEL_MIGRACAO)
        tem_expurgo = _papel_existe(cursor, PAPEL_EXPURGO)
        s = schema
        if not _pode(cursor, "has_schema_privilege(%s, %s, 'USAGE')", PAPEL_APP, s):
            erros.append(f"{s}: {PAPEL_APP} sem USAGE no schema")
        if _pode(cursor, "has_schema_privilege(%s, %s, 'CREATE')", PAPEL_APP, s):
            erros.append(f"{s}: {PAPEL_APP} com CREATE no schema")
        if tem_expurgo and _pode(
            cursor, "has_schema_privilege(%s, %s, 'CREATE')", PAPEL_EXPURGO, s
        ):
            erros.append(f"{s}: {PAPEL_EXPURGO} com CREATE no schema")
        cursor.execute(
            "SELECT count(*) FROM pg_namespace n, aclexplode(n.nspacl) a "
            "WHERE n.nspname = %s AND a.grantee = 0",
            [s],
        )
        if cursor.fetchone()[0]:
            erros.append(f"{s}: PUBLIC com privilégio no schema")

        cursor.execute(
            "SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'S') ORDER BY c.relname",
            [s],
        )
        for nome, tipo, dono in cursor.fetchall():
            completo = f'"{s}"."{nome}"'
            if tem_migracao and dono != PAPEL_MIGRACAO:
                erros.append(f"{s}.{nome}: dono {dono}, não {PAPEL_MIGRACAO}")
            if tipo == "S":
                for privilegio in ("USAGE", "SELECT"):
                    if not _pode(
                        cursor,
                        "has_sequence_privilege(%s, %s, %s)",
                        PAPEL_APP,
                        completo,
                        privilegio,
                    ):
                        erros.append(f"{s}.{nome}: {PAPEL_APP} sem {privilegio}")
                continue
            na_auditoria = nome == TABELA
            for privilegio in DML:
                tem = _pode(
                    cursor, "has_table_privilege(%s, %s, %s)", PAPEL_APP, completo, privilegio
                )
                if na_auditoria and privilegio in SO_NA_AUDITORIA:
                    if tem:
                        erros.append(f"{s}.{nome}: {PAPEL_APP} com {privilegio}")
                elif not tem:
                    erros.append(f"{s}.{nome}: {PAPEL_APP} sem {privilegio}")
            if na_auditoria and _pode(
                cursor, "has_table_privilege(%s, %s, 'TRUNCATE')", PAPEL_APP, completo
            ):
                erros.append(f"{s}.{nome}: {PAPEL_APP} com TRUNCATE")

        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace, "
            "aclexplode(c.relacl) a WHERE n.nspname = %s AND a.grantee = 0 "
            "GROUP BY c.relname ORDER BY c.relname",
            [s],
        )
        for (nome,) in cursor.fetchall():
            erros.append(f"{s}.{nome}: PUBLIC com privilégio")

        cursor.execute("SELECT to_regprocedure(%s)", [f'"{s}".{FUNCAO}'])
        if cursor.fetchone()[0] is not None:
            cursor.execute(
                "SELECT coalesce(nullif(a.grantee, 0)::regrole::text, 'PUBLIC') "
                "FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a "
                "WHERE p.oid = to_regprocedure(%s) AND a.privilege_type = 'EXECUTE'",
                [f'"{s}".{FUNCAO}'],
            )
            for (papel,) in cursor.fetchall():
                if papel not in (PAPEL_APP, PAPEL_EXPURGO):
                    erros.append(f"{s}.auditoria_expurgar: EXECUTE para {papel}")
    return erros


def problemas_gerais() -> list[str]:
    """Fora dos schemas de empresa: o `giro_app` não cria no `public`."""
    with connections["default"].cursor() as cursor:
        if not _papel_existe(cursor, PAPEL_APP):
            return []
        if _pode(cursor, "has_schema_privilege(%s, 'public', 'CREATE')", PAPEL_APP):
            return [f"public: {PAPEL_APP} com CREATE no schema"]
    return []
