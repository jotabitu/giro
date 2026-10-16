"""Assinantes de `movimentacoes` (ADR 0011, item 3): rodam na transação de quem publica."""

from typing import Any

from comum.eventos import assinante

from . import services


@assinante("veiculos.veiculo_baixado")
def cancelar_pela_baixa(*, veiculo_id: int, motivo_texto: str, **_: Any) -> None:
    """MOV-03 (T-310, T-311): a baixa encerra a movimentação aberta do veículo, na mesma
    transação; erro aqui desfaz a baixa."""
    services.cancelar_pela_baixa(veiculo_id, motivo_texto)
