"""T-287 · Veículos, só leitura, no menu do vendedor e do financeiro (USR-05, USR-09, T-283).

`pode.veiculos` passa a `ver` para vendedor e financeiro: a Frota e a ficha respondem a eles,
sem nenhuma ação de cadastro, documento, km, status ou transferência; o rendimento e o custo
(`VEI-05`) só para o financeiro. Roda na `empresa_a` com a frota da Moto Rápida.
"""

from typing import Any

import pytest

from apps.contas import selectors as contas
from apps.veiculos.models import Veiculo

from .frota import Frota, montar_frota
from .test_t012_filiais import MotoRapida

LEEM = ("Bruna", "Lúcia")


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _url(veiculo: Veiculo, acao: str = "") -> str:
    return f"/api/veiculos/{veiculo.pk}/{acao + '/' if acao else ''}"


def test_usr_05_pode_veiculos_por_perfil(moto):
    esperado = {
        "Mariana": "editar",
        "Rodrigo": "editar",
        "Bruna": "ver",
        "João": "km_e_avarias",
        "Lúcia": "ver",
    }
    obtido = {nome: contas.pode(moto.pessoas[nome], "veiculos") for nome in esperado}
    assert obtido == esperado
    for nome in LEEM:
        eu = moto.api(nome).get("/api/auth/eu/")
        assert eu.status_code == 200, eu.json()
        assert eu.json()["pode"]["veiculos"] == "ver"


def test_usr_09_vendedor_e_financeiro_leem_a_frota_e_a_ficha(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    for nome in LEEM:
        api = moto.api(nome)
        lista = api.get("/api/veiculos/")
        assert lista.status_code == 200, (nome, lista.json())
        assert lista.json()["contagens"]["todos"] > 0
        ficha = api.get(_url(sak))
        assert ficha.status_code == 200, (nome, ficha.json())
        corpo: dict[str, Any] = ficha.json()
        assert corpo["placa"] == "SAK1D39"
        # Só leitura: nenhuma ação vem `true`.
        assert not [acao for acao, vale in corpo["acoes"].items() if vale is True], nome
        # Valor e data de compra são só de administrador e gerente.
        assert corpo.get("valor_compra_centavos") is None, nome

    # O rendimento e o custo (VEI-05) vão para o financeiro, não para a vendedora.
    assert "indicadores_financeiros" in moto.api("Lúcia").get(_url(sak)).json()
    assert "indicadores_financeiros" not in moto.api("Bruna").get(_url(sak)).json()


def test_usr_09_vendedor_e_financeiro_nao_escrevem_no_veiculo(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    antes = (sak.status, sak.cor, sak.km_atual)
    novo = {
        "placa": "QAB1C23",
        "chassi": "9C2JC4820TR000123",
        "marca": "Honda",
        "modelo": "Biz 125",
        "ano_fabricacao": 2026,
        "ano_modelo": 2026,
        "cor": "branca",
        "km_atual": 0,
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
    }
    for nome in LEEM:
        api = moto.api(nome)
        assert api.post("/api/veiculos/", novo, format="json").status_code == 403, nome
        assert api.patch(_url(sak), {"cor": "preta"}, format="json").status_code == 403, nome
        for acao, corpo in (
            ("bloquear", {"motivo": "Teste"}),
            ("colocar-a-venda", {}),
            ("km", {"km": sak.km_atual + 10}),
            ("baixar", {"motivo": "Teste"}),
        ):
            resposta = api.post(_url(sak, acao), corpo, format="json")
            assert resposta.status_code == 403, (nome, acao, resposta.status_code)
    sak.refresh_from_db()
    assert (sak.status, sak.cor, sak.km_atual) == antes
