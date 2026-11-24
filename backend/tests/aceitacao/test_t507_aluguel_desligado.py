"""T-507 · Aluguel ligado ou desligado no veículo (VEI-21, padrão A nos dois pontos em aberto).

Moto Rápida, Filial Centro, 07 out 2026: o SAK-1D39 (Street) com os planos do modelo (diária
R$ 54,90, semanal R$ 329,00, mensal R$ 1.190,00) e a Pop 110i TBC-5H21 com a locação com compra
ligada (`dados-de-teste.md`). Desligar o aluguel guarda os planos, não muda o status (VEI-15),
tira o veículo da Nova locação e da troca (409 `VEI-21`) e deixa a compra e as renovações.
"""

from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.locacoes import services
from apps.locacoes.models import Locacao
from apps.veiculos.models import HistoricoPrecoVeiculo, PlanoVeiculo, Veiculo
from comum.erros import Conflito

from .test_t015_locacoes import LISTA, SIMULAR, Cenario
from .test_t015_locacoes import cenario as cenario
from .test_t495_locacao_le_plano import (
    STREET,
    _corpo_da_compra,
    _mudar_plano,
    _plano,
    _retirar,
)
from .test_t495_locacao_le_plano import pop as pop

VEICULOS = "/api/veiculos/"
DESATIVADO = "O aluguel desta moto está desativado. O administrador ativa em Planos e preços."


def _aluguel(cenario: Cenario, veiculo: Veiculo, ligado: bool, quem: str = "Mariana") -> Any:
    return cenario.moto.api(quem).put(
        f"{VEICULOS}{veiculo.pk}/precos/", {"aluguel_ligado": ligado}, format="json"
    )


def _ligados(veiculo: Veiculo) -> list[str]:
    return sorted(
        PlanoVeiculo.ativos.filter(veiculo=veiculo, ligado=True).values_list("tipo", flat=True)
    )


def test_vei_21_desligar_guarda_os_planos_e_nao_muda_o_status(cenario: Cenario) -> None:
    sak = cenario.sak
    _mudar_plano(sak, "mensal", ligado=False)
    antes = _ligados(sak)
    resposta = _aluguel(cenario, sak, False)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["aluguel_ligado"], corpo["aviso_aluguel"]) == (False, DESATIVADO)
    # Os planos ficam como estavam, com o ligado de cada um; a VEI-15 não conta o aluguel.
    assert _ligados(sak) == antes
    assert {p["tipo"]: p["ligado"] for p in corpo["planos"]}["mensal"] is False
    assert corpo["aviso_preco"] is None
    assert Veiculo.objects.get(pk=sak.pk).status == "disponivel"
    # Ligar de novo: voltam como estavam.
    religado = _aluguel(cenario, sak, True)
    assert (religado.json()["aluguel_ligado"], religado.json()["aviso_aluguel"]) == (True, None)
    assert _ligados(sak) == antes


def test_vei_21_vei_17_historico_e_auditoria_com_o_antes_e_o_depois(cenario: Cenario) -> None:
    assert _aluguel(cenario, cenario.sak, False).status_code == 200
    linha = HistoricoPrecoVeiculo.objects.get(veiculo=cenario.sak, campo="aluguel_ligado")
    assert (linha.alvo, linha.de, linha.para) == ("aluguel", True, False)
    assert linha.por_id == cenario.pessoas["Mariana"].pk
    evento = EventoAuditoria.objects.filter(acao="veiculo.precos_salvar").latest("id")
    assert {
        "alvo": "aluguel",
        "alvo_nome": "",
        "campo": "aluguel_ligado",
        "de": True,
        "para": False,
    } in evento.depois["mudancas"]
    # O mesmo valor de novo não grava nada.
    assert _aluguel(cenario, cenario.sak, False).status_code == 200
    assert (
        HistoricoPrecoVeiculo.objects.filter(veiculo=cenario.sak, campo="aluguel_ligado").count()
        == 1
    )


def test_vei_21_so_o_administrador_liga_e_desliga(cenario: Cenario) -> None:
    assert _aluguel(cenario, cenario.sak, False, quem="Rodrigo").status_code == 403
    assert Veiculo.objects.get(pk=cenario.sak.pk).aluguel_ligado is True
    lido = cenario.moto.api("Rodrigo").get(f"{VEICULOS}{cenario.sak.pk}/precos/").json()
    assert (lido["aluguel_ligado"], lido["pode_editar"]) == (True, False)


def test_vei_21_nova_locacao_de_aluguel_recusada(cenario: Cenario) -> None:
    assert _aluguel(cenario, cenario.sak, False).status_code == 200
    for rota in (SIMULAR, LISTA):
        resposta = cenario.moto.api("Bruna").post(rota, cenario.corpo(), format="json")
        assert resposta.status_code == 409, resposta.json()
        assert (resposta.json()["codigo"], resposta.json()["mensagem"]) == ("VEI-21", DESATIVADO)
    assert not Locacao.objects.exists()


def test_vei_21_ficha_e_frota_mostram_o_aluguel_desligado(cenario: Cenario) -> None:
    assert _aluguel(cenario, cenario.sak, False).status_code == 200
    api = cenario.moto.api("Bruna")
    ficha = api.get(f"{VEICULOS}{cenario.sak.pk}/").json()
    assert (ficha["aluguel_ligado"], ficha["status"]) == (False, "disponivel")
    lista = api.get(VEICULOS, {"busca": cenario.sak.placa}).json()["resultados"]
    assert [v["aluguel_ligado"] for v in lista] == [False]


def test_vei_21_locacao_com_compra_independe_do_aluguel(cenario: Cenario, pop: Veiculo) -> None:
    """Padrão A: com o aluguel desligado, a compra ligada segue na Nova locação."""
    assert _aluguel(cenario, pop, False).status_code == 200
    resposta = cenario.moto.api("Bruna").post(
        SIMULAR, _corpo_da_compra(cenario, pop), format="json"
    )
    assert resposta.status_code == 200, resposta.json()


def test_vei_21_loc_09_troca_nao_oferece_o_veiculo_desligado(cenario: Cenario) -> None:
    locacao = _retirar(cenario.confirmada(periodos=2)["id"])
    novo = cenario.veiculo(STREET, exceto=(cenario.sak.placa,))
    assert _aluguel(cenario, novo, False).status_code == 200
    with pytest.raises(Conflito) as erro:
        services.pedir_troca(locacao, novo.pk, "Pneu furado", cenario.pessoas["Bruna"])
    assert (erro.value.codigo, erro.value.mensagem) == ("VEI-21", DESATIVADO)


def test_vei_21_loc_15_locacao_aberta_segue_renovando(cenario: Cenario) -> None:
    locacao = _retirar(cenario.confirmada(periodos=1)["id"])
    assert _aluguel(cenario, cenario.sak, False).status_code == 200
    services.renovar(locacao, {"periodos": 1}, cenario.pessoas["Bruna"])
    locacao.refresh_from_db()
    assert locacao.plano_veiculo_id == _plano(cenario.sak, "semanal").pk
