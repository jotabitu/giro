"""FIN-15 sobre a carteira de outubro da Moto Rápida (T-056).

Os dados vêm de `docs/qa/carteira-outubro/` (gerados por `gerar.py`). Não usam banco nem API:
provam que os números de referência saem das 42 locações pela tabela de preços. Quando a T-017 e o
seed da T-019 existirem, o mesmo conjunto de números é conferido contra a API.
"""

import csv
import importlib.util
from datetime import date
from pathlib import Path

import pytest

PASTA = Path(__file__).resolve().parents[3] / "docs" / "qa" / "carteira-outubro"


def _gerador():
    spec = importlib.util.spec_from_file_location("gerar_carteira_outubro", PASTA / "gerar.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def parcelas():
    with open(PASTA / "parcelas.csv", encoding="utf-8") as f:
        return [
            {
                "codigo": linha["codigo"],
                "vencimento": date.fromisoformat(linha["vencimento"]),
                "valor_centavos": int(linha["valor_centavos"]),
                "situacao": linha["situacao"],
            }
            for linha in csv.DictReader(f)
        ]


def test_fin_15_carteira_tem_42_locacoes_e_csv_igual_ao_gerador(parcelas):
    gerador = _gerador()
    locacoes, esperadas = gerador.carteira()
    assert len(locacoes) == 42
    with open(PASTA / "locacoes.csv", encoding="utf-8") as f:
        assert [linha["codigo"] for linha in csv.DictReader(f)] == [x[0] for x in locacoes]
    assert sorted(
        (p["codigo"], p["vencimento"], p["valor_centavos"], p["situacao"]) for p in parcelas
    ) == sorted(
        (p["codigo"], p["vencimento"], p["valor_centavos"], p["situacao"]) for p in esperadas
    )


def test_fin_15_previsto_recebido_vence_hoje_e_atraso_em_07_out(parcelas):
    n = _gerador().numeros(parcelas)
    assert (n["previsto_centavos"], n["previsto_parcelas"]) == (5200210, 128)
    assert (n["recebido_centavos"], n["recebido_parcelas"], n["recebido_percentual"]) == (
        1340170,
        30,
        25.77,
    )
    assert (n["vence_hoje_centavos"], n["vence_hoje_parcelas"]) == (262580, 6)
    assert (n["atraso_centavos"], n["atraso_parcelas"], n["atraso_clientes"]) == (164640, 2, 2)
    assert (n["atraso_1_7_centavos"], n["atraso_8_30_centavos"], n["atraso_mais_30_centavos"]) == (
        29940,
        134700,
        0,
    )


def test_fin_15_abas_somam_a_aba_todas(parcelas):
    n = _gerador().numeros(parcelas)
    assert (n["aba_em_atraso"], n["aba_vencem_hoje"], n["aba_a_vencer"], n["aba_pagas"]) == (
        2,
        6,
        92,
        30,
    )
    assert (
        n["aba_todas"]
        == 130
        == n["aba_em_atraso"] + n["aba_vencem_hoje"] + n["aba_a_vencer"] + n["aba_pagas"]
    )


def test_fin_15_contador_do_menu_e_a_aba_em_atraso(parcelas):
    n = _gerador().numeros(parcelas)
    assert (
        n["aba_em_atraso"] == n["atraso_parcelas"] == 2
    )  # Carlos e Rafael (caso "Contadores do menu")


def test_fin_15_recebido_nunca_passa_do_previsto(parcelas):
    n = _gerador().numeros(parcelas)
    assert n["recebido_centavos"] <= n["previsto_centavos"]
    assert 0 <= n["recebido_percentual"] <= 100
