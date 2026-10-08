"""Assinantes de `empresas` (ADR 0011, item 3)."""

from typing import Any

from comum.eventos import assinante


@assinante("plataforma.empresa_criada")
def criar_configuracao_da_empresa(**_: Any) -> None:
    """Roda no schema da empresa nova, na transação de `criar_empresa`."""
    from .services import criar_configuracao_padrao

    criar_configuracao_padrao()
