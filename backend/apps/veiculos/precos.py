"""Cálculo dos preços do veículo (VEI-13, VEI-16; ADR 0041, item 4). Módulo puro: sem banco e
sem Django.

Valores em centavos (`int`) na entrada e na saída; contas intermediárias em `Decimal`, com
`ROUND_HALF_UP` só no que se grava ou se exibe (ADR 0009). Percentuais saem com 2 casas.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, localcontext

UM = Decimal(1)
CEM = Decimal(100)
DUAS_CASAS = Decimal("0.01")
# VEI-16: meses por período da compra (104 semanais = 52 quinzenais = 730 diárias = 24 mensais).
MESES_POR_PERIODO = {
    "diaria": Decimal(12) / Decimal(365),
    "semanal": Decimal(12) / Decimal(52),
    "quinzenal": Decimal(12) / Decimal(26),
    "mensal": UM,
}
PERIODICIDADES = ("diaria", "semanal", "quinzenal", "mensal")
# VEI-13: valor em mês do plano de aluguel, pelo período.
MES_DO_PERIODO = {"dia": Decimal(30), "semana": Decimal(52) / Decimal(12), "mes": UM}
MESES_DA_DESVALORIZACAO = Decimal(24)  # "Revenda estimada em 24 meses" (padrão A)
# VEI-16: acima disto salvar pede confirmação.
JUROS_SEM_CONFIRMACAO_PCT = Decimal("1.00")
# Bisseção do modo `digitar` (ADR 0041): 0 a 20% ao mês, meio centavo, até 100 iterações.
JUROS_MAXIMO_PCT = Decimal(20)
TOLERANCIA_CENTAVOS = Decimal("0.5")
ITERACOES = 100

ALERTA_VENDA_ABAIXO = "Valor de venda abaixo do que foi pago: o lucro vem só dos juros."
ALERTA_JUROS = (
    "Locadora não é financeira: juros acima de 1% ao mês (12% ao ano) pedem confirmação. "
    "Valide o contrato com seu advogado."
)
MENSAGEM_PARCELA_NAO_COBRE = "A parcela não cobre o valor de venda."


class ParcelaNaoCobre(ValueError):
    """VEI-16: no modo `digitar`, parcela menor que financiado ÷ `n`."""


def centavos(valor: Decimal) -> int:
    """Arredonda para o centavo inteiro, `ROUND_HALF_UP`."""
    return int(valor.quantize(UM, rounding=ROUND_HALF_UP))


def pct(valor: Decimal) -> Decimal:
    return valor.quantize(DUAS_CASAS, rounding=ROUND_HALF_UP)


# --- VEI-13: custo, receita e margem do plano de aluguel ---


def custo_mes(
    *,
    manutencao_mes: int,
    seguro_mes: int,
    rastreador_mes: int,
    ipva_ano: int,
    pago_na_moto: int,
    revenda_estimada: int | None,
) -> Decimal:
    """manutenção + seguro + IPVA ÷ 12 + rastreador + (pago na moto − revenda) ÷ 24. Sem revenda
    estimada, sem desvalorização."""
    custo = Decimal(manutencao_mes + seguro_mes + rastreador_mes) + Decimal(ipva_ano) / 12
    if revenda_estimada is not None:
        custo += Decimal(pago_na_moto - revenda_estimada) / MESES_DA_DESVALORIZACAO
    return custo


def receita_mes(valor: int, periodo: str, ocupacao_pct: Decimal) -> Decimal:
    """valor em mês × ocupação; valor em mês = diária × 30, semanal × 52 ÷ 12, mensal × 1."""
    return Decimal(valor) * MES_DO_PERIODO[periodo] * ocupacao_pct / CEM


@dataclass(frozen=True)
class Margem:
    receita_mes_centavos: int
    lucro_mes_centavos: int
    margem_pct: Decimal | None  # nula quando a receita é zero
    abaixo_da_minima: bool


def margem(
    valor: int,
    periodo: str,
    ocupacao_pct: Decimal | None,
    custo: Decimal,
    margem_minima_pct: Decimal | None = None,
) -> Margem | None:
    """lucro = receita − custo; margem = lucro ÷ receita. Sem ocupação, `None` ("Informe a
    ocupação"). Abaixo da margem mínima da empresa, a faixa fica amarela."""
    if ocupacao_pct is None:
        return None
    receita = receita_mes(valor, periodo, ocupacao_pct)
    lucro = receita - custo
    valor_margem = pct(lucro / receita * CEM) if receita > 0 else None
    abaixo = (
        margem_minima_pct is not None
        and valor_margem is not None
        and valor_margem < margem_minima_pct
    )
    return Margem(centavos(receita), centavos(lucro), valor_margem, abaixo)


# --- VEI-16: locação com compra ---


def meses_do_prazo(parcelas: int, periodicidade: str) -> Decimal:
    return Decimal(parcelas) * MESES_POR_PERIODO[periodicidade]


def taxa_periodo(juros_mes_pct: Decimal, meses: Decimal, parcelas: int) -> Decimal:
    """(1 + juros ao mês) ^ (meses do prazo ÷ n) − 1."""
    with localcontext() as contexto:
        contexto.prec = 40
        return (UM + juros_mes_pct / CEM) ** (meses / Decimal(parcelas)) - UM


def pmt(taxa: Decimal, parcelas: int, financiado: Decimal) -> Decimal:
    """financiado × taxa ÷ (1 − (1 + taxa) ^ −n); com taxa 0, financiado ÷ n. Sem arredondar."""
    if taxa == 0:
        return financiado / Decimal(parcelas)
    with localcontext() as contexto:
        contexto.prec = 40
        return financiado * taxa / (UM - (UM + taxa) ** -parcelas)


def parcela_pelos_juros(
    financiado: int, parcelas: int, periodicidade: str, juros_mes_pct: Decimal
) -> Decimal:
    meses = meses_do_prazo(parcelas, periodicidade)
    return pmt(taxa_periodo(juros_mes_pct, meses, parcelas), parcelas, Decimal(financiado))


def juros_por_bissecao(parcela: int, financiado: int, parcelas: int, periodicidade: str) -> Decimal:
    """Os juros ao mês em que o PMT dá a parcela digitada, com 2 casas. Parcela menor que
    financiado ÷ n levanta `ParcelaNaoCobre`; acima do PMT a 20%, devolve 20,00."""
    alvo = Decimal(parcela)
    if alvo * parcelas < financiado:
        raise ParcelaNaoCobre(MENSAGEM_PARCELA_NAO_COBRE)
    baixo, alto = Decimal(0), JUROS_MAXIMO_PCT
    meio = baixo
    for _ in range(ITERACOES):
        meio = (baixo + alto) / 2
        valor = parcela_pelos_juros(financiado, parcelas, periodicidade, meio)
        if abs(valor - alvo) < TOLERANCIA_CENTAVOS:
            break
        if valor < alvo:
            baixo = meio
        else:
            alto = meio
    return pct(meio)


@dataclass(frozen=True)
class ParcelaNaPeriodicidade:
    periodicidade: str
    parcelas: int
    parcela_cliente_centavos: int


@dataclass(frozen=True)
class ResultadoCompra:
    financiado_centavos: int
    meses_do_prazo: Decimal
    taxa_periodo_pct: Decimal
    juros_mes_pct: Decimal
    parcela_moto_centavos: int
    adicional_centavos: int
    parcela_cliente_centavos: int
    recebe_pela_moto_centavos: int
    juros_no_prazo_centavos: int
    lucro_centavos: int | None  # sem o pago na moto (sem valor de compra), `None`
    margem_sobre_pago_pct: Decimal | None
    venda_abaixo_do_pago: bool
    pede_confirmacao_juros: bool
    nas_periodicidades: list[ParcelaNaPeriodicidade] = field(default_factory=list)


def _nas_periodicidades(
    financiado: int, meses: Decimal, parcelas: int, adicional: int, juros_mes_pct: Decimal
) -> list[ParcelaNaPeriodicidade]:
    """A parcela do cliente com o mesmo prazo em meses nas 4 periodicidades. O adicional se
    converte pelo prazo (adicional × n ÷ n'); parcela da moto e adicional se arredondam cada um,
    como a parcela gravada (Pop: 730 × R$ 27,19; 24 × R$ 830,39)."""
    resultado = []
    for periodicidade in PERIODICIDADES:
        quantas = centavos(meses / MESES_POR_PERIODO[periodicidade])
        if quantas < 1:
            continue
        moto = pmt(taxa_periodo(juros_mes_pct, meses, quantas), quantas, Decimal(financiado))
        extra = Decimal(adicional) * parcelas / quantas
        resultado.append(
            ParcelaNaPeriodicidade(periodicidade, quantas, centavos(moto) + centavos(extra))
        )
    return resultado


def simular_compra(
    *,
    valor_venda: int,
    entrada: int,
    parcelas: int,
    periodicidade: str,
    modo: str,
    juros_mes_pct: Decimal,
    parcela_digitada: int,
    adicional: int,
    pago_na_moto: int | None,
) -> ResultadoCompra:
    """VEI-16. No `calcular`, a parcela da moto é o PMT arredondado; no `digitar`, a digitada, e
    os juros saem da bisseção. Recebe pela moto = parcela arredondada × n + entrada (padrão A do
    "Arredondamento do recebe pela moto": Pop R$ 17.768,96)."""
    financiado = valor_venda - entrada
    meses = meses_do_prazo(parcelas, periodicidade)
    if modo == "digitar":
        juros = juros_por_bissecao(parcela_digitada, financiado, parcelas, periodicidade)
        parcela_moto = parcela_digitada
    else:
        juros = pct(juros_mes_pct)
        parcela_moto = centavos(parcela_pelos_juros(financiado, parcelas, periodicidade, juros))
    taxa = taxa_periodo(juros, meses, parcelas)
    recebe = parcela_moto * parcelas + entrada
    lucro = None if pago_na_moto is None else recebe - pago_na_moto
    margem_pago = (
        pct(Decimal(lucro) / Decimal(pago_na_moto) * CEM)
        if lucro is not None and pago_na_moto
        else None
    )
    return ResultadoCompra(
        financiado_centavos=financiado,
        meses_do_prazo=pct(meses),
        taxa_periodo_pct=pct(taxa * CEM),
        juros_mes_pct=juros,
        parcela_moto_centavos=parcela_moto,
        adicional_centavos=adicional,
        parcela_cliente_centavos=parcela_moto + adicional,
        recebe_pela_moto_centavos=recebe,
        juros_no_prazo_centavos=recebe - valor_venda,
        lucro_centavos=lucro,
        margem_sobre_pago_pct=margem_pago,
        venda_abaixo_do_pago=pago_na_moto is not None and valor_venda < pago_na_moto,
        pede_confirmacao_juros=juros > JUROS_SEM_CONFIRMACAO_PCT,
        nas_periodicidades=_nas_periodicidades(financiado, meses, parcelas, adicional, juros),
    )


# --- Simulação do documento inteiro ---


@dataclass(frozen=True)
class Custos:
    manutencao_mes: int = 0
    seguro_mes: int = 0
    rastreador_mes: int = 0
    ipva_ano: int = 0
    revenda_estimada: int | None = None
    ocupacao_esperada_pct: Decimal | None = None


@dataclass(frozen=True)
class PlanoAluguel:
    chave: str  # o id do plano, ou o tipo do plano ainda sem id
    periodo: str
    valor: int
    ligado: bool


@dataclass(frozen=True)
class Compra:
    ligado: bool
    periodicidade: str
    parcelas: int
    entrada: int
    juros_mes_pct: Decimal
    modo: str
    parcela_digitada: int
    adicional: int


@dataclass(frozen=True)
class Entrada:
    valor_venda: int | None
    pago_na_moto: int | None
    custos: Custos
    planos: list[PlanoAluguel]
    compra: Compra | None
    margem_minima_pct: Decimal | None = None


@dataclass(frozen=True)
class Resultado:
    custo_mes_centavos: int
    margens: dict[str, Margem | None]
    compra: ResultadoCompra | None
    alertas: list[dict[str, str]]
    pede_confirmacao_juros: bool


def simular(entrada: Entrada) -> Resultado:
    """Custo por mês, a margem de cada plano e o resultado da compra, sem gravar (ADR 0041).
    A compra só se calcula com valor de venda e entrada menor que ele; `digitar` com parcela que
    não cobre levanta `ParcelaNaoCobre` (o serviço responde no campo)."""
    pago = entrada.pago_na_moto or 0
    custo = custo_mes(
        manutencao_mes=entrada.custos.manutencao_mes,
        seguro_mes=entrada.custos.seguro_mes,
        rastreador_mes=entrada.custos.rastreador_mes,
        ipva_ano=entrada.custos.ipva_ano,
        pago_na_moto=pago,
        revenda_estimada=entrada.custos.revenda_estimada,
    )
    margens = {
        plano.chave: margem(
            plano.valor,
            plano.periodo,
            entrada.custos.ocupacao_esperada_pct,
            custo,
            entrada.margem_minima_pct,
        )
        for plano in entrada.planos
    }
    compra = None
    if (
        entrada.compra is not None
        and entrada.valor_venda
        and entrada.compra.entrada < entrada.valor_venda
    ):
        compra = simular_compra(
            valor_venda=entrada.valor_venda,
            entrada=entrada.compra.entrada,
            parcelas=entrada.compra.parcelas,
            periodicidade=entrada.compra.periodicidade,
            modo=entrada.compra.modo,
            juros_mes_pct=entrada.compra.juros_mes_pct,
            parcela_digitada=entrada.compra.parcela_digitada,
            adicional=entrada.compra.adicional,
            pago_na_moto=entrada.pago_na_moto,
        )
    alertas = []
    if compra is not None and compra.venda_abaixo_do_pago:
        alertas.append({"codigo": "venda_abaixo_do_pago", "mensagem": ALERTA_VENDA_ABAIXO})
    pede = bool(compra and compra.pede_confirmacao_juros)
    if pede:
        alertas.append({"codigo": "VEI-16", "mensagem": ALERTA_JUROS})
    return Resultado(centavos(custo), margens, compra, alertas, pede)
