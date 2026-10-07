from decimal import Decimal

import pytest

from comum.dinheiro import aplicar_percentual, dividir_em_parcelas, proporcional


def test_percentual_3_pct_de_21068_reais():
    # ADR 0009: 3% de R$ 21.068,00 = R$ 632,04.
    assert aplicar_percentual(2_106_800, Decimal("3")) == 63_204


def test_percentual_arredonda_meio_centavo_para_cima():
    # 8% de R$ 0,25 = 2,0 centavos; 50% de 1 centavo = 0,5 → 1 (ROUND_HALF_UP).
    assert aplicar_percentual(25, Decimal("8.00")) == 2
    assert aplicar_percentual(1, Decimal("50")) == 1
    assert aplicar_percentual(3, Decimal("50")) == 2


def test_percentual_recusa_float():
    with pytest.raises(TypeError):
        aplicar_percentual(1000, 3.0)  # type: ignore[arg-type]


def test_parcelas_16068_em_12():
    # ADR 0009: R$ 16.068,00 / 12 = R$ 1.339,00.
    assert dividir_em_parcelas(1_606_800, 12) == [133_900] * 12


def test_parcelas_diferenca_vai_na_ultima():
    parcelas = dividir_em_parcelas(10_000, 3)
    assert parcelas == [3_333, 3_333, 3_334]
    assert sum(parcelas) == 10_000


def test_parcelas_recusa_zero():
    with pytest.raises(ValueError):
        dividir_em_parcelas(10_000, 0)


def test_proporcional_arredonda_no_centavo():
    # 10 de 30 dias de R$ 1.000,00 = 333,333... → 33.333 centavos.
    assert proporcional(100_000, 10, 30) == 33_333
    # 1 de 2 de 1 centavo = 0,5 → 1.
    assert proporcional(1, 1, 2) == 1
