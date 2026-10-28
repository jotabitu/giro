"""Leituras das contas a receber, do caixa, das despesas e das comissões (FIN-01 a FIN-09,
FIN-15).

Interface para os outros apps: `contas_da_origem`, `representacao_conta`, `primeiro_pagamento_em`,
`pago_da_origem_centavos`, `reembolsos_da_origem`, `anotar_resumo_da_origem` (uma query para a
lista inteira da origem), `comissoes_confirmadas_centavos`, `devido_ate` (a única conta da
FIN-03) e as leituras do painel (`relatorios`).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import Count, IntegerField, Min, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.contratos.selectors import permite_juros
from apps.empresas.models import ConfiguracaoEmpresa
from apps.empresas.selectors import configuracao
from apps.veiculos.selectors import frota_ativa_em
from apps.veiculos.services import normalizar_placa
from comum import arquivos, leituras
from comum.dinheiro import aplicar_percentual, formatar_reais, juros_pro_rata
from comum.erros import ErroDeValidacao

from .models import (
    Caixa,
    CobrancaExterna,
    Comissao,
    ContaReceber,
    Despesa,
    FormaMovimento,
    FormaPagamento,
    FormaReembolso,
    MotivoPendencia,
    MovimentoCaixa,
    OrigemTipo,
    PendenciaPagamento,
    Reembolso,
    StatusCaixa,
    StatusCobranca,
    StatusComissao,
    StatusConta,
    StatusDespesa,
    StatusPendencia,
    StatusReembolso,
    TipoCobranca,
    TipoConta,
    TipoMovimento,
    texto_de_busca,
)


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


def devido_ate(
    conta: ContaReceber,
    dia: date,
    *,
    cobra_juros: bool | None = None,
    taxas: ConfiguracaoEmpresa | None = None,
) -> Devido:
    """FIN-03, a única conta de multa e juros: o acerto da devolução (DEV-01), o valor do dia das
    contas a receber e o recebimento no caixa usam esta função. O atraso conta do dia seguinte
    ao vencimento, ou ao dia em que a conta nasceu, se ela nasceu vencida, até `dia`. Multa uma
    vez, a partir de 1 dia de atraso; juros pro rata dia, com mês de 30 dias. Sem a cláusula no
    contrato da origem, não cobra nenhum dos dois. Ex.: 29940 vencida em 30 set, paga em 07 out,
    2% + 1% ao mês → 29940 + 599 + 70 = 30609.

    `cobra_juros` e `taxas` já lidos poupam uma consulta por conta numa lista."""
    inicio = max(conta.vencimento, timezone.localdate(conta.criado_em))
    dias = (dia - inicio).days
    if dias <= 0:
        return Devido(conta.valor_centavos, 0, 0, 0)
    if cobra_juros is None:
        cobra_juros = permite_juros(conta.origem_tipo, conta.origem_id)
    if not cobra_juros:
        return Devido(conta.valor_centavos, 0, 0, dias)
    taxas = taxas or configuracao()
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
    `fin_parcela_atrasada` (a mais antiga), `fin_pago_centavos` (com caução),
    `fin_pago_sem_caucao_centavos` (FIN-13, a linha da lista de locações) e `fin_abertas`."""
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
        fin_pago_sem_caucao_centavos=Coalesce(
            _soma(Q(status=StatusConta.PAGA) & ~Q(tipo=TipoConta.CAUCAO), origem_tipo), 0
        ),
        fin_abertas=Coalesce(abertas, 0),
    )


def comissoes_confirmadas_centavos(usuario_id: int, mes: date) -> int:
    """FIN-10: confirmadas no mês (pagas no dia 5 do mês seguinte), ainda não pagas."""
    seguinte = date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)
    total = Comissao.objects.filter(
        usuario_id=usuario_id, status=StatusComissao.CONFIRMADA, mes_pagamento=seguinte
    ).aggregate(total=Sum("valor_centavos"))["total"]
    return int(total or 0)


# --- Painel (`relatorios`, docs/api/painel.md) ---


@dataclass(frozen=True)
class Soma:
    centavos: int
    quantidade: int
    clientes: int = 0


def contas_do_painel(filiais: Iterable[int]) -> QuerySet[ContaReceber]:
    """FIN-15: contas das filiais do escopo, sem caução e sem as canceladas e renegociadas.
    Valores sem multa e juros."""
    return ContaReceber.objects.filter(filial_id__in=list(filiais)).exclude(
        Q(tipo=TipoConta.CAUCAO) | Q(status__in=(StatusConta.CANCELADA, StatusConta.RENEGOCIADA))
    )


def _somar(qs: QuerySet[ContaReceber]) -> Soma:
    total = qs.aggregate(
        centavos=Coalesce(Sum("valor_centavos"), 0),
        quantidade=Count("id"),
        clientes=Count("cliente_id", distinct=True),
    )
    return Soma(int(total["centavos"]), int(total["quantidade"]), int(total["clientes"]))


def atrasadas(filiais: Iterable[int], hoje: date, origens: Iterable[int] | None = None) -> Soma:
    """FIN-01 e FIN-15: contas `atrasada` (abertas e vencidas), de qualquer mês. Com `origens`,
    só as dessas locações (as do vendedor)."""
    qs = contas_do_painel(filiais).filter(status=StatusConta.ABERTA, vencimento__lt=hoje)
    if origens is not None:
        qs = qs.filter(origem_tipo="locacao", origem_id__in=list(origens))
    return _somar(qs)


def atrasadas_das_origens(origens: Iterable[int], hoje: date) -> QuerySet[ContaReceber]:
    """Parcelas atrasadas das locações do vendedor, da mais antiga para a mais nova."""
    return (
        ContaReceber.objects.filter(
            origem_tipo="locacao",
            origem_id__in=list(origens),
            status=StatusConta.ABERTA,
            vencimento__lt=hoje,
        )
        .exclude(tipo=TipoConta.CAUCAO)
        .select_related("cliente")
        .order_by("vencimento", "id")
    )


def vencem_entre(filiais: Iterable[int], de: date, ate: date) -> Soma:
    """Contas ainda não pagas com vencimento entre `de` e `ate` (o "vence hoje" da FIN-15 com
    `de == ate == hoje`)."""
    return _somar(
        contas_do_painel(filiais).filter(
            status=StatusConta.ABERTA, vencimento__gte=de, vencimento__lte=ate
        )
    )


