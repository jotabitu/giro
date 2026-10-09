"""Assinantes de eventos de outros apps (ADR 0011). Registrados ao importar, no `ready()`."""

from typing import Any

from comum.eventos import assinante

from . import services


@assinante("aprovacoes.pedido_decidido")
def aplicar_correcao_de_km(
    *,
    pedido_id: int,
    tipo: str,
    status: str,
    origem_tipo: str,
    origem_id: int,
    dados: dict[str, Any],
    motivo_pedido: str = "",
    **_: Any,
) -> None:
    """APR-06 aprovado: o km vai para `km_novo`. Recusado ou cancelado: o km já ficou como
    estava, nada a fazer."""
    if tipo != "APR-06" or origem_tipo != "veiculo" or status != "aprovado":
        return
    services.aplicar_correcao_aprovada(
        origem_id, int(dados["km_novo"]), int(dados["km_anterior"]), motivo_pedido, pedido_id
    )
