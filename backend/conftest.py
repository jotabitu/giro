"""Fixtures comuns: duas empresas de teste (A e B), cada uma com seu schema e subdomínio.

As empresas são criadas uma vez por sessão, fora da transação dos testes (criar schema roda
as migrações da empresa). Cada teste roda numa transação que volta no fim.
"""

from collections.abc import Iterator

import pytest

from comum.conexao import conexao

EMPRESAS_DE_TESTE = {
    "empresa_a": ("Empresa A", "empresa-a.localhost"),
    "empresa_b": ("Empresa B", "empresa-b.localhost"),
}


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    from apps.plataforma.models import Dominio, Empresa

    with django_db_blocker.unblock():
        for schema, (nome, dominio) in EMPRESAS_DE_TESTE.items():
            empresa = Empresa.objects.filter(schema_name=schema).first()
            if empresa is None:
                empresa = Empresa(schema_name=schema, nome=nome, status=Empresa.Status.ATIVA)
                empresa.save()
            Dominio.objects.get_or_create(
                domain=dominio, defaults={"tenant": empresa, "is_primary": True}
            )
        conexao().set_schema_to_public()
        _papeis_de_banco(["public", *EMPRESAS_DE_TESTE])


def _papeis_de_banco(schemas: list[str]) -> None:
    """Papéis da ADR 0016 no banco de teste, para provar os REVOKE com `SET ROLE giro_app`."""
    from django.db import connection

    from apps.auditoria.banco import aplicar_permissoes

    with connection.cursor() as cursor:
        for papel in ("giro_app", "giro_expurgo"):
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
            if cursor.fetchone() is None:
                cursor.execute(f"CREATE ROLE {papel} NOLOGIN")
        for schema in schemas:
            aplicar_permissoes(cursor, schema)


def _entrar(schema: str) -> Iterator["object"]:
    from apps.plataforma.models import Empresa

    empresa = Empresa.objects.get(schema_name=schema)
    conexao().set_tenant(empresa)
    try:
        yield empresa
    finally:
        conexao().set_schema_to_public()


@pytest.fixture
def empresa_a(db):
    yield from _entrar("empresa_a")


@pytest.fixture
def empresa_b(db):
    yield from _entrar("empresa_b")


@pytest.fixture
def publico(db):
    conexao().set_schema_to_public()
    yield
    conexao().set_schema_to_public()