def em_aberto(filiais: Iterable[int]) -> int:
    """Tudo o que ainda não foi pago, sem caução (o "a receber" da implantação)."""
    return _somar(contas_do_painel(filiais).filter(status=StatusConta.ABERTA)).centavos


def receita_de_locacao(filiais: Iterable[int], de: datetime, ate: datetime) -> int:
    """Contas de locação pagas no período, sem caução (FIN-13), pelo valor da conta."""
    return _somar(
        contas_do_painel(filiais).filter(
            origem_tipo="locacao", status=StatusConta.PAGA, pago_em__gte=de, pago_em__lt=ate
        )
    ).centavos


def reembolsos_a_fazer(filiais: Iterable[int]) -> QuerySet[Reembolso]:
    return (
        Reembolso.objects.filter(filial_id__in=list(filiais), status="a_fazer")
        .select_related("cliente")
        .order_by("criado_em", "id")
    )


def pendencias_abertas() -> QuerySet[PendenciaPagamento]:
    """O contador `pendencias_pagamento` do menu (S-14): da empresa, sem filial."""
    return PendenciaPagamento.objects.filter(status=StatusPendencia.ABERTA)


# --- Contas a receber da tela `Receber` (FIN-01, FIN-02, FIN-03, FIN-15) ---

CONTA = "financeiro.ContaReceber"  # alvo das leituras compostas (ADR 0015): `locacoes` dá a placa
RECEBEM = frozenset({"administrador", "gerente", "vendedor", "financeiro"})
GERENCIAM = frozenset({"administrador", "gerente", "financeiro"})
PERIODOS = ("hoje", "semana", "mes")
SITUACOES = ("atrasadas", "vencem_hoje", "a_vencer", "pagas", "canceladas")
FAIXAS = ("1_7", "8_30", "mais_30")
ORDENS = {"vencimento": ("vencimento", "id"), "-valor": ("-valor_centavos", "-id")}


def dias_de_atraso(vencimento: date, hoje: date) -> int:
    """Dias desde o vencimento (FIN-01, FIN-02). A cobrança usa `devido_ate` (FIN-03)."""
    return max((hoje - vencimento).days, 0)


def faixa_de_atraso(dias: int) -> str | None:
    """FIN-02: 1–7, 8–30 e mais de 30 dias. Vence hoje (0 dias) não entra em faixa."""
    if dias <= 0:
        return None
    if dias <= 7:
        return "1_7"
    if dias <= 30:
        return "8_30"
    return "mais_30"


def _faixa_q(faixa: str, hoje: date) -> Q:
    """A faixa pela data do vencimento, a mesma regra de `faixa_de_atraso`."""
    if faixa == "1_7":
        return Q(vencimento__gte=hoje - timedelta(days=7), vencimento__lt=hoje)
    if faixa == "8_30":
        return Q(vencimento__gte=hoje - timedelta(days=30), vencimento__lt=hoje - timedelta(days=7))
    return Q(vencimento__lt=hoje - timedelta(days=30))


def periodo(nome: str | None, hoje: date) -> tuple[date, date]:
    """Vencimentos do período da tela: hoje, a semana (segunda a domingo) ou o mês (padrão)."""
    if nome == "hoje":
        return hoje, hoje
    if nome == "semana":
        inicio = hoje - timedelta(days=hoje.weekday())
        return inicio, inicio + timedelta(days=6)
    inicio = hoje.replace(day=1)
    return inicio, _mes_seguinte(inicio) - timedelta(days=1)


def _mes_seguinte(dia: date) -> date:
    return date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)


def _q_situacao(situacao: str, hoje: date, de: date, ate: date) -> Q:
    """FIN-01 pela data, sem tarefa à meia-noite. `atrasadas` ignora o período (FIN-15)."""
    aberta = Q(status=StatusConta.ABERTA)
    no_periodo = Q(vencimento__gte=de, vencimento__lte=ate)
    return {
        "atrasadas": aberta & Q(vencimento__lt=hoje),
        "vencem_hoje": aberta & Q(vencimento=hoje) & no_periodo,
        "a_vencer": aberta & Q(vencimento__gt=hoje) & no_periodo,
        "pagas": Q(status=StatusConta.PAGA) & no_periodo,
        "canceladas": Q(status=StatusConta.CANCELADA) & no_periodo,
    }[situacao]


def base_das_contas() -> QuerySet[ContaReceber]:
    return ContaReceber.objects.select_related("cliente", "filial").prefetch_related("cobrancas")


def filtrar_contas(qs: QuerySet[ContaReceber], params: Any, hoje: date) -> QuerySet[ContaReceber]:
    """Os filtros da tela. Sem `situacao`, as quatro abas (FIN-15): `todas` é a soma delas. A
    caução não é receita (LOC-04) e só aparece quando a lista é de um cliente ou de uma origem."""
    de, ate = periodo(params.get("periodo"), hoje)
    situacao = params.get("situacao")
    if situacao in SITUACOES:
        qs = qs.filter(_q_situacao(situacao, hoje, de, ate))
    else:
        abas = Q()
        for aba in ("atrasadas", "vencem_hoje", "a_vencer", "pagas"):
            abas |= _q_situacao(aba, hoje, de, ate)
        qs = qs.filter(abas)
    if params.get("faixa") in FAIXAS:
        qs = qs.filter(_faixa_q(params["faixa"], hoje), status=StatusConta.ABERTA)
    qs, de_um_recorte = _recortar(qs, params)
    if not de_um_recorte:
        qs = qs.exclude(tipo=TipoConta.CAUCAO)
    if params.get("forma"):
        qs = qs.filter(forma=params["forma"])
    return qs


def _recortar(qs: QuerySet[ContaReceber], params: Any) -> tuple[QuerySet[ContaReceber], bool]:
    """`?cliente=`, `?origem_tipo=&origem_id=` e `?busca=`: valem para a lista e para as
    contagens (FIN-15, T-148). Devolve também se a lista é recortada (cliente, origem ou busca),
    que é quando a caução aparece: a busca do caixa por cliente ou locação traz a caução a
    receber (CA-023-15, T-205)."""
    da_origem = bool(params.get("origem_tipo") and str(params.get("origem_id", "")).isdigit())
    if da_origem:
        qs = qs.filter(origem_tipo=params["origem_tipo"], origem_id=int(params["origem_id"]))
    do_cliente = str(params.get("cliente", "")).isdigit()
    if do_cliente:
        qs = qs.filter(cliente_id=int(params["cliente"]))
    busca = (params.get("busca") or "").strip()
    if busca:
        qs = qs.filter(Q(cliente__nome__icontains=busca) | Q(origem_codigo__icontains=busca))
    return qs, da_origem or do_cliente or bool(busca)


