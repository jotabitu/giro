"""T-449: data e dias da devolução atrasada (LOC-10, "Data e dias do atraso na tela").

O "desde" do card "Agora" da ficha do veículo vem pronto da API, em `situacao.desde` (e em
`locacao_atual.desde`): o fim previsto na devolução atrasada, o início nos outros casos. Os dias
da lista contam do fim previsto. Caso do seed: LOC-2836, Juliana, PNB-7C04, semanal de 30 set
18:00 a 14 out 18:00 (docs/qa/criterios/T-449.md).
"""

from typing import Any

import pytest

from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo

from .test_t015_locacoes import Cenario, com_carteira  # noqa: F401 - fixture
from .test_t016_vistorias import _ir_para, cenario  # noqa: F401 - fixtures

FICHA = "/api/veiculos/{}/"


def _no_dia(cenario: Cenario, relogio: Any, quando: str) -> None:  # noqa: F811
    _ir_para(cenario, relogio, quando)
    locacoes_services.marcar_devolucoes_atrasadas()


def _ficha(cenario: Cenario, veiculo_id: int) -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api("Rodrigo").get(FICHA.format(veiculo_id))
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _situacao_na_lista(cenario: Cenario, locacao: Locacao) -> dict[str, Any]:  # noqa: F811
    api = cenario.moto.api("Rodrigo")
    corpo = api.get("/api/locacoes/", {"veiculo": locacao.veiculo_id}).json()
    linha = next(x for x in corpo["resultados"] if x["codigo"] == locacao.codigo)
    return dict(linha["situacao"])


@pytest.fixture
def juliana(com_carteira) -> Locacao:  # noqa: F811
    return com_carteira["LOC-2836"]


def test_loc_10_atrasado_desde_a_devolucao_prevista(cenario, juliana, relogio):  # noqa: F811
    """CA-449-01: em 10 nov, "Atrasado desde 14 out" na ficha e "Devolução atrasada 27 dias"
    na lista; a data é a do fim previsto, não a do início (30 set)."""
    _no_dia(cenario, relogio, "2026-11-10 10:00")
    ficha = _ficha(cenario, juliana.veiculo_id)
    assert ficha["situacao"] == {
        "codigo": "atrasado",
        "rotulo": "Atrasado",
        "tom": "perigo",
        "desde": "2026-10-14",
    }
    assert ficha["locacao_atual"]["desde"] == "2026-10-14"
    assert _situacao_na_lista(cenario, juliana)["rotulo"] == "Devolução atrasada 27 dias"


def test_loc_10_primeiro_dia_de_atraso(cenario, juliana, relogio):  # noqa: F811
    """CA-449-02: em 15 out 10:00, desde 14 out e 1 dia, no singular."""
    _no_dia(cenario, relogio, "2026-10-15 10:00")
    juliana.refresh_from_db()
    assert juliana.status == "devolucao_atrasada"
    assert _ficha(cenario, juliana.veiculo_id)["situacao"]["desde"] == "2026-10-14"
    assert _situacao_na_lista(cenario, juliana)["rotulo"] == "Devolução atrasada 1 dia"


def test_loc_10_dentro_da_tolerancia_alugado_desde_o_inicio(cenario, juliana, relogio):  # noqa: F811
    """CA-449-03: em 14 out 18:30 a locação segue ativa; o "desde" é o início (30 set)."""
    _no_dia(cenario, relogio, "2026-10-14 18:30")
    juliana.refresh_from_db()
    assert juliana.status == "ativa"
    situacao = _ficha(cenario, juliana.veiculo_id)["situacao"]
    assert situacao["codigo"] == "alugado"
    assert situacao["desde"] == "2026-09-30"
    assert "atrasad" not in _situacao_na_lista(cenario, juliana)["rotulo"].lower()


def test_loc_10_sem_locacao_o_desde_vem_nulo(cenario, com_carteira):  # noqa: F811
    """Veículo sem locação aberta: `situacao.desde` vem `null` (a tela mostra só o rótulo)."""
    livre = Veiculo.objects.filter(status="disponivel").order_by("id")[0]
    assert _ficha(cenario, livre.pk)["situacao"]["desde"] is None
