"""T-499 · Seed do estoque à venda parado (`docs/regras/dados-de-teste.md`, casos "Dias em estoque
em 07 out" da T-486 e "Estoque à venda em 07 out" da T-487).

Roda sobre o seed pronto e confere os dados de entrada (datas de entrada à venda, valores e
despesas) e os números do caso, calculados aqui a partir do histórico de status e das despesas:
a API de `VEI-18`, `VEI-19` e `VEI-20` ainda não existe, e a conferência por ela é das T-486 e
T-487. As vendas de setembro e outubro (`VEN-12`) esperam o fluxo de venda (`VEN-01` a `VEN-09`).
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from apps.financeiro.models import Despesa
from apps.veiculos.models import HistoricoStatusVeiculo, Veiculo

from .test_t019_seed_completo import seed  # noqa: F401 - fixture
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures

FUSO = ZoneInfo("America/Sao_Paulo")
HOJE = date(2026, 10, 7)
LIMITE_DE_DIAS = 30  # `VEI-19`: padrão da empresa


def _centavos(valor: Decimal) -> int:
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _percentual(parte: int, total: int) -> Decimal:
    return (Decimal(parte) * 100 / Decimal(total)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _entrada(veiculo: Veiculo) -> date:
    """`VEI-18`: a última passagem para `a_venda`, no dia de `America/Sao_Paulo`."""
    passagem = (
        HistoricoStatusVeiculo.objects.filter(veiculo=veiculo, para="a_venda").order_by("em").last()
    )
    assert passagem is not None
    return passagem.em.astimezone(FUSO).date()


def _custo(veiculo: Veiculo) -> int:
    """`VEI-13` e `VEI-20`: compra mais as despesas ligadas, sem as `recusada`."""
    despesas = Despesa.objects.filter(veiculo=veiculo).exclude(status="recusada")
    return (veiculo.valor_compra_centavos or 0) + sum(d.valor_centavos for d in despesas)


def _estoque() -> dict[str, Veiculo]:
    return {v.placa: v for v in Veiculo.objects.filter(status="a_venda")}


def test_vei_18_dias_em_estoque_seed(seed):  # noqa: F811
    estoque = _estoque()
    assert len(estoque) == 12
    assert Veiculo.objects.count() == 86
    dias = {placa: (HOJE - _entrada(v)).days for placa, v in estoque.items()}
    assert _entrada(estoque["PVE1A07"]) == date(2026, 8, 15)
    assert _entrada(estoque["PVF2B18"]) == date(2026, 9, 6)
    assert _entrada(estoque["PVG3C29"]) == date(2026, 9, 7)
    assert (dias["PVE1A07"], dias["PVF2B18"], dias["PVG3C29"]) == (53, 31, 30)
    outros = [d for placa, d in dias.items() if not placa.startswith("PV")]
    assert len(outros) == 9
    assert set(outros) == {0}  # "Hoje": colocados à venda em 07 out às 07:00


def test_vei_19_veiculos_parados_com_limite_de_30_dias(seed):  # noqa: F811
    estoque = _estoque()
    parados = sorted(
        placa for placa, v in estoque.items() if (HOJE - _entrada(v)).days > LIMITE_DE_DIAS
    )
    assert parados == ["PVE1A07", "PVF2B18"]  # PVG3C29, com 30 dias, ainda não está parado


def test_vei_20_dados_de_entrada_do_estoque_seed(seed):  # noqa: F811
    estoque = _estoque()
    biz, cg, factor = estoque["PVE1A07"], estoque["PVF2B18"], estoque["PVG3C29"]
    assert [(v.marca, v.modelo, v.ano_modelo) for v in (biz, cg, factor)] == [
        ("Honda", "Biz 125", 2023),
        ("Honda", "CG 160 Fan", 2023),
        ("Yamaha", "Factor 150", 2023),
    ]
    assert [v.categoria.nome for v in (biz, cg, factor)] == [
        "Urbana 110–125",
        "Street 150–160",
        "Street 150–160",
    ]
    assert [v.valor_compra_centavos for v in (biz, cg, factor)] == [1120000, 1390000, 1280000]
    assert [v.valor_venda_centavos for v in (biz, cg, factor)] == [1290000, 1550000, 1320000]
    assert all(v.filial.nome == "Filial Centro" for v in (biz, cg, factor))
    # Os outros 9 `a_venda` não têm valor de compra: "9 veículos sem valor de compra".
    sem_compra = [v for placa, v in estoque.items() if not placa.startswith("PV")]
    assert len(sem_compra) == 9
    assert all(v.valor_compra_centavos is None for v in sem_compra)


def test_vei_20_despesas_ligadas_e_a_recusada_seed(seed):  # noqa: F811
    def valores(placa: str, **filtro: Any) -> list[int]:
        despesas = Despesa.objects.filter(veiculo__placa=placa, **filtro).order_by("data", "id")
        return [d.valor_centavos for d in despesas]

    assert valores("PVE1A07") == [45000]
    assert valores("PVF2B18") == []
    assert sum(valores("PVG3C29", status__in=["a_pagar", "paga", "aguardando_aprovacao"])) == 115000
    recusadas = Despesa.objects.filter(veiculo__placa="PVG3C29", status="recusada")
    assert [d.valor_centavos for d in recusadas] == [60000]
    assert recusadas[0].data == date(2026, 9, 15)
    assert recusadas[0].lancada_por.nome == "João Silva"
    assert recusadas[0].motivo_recusa


def test_vei_20_capital_imobilizado_custo_medio_e_margens_seed(seed):  # noqa: F811
    estoque = _estoque()
    com_compra = [v for v in estoque.values() if v.valor_compra_centavos is not None]
    assert sorted(v.placa for v in com_compra) == ["PVE1A07", "PVF2B18", "PVG3C29"]
    custos = {v.placa: _custo(v) for v in com_compra}
    assert custos == {"PVE1A07": 1165000, "PVF2B18": 1390000, "PVG3C29": 1395000}

    capital = sum(custos.values())
    assert capital == 3950000  # R$ 39.500,00 em 3 veículos
    assert _centavos(Decimal(capital) / len(com_compra)) == 1316667  # R$ 13.166,67

    margens = {v.placa: (v.valor_venda_centavos or 0) - custos[v.placa] for v in com_compra}
    assert margens == {"PVE1A07": 125000, "PVF2B18": 160000, "PVG3C29": -75000}
    assert _percentual(margens["PVE1A07"], 1290000) == Decimal("9.69")
    assert _percentual(margens["PVF2B18"], 1550000) == Decimal("10.32")
    assert _percentual(margens["PVG3C29"], 1320000) == Decimal("-5.68")  # em alerta

    vendas = sum(v.valor_venda_centavos or 0 for v in com_compra)
    assert vendas == 4160000
    assert sum(margens.values()) == 210000  # R$ 2.100,00
    assert _percentual(sum(margens.values()), vendas) == Decimal("5.05")