def indicadores_e_contagens(filiais: Iterable[int], params: Any, hoje: date) -> dict[str, Any]:
    """Os números da `FIN-15`: contas da filial, sem caução e sem `cancelada` e `renegociada`,
    valores sem multa e juros. Os indicadores são da filial e não seguem filtro; as abas seguem
    o `periodo` (menos `atrasadas`) e o recorte de cliente, origem e busca (T-148)."""
    base = contas_do_painel(filiais)
    inicio_mes, fim_mes = periodo("mes", hoje)
    previsto = _somar(base.filter(vencimento__gte=inicio_mes, vencimento__lte=fim_mes))
    recebido = _somar(
        base.filter(vencimento__gte=inicio_mes, vencimento__lte=fim_mes, status=StatusConta.PAGA)
    )
    vence_hoje = vencem_entre(filiais, hoje, hoje)
    atraso = atrasadas(filiais, hoje)
    faixas = {
        faixa: _somar(base.filter(_faixa_q(faixa, hoje), status=StatusConta.ABERTA)).centavos
        for faixa in FAIXAS
    }
    pct = None
    if previsto.centavos:
        pct = str(
            (Decimal(recebido.centavos * 100) / previsto.centavos).quantize(
                Decimal("0.01"), ROUND_HALF_UP
            )
        )
    de, ate = periodo(params.get("periodo"), hoje)
    recorte, _ = _recortar(base, params)  # a caução já está fora da base
    contagens = {
        aba: recorte.filter(_q_situacao(aba, hoje, de, ate)).count()
        for aba in ("atrasadas", "vencem_hoje", "a_vencer", "pagas")
    }
    return {
        "indicadores": {
            "previsto_mes_centavos": previsto.centavos,
            "previsto_mes_parcelas": previsto.quantidade,
            "recebido_mes_centavos": recebido.centavos,
            "recebido_pct": pct,
            "vence_hoje_centavos": vence_hoje.centavos,
            "vence_hoje_parcelas": vence_hoje.quantidade,
            "em_atraso_centavos": atraso.centavos,
            "em_atraso_clientes": atraso.clientes,
            "em_atraso_parcelas": atraso.quantidade,
            "faixas": faixas,
        },
        "contagens": {"todas": sum(contagens.values()), **contagens},
    }


class JurosDaPagina:
    """Lê a configuração e a cláusula de juros uma vez por origem, para a página inteira."""

    def __init__(self) -> None:
        self._taxas: ConfiguracaoEmpresa | None = None
        self._cobra: dict[tuple[str, int], bool] = {}

    def devido(self, conta: ContaReceber, dia: date) -> Devido:
        if self._taxas is None:
            self._taxas = configuracao()
        chave = (conta.origem_tipo, conta.origem_id)
        if chave not in self._cobra:
            self._cobra[chave] = permite_juros(*chave)
        return devido_ate(conta, dia, cobra_juros=self._cobra[chave], taxas=self._taxas)

    def cobra(self, conta: ContaReceber) -> bool:
        chave = (conta.origem_tipo, conta.origem_id)
        if chave not in self._cobra:
            self._cobra[chave] = permite_juros(*chave)
        return self._cobra[chave]


def valor_hoje(
    conta: ContaReceber, hoje: date, juros: JurosDaPagina | None = None
) -> dict[str, Any]:
    """O valor a pagar hoje, calculado pela API (FIN-03). Conta que não está em aberto: o que foi
    gravado na baixa."""
    if conta.status != StatusConta.ABERTA:
        principal, multa, juros_c, dias = (
            conta.valor_centavos,
            conta.multa_centavos,
            conta.juros_centavos,
            0,
        )
        cobra = multa + juros_c > 0
    else:
        juros = juros or JurosDaPagina()
        devido = juros.devido(conta, hoje)
        principal, multa, juros_c, dias = (
            devido.valor_centavos,
            devido.multa_centavos,
            devido.juros_centavos,
            devido.dias_atraso,
        )
        cobra = juros.cobra(conta)
    return {
        "data": hoje,
        "dias_atraso": dias,
        "principal_centavos": principal,
        "multa_centavos": multa,
        "juros_centavos": juros_c,
        "total_centavos": principal + multa + juros_c,
        "cobra_juros": cobra,
    }


def cobranca_aberta(conta: ContaReceber) -> dict[str, Any] | None:
    for cobranca in conta.cobrancas.all():
        if cobranca.status == StatusCobranca.AGUARDANDO:
            return representacao_cobranca(cobranca)
    return None


def representacao_cobranca(cobranca: CobrancaExterna) -> dict[str, Any]:
    pix = cobranca.tipo == "pix"
    return {
        "id": cobranca.pk,
        "tipo": cobranca.tipo,
        "valor_centavos": cobranca.valor_centavos,
        "vence_em": cobranca.vence_em,
        "pix_copia_e_cola": cobranca.pix_copia_e_cola or None,
        "qr_code_url": cobranca.url if pix else None,
        "linha_digitavel": cobranca.linha_digitavel or None,
        "boleto_url": None if pix else (cobranca.url or None),
        "status": cobranca.status,
    }


def acoes_da_conta(conta: ContaReceber, perfil: str) -> dict[str, bool]:
    aberta = conta.status == StatusConta.ABERTA
    recebe = aberta and perfil in RECEBEM
    gerencia = perfil in GERENCIAM
    return {
        "receber": recebe,
        "gerar_pix": recebe,
        "gerar_boleto": recebe,
        "cobrar": recebe,
        "cancelar": aberta and gerencia,
        "renegociar": aberta and gerencia,
        "estornar": conta.status == StatusConta.PAGA
        and conta.estornada_em is None
        and conta.forma != FormaPagamento.CAUCAO
        and gerencia,
    }


