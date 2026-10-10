"""Contas puras do acerto da devolução (DEV-01, DEV-02): sem banco, sem relógio.

O combustível sai da capacidade do tanque × a diferença entre o nível da saída e o da chegada,
com os níveis da VIS-03 valendo 0, 1/4, 1/2, 3/4 e 1; o valor é litros × preço do litro da
filial + R$ 10,00, uma vez por devolução e só quando falta combustível (decisão de 07 out 2026,
T-041). O saldo é caução + créditos − cobranças.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from comum.dinheiro import formatar_reais

TAXA_COMBUSTIVEL_CENTAVOS = 1000  # DEV-01
DIAS_PARA_PAGAR_O_SALDO = 3  # DEV-02

# VIS-03: o nível em quartos de tanque.
QUARTOS = {"reserva": 0, "um_quarto": 1, "meio": 2, "tres_quartos": 3, "cheio": 4}
FALTOU = {1: "1/4 tanque", 2: "1/2 tanque", 3: "3/4 tanque", 4: "o tanque todo"}


@dataclass(frozen=True)
class Combustivel:
    calculado: bool  # falso sem capacidade do tanque, sem preço ou sem os dois níveis
    quartos: int  # quartos de tanque que faltaram (0 se voltou igual ou mais cheio)
    litros: Decimal
    valor_centavos: int
    descricao: str


def litros(texto: Decimal) -> str:
    """`Decimal("4.0")` vira `"4 L"`; `Decimal("4.5")` vira `"4,5 L"`."""
    normal = texto.quantize(Decimal("0.1"))
    if normal == normal.to_integral_value():
        return f"{int(normal)} L"
    return f"{str(normal).replace('.', ',')} L"


def combustivel(
    *,
    capacidade_litros: Decimal | None,
    preco_litro_centavos: int | None,
    saida: str,
    chegada: str,
) -> Combustivel:
    if not chegada:  # a vistoria de chegada ainda não tem o nível
        return Combustivel(True, 0, Decimal("0.0"), 0, "Combustível (falta o nível na chegada)")
    if not saida:  # sem a vistoria de saída, a tela pede o valor
        return Combustivel(False, 0, Decimal("0.0"), 0, "Combustível (sem o nível da saída)")
    quartos = max(0, QUARTOS[saida] - QUARTOS[chegada])
    if quartos == 0:
        return Combustivel(True, 0, Decimal("0.0"), 0, "Combustível (voltou como saiu)")
    if capacidade_litros is None or preco_litro_centavos is None:
        faltou = f"Combustível (faltou {FALTOU[quartos]})"
        return Combustivel(False, quartos, Decimal("0.0"), 0, faltou)
    faltaram = (Decimal(capacidade_litros) * quartos / 4).quantize(Decimal("0.1"))
    valor = (faltaram * preco_litro_centavos).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    descricao = (
        f"Combustível (faltou {FALTOU[quartos]}, {litros(faltaram)} × "
        f"{formatar_reais(preco_litro_centavos)} + {formatar_reais(TAXA_COMBUSTIVEL_CENTAVOS)})"
    )
    return Combustivel(True, quartos, faltaram, int(valor) + TAXA_COMBUSTIVEL_CENTAVOS, descricao)


@dataclass(frozen=True)
class Resultado:
    tipo: str  # devolver, cobrar, zerado
    valor_centavos: int
    texto: str
    botao: str


def resultado(caucao_centavos: int, creditos_centavos: int, cobrancas_centavos: int) -> Resultado:
    """DEV-02: o que a tela mostra no fim do acerto."""
    saldo = caucao_centavos + creditos_centavos - cobrancas_centavos
    caucao = formatar_reais(caucao_centavos)
    liquido = cobrancas_centavos - creditos_centavos
    if saldo > 0:
        if liquido > 0:
            texto = f"Desconta {formatar_reais(liquido)} da caução de {caucao}"
        elif liquido < 0:
            texto = f"Devolve a caução de {caucao} e mais {formatar_reais(-liquido)}"
        else:
            texto = f"Devolve a caução de {caucao}"
        return Resultado("devolver", saldo, texto, f"Encerrar e devolver {formatar_reais(saldo)}")
    if saldo < 0:
        texto = (
            f"As cobranças passam da caução de {caucao} em {formatar_reais(-saldo)}, "
            f"que viram uma conta com vencimento em {DIAS_PARA_PAGAR_O_SALDO} dias"
        )
        return Resultado("cobrar", -saldo, texto, f"Encerrar e cobrar {formatar_reais(-saldo)}")
    return Resultado("zerado", 0, f"A caução de {caucao} cobre as cobranças", "Encerrar")
