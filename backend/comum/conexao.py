"""Acesso tipado à conexão do django-tenants (a biblioteca não tem anotações de tipo)."""

from typing import Any, cast

from django.db import connection


def conexao() -> Any:
    """A conexão padrão com `schema_name`, `tenant`, `set_tenant` e `set_schema_to_public`."""
    return cast(Any, connection)


def schema_atual() -> str:
    return str(conexao().schema_name)