def representacao_completa(
    conta: ContaReceber, hoje: date, perfil: str, juros: JurosDaPagina | None = None
) -> dict[str, Any]:
    """A conta da tela `Receber` (contrato de financeiro, "Representação")."""
    dias = dias_de_atraso(conta.vencimento, hoje) if conta.status == StatusConta.ABERTA else 0
    locacao = leituras.blocos(CONTA, conta).get("locacao") or {}
    return {
        "id": conta.pk,
        "tipo": conta.tipo,
        "numero": conta.numero_parcela,
        "total_parcelas": conta.total_parcelas,
        "origem": {
            "tipo": conta.origem_tipo,
            "id": conta.origem_id,
            "codigo": conta.origem_codigo or None,
        },
        "cliente": {"id": conta.cliente_id, "nome": conta.cliente.nome},
        "filial": {"id": conta.filial_id, "nome": conta.filial.nome},
        "veiculo_placa": locacao.get("veiculo_placa"),
        "vencimento": conta.vencimento,
        "valor_centavos": conta.valor_centavos,
        "status": status_exibido(conta.status, conta.vencimento, hoje),
        "dias_atraso": dias,
        "faixa_atraso": faixa_de_atraso(dias),
        "forma_prevista": locacao.get("forma_prevista"),
        "observacao": conta.observacao or None,
        "valor_hoje": valor_hoje(conta, hoje, juros),
        "pago_em": conta.pago_em,
        "forma": conta.forma or None,
        "multa_centavos": conta.multa_centavos,
        "juros_centavos": conta.juros_centavos,
        "estorno_de": conta.estorno_de_id,
        "estornada_em": conta.estornada_em,
        "cobranca_aberta": cobranca_aberta(conta),
        "acoes": acoes_da_conta(conta, perfil),
    }


def historico_da_conta(conta: ContaReceber) -> list[dict[str, Any]]:
    """Cobranças geradas, baixa, estorno e mudanças, da auditoria (mais antigo primeiro)."""
    eventos = EventoAuditoria.objects.filter(
        objeto_tipo="contareceber", objeto_id=conta.pk
    ).order_by("ocorrido_em", "id")
    linhas = [
        {
            "em": evento.ocorrido_em,
            "acao": evento.acao,
            "por": evento.ator_nome,
            "motivo": evento.motivo or None,
        }
        for evento in eventos
    ]
    for cobranca in conta.cobrancas.all():
        linhas.append(
            {
                "em": cobranca.criado_em,
                "acao": f"cobranca.{cobranca.tipo}",
                "por": None,
                "motivo": None,
            }
        )
    return sorted(linhas, key=lambda linha: linha["em"])


def em_aberto_do_cliente(cliente_id: int, hoje: date) -> int:
    """CA-017-03: vencidas e não pagas, sem caução. `vence_hoje` não entra."""
    total = (
        ContaReceber.objects.filter(
            cliente_id=cliente_id, status=StatusConta.ABERTA, vencimento__lt=hoje
        )
        .exclude(tipo=TipoConta.CAUCAO)
        .aggregate(total=Sum("valor_centavos"))["total"]
    )
    return int(total or 0)


# --- Caixa do dia (FIN-07) ---


def caixa_do_dia(filial_id: int, dia: date) -> Caixa | None:
    caixa: Caixa | None = Caixa.objects.filter(filial_id=filial_id, data=dia).first()
    return caixa


def _sinal(movimento: MovimentoCaixa) -> int:
    """O estorno desconta o original: mesmo tipo e forma, valor com sinal trocado (CA-017-17)."""
    return -1 if movimento.estorno_de_id is not None else 1


def resumo_do_caixa(caixa: Caixa) -> dict[str, Any]:
    """FIN-07: entrou hoje (com a caução recebida), por forma, e a gaveta esperada = troco +
    entradas em dinheiro − saídas em dinheiro (saídas e sangrias)."""
    movimentos = list(caixa.movimentos.all())
    estornados = {m.estorno_de_id for m in movimentos if m.estorno_de_id is not None}
    entradas = [m for m in movimentos if m.tipo == TipoMovimento.ENTRADA]
    por_forma: dict[str, dict[str, Any]] = {
        "pix": {"centavos": 0, "quantidade": 0},
        "cartao": {"centavos": 0, "quantidade": 0, "texto": "cai em 30 dias"},
        "dinheiro": {"centavos": 0, "quantidade": 0},
    }
    for movimento in entradas:
        grupo = "cartao" if movimento.forma.startswith("cartao") else movimento.forma
        por_forma[grupo]["centavos"] += _sinal(movimento) * movimento.valor_centavos
        if movimento.estorno_de_id is None and movimento.pk not in estornados:
            por_forma[grupo]["quantidade"] += 1
    entradas_dinheiro = sum(
        _sinal(m) * m.valor_centavos for m in entradas if m.forma == FormaMovimento.DINHEIRO
    )
    saidas_dinheiro = sum(
        _sinal(m) * m.valor_centavos
        for m in movimentos
        if m.tipo != TipoMovimento.ENTRADA and m.forma == FormaMovimento.DINHEIRO
    )
    return {
        "entrou_hoje_centavos": sum(_sinal(m) * m.valor_centavos for m in entradas),
        "recebimentos": sum(
            1 for m in entradas if m.estorno_de_id is None and m.pk not in estornados
        ),
        "por_forma": por_forma,
        "gaveta": {
            "troco_centavos": caixa.troco_centavos,
            "entradas_dinheiro_centavos": entradas_dinheiro,
            "saidas_dinheiro_centavos": saidas_dinheiro,
            "esperado_centavos": caixa.troco_centavos + entradas_dinheiro - saidas_dinheiro,
        },
    }


def esperado_na_gaveta(caixa: Caixa) -> int:
    return int(resumo_do_caixa(caixa)["gaveta"]["esperado_centavos"])


def saidas_do_caixa_centavos(caixa: Caixa) -> int:
    """Despesas pagas no caixa (saídas, sem sangria): o "despesas" do caixa no painel."""
    return sum(
        _sinal(m) * m.valor_centavos
        for m in caixa.movimentos.all()
        if m.tipo == TipoMovimento.SAIDA and m.origem_tipo == OrigemTipo.DESPESA
    )


def _pessoa(usuario: Any) -> dict[str, Any] | None:
    return {"id": usuario.pk, "nome": usuario.nome} if usuario is not None else None


