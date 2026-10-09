"""Contas com dinheiro em centavos (ADR 0003 e 0009).

Contas intermediárias em `Decimal`; cada valor calculado é arredondado para o centavo com
`ROUND_HALF_UP`. Nada de `float`.
"""

from decimal import ROUND_HALF_UP, Decimal


def _para_centavos(valor: Decimal) -> int:
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def aplicar_percentual(valor_centavos: int, pct: Decimal | int | str) -> int:
    """`pct` em pontos percentuais: 3% de 2.106.800 centavos = 63.204 centavos."""
    if isinstance(pct, float):
        raise TypeError("Percentual não pode ser float; use Decimal ou str.")
    return _para_centavos(Decimal(valor_centavos) * Decimal(pct) / Decimal(100))


def proporcional(valor_centavos: int, numerador: int, denominador: int) -> int:
    """`valor * numerador / denominador`, arredondado no centavo (ex.: dias usados do período)."""
    if denominador == 0:
        raise ZeroDivisionError("Denominador não pode ser zero.")
    return _para_centavos(Decimal(valor_centavos) * numerador / Decimal(denominador))


def dividir_em_parcelas(total_centavos: int, n: int) -> list[int]:
    """Parcelas iguais arredondadas para baixo; a diferença vai na última (ADR 0003)."""
    if n < 1:
        raise ValueError("Número de parcelas deve ser pelo menos 1.")
    base = total_centavos // n
    return [base] * (n - 1) + [total_centavos - base * (n - 1)]


def formatar_reais(valor_centavos: int) -> str:
    """`32900` vira `"R$ 329,00"`; `164640` vira `"R$ 1.646,40"` (textos prontos da API)."""
    sinal = "-" if valor_centavos < 0 else ""
    reais, centavos = divmod(abs(valor_centavos), 100)
    return f"{sinal}R$ {reais:,}".replace(",", ".") + f",{centavos:02d}"
