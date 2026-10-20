"""Leituras dos pedidos de aprovação: a tabela "Quem decide" (APR-01 a APR-06), o escopo de
filial, a lista e a representação (docs/api/aprovacoes.md). `pendente` serve à porta
`comum.aprovacoes` (ADR 0019).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    FloatField,
    Min,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Extract
from django.utils import timezone

from comum import relogio
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


MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)  # fmt: skip


def inicio_do_mes() -> datetime:
    """APR-12: o mês corrente em `America/Sao_Paulo`, pelo dia da decisão."""
    hoje = timezone.localtime(relogio.agora())
    return hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def filtrar(
    qs: QuerySet[PedidoAprovacao], *, status: str | None, tipo: str | None, minhas: bool = False
) -> QuerySet[PedidoAprovacao]:
    """Uma aba (T-201). Pendentes (padrão): do mais antigo. Aprovadas e Recusadas: as decididas
    no mês corrente, da mais recente. Meus pedidos: qualquer status e mês, os pendentes primeiro
    (do mais antigo), depois os outros pela decisão ou cancelamento, do mais recente; a ordem
    vai em `ordem_da_aba`, um número só, para a paginação por cursor."""
    if tipo in TipoPedido.values:
        qs = qs.filter(tipo=tipo)
    if minhas:
        if status in S.values:
            qs = qs.filter(status=status)
        epoca = Extract("criado_em", "epoch")
        return qs.annotate(
            ordem_da_aba=Case(
                When(status=S.PENDENTE, then=epoca - Value(1e11)),
                default=-Extract("decidido_em", "epoch"),
                output_field=FloatField(),
            )
        )
    status = status if status in S.values else S.PENDENTE
    qs = qs.filter(status=status)
    if status == S.PENDENTE:
        return qs.annotate(ordem_da_aba=Extract("criado_em", "epoch"))
    return qs.filter(decidido_em__gte=inicio_do_mes()).annotate(
        ordem_da_aba=-Extract("decidido_em", "epoch")
    )


def _ha(desde: datetime) -> str:
    minutos = int((relogio.agora() - desde).total_seconds() // 60)
    if minutos < 60:
        return f"há {max(minutos, 0)} min"
    if minutos < 24 * 60:
        return f"há {minutos // 60} h"
    dias = minutos // (24 * 60)
    return f"há {dias} dia" if dias == 1 else f"há {dias} dias"


def _duracao(minutos: int) -> str:
    horas, resto = divmod(minutos, 60)
    if horas == 0:
        return f"{resto} min"
    return f"{horas} h" if resto == 0 else f"{horas} h {resto:02d} min"


def indicadores_e_contagens(
    decide: QuerySet[PedidoAprovacao], minhas: QuerySet[PedidoAprovacao]
) -> tuple[dict[str, Any], dict[str, int]]:
    """APR-12 (T-201): os números da tela inteira, sobre os pedidos que a pessoa decide (já no
    escopo de filial e sem os próprios, salvo o administrador). Cancelado não conta. Uma
    consulta agregada por indicador."""
    inicio = inicio_do_mes()
    no_mes = decide.filter(decidido_em__gte=inicio)
    esperando = decide.filter(status=S.PENDENTE).aggregate(
        quantidade=Count("id"), mais_antigo=Min("criado_em")
    )
    aprovadas = no_mes.filter(status=S.APROVADO).aggregate(
        quantidade=Count("id"),
        media=Avg(
            ExpressionWrapper(F("decidido_em") - F("criado_em"), output_field=DurationField())
        ),
    )
    recusadas = no_mes.filter(status=S.RECUSADO).count()
    descontos = no_mes.filter(status=S.APROVADO, tipo=TipoPedido.APR_01).aggregate(
        quantidade=Count("id"), valor=Sum("valor_centavos")
    )
    media: timedelta | None = aprovadas["media"]
    tempo_medio = (
        int((Decimal(media.total_seconds()) / 60).quantize(Decimal("1"), ROUND_HALF_UP))
        if media is not None and aprovadas["quantidade"]
        else None
    )
    mes = MESES[inicio.month - 1]
    quantos_descontos = descontos["quantidade"]
    indicadores = {
        "mes": inicio.strftime("%Y-%m"),
        "esperando": {
            "quantidade": esperando["quantidade"],
            "mais_antigo_em": esperando["mais_antigo"],
            "contexto": (
                f"mais antigo {_ha(esperando['mais_antigo'])}"
                if esperando["mais_antigo"] is not None
                else None
            ),
        },
        "aprovadas": {
            "titulo": f"Aprovadas em {mes}",
            "quantidade": aprovadas["quantidade"],
            "tempo_medio_min": tempo_medio,
            "contexto": (
                f"tempo médio de {_duracao(tempo_medio)}" if tempo_medio is not None else None
            ),
        },
        "recusadas": {
            "titulo": f"Recusadas em {mes}",
            "quantidade": recusadas,
            "contexto": "sempre com motivo",
        },
        "descontos": {
            "titulo": "Descontos aprovados",
            "valor_centavos": descontos["valor"] or 0,
            "quantidade": quantos_descontos,
            "contexto": (
                "em 1 pedido" if quantos_descontos == 1 else f"em {quantos_descontos} pedidos"
            ),
        },
    }
    contagens = {
        "pendente": esperando["quantidade"],
        "aprovado": aprovadas["quantidade"],
        "recusado": recusadas,
        "minhas_pendentes": minhas.filter(status=S.PENDENTE).count(),
    }
    return indicadores, contagens


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
        "resumo": pedido.resumo or None,
        "pode_decidir": quem.decide(pedido),
        "pode_cancelar": pedido.status == S.PENDENTE and pedido.solicitante_id == quem.usuario_id,
        # APR-09: quem decidiu foi quem pediu (só o administrador chega a isso).
        "proprio_pedido": pedido.decidido_pelo_solicitante,
    }
