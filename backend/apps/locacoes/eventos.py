"""Assinantes de eventos de outros apps (ADR 0011). Registrados ao importar, no `ready()`."""

from datetime import datetime
from typing import Any

from comum.eventos import assinante

from . import services


@assinante("financeiro.parcela_paga")
def primeiro_pagamento(*, origem_tipo: str = "", origem_id: int | None = None, **_: Any) -> None:
    """1ª parcela e caução pagas: uma das três condições da ativação."""
    if origem_tipo == services.ORIGEM and origem_id is not None:
        services.registrar_pagamento(origem_id)


@assinante("contratos.contrato_assinado")
def contrato_assinado(
    *,
    origem_tipo: str,
    origem_id: int,
    tipo: str = "contrato",
    assinado_em: datetime | None = None,
    **_: Any,
) -> None:
    """O contrato assinado é outra condição da ativação; o aditivo da renovação não conta."""
    if origem_tipo == services.ORIGEM and tipo == "contrato":
        services.registrar_contrato_assinado(origem_id, assinado_em)


@assinante("aprovacoes.pedido_decidido")
def decisao_do_pedido(
    *,
    tipo: str,
    status: str,
    origem_tipo: str,
    origem_id: int,
    motivo: str = "",
    dados: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    """APR-01: aprovado refaz as parcelas em aberto; recusado avisa o vendedor. APR-02: aprovado
    cancela (ou aprova o encerramento antecipado); recusado avisa quem pediu."""
    if origem_tipo != services.ORIGEM:
        return
    if tipo == "APR-01":
        services.aplicar_decisao_desconto(origem_id, status, motivo)
    elif tipo == "APR-02":
        services.aplicar_decisao_cancelamento(origem_id, status, motivo, dados)
