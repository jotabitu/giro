"""Permissões do DRF comuns a todos os apps.

Perfis e permissões extras são valores fechados de `contas.Usuario` (USR-03); aqui eles chegam
como texto para que `comum` não dependa de `contas` (ADR 0011). O escopo por filial (USR-07)
vem do app `filiais`, que registra `filiais_do_usuario` no `ready()`; `EscopoDeFilial` confere o
cabeçalho `X-Filial` em toda requisição da empresa.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import SAFE_METHODS, BasePermission

from comum.empresa import STATUS_OPERANDO
from comum.erros import EmpresaSemOperacao, SemPermissao

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


# --- Escopo de filial (USR-07) ---

CABECALHO_FILIAL = "HTTP_X_FILIAL"
TODAS_AS_FILIAIS = "todas"
PERFIL_QUE_VE_TODAS = "administrador"

_filiais_do_usuario: Callable[[Any], set[int]] | None = None


def registrar_escopo_de_filial(funcao: Callable[[Any], set[int]]) -> None:
    """Chamado pelo `ready()` do app `filiais`: ids das filiais ativas da pessoa."""
    global _filiais_do_usuario
    _filiais_do_usuario = funcao


def filiais_permitidas(usuario: Any) -> set[int]:
    return _filiais_do_usuario(usuario) if _filiais_do_usuario is not None else set()


def pode_escolher_todas(usuario: Any) -> bool:
    return getattr(usuario, "perfil", "") == PERFIL_QUE_VE_TODAS


def sem_acesso_a_filial() -> SemPermissao:
    return SemPermissao("USR-07", "Você não tem acesso a esta filial")


def filial_pedida(request: "Request") -> int | str | None:
    """O `X-Filial` conferido: id, `"todas"` ou `None` (sem cabeçalho).

    Filial fora do escopo da pessoa: 403 `USR-07`.
    """
    valor = str(request.META.get(CABECALHO_FILIAL, "")).strip()
    if not valor:
        return None
    usuario = request.user
    if valor == TODAS_AS_FILIAIS:
        if pode_escolher_todas(usuario):
            return TODAS_AS_FILIAIS
        raise sem_acesso_a_filial()
    if not valor.isdigit() or int(valor) not in filiais_permitidas(usuario):
        raise sem_acesso_a_filial()
    return int(valor)


class EscopoDeFilial(BasePermission):
    """Recusa `X-Filial` de filial fora do escopo da pessoa (403 `USR-07`)."""

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        empresa = getattr(request, "tenant", None)
        if empresa is None or empresa.schema_name == get_public_schema_name():
            return True
        if not getattr(request.user, "is_authenticated", False):
            return True
        filial_pedida(request)
        return True
