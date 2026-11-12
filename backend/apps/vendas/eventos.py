"""Assinantes de `vendas` (ADR 0011, item 3): rodam na transação de quem publica."""

from datetime import datetime
from typing import Any

from comum.eventos import assinante

from . import services


@assinante("locacoes.locacao_quitada")
def locacao_quitada(
    *,
    locacao_id: int,
    codigo: str,
    filial_id: int,
    cliente_id: int,
    veiculo_id: int,
    vendedor_id: int | None,
    quitada_em: datetime,
    **_: Any,
) -> None:
    """VEN-11 (T-420, ADR 0037, item 4): a quitação cria a venda de R$ 0,00 e passa o veículo a
    `vendido`, na mesma transação; erro aqui desfaz a quitação."""
    services.criar_venda_da_quitacao(
        locacao_id=locacao_id,
        codigo=codigo,
        filial_id=filial_id,
        cliente_id=cliente_id,
        veiculo_id=veiculo_id,
        vendedor_id=vendedor_id,
        quitada_em=quitada_em,
    )