def representacao_caixa(caixa: Caixa, perfil: str) -> dict[str, Any]:
    aberto = caixa.status == StatusCaixa.ABERTO
    fechamento = None
    if caixa.status != StatusCaixa.ABERTO or caixa.contado_centavos is not None:
        fechamento = {
            "contado_centavos": caixa.contado_centavos,
            "esperado_centavos": caixa.esperado_centavos,
            "diferenca_centavos": caixa.diferenca_centavos,
            "motivo_diferenca": caixa.motivo_diferenca or None,
            "fechado_por": _pessoa(caixa.fechado_por),
            "fechado_em": caixa.fechado_em,
            "pedido_aprovacao_id": caixa.pedido_aprovacao_id,
        }
    opera = perfil in RECEBEM
    return {
        "id": caixa.pk,
        "filial": {"id": caixa.filial_id, "nome": caixa.filial.nome},
        "data": caixa.data,
        "status": caixa.status,
        "aberto_por": _pessoa(caixa.aberto_por),
        "aberto_em": caixa.criado_em,
        "resumo": resumo_do_caixa(caixa),
        "fechamento": fechamento,
        "acoes": {
            "sangria": aberto and opera,
            "fechar": aberto and opera,
            "receber": aberto and opera,
        },
    }


def representacao_movimento(movimento: MovimentoCaixa) -> dict[str, Any]:
    origem = None
    if movimento.origem_tipo:
        origem = {
            "tipo": movimento.origem_tipo,
            "id": movimento.origem_id,
            "codigo": movimento.origem_codigo or None,
        }
    return {
        "id": movimento.pk,
        "hora": movimento.criado_em,
        "tipo": movimento.tipo,
        "forma": movimento.forma,
        "descricao": movimento.descricao,
        "valor_centavos": movimento.valor_centavos,
        "origem": origem,
        "registrado_por": movimento.registrado_por.nome if movimento.registrado_por else "Sistema",
        "estorno_de": movimento.estorno_de_id,
    }


def caixas_abertos_da_filial(filial_id: int) -> int:
    """FIL-06: caixa `aberto` ou `aguardando_aprovacao` impede desativar a filial."""
    return int(
        Caixa.objects.filter(
            filial_id=filial_id,
            status__in=(StatusCaixa.ABERTO, StatusCaixa.AGUARDANDO_APROVACAO),
        ).count()
    )


# --- Despesas (FIN-05, FIN-06) ---


def rotulo_da_despesa(despesa: Despesa) -> str:
    return {
        StatusDespesa.AGUARDANDO_APROVACAO: "Aguardando gerente",
        StatusDespesa.A_PAGAR: "A pagar",
        StatusDespesa.PAGA: "Paga",
        StatusDespesa.RECUSADA: "Recusada",
    }[StatusDespesa(despesa.status)]


def representacao_despesa(despesa: Despesa) -> dict[str, Any]:
    nota = None
    if despesa.nota:
        assinada = arquivos.url_assinada(despesa.nota.name)
        nota = {"url": assinada.url, "url_expira_em": assinada.expira_em}
    return {
        "id": despesa.pk,
        "data": despesa.data,
        "descricao": despesa.descricao,
        "categoria": despesa.categoria,
        "veiculo": (
            {"id": despesa.veiculo_id, "placa": despesa.veiculo.placa}
            if despesa.veiculo is not None
            else None
        ),
        "filial": {"id": despesa.filial_id, "nome": despesa.filial.nome},
        "valor_centavos": despesa.valor_centavos,
        "vencimento": despesa.vencimento,
        "status": despesa.status,
        "pago_em": despesa.pago_em,
        "forma": despesa.forma or None,
        "lancada_por": _pessoa(despesa.lancada_por),
        "nota": nota,
        # A despesa da parada pode nascer sem a nota, que se anexa depois (MOV-04).
        "sem_nota": not despesa.nota,
        "origem": (
            {
                "tipo": despesa.origem_tipo,
                "id": despesa.origem_id,
                "codigo": despesa.origem_codigo or None,
            }
            if despesa.origem_tipo
            else None
        ),
        "pedido_aprovacao_id": despesa.pedido_aprovacao_id,
        "rotulo_situacao": rotulo_da_despesa(despesa),
    }


def base_das_despesas() -> QuerySet[Despesa]:
    return Despesa.objects.select_related("veiculo", "filial", "lancada_por")


def mes_pedido(texto: str | None, hoje: date) -> date:
    """`?mes=2026-10`; sem ele (ou inválido), o mês de hoje."""
    try:
        ano, mes = (int(x) for x in (texto or "").split("-"))
        return date(ano, mes, 1)
    except ValueError:
        return hoje.replace(day=1)


BUSCA_MAXIMO = 60  # FIN-16


def termo_de_busca(params: Any) -> str:
    """`?busca=`: vazio ou só espaços é ignorado; acima de 60 caracteres, 400 (FIN-16)."""
    termo = str(params.get("busca") or "").strip()
    if len(termo) > BUSCA_MAXIMO:
        raise ErroDeValidacao({"busca": [f"Use até {BUSCA_MAXIMO} caracteres na busca."]})
    return termo


def buscar_despesas(qs: QuerySet[Despesa], termo: str) -> QuerySet[Despesa]:
    """A descrição, sem diferenciar maiúsculas e acentos, ou a placa do veículo, sem hífen nem
    espaço (FIN-16). Termo que fica vazio depois de normalizado não procura na placa."""
    if not termo:
        return qs
    condicao = Q(descricao_busca__contains=texto_de_busca(termo))
    placa = normalizar_placa(termo)
    if placa:
        condicao |= Q(veiculo__placa__contains=placa)
    return qs.filter(condicao)


def filtrar_despesas(qs: QuerySet[Despesa], params: Any, hoje: date) -> QuerySet[Despesa]:
    inicio = mes_pedido(params.get("mes"), hoje)
    qs = qs.filter(data__gte=inicio, data__lt=_mes_seguinte(inicio))
    qs = buscar_despesas(qs, termo_de_busca(params))
    if params.get("status"):
        qs = qs.filter(status=params["status"])
    if params.get("categoria"):
        qs = qs.filter(categoria=params["categoria"])
    if str(params.get("veiculo", "")).isdigit():
        qs = qs.filter(veiculo_id=int(params["veiculo"]))
    return qs


