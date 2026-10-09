"""Leituras dos pedidos de aprovação. `pendente` serve à porta `comum.aprovacoes` (ADR 0019)."""

from comum.aprovacoes import PedidoRef

from .models import PedidoAprovacao
from .services import ref


def pendente(*, tipo: str, origem_tipo: str, origem_id: int) -> PedidoRef | None:
    pedido = PedidoAprovacao.objects.filter(
        tipo=tipo, origem_tipo=origem_tipo, origem_id=origem_id, status="pendente"
    ).first()
    return ref(pedido) if pedido is not None else None
