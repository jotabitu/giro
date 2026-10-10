"""Leituras das contas a receber e das comissões (FIN-01, FIN-09).

Interface para os outros apps: `contas_da_origem`, `representacao_conta`, `primeiro_pagamento_em`,
`pago_da_origem_centavos`, `reembolsos_da_origem`, `anotar_resumo_da_origem` (uma query para a
lista inteira da origem), `comissoes_confirmadas_centavos` e `devido_ate` (a única conta da
FIN-03).
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.db.models import Count, IntegerField, Min, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.contratos.selectors import permite_juros
from apps.empresas.selectors import configuracao
from comum.dinheiro import aplicar_percentual, juros_pro_rata

from .models import Comissao, ContaReceber, Reembolso, StatusComissao, StatusConta, TipoConta


def status_exibido(status: str, vencimento: date, hoje: date) -> str:
    """FIN-01: `aberta` aparece como `vence_hoje` ou `atrasada` pela data (modelo de dados)."""
    if status != StatusConta.ABERTA:
        return status
    if vencimento < hoje:
        return "atrasada"
    if vencimento == hoje:
        return "vence_hoje"
    return status


@dataclass(frozen=True)
class Devido:
    """O que uma conta em aberto vale num dia (FIN-03)."""

    valor_centavos: int
    multa_centavos: int
    juros_centavos: int
    dias_atraso: int

    @property
    def total_centavos(self) -> int:
        return self.valor_centavos + self.multa_centavos + self.juros_centavos


def devido_ate(conta: ContaReceber, dia: date) -> Devido:
    """FIN-03, a única conta de multa e juros: o acerto da devolução (DEV-01), o valor do dia das
    contas a receber e o recebimento no caixa usam esta função. O atraso conta do dia seguinte
    ao vencimento, ou ao dia em que a conta nasceu, se ela nasceu vencida, até `dia`. Multa uma
    vez, a partir de 1 dia de atraso; juros pro rata dia, com mês de 30 dias. Sem a cláusula no
    contrato da origem, não cobra nenhum dos dois. Ex.: 29940 vencida em 30 set, paga em 07 out,
    2% + 1% ao mês → 29940 + 599 + 70 = 30609."""
    inicio = max(conta.vencimento, timezone.localdate(conta.criado_em))
    dias = (dia - inicio).days
    if dias <= 0 or not permite_juros(conta.origem_tipo, conta.origem_id):
        return Devido(conta.valor_centavos, 0, 0, max(dias, 0))
    taxas = configuracao()
    return Devido(
        conta.valor_centavos,
        aplicar_percentual(conta.valor_centavos, taxas.multa_atraso_pct),
        juros_pro_rata(conta.valor_centavos, taxas.juros_mes_pct, dias),
        dias,
    )


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


def pago_da_origem_centavos(origem_tipo: str, origem_id: int) -> int:
    """O que o cliente já pagou na origem, com a caução (LOC-12: devolve tudo antes da retirada)."""
    total = ContaReceber.objects.filter(
        origem_tipo=origem_tipo, origem_id=origem_id, status=StatusConta.PAGA
    ).aggregate(total=Sum("valor_centavos"))["total"]
    return int(total or 0)


def abertas_vencendo_depois(origem_tipo: str, origem_id: int, dia: date) -> list[ContaReceber]:
    """Parcelas em aberto que vencem depois de `dia` (as que o encerramento antecipado cancela)."""
    return list(
        ContaReceber.objects.filter(
            origem_tipo=origem_tipo,
            origem_id=origem_id,
            status=StatusConta.ABERTA,
            tipo=TipoConta.PARCELA,
            vencimento__gt=dia,
        )
    )


def parcelas_canceladas_vencendo_entre(
    origem_tipo: str, origem_id: int, depois_de: date, antes_de: date
) -> list[ContaReceber]:
    """Parcelas canceladas que vencem depois de `depois_de` e antes de `antes_de` (as do mês
    que o encerramento antecipado do mensal em 4 semanais cancelou, LOC-13)."""
    return list(
        ContaReceber.objects.filter(
            origem_tipo=origem_tipo,
            origem_id=origem_id,
            status=StatusConta.CANCELADA,
            tipo=TipoConta.PARCELA,
            vencimento__gt=depois_de,
            vencimento__lt=antes_de,
        ).order_by("vencimento", "id")
    )


def reembolsos_da_origem(origem_tipo: str, origem_id: int) -> QuerySet[Reembolso]:
    return Reembolso.objects.filter(origem_tipo=origem_tipo, origem_id=origem_id)


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
