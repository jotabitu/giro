"""T-320 · OpenAPI das Movimentações sem nomes repetidos (MOV-01; achado do frontend na T-289).

Os componentes das movimentações têm nome próprio (`ref_name`), para não perder campos para os de
outro app; o quadro declara e aplica `levando` e `busca`, como a lista.
"""

from pathlib import Path
from typing import Any

import yaml

from .test_t288_movimentacoes import LISTA, _criada, cenario  # noqa: F401 - fixture

OPENAPI = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.yaml"


def _esquema() -> dict[str, Any]:
    return dict(yaml.safe_load(OPENAPI.read_text(encoding="utf-8")))


def _codigos(quadro: dict[str, Any]) -> list[str]:
    return [i["codigo"] for c in quadro["colunas"] for i in c["itens"]]


def test_mov_01_openapi_com_nomes_proprios():
    esquema = _esquema()
    componentes = esquema["components"]["schemas"]
    veiculo = componentes["VeiculoDaMovimentacao"]["properties"]
    assert {"id", "placa", "modelo", "status"} <= set(veiculo)
    coluna = componentes["Coluna"]["properties"]["itens"]["items"]["$ref"]
    assert coluna == "#/components/schemas/LinhaDaMovimentacao"
    linha = componentes["LinhaDaMovimentacao"]["properties"]
    assert {"paradas_total", "resumo", "acoes"} <= set(linha)
    assert "paradas_total" not in componentes["Linha"]["properties"]  # a da importação
    parametros = esquema["paths"]["/api/movimentacoes/quadro/"]["get"]["parameters"]
    assert {p["name"] for p in parametros} >= {"filial", "levando", "busca"}


def test_mov_01_quadro_com_busca_e_levando(cenario):  # noqa: F811
    _criada(cenario)  # MOV-0001, SAK1D39, levada pelo João
    rodrigo = cenario.moto.api("Rodrigo")
    assert _codigos(rodrigo.get(f"{LISTA}quadro/").json()) == ["MOV-0001"]
    assert _codigos(rodrigo.get(f"{LISTA}quadro/?busca=mov-0001").json()) == ["MOV-0001"]
    assert _codigos(rodrigo.get(f"{LISTA}quadro/?busca=SAK-1D39").json()) == ["MOV-0001"]
    assert _codigos(rodrigo.get(f"{LISTA}quadro/?busca=XYZ9Z99").json()) == []
    assert _codigos(rodrigo.get(f"{LISTA}quadro/?levando=eu").json()) == []
    joao = cenario.moto.api("João")
    assert _codigos(joao.get(f"{LISTA}quadro/?levando=eu").json()) == ["MOV-0001"]
