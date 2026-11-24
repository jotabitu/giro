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


@assinante("contratos.contrato_assinado")
def contrato_assinado(
    *,
    origem_tipo: str,
    origem_id: int,
    tipo: str = "contrato",
    contrato_id: int | None = None,
    assinado_em: datetime | None = None,
    **_: Any,
) -> None:
    """VEN-15 (ADR 0042, item 1): uma das duas condições da conclusão; o aditivo não conta."""
    if origem_tipo == services.ORIGEM and tipo == "contrato":
        services.registrar_contrato_assinado(origem_id, contrato_id, assinado_em)


@assinante("financeiro.parcela_paga")
def entrada_paga(
    *,
    origem_tipo: str = "",
    origem_id: int | None = None,
    tipo: str = "",
    conta_id: int | None = None,
    pago_em: datetime | None = None,
    **_: Any,
) -> None:
    """VEN-15 (ADR 0042, item 1): a entrada (ou o total à vista) paga, a outra condição."""
    if origem_tipo == services.ORIGEM and tipo == "entrada" and origem_id is not None:
        services.registrar_entrada_paga(origem_id, conta_id, pago_em)


@assinante("aprovacoes.pedido_decidido")
def decisao_do_pedido(
    *,
    tipo: str,
    status: str,
    origem_tipo: str,
    origem_id: int,
    motivo: str = "",
    decidido_por_id: int | None = None,
    **_: Any,
) -> None:
    """APR-01 da venda (ADR 0042, item 5): aprovado, recusado ou cancelado volta a venda ao
    estado de antes do pedido (`VEN-13`), na transação da decisão."""
    if origem_tipo == services.ORIGEM and tipo == "APR-01":
        services.aplicar_decisao_desconto(origem_id, status, motivo, decidido_por_id)
