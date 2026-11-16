"""O `TenantSyncRouter` do django-tenants, também para o alias `migracao` (ADR 0040, item 1).

O roteador do django-tenants só deixa migrar no alias do tenant (`default`): no alias `migracao`
toda migração seria marcada como aplicada sem criar nada. Aqui o `migracao` segue a mesma regra
(`SHARED_APPS` no `public`, `TENANT_APPS` num schema de empresa).
"""

from typing import Any

from django.conf import settings
from django.db import connections
from django_tenants.routers import TenantSyncRouter
from django_tenants.utils import get_public_schema_name

ALIAS_DE_MIGRACAO = "migracao"


class RoteadorDeSchemas(TenantSyncRouter):
    """Vem antes do `TenantSyncRouter` em `DATABASE_ROUTERS` (o django-tenants exige que ele esteja
    lá): decide só no alias `migracao` e deixa os outros para ele."""

    def allow_migrate(
        self, db: str, app_label: str, model_name: str | None = None, **hints: Any
    ) -> bool | None:
        if db != ALIAS_DE_MIGRACAO:
            return None
        conexao: Any = connections[db]
        no_public = conexao.schema_name == get_public_schema_name()
        apps = settings.SHARED_APPS if no_public else settings.TENANT_APPS
        return bool(self.app_in_list(app_label, apps))
