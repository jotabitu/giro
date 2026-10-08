"""Assinantes de `contas` (ADR 0011, item 3) e o contador de usuários do plano (PLT-03)."""

from typing import Any

from comum.eventos import assinante

from .models import StatusUsuario, Usuario


@assinante("plataforma.empresa_criada")
def convidar_administrador_da_empresa(
    *, empresa_id: int, administrador: dict[str, Any], **_: Any
) -> None:
    """Roda no schema da empresa nova, na transação de `criar_empresa` (PLT-01)."""
    from .services import convidar_administrador

    convidar_administrador(
        nome=administrador["nome"],
        email=administrador["email"],
        celular=administrador.get("celular", ""),
    )


def contar_usuarios() -> int:
    """Contam no limite: `ativo` e `convite_pendente` (USR-01, USR-04)."""
    return int(
        Usuario.objects.filter(
            status__in=[StatusUsuario.ATIVO, StatusUsuario.CONVITE_PENDENTE]
        ).count()
    )