def despesa_por_veiculo(gasto_centavos: int, veiculos: int) -> int | None:
    """FIN-16: o gasto do mês ÷ a frota ativa, arredondado uma vez (ROUND_HALF_UP). Sem
    veículo, `None`: a tela não mostra valor nem zero (CA-DES-03)."""
    if veiculos <= 0:
        return None
    valor = Decimal(gasto_centavos) / Decimal(veiculos)
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def indicadores_das_despesas(
    qs: QuerySet[Despesa], params: Any, hoje: date, filiais: Iterable[int]
) -> dict[str, Any]:
    """Os números da tela `Despesas` no mês pedido (CA-017-19). Recusadas não entram no gasto.
    Os indicadores não mudam com nenhum filtro; as contagens seguem só a busca (FIN-16)."""
    inicio = mes_pedido(params.get("mes"), hoje)
    fim_do_mes = _mes_seguinte(inicio) - timedelta(days=1)
    do_mes = qs.filter(data__gte=inicio, data__lt=_mes_seguinte(inicio)).exclude(
        status=StatusDespesa.RECUSADA
    )
    aguardando = do_mes.filter(status=StatusDespesa.AGUARDANDO_APROVACAO).aggregate(
        centavos=Coalesce(Sum("valor_centavos"), 0), quantidade=Count("id")
    )
    fim_semana = hoje + timedelta(days=6 - hoje.weekday())
    a_pagar_semana = qs.filter(status=StatusDespesa.A_PAGAR, vencimento__lte=fim_semana).aggregate(
        centavos=Coalesce(Sum("valor_centavos"), 0)
    )["centavos"]
    por_categoria = {
        linha["categoria"]: int(linha["centavos"])
        for linha in do_mes.values("categoria")
        .annotate(centavos=Sum("valor_centavos"))
        .order_by("-centavos")
    }
    buscadas = buscar_despesas(
        qs.filter(data__gte=inicio, data__lt=_mes_seguinte(inicio)), termo_de_busca(params)
    )
    contagens = {status: buscadas.filter(status=status).count() for status in StatusDespesa.values}
    gasto = int(do_mes.aggregate(t=Coalesce(Sum("valor_centavos"), 0))["t"])
    # A frota do último dia do mês; no mês corrente (ou futuro), a de hoje.
    frota = frota_ativa_em(min(fim_do_mes, hoje), filiais)
    return {
        "indicadores": {
            "gasto_mes_centavos": gasto,
            "despesa_por_veiculo_centavos": despesa_por_veiculo(gasto, frota),
            "aguardando_aprovacao_centavos": int(aguardando["centavos"]),
            "aguardando_aprovacao_quantidade": int(aguardando["quantidade"]),
            "a_pagar_semana_centavos": int(a_pagar_semana),
            "por_categoria": por_categoria,
        },
        "contagens": contagens,
    }


def custo_do_veiculo_no_ano(veiculo_id: int, hoje: date) -> int:
    """VEI-05: despesas do veículo no ano (sem as recusadas), o `custo_manutencao_ano`."""
    total = (
        Despesa.objects.filter(veiculo_id=veiculo_id, data__year=hoje.year)
        .exclude(status=StatusDespesa.RECUSADA)
        .aggregate(total=Sum("valor_centavos"))["total"]
    )
    return int(total or 0)


def despesas_a_pagar_ate(filiais: Iterable[int], dia: date) -> Soma:
    """Despesas `a_pagar` com vencimento até `dia` (contas a pagar do painel)."""
    total = Despesa.objects.filter(
        filial_id__in=list(filiais), status=StatusDespesa.A_PAGAR, vencimento__lte=dia
    ).aggregate(centavos=Coalesce(Sum("valor_centavos"), 0), quantidade=Count("id"))
    return Soma(int(total["centavos"]), int(total["quantidade"]))


# --- Reembolsos e pendências ---


REEMBOLSO = "financeiro.Reembolso"  # alvo das leituras compostas: `locacoes` dá locação e veículo
# A origem guardada (ADR 0011) e o tipo e o rótulo da tela (`financeiro.md`, "Tela Reembolsos").
ORIGENS_DO_REEMBOLSO: dict[str, tuple[str, str]] = {
    OrigemTipo.DEVOLUCAO: ("devolucao", "Devolução com caução"),  # DEV-02
    OrigemTipo.LOCACAO: ("cancelamento", "Locação cancelada antes da retirada"),  # LOC-12
    "credito": ("credito", "Crédito de semanas"),  # LOC-13
}
STATUS_DOS_REEMBOLSOS = ("a_fazer", "feito", "todos")


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _entre_dias(campo: str, de: date, ate: date) -> Q:
    """`campo` (data e hora em UTC) entre o começo de `de` e o fim de `ate`, no fuso da empresa."""
    fuso = timezone.get_current_timezone()
    inicio = datetime.combine(de, datetime.min.time(), tzinfo=fuso)
    fim = datetime.combine(ate + timedelta(days=1), datetime.min.time(), tzinfo=fuso)
    return Q(**{f"{campo}__gte": inicio, f"{campo}__lt": fim})


def base_dos_reembolsos() -> QuerySet[Reembolso]:
    return leituras.aplicar(REEMBOLSO, Reembolso.objects.select_related("cliente", "feito_por"))


def _buscar_reembolsos(qs: QuerySet[Reembolso], termo: str) -> QuerySet[Reembolso]:
    if not termo:
        return qs
    return qs.filter(Q(cliente__nome__icontains=termo) | Q(origem_codigo__icontains=termo))


def lista_de_reembolsos(
    escopo: QuerySet[Reembolso], params: Any, hoje: date
) -> tuple[QuerySet[Reembolso], dict[str, Any]]:
    """DEV-02, tela `Reembolsos`: as linhas pedidas e os extras (`indicadores`, `contagens`).

    Os `a_fazer` não dependem do período; os `feito` contam pelo `feito_em` dentro dele. Os
    indicadores ignoram a busca, e as contagens das abas a respeitam (como as despesas)."""
    de, ate = periodo(params.get("periodo"), hoje)
    a_fazer = Q(status="a_fazer")
    feitos = Q(status="feito") & _entre_dias("feito_em", de, ate)
    buscados = _buscar_reembolsos(escopo, termo_de_busca(params))
    status = params.get("status")
    filtro = {"feito": feitos, "todos": a_fazer | feitos}.get(str(status), a_fazer)
    soma_a_fazer = escopo.filter(a_fazer).aggregate(
        centavos=Coalesce(Sum("valor_centavos"), 0),
        quantidade=Count("id"),
        clientes=Count("cliente_id", distinct=True),
    )
    soma_feitos = escopo.filter(feitos).aggregate(
        centavos=Coalesce(Sum("valor_centavos"), 0), quantidade=Count("id")
    )
    contagens = {
        "a_fazer": buscados.filter(a_fazer).count(),
        "feito": buscados.filter(feitos).count(),
    }
    contagens["todos"] = contagens["a_fazer"] + contagens["feito"]
    return buscados.filter(filtro), {
        "indicadores": {
            "a_fazer": {
                "valor_centavos": int(soma_a_fazer["centavos"]),
                "quantidade": int(soma_a_fazer["quantidade"]),
                "texto": _plural(
                    int(soma_a_fazer["clientes"]),
                    "cliente com devolução",
                    "clientes com devolução",
                ),
            },
            "feitos": {
                "valor_centavos": int(soma_feitos["centavos"]),
                "quantidade": int(soma_feitos["quantidade"]),
                "texto": _plural(
                    int(soma_feitos["quantidade"]), "reembolso feito", "reembolsos feitos"
                ),
            },
        },
        "contagens": contagens,
    }


