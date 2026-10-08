"""Funções da equipe interna (PLT-09). A tabela é a do contrato; `eu.pode` sai daqui."""

from typing import TYPE_CHECKING, Any

from rest_framework.permissions import BasePermission

from comum.erros import SemPermissao

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

PODE: dict[str, frozenset[str]] = {
    "ver_empresas": frozenset({"dono", "suporte", "financeiro", "sucesso"}),
    "entrar_como_suporte": frozenset({"dono", "suporte", "sucesso"}),
    "estender_teste_e_mudar_plano": frozenset({"dono", "sucesso"}),
    "cobranca_e_faturas": frozenset({"dono", "financeiro"}),
    "suspender_empresa": frozenset({"dono", "financeiro"}),
    "planos_e_precos": frozenset({"dono"}),
    "equipe_interna": frozenset({"dono"}),
}


def pode(funcao: str) -> dict[str, bool]:
    return {permissao: funcao in funcoes for permissao, funcoes in PODE.items()}


def exige_permissao(permissao: str) -> type[BasePermission]:
    """`permission_classes = [IsAuthenticated, exige_permissao("ver_empresas")]`."""
    if permissao not in PODE:
        raise ValueError(f"Permissão da plataforma desconhecida: {permissao}")

    class PermissaoDaPlataforma(BasePermission):
        def has_permission(self, request: "Request", view: "APIView") -> bool:
            usuario: Any = request.user
            if getattr(usuario, "funcao_plataforma", "") not in PODE[permissao]:
                raise SemPermissao("PLT-09", "Sua função não permite esta ação")
            return True

    PermissaoDaPlataforma.__name__ = f"Pode_{permissao}"
    return PermissaoDaPlataforma
