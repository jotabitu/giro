"""Leituras dos pedidos de aprovação: a tabela "Quem decide" (APR-01 a APR-06), o escopo de
filial, a lista e a representação (docs/api/aprovacoes.md). `pendente` serve à porta
`comum.aprovacoes` (ADR 0019).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db.models import Q, QuerySet

from comum.aprovacoes import PedidoRef
from comum.permissoes import filiais_permitidas, pode

from .models import PedidoAprovacao, TipoPedido
from .services import ref

S = PedidoAprovacao.Status
GESTAO = frozenset({"gerente", "administrador"})
DECIDE = ("aprova", "sim")


def pendente(*, tipo: str, origem_tipo: str, origem_id: int) -> PedidoRef | None:
    pedido = PedidoAprovacao.objects.filter(
        tipo=tipo, origem_tipo=origem_tipo, origem_id=origem_id, status="pendente"
    ).first()
    return ref(pedido) if pedido is not None else None


# --- Quem decide (contrato de aprovações) ---


def _gestao(usuario: Any) -> bool:
    return getattr(usuario, "perfil", "") in GESTAO


# APR-01 e APR-02 também com as permissões extras `aprovar_desconto` e `cancelar_contrato`
# (USR-03), que chegam como `aprova` em `pode`.
QUEM_DECIDE: dict[str, Callable[[Any], bool]] = {
    TipoPedido.APR_01: lambda u: pode(u, "desconto_acima_limite") in DECIDE,
    TipoPedido.APR_02: lambda u: pode(u, "locacoes_cancelar") in DECIDE,
    TipoPedido.APR_03: _gestao,
    TipoPedido.APR_04: _gestao,
    TipoPedido.APR_05: _gestao,
    TipoPedido.APR_06: _gestao,
}


def tipos_que_decide(usuario: Any) -> set[str]:
    return {str(tipo) for tipo, decide in QUEM_DECIDE.items() if decide(usuario)}


@dataclass(frozen=True)
class Decisor:
    """Quem decide, calculado uma vez por requisição: os tipos e as filiais (`None` = todas,
    o administrador, inclusive as filiais desativadas). `decide_os_proprios`: só o
    administrador decide o próprio pedido (APR-09, T-250)."""

    usuario_id: int
    tipos: frozenset[str]
    filiais: frozenset[int] | None
    decide_os_proprios: bool = False

    def decide(self, pedido: PedidoAprovacao) -> bool:
        return (
            pedido.status == S.PENDENTE
            and (self.decide_os_proprios or pedido.solicitante_id != self.usuario_id)  # APR-09
            and pedido.tipo in self.tipos
            and (self.filiais is None or pedido.filial_id in self.filiais)
        )


def decisor(usuario: Any) -> Decisor:
    todas = getattr(usuario, "perfil", "") == "administrador"
    return Decisor(
        usuario.pk,
        frozenset(tipos_que_decide(usuario)),
        None if todas else frozenset(filiais_permitidas(usuario)),
        decide_os_proprios=todas,
    )


def que_decide(quem: Decisor) -> QuerySet[PedidoAprovacao]:
    """Pedidos dos tipos que a pessoa decide, nas filiais dela, sem os que ela fez (APR-09);
    os do administrador entram, porque ele pode decidi-los (APR-12, T-250)."""
    qs = PedidoAprovacao.objects.filter(tipo__in=quem.tipos)
    if quem.filiais is not None:
        qs = qs.filter(filial_id__in=quem.filiais)
    return qs if quem.decide_os_proprios else qs.exclude(solicitante_id=quem.usuario_id)


def visiveis(quem: Decisor) -> QuerySet[PedidoAprovacao]:
    """Os que a pessoa decide mais os que ela fez. Fora disso, 404."""
    return PedidoAprovacao.objects.filter(
        Q(pk__in=que_decide(quem).values("pk")) | Q(solicitante_id=quem.usuario_id)
    )


# --- Lista ---


def filtrar(
    qs: QuerySet[PedidoAprovacao], *, status: str | None, tipo: str | None
) -> QuerySet[PedidoAprovacao]:
    """Padrão `pendente`."""
    qs = qs.filter(status=status if status in S.values else S.PENDENTE)
    if tipo in TipoPedido.values:
        qs = qs.filter(tipo=tipo)
    return qs


def contagens(qs: QuerySet[PedidoAprovacao]) -> dict[str, int]:
    """`pendente` alimenta o sino do gerente."""
    return {"pendente": qs.filter(status=S.PENDENTE).count()}


# --- Representação ---


def _id_nome(objeto: Any) -> dict[str, Any] | None:
    return {"id": objeto.pk, "nome": objeto.nome} if objeto is not None else None


def representacao(pedido: PedidoAprovacao, quem: Decisor) -> dict[str, Any]:
    return {
        "id": pedido.pk,
        "tipo": pedido.tipo,
        "status": pedido.status,
        "titulo": pedido.titulo,
        "detalhe": pedido.detalhe,
        "origem": {
            "tipo": pedido.origem_tipo,
            "id": pedido.origem_id,
            "codigo": pedido.origem_codigo or None,
        },
        "filial": _id_nome(pedido.filial),
        "solicitante": _id_nome(pedido.solicitante),
        "pedido_em": pedido.criado_em,
        "motivo_pedido": pedido.motivo_pedido or None,
        "valor_centavos": pedido.valor_centavos,
        "pct": pedido.pct,
        "decidido_por": _id_nome(pedido.aprovador),
        "decidido_em": pedido.decidido_em,
        "motivo_recusa": pedido.motivo_recusa or None,
        "pode_decidir": quem.decide(pedido),
        # APR-09: quem decidiu foi quem pediu (só o administrador chega a isso).
        "proprio_pedido": pedido.decidido_pelo_solicitante,
    }
