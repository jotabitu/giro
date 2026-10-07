"""Permissões do DRF comuns a todos os apps.

Perfis e permissões extras são valores fechados de `contas.Usuario` (USR-03); aqui eles chegam
como texto para que `comum` não dependa de `contas` (ADR 0011). O escopo por filial (USR-07)
entra com o app `filiais` (T-012).
"""

from typing import TYPE_CHECKING, Any

from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import SAFE_METHODS, BasePermission

from comum.empresa import STATUS_OPERANDO
from comum.erros import EmpresaSemOperacao

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class EmpresaOperando(BasePermission):
    """Recusa escrita quando a empresa está suspensa, pausada ou cancelada (403)."""

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        if request.method in SAFE_METHODS:
            return True
        empresa = getattr(request, "tenant", None)
        if empresa is None or empresa.schema_name == get_public_schema_name():
            return True
        status = getattr(empresa, "status", None)
        if status not in STATUS_OPERANDO:
            raise EmpresaSemOperacao(str(status))
        return True


def exige_perfil(*perfis: str) -> type[BasePermission]:
    """`permission_classes = [IsAuthenticated, exige_perfil("administrador", "gerente")]`."""

    class PerfilPermitido(BasePermission):
        message = "Seu perfil não tem acesso a esta ação."

        def has_permission(self, request: "Request", view: "APIView") -> bool:
            usuario: Any = request.user
            return bool(usuario and getattr(usuario, "perfil", None) in perfis)

    PerfilPermitido.__name__ = f"Perfil_{'_'.join(perfis)}"
    return PerfilPermitido
