"""Resolução da empresa pelo host só entre as que têm o schema pronto (ADR 0040, item 7).

A reserva (`Empresa.schema_pronto_em` nulo) já tem o `Dominio`, gravado no passo 1 da criação,
mas é inalcançável: o host dela responde 404 como um host desconhecido, inclusive em `entrar` e
`renovar`, porque nenhum pedido chega a ela.
"""

from typing import Any

from django.db.models import Q
from django_tenants.middleware.main import TenantMainMiddleware
from django_tenants.utils import get_public_schema_name


class EmpresaProntaMiddleware(TenantMainMiddleware):
    def get_tenant(self, domain_model: Any, hostname: str) -> Any:
        pronta = Q(tenant__schema_pronto_em__isnull=False) | Q(
            tenant__schema_name=get_public_schema_name()
        )
        dominio = domain_model.objects.select_related("tenant").filter(pronta).get(domain=hostname)
        return dominio.tenant
