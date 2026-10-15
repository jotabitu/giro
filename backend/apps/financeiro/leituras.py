"""O que `financeiro` fornece aos apps de cima (ADR 0015), registrado no `ready()`.

- `clientes.Cliente`: bloco `financeiro` (`total_pago_centavos` sem caução, `em_aberto_centavos`
  das contas vencidas e não pagas, `a_devolver_centavos` dos reembolsos a fazer e
  `conta_mais_antiga_id`), bloco `historico` (item da análise, CLI-04), filtro `em_aberto`,
  contadores `contas_atrasadas_15_dias` e `dias_de_atraso` (CLI-05) e `em_aberto_centavos`
  (CLI-09) e o total `em_aberto_centavos` da lista (CA-017-03).
- `filiais.Filial`: contador `caixas`, os caixas `aberto` ou `aguardando_aprovacao` (FIL-06).
- `veiculos.Veiculo`: `custo_manutencao_ano_centavos` no bloco `indicadores_financeiros`
  (VEI-05, FIN-06); o `rendeu_no_ano_centavos` vem de `locacoes`, que sabe o veículo da locação.
"""

from datetime import timedelta
from typing import Any

from django.db.models import Exists, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce, Greatest, TruncDate

from comum import leituras, relogio

from . import selectors
from .models import ContaReceber, Despesa, Reembolso, StatusConta, StatusDespesa, TipoConta

CLIENTE = "clientes.Cliente"
FILIAL = "filiais.Filial"
VEICULO = "veiculos.Veiculo"
DIAS_PARA_BLOQUEIO = 15  # CLI-05
NOVO = {"situacao": "ok", "rotulo": "Cliente novo na empresa"}  # CLI-04


def _vencidas(hoje: Any) -> Q:
    return Q(status=StatusConta.ABERTA, vencimento__lt=hoje) & ~Q(tipo=TipoConta.CAUCAO)


def _soma_do_cliente(filtro: Q, modelo: Any = ContaReceber) -> Subquery:
    return Subquery(
        modelo.objects.filter(filtro, cliente_id=OuterRef("pk"))
        .order_by()
        .values("cliente_id")
        .annotate(total=Sum("valor_centavos"))
        .values("total"),
        output_field=IntegerField(),
    )


# --- clientes.Cliente ---


def anotar_cliente(queryset: QuerySet[Any]) -> QuerySet[Any]:
    hoje = relogio.hoje()
    mais_antiga = Subquery(
        ContaReceber.objects.filter(_vencidas(hoje), cliente_id=OuterRef("pk"))
        .order_by("vencimento", "id")
        .values("pk")[:1]
    )
    return queryset.annotate(  # type: ignore[no-any-return]
        fin_total_pago=Coalesce(
            _soma_do_cliente(Q(status=StatusConta.PAGA) & ~Q(tipo=TipoConta.CAUCAO)), 0
        ),
        fin_em_aberto=Coalesce(_soma_do_cliente(_vencidas(hoje)), 0),
        fin_a_devolver=Coalesce(_soma_do_cliente(Q(status="a_fazer"), Reembolso), 0),
        fin_conta_mais_antiga=mais_antiga,
    )


def montar_cliente(cliente: Any) -> dict[str, Any]:
    if not hasattr(cliente, "fin_em_aberto"):
        cliente = anotar_cliente(type(cliente).objects.filter(pk=cliente.pk)).get()
    return {
        "total_pago_centavos": int(cliente.fin_total_pago),
        "em_aberto_centavos": int(cliente.fin_em_aberto),
        "a_devolver_centavos": int(cliente.fin_a_devolver),
        "conta_mais_antiga_id": cliente.fin_conta_mais_antiga,
    }


def montar_historico(cliente: Any | None) -> dict[str, str]:
    """Item `historico` da análise do cadastro (CLI-04): atrasos na empresa, sem a caução, com o
    atraso contado como na FIN-03 (do dia seguinte ao mais tarde entre o vencimento e o dia em
    que a conta nasceu, em `America/Sao_Paulo`). Vale a primeira situação que servir. Sem conta
    nenhuma, ou na análise antes do cadastro (`None`), o cliente é novo na empresa."""
    if cliente is None:
        return dict(NOVO)
    contas = (
        ContaReceber.objects.filter(cliente_id=cliente.pk)
        .exclude(tipo=TipoConta.CAUCAO)
        .annotate(inicio_atraso=Greatest(F("vencimento"), TruncDate("criado_em")))
    )
    if not contas.exists():
        return dict(NOVO)
    if contas.filter(status=StatusConta.ABERTA, inicio_atraso__lt=relogio.hoje()).exists():
        return {"situacao": "problema", "rotulo": "Conta em atraso na empresa"}
    pagou_atrasado = (
        contas.filter(status=StatusConta.PAGA)
        .annotate(dia_pago=TruncDate("pago_em"))
        .filter(dia_pago__gt=F("inicio_atraso"))
        .exists()
    )
    if pagou_atrasado:
        return {"situacao": "pendente", "rotulo": "Já pagou com atraso na empresa"}
    return {"situacao": "ok", "rotulo": "Sem atraso na empresa"}