def representacao_reembolso(
    reembolso: Reembolso, *, suporte: bool = False, pode_marcar: bool = False
) -> dict[str, Any]:
    """Um item da tela `Reembolsos`. Com o token de suporte, sem comprovante (AUD-09, M-02 da
    T-384) e sem marcar feito (PLT-07). `origem.id` é a locação, para o "Ver acerto"; o bloco
    `locacao` vem de `locacoes` (ADR 0015) e falta sem o módulo (PLT-12)."""
    comprovante = None
    if reembolso.comprovante and not suporte:
        assinada = arquivos.url_assinada(reembolso.comprovante.name)
        comprovante = {"url": assinada.url, "url_expira_em": assinada.expira_em}
    tipo, rotulo = ORIGENS_DO_REEMBOLSO.get(
        reembolso.origem_tipo, (reembolso.origem_tipo, OrigemTipo(reembolso.origem_tipo).label)
    )
    locacao = leituras.bloco(REEMBOLSO, "locacao", reembolso) or {}
    status = StatusReembolso(reembolso.status)
    feito_por = reembolso.feito_por
    return {
        "id": reembolso.pk,
        "criado_em": reembolso.criado_em,
        "cliente": {"id": reembolso.cliente_id, "nome": reembolso.cliente.nome},
        "origem": {
            "tipo": tipo,
            "codigo": reembolso.origem_codigo or None,
            "id": locacao.get("id"),
            "veiculo": locacao.get("veiculo"),
        },
        "origem_rotulo": rotulo,
        "motivo": reembolso.motivo,
        "forma": reembolso.forma,
        "forma_rotulo": FormaReembolso(reembolso.forma).label,
        "valor_centavos": reembolso.valor_centavos,
        "status": status.value,
        "status_rotulo": status.label,
        "feito_em": reembolso.feito_em,
        "feito_por": {"id": feito_por.pk, "nome": feito_por.nome} if feito_por else None,
        "comprovante": comprovante,
        "acoes": {
            "marcar_feito": status == StatusReembolso.A_FAZER and pode_marcar and not suporte
        },
    }


MOTIVOS_DA_PENDENCIA = {
    MotivoPendencia.VALOR_DIFERENTE: "Valor pago diferente",
    MotivoPendencia.ESTORNADA_NO_PARCEIRO: "Estornada no parceiro",
    MotivoPendencia.SEM_CONTA: "A conta já não estava aberta",
}
RESOLUCOES = {"baixar": "Baixada", "ignorar": "Ignorada"}
STATUS_DAS_PENDENCIAS = ("aberta", "resolvida", "todas")


def base_das_pendencias() -> QuerySet[PendenciaPagamento]:
    """Com `resolvida_em`, a hora do evento `pendencia_pagamento.baixar` ou `.ignorar`."""
    resolvida_em = (
        EventoAuditoria.objects.filter(
            objeto_tipo="pendenciapagamento",
            objeto_id=OuterRef("pk"),
            acao__in=[f"pendencia_pagamento.{acao}" for acao in RESOLUCOES],
        )
        .order_by("-ocorrido_em")
        .values("ocorrido_em")[:1]
    )
    base = PendenciaPagamento.objects.select_related("cobranca__conta_receber__cliente")
    return base.annotate(resolvida_em=Subquery(resolvida_em))  # type: ignore[no-any-return]


def lista_de_pendencias(
    todas: QuerySet[PendenciaPagamento], params: Any, hoje: date
) -> tuple[QuerySet[PendenciaPagamento], dict[str, Any]]:
    """AUT-05, tela `Pendências do pagamento`. As resolvidas do mês contam pela hora do evento
    da resolução (`base_das_pendencias`). Indicadores sem a busca; contagens com."""
    de, ate = periodo("mes", hoje)
    termo = termo_de_busca(params)
    buscadas = todas
    if termo:
        buscadas = todas.filter(
            Q(cobranca__externo_id__icontains=termo)
            | Q(cobranca__conta_receber__cliente__nome__icontains=termo)
            | Q(cobranca__conta_receber__origem_codigo__icontains=termo)
        )
    abertas = todas.filter(status=StatusPendencia.ABERTA).aggregate(
        centavos=Coalesce(Sum("valor_pago_centavos"), 0), quantidade=Count("id")
    )
    resolvidas = (
        todas.filter(status=StatusPendencia.RESOLVIDA)
        .filter(_entre_dias("resolvida_em", de, ate))
        .aggregate(centavos=Coalesce(Sum("valor_pago_centavos"), 0), quantidade=Count("id"))
    )
    contagens = {s: buscadas.filter(status=s).count() for s in StatusPendencia.values}
    contagens["todas"] = sum(contagens.values())
    status = params.get("status")
    if status != "todas":
        buscadas = buscadas.filter(
            status=status if status in StatusPendencia.values else StatusPendencia.ABERTA
        )
    return buscadas, {
        "indicadores": {
            "abertas": {
                "quantidade": int(abertas["quantidade"]),
                "valor_centavos": int(abertas["centavos"]),
                "texto": f"{formatar_reais(int(abertas['centavos']))} em análise",
            },
            "resolvidas": {
                "quantidade": int(resolvidas["quantidade"]),
                "valor_centavos": int(resolvidas["centavos"]),
                "texto": _plural(
                    int(resolvidas["quantidade"]), "resolvida no mês", "resolvidas no mês"
                ),
            },
        },
        "contagens": contagens,
    }


