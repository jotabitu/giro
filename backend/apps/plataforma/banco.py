"""O DDL dos schemas de empresa: o `CREATE SCHEMA` da criação (ADR 0040, item 1), a compensação
da criação que falhou (ADR 0040, itens 3 e 8) e o `DROP SCHEMA` do apagamento da empresa
cancelada (AUD-08, ADR 0025, item 2).

`criar_schema(empresa_id)` é o único lugar do código que cria um schema: lê o nome da `Empresa`
no `public` (nunca de fora), confere o padrão, cria pelo alias `migracao` (`giro_migracao`)
`AUTHORIZATION giro_migracao`, aplica as concessões antes das migrações e roda o
`migrate_schemas` pelo mesmo alias. Sem o alias (desenvolvimento e testes com um papel só), usa
`default`.

`desfazer_schema(empresa_id, pedido_id)` só aceita a reserva da tarefa de criação: empresa com
`schema_pronto_em` nulo, travada, e o pedido em `criando` apontando para ela.

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

import logging
import re
from typing import Any

import psycopg
from django.conf import settings
from django.core.management import call_command
from django.db import DatabaseError, connection, connections, transaction
from django_tenants.utils import get_public_schema_name, schema_context
from psycopg import sql

from apps.auditoria.banco import PAPEL_MIGRACAO, aplicar_permissoes
from comum import relogio

from .models import Dominio, Empresa, PedidoCompra, StatusPedidoCompra

logger = logging.getLogger(__name__)

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


# --- Criação do schema (ADR 0040) ---


class SchemaJaExiste(Exception):
    """O `CREATE SCHEMA` deu `DuplicateSchema` (42P06): outra coisa criou o schema na corrida."""


def alias_de_migracao() -> str:
    """O alias com o `giro_migracao`, quando a `DATABASE_URL_MIGRACAO` chegou a este processo."""
    return "migracao" if "migracao" in settings.DATABASES else "default"


def _causa_psycopg(erro: BaseException) -> BaseException:
    return erro.__cause__ if isinstance(erro.__cause__, psycopg.Error) else erro


def sqlstate(erro: BaseException) -> str:
    return str(getattr(_causa_psycopg(erro), "sqlstate", "") or "")


def _schema_existe(cursor: Any, nome: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [nome])
    return cursor.fetchone() is not None


def _papel_existe(cursor: Any, papel: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
    return cursor.fetchone() is not None


def _dono_e_migracao(cursor: Any, nome: str) -> bool:
    """Com os papéis separados, o schema da reserva é do giro_migracao. Com um papel só
    (desenvolvimento e testes), não há como distinguir: aceita."""
    if not _papel_existe(cursor, PAPEL_MIGRACAO):
        return True
    cursor.execute(
        "SELECT pg_get_userbyid(nspowner) = %s FROM pg_namespace WHERE nspname = %s",
        [PAPEL_MIGRACAO, nome],
    )
    linha = cursor.fetchone()
    return bool(linha and linha[0])


def _reserva(empresa_id: int) -> Empresa:
    with schema_context(get_public_schema_name()):
        empresa: Empresa = Empresa.objects.get(pk=empresa_id)
    if not schema_apagavel(empresa.schema_name):
        raise ApagamentoRecusado(f"Schema fora do padrão: {empresa.schema_name!r}")
    if empresa.schema_pronto_em is not None:
        raise ApagamentoRecusado(f"Empresa {empresa.pk} já tem o schema pronto.")
    return empresa


def criar_schema(empresa_id: int, *, retomar: bool = False) -> str:
    """Cria (se ainda não existe) e migra o schema da reserva. Pode rodar de novo: a tarefa
    retoma a reserva do mesmo pedido (ADR 0040, item 8). Devolve o nome do schema.

    `DuplicateSchema` vira `SchemaJaExiste`; qualquer outro erro (`InsufficientPrivilege`...)
    sobe como veio, para o Sentry com o SQLSTATE. Schema que já existe só é reaproveitado com
    `retomar` (a reserva do mesmo pedido, reentregue); fora disso, `SchemaJaExiste` (P-04, T-057).
    """
    empresa = _reserva(empresa_id)
    nome = str(empresa.schema_name)
    alias = alias_de_migracao()
    conexao_ddl: Any = connections[alias]
    with transaction.atomic(using=alias), conexao_ddl.cursor() as cursor:
        existe = _schema_existe(cursor, nome)
        if existe and not (retomar and _dono_e_migracao(cursor, nome)):
            # Retomada só do schema que a entrega anterior criou (dono giro_migracao); outro
            # schema com o mesmo nome é RESERVADO e nunca é apagado pela compensação.
            raise SchemaJaExiste(nome)
        if not existe:
            dono = PAPEL_MIGRACAO if _papel_existe(cursor, PAPEL_MIGRACAO) else None
            conexao_ddl.ensure_connection()
            if dono:
                comando = sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                    sql.Identifier(nome), sql.Identifier(dono)
                )
            else:
                comando = sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(nome))
            try:
                with transaction.atomic(using=alias):
                    cursor.execute(comando.as_string(conexao_ddl.connection))
            except DatabaseError as erro:
                if isinstance(_causa_psycopg(erro), psycopg.errors.DuplicateSchema):
                    raise SchemaJaExiste(nome) from erro
                raise
        # Antes das migrações: as regras padrão precisam existir antes das tabelas.
        aplicar_permissoes(cursor, nome)
    call_command(
        "migrate_schemas",
        tenant=True,
        schema_name=nome,
        database=alias,
        interactive=False,
        verbosity=0,
    )
    # O `post_migrate` já reaplicou; de novo aqui, explícito, porque o `schema_pronto_em` só é
    # gravado depois das concessões finais (ADR 0040, item 11).
    conexao_ddl = connections[alias]
    with transaction.atomic(using=alias), conexao_ddl.cursor() as cursor:
        aplicar_permissoes(cursor, nome)
    return nome


def desfazer_schema(empresa_id: int, pedido_id: int, *, apagar: bool = True) -> str:
    """Compensação da criação que falhou (ADR 0040, itens 3 e 8): apaga o schema da reserva e as
    linhas do passo 1 (`Dominio` e `Empresa`, que ninguém viu). Recusa (`ApagamentoRecusado`)
    empresa com schema pronto, fora do padrão, ou pedido que não esteja em `criando` apontando
    para ela. Não é um segundo caminho de `DROP SCHEMA`: o apagamento é `apagar_schema`."""
    with schema_context(get_public_schema_name()), transaction.atomic():
        empresa = Empresa.objects.select_for_update(of=("self",)).get(pk=empresa_id)
        if not schema_apagavel(empresa.schema_name):
            raise ApagamentoRecusado(f"Schema fora do padrão: {empresa.schema_name!r}")
        if empresa.schema_pronto_em is not None:
            raise ApagamentoRecusado(f"Empresa {empresa.pk} tem o schema pronto.")
        pedido = PedidoCompra.objects.select_for_update().get(pk=pedido_id)
        if pedido.empresa_id != empresa.pk or pedido.status != StatusPedidoCompra.CRIANDO:
            raise ApagamentoRecusado(f"Pedido {pedido_id} não está criando a empresa {empresa.pk}.")
        schema_name = str(empresa.schema_name)
        alias = alias_de_migracao()
        if not apagar:
            pass  # o schema não é desta reserva (`SchemaJaExiste`): só as linhas saem
        elif alias == "default":
            connection.ensure_connection()
            with connection.connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            _drop(schema_name, connection.connection)
        else:
            conexao_ddl: Any = connections[alias]
            conexao_ddl.ensure_connection()
            _drop(schema_name, conexao_ddl.connection)
        PedidoCompra.objects.filter(pk=pedido.pk).update(empresa=None)
        Dominio.objects.filter(tenant_id=empresa.pk).delete()
        Empresa.objects.filter(pk=empresa.pk).delete()
    logger.warning(
        "ADR 0040: reserva desfeita (empresa_id=%s, pedido_id=%s, schema=%s).",
        empresa_id,
        pedido_id,
        schema_name,
    )
    return schema_name