def _sem_anotacao(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset


def em_aberto(queryset: QuerySet[Any]) -> QuerySet[Any]:
    """Filtro `em_aberto` da lista de clientes: alguma conta vencida e não paga."""
    hoje = relogio.hoje()
    return queryset.filter(
        Exists(ContaReceber.objects.filter(_vencidas(hoje), cliente_id=OuterRef("pk")))
    )


def total_em_aberto(queryset: QuerySet[Any]) -> int:
    """`em_aberto_total_centavos` da lista: vencidas e não pagas dos clientes da lista."""
    hoje = relogio.hoje()
    total = ContaReceber.objects.filter(
        _vencidas(hoje), cliente_id__in=queryset.values("pk")
    ).aggregate(total=Sum("valor_centavos"))["total"]
    return int(total or 0)


def contas_atrasadas_15_dias(cliente_id: int) -> int:
    """CLI-05: contas do cliente com 15 dias ou mais de atraso (o desbloqueio espera zerar)."""
    limite = relogio.hoje() - timedelta(days=DIAS_PARA_BLOQUEIO)
    return int(
        ContaReceber.objects.filter(
            cliente_id=cliente_id, status=StatusConta.ABERTA, vencimento__lte=limite
        )
        .exclude(tipo=TipoConta.CAUCAO)
        .count()
    )


def dias_de_atraso(cliente_id: int) -> int:
    """CLI-05: os dias de atraso de hoje da conta vencida mais antiga do cliente, sem a caução
    (dia corrido em `America/Sao_Paulo`, como a FIN-03). Sem conta vencida, 0."""
    hoje = relogio.hoje()
    vencimento = (
        ContaReceber.objects.filter(_vencidas(hoje), cliente_id=cliente_id)
        .order_by("vencimento")
        .values_list("vencimento", flat=True)
        .first()
    )
    return (hoje - vencimento).days if vencimento is not None else 0


def em_aberto_centavos(cliente_id: int) -> int:
    return selectors.em_aberto_do_cliente(cliente_id, relogio.hoje())


# --- veiculos.Veiculo ---


def anotar_veiculo(queryset: QuerySet[Any]) -> QuerySet[Any]:
    ano = relogio.hoje().year
    custo = Subquery(
        Despesa.objects.filter(veiculo_id=OuterRef("pk"), data__year=ano)
        .exclude(status=StatusDespesa.RECUSADA)
        .order_by()
        .values("veiculo_id")
        .annotate(total=Sum("valor_centavos"))
        .values("total"),
        output_field=IntegerField(),
    )
    return queryset.annotate(fin_custo_ano=Coalesce(custo, 0))  # type: ignore[no-any-return]


def montar_veiculo(veiculo: Any) -> dict[str, Any]:
    if hasattr(veiculo, "fin_custo_ano"):
        return {"custo_manutencao_ano_centavos": int(veiculo.fin_custo_ano)}
    return {
        "custo_manutencao_ano_centavos": selectors.custo_do_veiculo_no_ano(
            veiculo.pk, relogio.hoje()
        )
    }


def registrar() -> None:
    leituras.registrar_anotacao(CLIENTE, "financeiro", anotar_cliente, montar_cliente)
    leituras.registrar_anotacao(CLIENTE, "historico", _sem_anotacao, montar_historico)
    leituras.registrar_filtro(CLIENTE, "em_aberto", em_aberto)
    leituras.registrar_contador(CLIENTE, "contas_atrasadas_15_dias", contas_atrasadas_15_dias)
    leituras.registrar_contador(CLIENTE, "dias_de_atraso", dias_de_atraso)
    leituras.registrar_contador(CLIENTE, "em_aberto_centavos", em_aberto_centavos)
    leituras.registrar_total(CLIENTE, "em_aberto_centavos", total_em_aberto)
    leituras.registrar_contador(FILIAL, "caixas", selectors.caixas_abertos_da_filial)
    leituras.registrar_anotacao(VEICULO, "indicadores_financeiros", anotar_veiculo, montar_veiculo)
