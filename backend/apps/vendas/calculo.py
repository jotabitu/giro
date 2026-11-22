"""Contas da venda, sem banco (ADR 0042, item 4; `VEN-02`, `VEN-04`, `FIN-09`).

Módulo puro, como `locacoes.calculo`: recebe números e devolve números. `Decimal` nas contas
intermediárias e `ROUND_HALF_UP` no centavo só no que se grava ou se mostra como linha própria
(`docs/regras-de-negocio.md`, "Dinheiro"). A simulação, a criação, a edição e o pedido de
desconto chamam `calcular` com o preço de tabela copiado do veículo.
"""

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from apps.veiculos import precos

# VEN-02 (decisão do dono de 18 nov 2026): limite fixo da venda; o do veículo vale só na locação.
LIMITE_DESCONTO_PCT = Decimal("5.00")
PARCELAS_MIN, PARCELAS_MAX = 2, 24  # VEN-04
CEM = Decimal(100)
UM = Decimal(1)

A_VISTA = "a_vista"
ENTRADA_PARCELAS = "entrada_parcelas"
FINANCIAMENTO = "financiamento"

ACIMA_DO_LIMITE = "Acima de 5% precisa do gerente. Use Pedir aprovação."
FINANCIAMENTO_FORA = "O financiamento ainda não está disponível."


def arredondar(valor: Decimal) -> int:
    """Para o centavo, com meio centavo para cima."""
    return int(valor.quantize(UM, rounding=ROUND_HALF_UP))


def pmt(saldo: Decimal, taxa: Decimal, parcelas: int) -> Decimal:
    """A mesma conta da `VEI-16` (`veiculos.precos.pmt`, módulo puro): sem arredondar."""
    return precos.pmt(taxa, parcelas, saldo)


def limite_efetivo(desconto_aprovado_pct: Decimal | None) -> Decimal:
    """Até o maior desconto já aprovado não se pede de novo (ADR 0042, item 3)."""
    return max(LIMITE_DESCONTO_PCT, desconto_aprovado_pct or Decimal(0))


def precisa_aprovacao(desconto_pct: Decimal, desconto_aprovado_pct: Decimal | None) -> bool:
    return desconto_pct > limite_efetivo(desconto_aprovado_pct)


@dataclass(frozen=True)
class Entrada:
    preco_tabela_centavos: int
    desconto_pct: Decimal = Decimal(0)
    forma: str = ""
    entrada_centavos: int | None = None
    num_parcelas: int | None = None
    juros_pct: Decimal = Decimal(0)
    comissao_pct: Decimal = Decimal("3.00")
    desconto_aprovado_pct: Decimal | None = None
    troca_centavos: int = 0  # fase 2 (VEN-05)


@dataclass(frozen=True)
class Calculo:
    preco_tabela_centavos: int
    desconto_pct: Decimal
    desconto_centavos: int
    preco_final_centavos: int
    troca_centavos: int
    forma: str
    entrada_centavos: int | None
    saldo_centavos: int
    num_parcelas: int | None
    juros_pct: Decimal
    parcela_centavos: int | None
    ultima_parcela_centavos: int | None
    total_parcelas_centavos: int
    comissao_centavos: int
    precisa_aprovacao: bool
    erros: dict[str, list[str]] = field(default_factory=dict)

    @property
    def completo(self) -> bool:
        """Forma escolhida e sem erro: dá para enviar a proposta ou pedir o desconto."""
        return self.forma in (A_VISTA, ENTRADA_PARCELAS) and not self.erros


def _parcelas(saldo: int, n: int, juros_pct: Decimal) -> tuple[int, int]:
    """(parcela, última). Sem juros, `saldo // n` e a última leva a diferença; com juros, a
    parcela da tabela Price arredondada, igual em todas (o total é parcela × n)."""
    if juros_pct == 0:
        parcela = saldo // n
        return parcela, saldo - parcela * (n - 1)
    parcela = arredondar(pmt(Decimal(saldo), juros_pct / CEM, n))
    return parcela, parcela


def calcular(entrada: Entrada) -> Calculo:
    erros: dict[str, list[str]] = {}
    tabela = entrada.preco_tabela_centavos
    pct = Decimal(entrada.desconto_pct)
    if pct < 0 or pct > CEM:
        erros["desconto_pct"] = ["O desconto vai de 0% a 100%."]
        pct = min(max(pct, Decimal(0)), CEM)
    desconto = arredondar(Decimal(tabela) * pct / CEM)
    final = tabela - desconto
    troca = entrada.troca_centavos
    forma = entrada.forma
    valor_entrada: int | None = entrada.entrada_centavos
    saldo = 0
    n: int | None = None
    parcela: int | None = None
    ultima: int | None = None
    if forma == FINANCIAMENTO:
        erros["forma"] = [FINANCIAMENTO_FORA]  # VEN-18
    elif forma == A_VISTA:
        valor_entrada = final - troca
    elif forma == ENTRADA_PARCELAS:
        n = entrada.num_parcelas
        if n is None or not PARCELAS_MIN <= n <= PARCELAS_MAX:
            erros["num_parcelas"] = ["Escolha de 2 a 24 parcelas."]
            n = None
        if valor_entrada is None:
            erros["entrada_centavos"] = ["Informe a entrada."]
        elif valor_entrada + troca >= final:
            erros["entrada_centavos"] = ["A entrada tem que ser menor que o preço final."]
        else:
            saldo = final - valor_entrada - troca
            if n is not None:
                parcela, ultima = _parcelas(saldo, n, Decimal(entrada.juros_pct))
    total = 0 if parcela is None or ultima is None or n is None else parcela * (n - 1) + ultima
    return Calculo(
        preco_tabela_centavos=tabela,
        desconto_pct=pct,
        desconto_centavos=desconto,
        preco_final_centavos=final,
        troca_centavos=troca,
        forma=forma,
        entrada_centavos=valor_entrada,
        saldo_centavos=saldo,
        num_parcelas=n,
        juros_pct=Decimal(entrada.juros_pct) if forma == ENTRADA_PARCELAS else Decimal(0),
        parcela_centavos=parcela,
        ultima_parcela_centavos=ultima,
        total_parcelas_centavos=total,
        comissao_centavos=arredondar(Decimal(final) * Decimal(entrada.comissao_pct) / CEM),
        precisa_aprovacao=precisa_aprovacao(pct, entrada.desconto_aprovado_pct),
        erros=erros,
    )


def _somar_meses(dia: date, meses: int) -> date:
    """O mesmo dia `meses` depois; no mês sem esse dia, o último dia do mês (`VEN-04`)."""
    total = dia.month - 1 + meses
    ano, mes = dia.year + total // 12, total % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def vencimentos(vendida_em_local: date, parcelas: int) -> list[date]:
    """A 1ª um mês depois do dia em que a venda vira `vendida`, as outras no mesmo dia dos meses
    seguintes (`VEN-04`). Usado na conclusão (fase 1b)."""
    return [_somar_meses(vendida_em_local, i) for i in range(1, parcelas + 1)]
