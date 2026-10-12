"""Assinantes de eventos de outros apps (ADR 0011). Registrados ao importar, no `ready()`."""

from typing import Any

from comum.eventos import assinante

from . import services


@assinante("aprovacoes.pedido_decidido")
def aplicar_decisao(
    *, tipo: str, status: str, origem_tipo: str, origem_id: int, motivo: str = "", **_: Any
) -> None:
    """APR-04 (diferença no caixa) e APR-03 (despesa acima de R$ 500)."""
    if tipo == "APR-04" and origem_tipo == "caixa":
        services.decidir_diferenca_do_caixa(origem_id, status, motivo)
    elif tipo == "APR-03" and origem_tipo == "despesa":
        services.decidir_despesa(origem_id, status, motivo)
