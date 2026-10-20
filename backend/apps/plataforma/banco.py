"""O `DROP SCHEMA` do apagamento da empresa cancelada (AUD-08, ADR 0025, item 2).

`apagar_schema(empresa_id)` é o único lugar do código que apaga um schema:
- recebe o `empresa_id`, nunca um nome de schema de fora, e lê o `schema_name` da `Empresa` no
  `public`, travada;
- recusa o `public`, nome fora do padrão de schema de empresa, e a empresa que não esteja
  `cancelada` com `apagar_em` ≤ hoje e `apagada_em` nulo;
- monta o nome com `psycopg.sql.Identifier`, nunca por concatenação;
- roda pela conexão de migração (`giro_migracao`, dona dos schemas, ADR 0016), quando
  `DATABASE_URL_MIGRACAO` existe. No desenvolvimento e nos testes, com um papel só, usa a conexão
  da aplicação.
"""

import re
from typing import Any

import psycopg
from django.conf import settings
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context
from psycopg import sql

from comum import relogio

from .models import Empresa

# O schema de empresa nasce do subdomínio (`services.schema_do_subdominio`): 3 a 30 letras
# minúsculas, números ou `_`. Os do próprio Postgres (`pg_*`, `information_schema`) ficam fora.
_SCHEMA_DE_EMPRESA = re.compile(r"^[a-z0-9_]{3,30}$")
_SCHEMAS_DO_POSTGRES = frozenset({"information_schema"})


class ApagamentoRecusado(Exception):
    """O schema não pode ser apagado: a conferência falhou e nada foi feito."""


def schema_apagavel(schema_name: str) -> bool:
    return (
        bool(_SCHEMA_DE_EMPRESA.match(schema_name))
        and schema_name != get_public_schema_name()
        and schema_name not in _SCHEMAS_DO_POSTGRES
        and not schema_name.startswith("pg_")
    )


def conferir_para_apagar(empresa: Empresa) -> None:
    """A empresa travada está pronta para o apagamento, ou `ApagamentoRecusado`."""
    if not schema_apagavel(empresa.schema_name):
        raise ApagamentoRecusado(f"Schema fora do padrão: {empresa.schema_name!r}")
    if empresa.status != Empresa.Status.CANCELADA:
        raise ApagamentoRecusado(f"Empresa {empresa.pk} não está cancelada.")
    if empresa.apagar_em is None or empresa.apagar_em > relogio.hoje():
        raise ApagamentoRecusado(f"Empresa {empresa.pk} ainda não chegou ao dia do apagamento.")
    if empresa.apagada_em is not None:
        raise ApagamentoRecusado(f"Empresa {empresa.pk} já foi apagada.")


def _drop(schema_name: str, conexao_psycopg: Any) -> None:
    comando = sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name))
    with conexao_psycopg.cursor() as cursor:
        cursor.execute(comando)


def apagar_schema(empresa_id: int) -> str:
    """Apaga o schema da empresa (dados de negócio, usuários e a auditoria dela, ADR 0025, item
    1). Pode rodar de novo (`IF EXISTS`). Devolve o nome do schema apagado."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = Empresa.objects.select_for_update(of=("self",)).get(pk=empresa_id)
        conferir_para_apagar(empresa)
        schema_name = str(empresa.schema_name)
        url = getattr(settings, "DATABASE_URL_MIGRACAO", "")
        if url:
            with psycopg.connect(url, autocommit=True) as migracao:
                _drop(schema_name, migracao)
        else:
            connection.ensure_connection()
            with connection.connection.cursor() as cursor:
                # Na mesma transação, as chaves estrangeiras adiadas do schema precisam ser
                # conferidas antes do DROP ("pending trigger events").
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            _drop(schema_name, connection.connection)
    return schema_name