def _parcela(conta: ContaReceber) -> str:
    if conta.tipo == TipoConta.PARCELA and conta.numero_parcela and conta.total_parcelas:
        return f"parcela {conta.numero_parcela} de {conta.total_parcelas}"
    return TipoConta(conta.tipo).label.lower()


def _detalhe_da_pendencia(pendencia: PendenciaPagamento, taxas: ConfiguracaoEmpresa) -> str:
    """Texto pronto (a tela não faz conta). O valor da conta é o devido no dia da cobrança
    (FIN-03), o mesmo pelo qual a baixa da pendência paga a conta."""
    cobranca = pendencia.cobranca
    conta = cobranca.conta_receber
    pago = pendencia.valor_pago_centavos
    if pendencia.motivo == MotivoPendencia.ESTORNADA_NO_PARCEIRO:
        return (
            f"O parceiro estornou o pagamento de "
            f"{formatar_reais(pago if pago is not None else cobranca.valor_centavos)}."
        )
    pagou = f"Pagou {formatar_reais(pago or 0)}"
    if pendencia.motivo == MotivoPendencia.SEM_CONTA:
        return f"{pagou}, mas a conta já estava {StatusConta(conta.status).label.lower()}."
    devido = devido_ate(conta, cobranca.dia_da_geracao(), taxas=taxas).total_centavos
    diferenca = devido - (pago or 0)
    texto = f"{pagou}; a conta estava em {formatar_reais(devido)}"
    if diferenca > 0:
        return f"{texto} (falta {formatar_reais(diferenca)})."
    if diferenca < 0:
        return f"{texto} ({formatar_reais(-diferenca)} a mais)."
    return f"{texto}."


def _resolucao(pendencia: PendenciaPagamento) -> dict[str, Any] | None:
    """`resolucao` guarda "baixar: <motivo>" ou "ignorar: <motivo>" (`resolver_pendencia`)."""
    if pendencia.status != StatusPendencia.RESOLVIDA or not pendencia.resolucao:
        return None
    acao, _, motivo = pendencia.resolucao.partition(": ")
    rotulo = RESOLUCOES.get(acao)
    texto = f"{rotulo}: {motivo}" if rotulo else pendencia.resolucao
    em = getattr(pendencia, "resolvida_em", None) or pendencia.atualizado_em
    return {"texto": texto, "em": em}


def representacao_pendencia(
    pendencia: PendenciaPagamento,
    *,
    suporte: bool = False,
    taxas: ConfiguracaoEmpresa | None = None,
) -> dict[str, Any]:
    """Um item da tela `Pendências do pagamento`. Com o token de suporte, as ações são `false`
    (PLT-07). No estorno e na conta que já não está aberta, só ignorar."""
    cobranca = pendencia.cobranca
    conta = cobranca.conta_receber
    status = StatusPendencia(pendencia.status)
    resolver = status == StatusPendencia.ABERTA and not suporte
    return {
        "id": pendencia.pk,
        "criado_em": pendencia.criado_em,
        "cobranca": {
            "id_no_parceiro": cobranca.externo_id,
            "forma": cobranca.tipo,
            "forma_rotulo": TipoCobranca(cobranca.tipo).label,
        },
        "cliente": {"id": conta.cliente_id, "nome": conta.cliente.nome},
        "origem": {
            "codigo": conta.origem_codigo or None,
            "conta_id": conta.pk,
            "parcela": _parcela(conta),
        },
        "motivo": pendencia.motivo,
        "motivo_rotulo": MOTIVOS_DA_PENDENCIA.get(
            MotivoPendencia(pendencia.motivo), pendencia.motivo
        ),
        "detalhe": _detalhe_da_pendencia(pendencia, taxas or configuracao()),
        "valor_pago_centavos": pendencia.valor_pago_centavos,
        "status": status.value,
        "status_rotulo": status.label,
        "resolucao": _resolucao(pendencia),
        "acoes": {
            "resolver": resolver,
            "baixar": resolver
            and pendencia.motivo != MotivoPendencia.ESTORNADA_NO_PARCEIRO
            and conta.status == StatusConta.ABERTA,
        },
    }


# --- Painel: caixa e despesas (`relatorios`, docs/api/painel.md) ---


def caixas_de_hoje(filiais: Iterable[int], hoje: date) -> list[dict[str, Any]]:
    """`caixas_do_dia` do início do financeiro: o caixa de hoje de cada filial do escopo."""
    caixas = (
        Caixa.objects.filter(filial_id__in=list(filiais), data=hoje)
        .select_related("filial", "aberto_por")
        .order_by("-filial__matriz", "filial__nome")
    )
    return [
        {
            "filial": caixa.filial.nome,
            "status": caixa.status,
            "aberto_por": caixa.aberto_por.nome,
            "esperado_gaveta_centavos": esperado_na_gaveta(caixa),
        }
        for caixa in caixas
    ]


def caixa_hoje_do_painel(filial_id: int, hoje: date) -> dict[str, Any] | None:
    """`caixa_hoje` do início do administrador: recebido no caixa, o "vence hoje" da FIN-15,
    as despesas pagas no caixa e o saldo do dia (recebido − despesas). Sem caixa hoje: `None`."""
    caixa = Caixa.objects.select_related("filial").filter(filial_id=filial_id, data=hoje).first()
    if caixa is None:
        return None
    recebido = int(resumo_do_caixa(caixa)["entrou_hoje_centavos"])
    despesas = saidas_do_caixa_centavos(caixa)
    return {
        "filial": caixa.filial.nome,
        "data": caixa.data,
        "status": caixa.status,
        "recebido_centavos": recebido,
        "a_receber_hoje_centavos": vencem_entre([filial_id], hoje, hoje).centavos,
        "despesas_centavos": despesas,
        "saldo_dia_centavos": recebido - despesas,
    }


def despesas_para_aprovar(filiais: Iterable[int], exceto_usuario_id: int | None) -> int:
    """Contador `despesas`: aguardando aprovação, sem as que a pessoa lançou (APR-09)."""
    return int(
        Despesa.objects.filter(
            filial_id__in=list(filiais), status=StatusDespesa.AGUARDANDO_APROVACAO
        )
        .exclude(lancada_por_id=exceto_usuario_id)
        .count()
    )


def despesas_a_pagar_vencendo(filiais: Iterable[int], ate: date) -> QuerySet[Despesa]:
    return Despesa.objects.filter(
        filial_id__in=list(filiais), status=StatusDespesa.A_PAGAR, vencimento__lte=ate
    ).order_by("vencimento", "id")
