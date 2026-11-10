"""T-438 · Tipo do veículo (moto ou carro) no cadastro e no editar (VEI-11, LOC-15, AUD-01).

Critérios em docs/qa/criterios/T-438.md (CA-438-01 a 14); contrato em docs/api/veiculos.md,
"PATCH /api/veiculos/{id}/". O tipo é o da categoria: o `PATCH` recebe só `categoria_id`, e a
troca de tipo com locação aberta é recusada com 409 `tipo_com_locacao_aberta`. Os casos com
locação usam o cenário da T-015 (a próxima locação é a LOC-2856, no SAK-1D39).
"""

from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo

from .frota import Frota, montar_frota
from .test_t012_filiais import MotoRapida
from .test_t015_locacoes import (  # noqa: F401
    Cenario,
    _assinar,
    _pagar,
    _vistoriar,
    cenario,
)

VEICULOS = "/api/veiculos/"
SEM_EDITAR = ("Bruna", "João", "Lúcia")  # vendedor, vistoriador e financeiro


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _patch(moto: MotoRapida, veiculo: Veiculo, corpo: dict[str, Any], quem: str = "Rodrigo"):
    return moto.api(quem).patch(f"{VEICULOS}{veiculo.pk}/", corpo, format="json")


def _ficha(moto: MotoRapida, veiculo: Veiculo, quem: str = "Rodrigo") -> dict[str, Any]:
    resposta = moto.api(quem).get(f"{VEICULOS}{veiculo.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _placas_do_tipo(moto: MotoRapida, tipo: str) -> set[str]:
    resposta = moto.api("Rodrigo").get(VEICULOS, {"tipo_veiculo": tipo, "por_pagina": 100})
    assert resposta.status_code == 200, resposta.json()
    return {linha["placa"] for linha in resposta.json()["resultados"]}


def _categoria(veiculo: Veiculo) -> str:
    return Veiculo.objects.select_related("categoria").get(pk=veiculo.pk).categoria.nome


def _ativa(cenario: Cenario) -> dict[str, Any]:  # noqa: F811
    """A LOC-2856 no SAK-1D39, ativa: o veículo fica `alugado`."""
    criada = cenario.confirmada()
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "alugado"
    return criada


# --- Pela API, o tipo vem da categoria (CA-438-04, 07, 11) ---


def test_vei_11_pela_api_o_tipo_vem_da_categoria(moto, frota) -> None:
    """CA-438-04 e 07: o SAK-1D39 `disponivel` vai da Street para o Carro compacto; a resposta
    traz `tipo_veiculo: "carro"`, a Frota o filtra como carro, e o preço é o do Carro compacto."""
    sak = frota.veiculos["SAK1D39"]
    assert _ficha(moto, sak)["acoes"]["motivo_trocar_tipo"] is None
    resposta = _patch(moto, sak, {"categoria_id": frota.categorias["Carro compacto"].pk})
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["tipo_veiculo"] == "carro"
    assert corpo["categoria"]["nome"] == "Carro compacto"
    assert corpo["preco_vigente"]["diaria_centavos"] == 10900
    assert corpo["preco_vigente"]["caucao_centavos"] == 80000
    assert "SAK1D39" in _placas_do_tipo(moto, "carro")
    assert "SAK1D39" not in _placas_do_tipo(moto, "moto")


def test_vei_11_tipo_no_corpo_nao_muda_nada(moto, frota) -> None:
    """CA-438-07: o `tipo_veiculo` mandado no corpo, sem a categoria, não muda o veículo."""
    sak = frota.veiculos["SAK1D39"]
    resposta = _patch(moto, sak, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["tipo_veiculo"] == "moto"
    assert _categoria(sak) == "Street 150–160"


def test_vei_11_livre_fora_da_locacao(moto, frota) -> None:
    """CA-438-11: o PMZ-3E17 `em_manutencao` (Urbana) vai para o Carro compacto."""
    pmz = frota.veiculos["PMZ3E17"]
    assert _ficha(moto, pmz)["acoes"]["motivo_trocar_tipo"] is None
    resposta = _patch(moto, pmz, {"categoria_id": frota.categorias["Carro compacto"].pk})
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["tipo_veiculo"] == "carro"


# --- Recusa com locação aberta (CA-438-08, 09, 10) ---


def test_vei_11_recusa_com_locacao_ativa(cenario) -> None:  # noqa: F811
    """CA-438-08: com a LOC-2856 ativa, o tipo vem travado com a frase, e a troca para carro
    responde 409 `tipo_com_locacao_aberta`; o veículo continua na Street."""
    _ativa(cenario)
    frase = "Este veículo está na LOC-2856. Troque o tipo depois da devolução."
    assert _ficha(cenario.moto, cenario.sak)["acoes"]["motivo_trocar_tipo"] == frase
    resposta = _patch(
        cenario.moto, cenario.sak, {"categoria_id": cenario.frota.categorias["Carro compacto"].pk}
    )
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"
    assert resposta.json()["mensagem"] == frase
    assert _categoria(cenario.sak) == "Street 150–160"
    assert not EventoAuditoria.objects.filter(
        acao="veiculo.editar", objeto_id=cenario.sak.pk
    ).exists()


def test_vei_11_recusa_com_reserva(cenario) -> None:  # noqa: F811
    """CA-438-09: o veículo `reservado` pela locação confirmada recusa a troca de tipo, com o
    código da locação que o reservou."""
    criada = cenario.confirmada()
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "reservado"
    resposta = _patch(
        cenario.moto, cenario.sak, {"categoria_id": cenario.frota.categorias["Carro compacto"].pk}
    )
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"
    assert resposta.json()["mensagem"] == (
        f"Este veículo está na {criada['codigo']}. Troque o tipo depois da devolução."
    )


def test_vei_11_mesmo_tipo_continua_livre_com_locacao_aberta(cenario) -> None:  # noqa: F811
    """CA-438-10: alugado, a Street vira Urbana (mesmo tipo): 200, e a locação aberta mantém o
    semanal que já tinha (LOC-15)."""
    criada = _ativa(cenario)
    semanal = Locacao.objects.get(pk=criada["id"]).valor_periodo_centavos
    resposta = _patch(
        cenario.moto, cenario.sak, {"categoria_id": cenario.frota.categorias["Urbana 110–125"].pk}
    )
    assert resposta.status_code == 200, resposta.json()
    assert _categoria(cenario.sak) == "Urbana 110–125"
    assert Locacao.objects.get(pk=criada["id"]).valor_periodo_centavos == semanal


def test_vei_11_alugado_sem_a_locacao_tambem_recusa(moto, frota) -> None:
    """Dado antigo: o QXA-4B21 `alugado` sem a locação gravada também não troca de tipo."""
    qxa = frota.veiculos["QXA4B21"]
    frase = "Este veículo está numa locação aberta. Troque o tipo depois da devolução."
    assert _ficha(moto, qxa)["acoes"]["motivo_trocar_tipo"] == frase
    resposta = _patch(moto, qxa, {"categoria_id": frota.categorias["Carro compacto"].pk})
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"


# --- Quem troca e auditoria (CA-438-13, 14) ---


def test_vei_11_quem_troca(moto, frota) -> None:
    """CA-438-13: vendedor, vistoriador e financeiro não editam (403), e não recebem o motivo."""
    sak = frota.veiculos["SAK1D39"]
    for pessoa in SEM_EDITAR:
        resposta = _patch(moto, sak, {"categoria_id": frota.categorias["Carro compacto"].pk}, pessoa)
        assert resposta.status_code == 403, pessoa
        assert resposta.json()["codigo"] == "permissao"
    qxa = frota.veiculos["QXA4B21"]
    for pessoa in SEM_EDITAR:
        assert _ficha(moto, qxa, pessoa)["acoes"]["motivo_trocar_tipo"] is None, pessoa
    assert _categoria(sak) == "Street 150–160"


def test_vei_11_auditoria(moto, frota) -> None:
    """CA-438-14: o `veiculo.editar` do Rodrigo leva a categoria e o tipo de antes e depois."""
    sak = frota.veiculos["SAK1D39"]
    street, carro = frota.categorias["Street 150–160"], frota.categorias["Carro compacto"]
    assert _patch(moto, sak, {"categoria_id": carro.pk}).status_code == 200
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=sak.pk).latest("id")
    assert evento.antes == {
        "categoria_id": street.pk,
        "categoria_nome": "Street 150–160",
        "tipo_veiculo": "moto",
    }
    assert evento.depois == {
        "categoria_id": carro.pk,
        "categoria_nome": "Carro compacto",
        "tipo_veiculo": "carro",
    }
    # Mesmo tipo: a categoria muda, o tipo não entra.
    urbana = frota.categorias["Urbana 110–125"]
    pmz = frota.veiculos["PMZ3E17"]
    street_pk = frota.categorias["Street 150–160"].pk
    assert _patch(moto, pmz, {"categoria_id": street_pk}).status_code == 200
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=pmz.pk).latest("id")
    assert evento.antes == {"categoria_id": urbana.pk, "categoria_nome": "Urbana 110–125"}
