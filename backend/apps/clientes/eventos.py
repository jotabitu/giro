"""Assinantes de eventos de outros apps (ADR 0011). Registrados ao importar, no `ready()`."""

from datetime import date
from typing import Any

from comum.eventos import assinante

from . import services


@assinante("aprovacoes.pedido_decidido")
def aplicar_desbloqueio(
    *,
    tipo: str,
    status: str,
    origem_tipo: str,
    origem_id: int,
    motivo_pedido: str = "",
    **_: Any,
) -> None:
    """APR-05 aprovado: o cliente volta a `ativo` (ou `incompleto`). Recusado ou cancelado:
    continua bloqueado."""
    if tipo != "APR-05" or origem_tipo != "cliente" or status != "aprovado":
        return
    services.aplicar_desbloqueio_aprovado(origem_id, motivo_pedido)


@assinante("financeiro.parcela_atrasou")
def bloquear_com_15_dias(
    *, cliente_id: int, dias_atraso: int, vencimento: date | None = None, **_: Any
) -> None:
    """CLI-05, LOC-07: 15 dias de atraso em qualquer valor bloqueiam o cliente."""
    services.bloquear_por_atraso(cliente_id, dias_atraso, vencimento)


@assinante("financeiro.parcela_paga")
def desbloquear_ao_quitar(*, cliente_id: int | None = None, **_: Any) -> None:
    """CLI-05: o bloqueio por atraso sai sozinho quando não resta conta com 15 dias."""
    if cliente_id is not None:
        services.desbloquear_por_quitacao(cliente_id)
