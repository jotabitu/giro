"""Abrir e cancelar pedidos de aprovação (ADR 0019). Único lugar que grava `PedidoAprovacao`.

Os outros apps chegam aqui só por `comum.aprovacoes` (registrado no `ready()`). A lista e a
decisão (aprovar e recusar, com o evento `aprovacoes.pedido_decidido`) entram na T-081.
"""

from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction

from comum import estados
from comum.aprovacoes import PedidoPendente, PedidoRef
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.eventos import publicar

from .models import PedidoAprovacao

S = PedidoAprovacao.Status


def ref(pedido: PedidoAprovacao) -> PedidoRef:
    return PedidoRef(id=pedido.pk, tipo=pedido.tipo, status=pedido.status)


def _pendente_igual(tipo: str, origem_tipo: str, origem_id: int) -> PedidoAprovacao | None:
    pedido: PedidoAprovacao | None = PedidoAprovacao.objects.filter(
        tipo=tipo, origem_tipo=origem_tipo, origem_id=origem_id, status=S.PENDENTE
    ).first()
    return pedido


def pedir(
    *,
    tipo: str,
    origem_tipo: str,
    origem_id: int,
    origem_codigo: str | None,
    filial_id: int,
    solicitante: Any,
    titulo: str,
    detalhe: str,
    motivo: str | None = None,
    valor_centavos: int | None = None,
    pct: Decimal | None = None,
    dados: dict[str, Any] | None = None,
) -> PedidoRef:
    """Grava o pedido `pendente` e a auditoria (APR-10), na transação de quem chama.

    O aviso ao gerente (sino e push) entra com o app `notificacoes`.
    """
    with transaction.atomic():
        existente = _pendente_igual(tipo, origem_tipo, origem_id)
        if existente is not None:
            raise PedidoPendente(existente.pk)
        try:
            with transaction.atomic():
                pedido = PedidoAprovacao.objects.create(
                    tipo=tipo,
                    origem_tipo=origem_tipo,
                    origem_id=origem_id,
                    origem_codigo=origem_codigo or "",
                    filial_id=filial_id,
                    solicitante=solicitante,
                    titulo=titulo,
                    detalhe=detalhe,
                    motivo_pedido=(motivo or "")[:300],
                    valor_centavos=valor_centavos,
                    pct=pct,
                    dados=dados or {},
                )
        except IntegrityError as erro:  # o mesmo pedido numa corrida
            existente = _pendente_igual(tipo, origem_tipo, origem_id)
            if existente is None:
                raise
            raise PedidoPendente(existente.pk) from erro
        registrar_evento(
            "pedido_aprovacao.pedir",
            Categoria.OPERACAO,
            objeto=pedido,
            depois=retrato(pedido),
            motivo=motivo or "",
            regra="APR-10",
        )
    return ref(pedido)


def cancelar_pendentes(*, origem_tipo: str, origem_id: int, motivo: str) -> int:
    """A origem deixou de existir ou mudou: os pendentes ficam `cancelado` e publicam
    `aprovacoes.pedido_decidido`."""
    cancelados = 0
    with transaction.atomic():
        pedidos = PedidoAprovacao.objects.select_for_update().filter(
            origem_tipo=origem_tipo, origem_id=origem_id, status=S.PENDENTE
        )
        for pedido in pedidos:
            estados.transicionar(
                pedido, S.CANCELADO, motivo=motivo, acao="pedido_aprovacao.cancelar"
            )
            publicar(
                "aprovacoes.pedido_decidido",
                pedido_id=pedido.pk,
                tipo=pedido.tipo,
                status=S.CANCELADO,
                origem_tipo=pedido.origem_tipo,
                origem_id=pedido.origem_id,
                dados=pedido.dados,
                decidido_por_id=None,
                motivo=motivo,
            )
            cancelados += 1
    return cancelados
