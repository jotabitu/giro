"""Leituras das contas a receber e das comissões (FIN-01, FIN-09).

Interface para os outros apps: `contas_da_origem`, `representacao_conta`, `primeiro_pagamento_em`,
`anotar_resumo_da_origem` (uma query para a lista inteira da origem) e
`comissoes_confirmadas_centavos`.
"""

from datetime import date, datetime
from typing import Any

from django.db.models import Count, IntegerField, Min, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from .models import Comissao, ContaReceber, StatusComissao, StatusConta, TipoConta


def status_exibido(status: str, vencimento: date, hoje: date) -> str:
    """FIN-01: `aberta` aparece como `vence_hoje` ou `atrasada` pela data (modelo de dados)."""
    if status != StatusConta.ABERTA:
        return status
    if vencimento < hoje:
        return "atrasada"
    if vencimento == hoje:
        return "vence_hoje"
    return status


def contas_da_origem(origem_tipo: str, origem_id: int) -> QuerySet[ContaReceber]:
    """Parcelas pela ordem, depois caução e outras. As canceladas não aparecem."""
    return (
        ContaReceber.objects.filter(origem_tipo=origem_tipo, origem_id=origem_id)
        .exclude(status=StatusConta.CANCELADA)
        .order_by("vencimento", "tipo", "numero_parcela", "id")
    )


def representacao_conta(conta: ContaReceber, hoje: date) -> dict[str, Any]:
    return {
        "id": conta.pk,
        "tipo": conta.tipo,
        "numero": conta.numero_parcela,
        "total_parcelas": conta.total_parcelas,
        "vencimento": conta.vencimento,
        "valor_centavos": conta.valor_centavos,
        "status": status_exibido(conta.status, conta.vencimento, hoje),
        "forma": conta.forma or None,
        "pago_em": conta.pago_em,
        "observacao": conta.observacao or None,
    }


def primeiro_pagamento_em(origem_tipo: str, origem_id: int) -> datetime | None:
    """1ª parcela **e** caução pagas: o momento do último dos dois. Sem caução, só a parcela."""
    contas = list(
        contas_da_origem(origem_tipo, origem_id).filter(
            Q(tipo=TipoConta.PARCELA, numero_parcela=1) | Q(tipo=TipoConta.CAUCAO)
        )
    )
    parcela = [c for c in contas if c.tipo == TipoConta.PARCELA]
    if not parcela or any(c.status != StatusConta.PAGA for c in contas):
        return None
    return max(c.pago_em for c in contas if c.pago_em is not None)


def _soma(filtro: Q, origem_tipo: str) -> Subquery:
    return Subquery(
        ContaReceber.objects.filter(filtro, origem_tipo=origem_tipo, origem_id=OuterRef("pk"))
        .order_by()
        .values("origem_id")
        .annotate(total=Sum("valor_centavos"))
        .values("total"),
        output_field=IntegerField(),
    )


def anotar_resumo_da_origem(qs: QuerySet[Any], origem_tipo: str, hoje: date) -> QuerySet[Any]:
    """Para listas da origem, sem N+1: `fin_atrasado_centavos` (vencidas e não pagas),
    `fin_parcela_atrasada` (a mais antiga), `fin_pago_centavos` (com caução) e `fin_abertas`."""
    atrasada = Q(status=StatusConta.ABERTA, vencimento__lt=hoje)
    primeira_atrasada = Subquery(
        ContaReceber.objects.filter(
            atrasada, tipo=TipoConta.PARCELA, origem_tipo=origem_tipo, origem_id=OuterRef("pk")
        )
        .order_by()
        .values("origem_id")
        .annotate(n=Min("numero_parcela"))
        .values("n"),
        output_field=IntegerField(),
    )
    abertas = Subquery(
        ContaReceber.objects.filter(
            status=StatusConta.ABERTA, origem_tipo=origem_tipo, origem_id=OuterRef("pk")
        )
        .order_by()
        .values("origem_id")
        .annotate(n=Count("id"))
        .values("n"),
        output_field=IntegerField(),
    )
    return qs.annotate(  # type: ignore[no-any-return]
        fin_atrasado_centavos=Coalesce(_soma(atrasada, origem_tipo), 0),
        fin_parcela_atrasada=primeira_atrasada,
        fin_pago_centavos=Coalesce(_soma(Q(status=StatusConta.PAGA), origem_tipo), 0),
        fin_abertas=Coalesce(abertas, 0),
    )


def comissoes_confirmadas_centavos(usuario_id: int, mes: date) -> int:
    """FIN-10: confirmadas no mês (pagas no dia 5 do mês seguinte), ainda não pagas."""
    seguinte = date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)
    total = Comissao.objects.filter(
        usuario_id=usuario_id, status=StatusComissao.CONFIRMADA, mes_pagamento=seguinte
    ).aggregate(total=Sum("valor_centavos"))["total"]
    return int(total or 0)
