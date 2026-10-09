"""Contas da locação, sem banco (LOC-01 a LOC-05, LOC-14).

A simulação, a confirmação e a decisão do desconto (`APR-01`) chamam `calcular` com os preços já
escolhidos: na simulação e na confirmação, os de hoje (`LOC-15`); depois, os congelados na
locação. Cada valor é arredondado no centavo por `comum.dinheiro`.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from zoneinfo import ZoneInfo

from comum.dinheiro import aplicar_percentual, dividir_em_parcelas, formatar_reais
from comum.erros import ErroDeValidacao

from .models import ParcelamentoMensal, Periodicidade

P = Periodicidade
# Teto de períodos por locação: acima disso, é outro contrato.
MAXIMO_DE_PERIODOS = {P.DIARIA: 90, P.SEMANAL: 52, P.MENSAL: 24}
UNIDADE = {
    P.DIARIA: ("diária", "diárias"),
    P.SEMANAL: ("semana", "semanas"),
    P.MENSAL: ("mês", "meses"),
}


@dataclass(frozen=True)
class ItemExtra:
    extra_id: int
    nome: str
    quantidade: int
    valor_centavos: int
    cobranca: str  # "por_periodo" ou "unica" (cadastro de extras)


@dataclass(frozen=True)
class DescontoDoPlano:
    """Plano especial de desconto (`Mensal fidelidade`: 10.00 a partir do 3º período)."""

    pct: Decimal
    a_partir_do_periodo: int


@dataclass(frozen=True)
class Entrada:
    periodicidade: str
    inicio: datetime
    fuso: str
    preco_periodo_centavos: int  # tabela, ou o preço fixo do plano especial
    diaria_centavos: int
    caucao_centavos: int
    periodos: int | None = None
    fim_previsto: datetime | None = None
    desconto_do_plano: DescontoDoPlano | None = None
    extras: tuple[ItemExtra, ...] = ()
    desconto_pct: Decimal = Decimal("0.00")
    parcelamento_mensal: str = ""
    primeiro_vencimento: date | None = None


@dataclass(frozen=True)
class Parcela:
    numero: int
    vencimento: date
    valor_centavos: int


@dataclass
class Calculo:
    periodos: int
    fim_previsto: datetime
    valor_periodo_centavos: int  # 1º período com plano e desconto, sem extras
    proximos_periodos_centavos: int
    caucao_centavos: int
    periodos_centavos: int  # soma dos períodos sem desconto
    extras_centavos: int
    desconto_centavos: int
    parcelas: list[Parcela] = field(default_factory=list)
    linhas: list[dict[str, object]] = field(default_factory=list)
    texto_retirada: str = ""

    @property
    def hoje_na_retirada_centavos(self) -> int:
        return self.parcelas[0].valor_centavos + self.caucao_centavos


def somar_meses(momento: datetime, meses: int) -> datetime:
    """Mesmo dia e hora `meses` depois; dia 31 num mês de 30 vira 30."""
    ano, mes = divmod(momento.month - 1 + meses, 12)
    ano, mes = momento.year + ano, mes + 1
    dia = min(momento.day, calendar.monthrange(ano, mes)[1])
    return momento.replace(year=ano, month=mes, day=dia)


def somar_meses_data(dia: date, meses: int) -> date:
    ano, mes = divmod(dia.month - 1 + meses, 12)
    ano, mes = dia.year + ano, mes + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def fim_dos_periodos(periodicidade: str, inicio: datetime, periodos: int) -> datetime:
    if periodicidade == P.DIARIA:
        return inicio + timedelta(days=periodos)
    if periodicidade == P.SEMANAL:
        return inicio + timedelta(days=7 * periodos)
    return somar_meses(inicio, periodos)


def _periodos_ate(entrada: Entrada, inicio: datetime, fim: datetime) -> int:
    """Períodos inteiros que cobrem de `inicio` a `fim`; fração conta como período."""
    if fim <= inicio:
        raise ErroDeValidacao({"fim_previsto": ["O fim previsto precisa ser depois do início."]})
    if entrada.periodicidade == P.MENSAL:
        if somar_meses(inicio, 1) > fim:
            raise ErroDeValidacao(
                {
                    "fim_previsto": [
                        "O plano mensal precisa de pelo menos um mês. Use diária ou semanal."
                    ]
                }
            )
        n = 1
        while somar_meses(inicio, n) < fim:
            n += 1
        return n
    dias = 1 if entrada.periodicidade == P.DIARIA else 7
    return ceil((fim - inicio) / timedelta(days=dias))


def _quantos_periodos(entrada: Entrada, inicio: datetime) -> int:
    if entrada.periodos is not None:
        periodos = entrada.periodos
    elif entrada.fim_previsto is not None:
        periodos = _periodos_ate(entrada, inicio, entrada.fim_previsto)
    else:
        raise ErroDeValidacao({"periodos": ["Informe os períodos ou o fim previsto."]})
    if periodos < 1:
        raise ErroDeValidacao({"periodos": ["Informe pelo menos 1 período."]})
    maximo = MAXIMO_DE_PERIODOS[P(entrada.periodicidade)]
    if periodos > maximo:
        unidade = UNIDADE[P(entrada.periodicidade)][1]
        raise ErroDeValidacao({"periodos": [f"No máximo {maximo} {unidade} por locação."]})
    return periodos


def _preco_do_periodo(entrada: Entrada, k: int) -> int:
    """Preço do k-ésimo período (1, 2, ...) com o desconto do plano, sem o do vendedor."""
    preco = entrada.preco_periodo_centavos
    plano = entrada.desconto_do_plano
    if plano is not None and k >= plano.a_partir_do_periodo:
        preco -= aplicar_percentual(preco, plano.pct)
    return preco


def _rotulo_periodos(periodicidade: str, n: int, precos: list[int]) -> str:
    singular, plural = UNIDADE[P(periodicidade)]
    texto = f"{n} {singular if n == 1 else plural}"
    if len(set(precos)) == 1:
        texto += f" × {formatar_reais(precos[0])}"
    return texto


def _texto_retirada(entrada: Entrada, quatro_semanais: bool) -> str:
    if entrada.periodicidade == P.DIARIA:
        texto = "Hoje: todas as diárias"
    elif entrada.periodicidade == P.SEMANAL:
        texto = "Hoje: primeira semana"
    elif quatro_semanais:
        texto = "Hoje: primeira parcela do mês"
    else:
        texto = "Hoje: primeiro mês"
    return f"{texto} mais caução." if entrada.caucao_centavos else f"{texto}."


def calcular(entrada: Entrada) -> Calculo:
    fuso = ZoneInfo(entrada.fuso)
    inicio = entrada.inicio.astimezone(fuso)
    periodos = _quantos_periodos(entrada, inicio)
    fim = fim_dos_periodos(entrada.periodicidade, inicio, periodos)
    primeiro = entrada.primeiro_vencimento or inicio.date()

    extras_periodo = sum(
        e.valor_centavos * e.quantidade for e in entrada.extras if e.cobranca == "por_periodo"
    )
    extras_unicos = sum(
        e.valor_centavos * e.quantidade for e in entrada.extras if e.cobranca != "por_periodo"
    )
    precos = [_preco_do_periodo(entrada, k) for k in range(1, periodos + 1)]
    descontos = [aplicar_percentual(p, entrada.desconto_pct) for p in precos]
    valores = [p - d + extras_periodo for p, d in zip(precos, descontos, strict=True)]
    valores[0] += extras_unicos

    quatro_semanais = (
        entrada.periodicidade == P.MENSAL
        and entrada.parcelamento_mensal == ParcelamentoMensal.QUATRO_SEMANAIS
    )
    if entrada.periodicidade == P.DIARIA:
        parcelas = [Parcela(1, primeiro, sum(valores))]
    elif entrada.periodicidade == P.SEMANAL:
        parcelas = [
            Parcela(k + 1, primeiro + timedelta(days=7 * k), v) for k, v in enumerate(valores)
        ]
    elif quatro_semanais:
        parcelas = []
        for k, valor in enumerate(valores):
            comeco = somar_meses_data(primeiro, k)
            for semana, parte in enumerate(dividir_em_parcelas(valor, 4)):
                parcelas.append(
                    Parcela(len(parcelas) + 1, comeco + timedelta(days=7 * semana), parte)
                )
    else:
        parcelas = [Parcela(k + 1, somar_meses_data(primeiro, k), v) for k, v in enumerate(valores)]

    seguinte = _preco_do_periodo(entrada, 2)
    valor_seguinte = seguinte - aplicar_percentual(seguinte, entrada.desconto_pct) + extras_periodo
    proximos = parcelas[1].valor_centavos if len(parcelas) > 1 else valor_seguinte
    extras_total = extras_periodo * periodos + extras_unicos
    desconto_total = sum(descontos)
    return Calculo(
        periodos=periodos,
        fim_previsto=fim,
        valor_periodo_centavos=precos[0] - descontos[0],
        proximos_periodos_centavos=proximos,
        caucao_centavos=entrada.caucao_centavos,
        periodos_centavos=sum(precos),
        extras_centavos=extras_total,
        desconto_centavos=desconto_total,
        parcelas=parcelas,
        linhas=[
            {
                "rotulo": _rotulo_periodos(entrada.periodicidade, periodos, precos),
                "valor_centavos": sum(precos),
            },
            {"rotulo": "Adicionais", "valor_centavos": extras_total},
            {"rotulo": "Desconto", "valor_centavos": desconto_total},
            {"rotulo": "Caução (devolvida no fim)", "valor_centavos": entrada.caucao_centavos},
        ],
        texto_retirada=_texto_retirada(entrada, quatro_semanais),
    )
