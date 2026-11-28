"""T-438 · Tipo do veículo (moto ou carro) no cadastro e no editar (VEI-11, LOC-15, AUD-01).

Critérios em docs/qa/criterios/T-438.md (CA-438-01 a 14); contrato em docs/api/veiculos.md,
"PATCH /api/veiculos/{id}/". Desde a T-522 (ADR 0043) o tipo é do próprio veículo: o `PATCH`
recebe `tipo_veiculo`, e a troca com locação aberta é recusada com 409 `tipo_com_locacao_aberta`.
Os casos com locação usam o cenário da T-015 (a próxima locação é a LOC-2856, no SAK-1D39).
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
    resposta = moto.api("Rodrigo").get(VEICULOS, {"tipo_veiculo": tipo, "tamanho": 100})
    assert resposta.status_code == 200, resposta.json()
    return {linha["placa"] for linha in resposta.json()["resultados"]}


def _tipo(veiculo: Veiculo) -> str:
    return str(Veiculo.objects.get(pk=veiculo.pk).tipo_veiculo)


def _ativa(cenario: Cenario) -> dict[str, Any]:  # noqa: F811
    """A LOC-2856 no SAK-1D39, ativa: o veículo fica `alugado`."""
    criada = cenario.confirmada()
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "alugado"
    return criada


# --- O tipo é do veículo (CA-438-04, 07, 11; ADR 0043) ---


def test_vei_11_pela_api_o_tipo_e_do_veiculo(moto, frota) -> None:
    """CA-438-04 e 07: o SAK-1D39 `disponivel` passa a carro pelo `tipo_veiculo`; a resposta
    traz `tipo_veiculo: "carro"`, sem categoria, a Frota o filtra como carro, e os planos dele
    continuam os mesmos (o preço é do veículo)."""
    sak = frota.veiculos["SAK1D39"]
    planos = sorted(sak.planos.values_list("tipo", "valor_centavos"))
    assert _ficha(moto, sak)["acoes"]["motivo_trocar_tipo"] is None
    resposta = _patch(moto, sak, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["tipo_veiculo"] == "carro"
    assert "categoria" not in corpo
    assert sorted(sak.planos.values_list("tipo", "valor_centavos")) == planos
    assert "SAK1D39" in _placas_do_tipo(moto, "carro")
    assert "SAK1D39" not in _placas_do_tipo(moto, "moto")


def test_vei_11_tipo_invalido_400(moto, frota) -> None:
    """ADR 0043: outro valor no `tipo_veiculo` é 400 com a frase da regra; nada muda."""
    sak = frota.veiculos["SAK1D39"]
    resposta = _patch(moto, sak, {"tipo_veiculo": "caminhao"})
    assert resposta.status_code == 400, resposta.json()
    assert resposta.json()["campos"]["tipo_veiculo"] == ["Escolha moto ou carro."]
    assert _tipo(sak) == "moto"


def test_vei_11_categoria_id_no_corpo_e_ignorada(moto, frota) -> None:
    """ADR 0043: `categoria_id` saiu do contrato; mandado no `PATCH`, não muda nada."""
    sak = frota.veiculos["SAK1D39"]
    resposta = _patch(moto, sak, {"categoria_id": 999})
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["tipo_veiculo"] == "moto"
    assert Veiculo.objects.get(pk=sak.pk).categoria_id is None


def test_vei_11_livre_fora_da_locacao(moto, frota) -> None:
    """CA-438-11: o PMZ-3E17 `em_manutencao` vira carro."""
    pmz = frota.veiculos["PMZ3E17"]
    assert _ficha(moto, pmz)["acoes"]["motivo_trocar_tipo"] is None
    resposta = _patch(moto, pmz, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["tipo_veiculo"] == "carro"


# --- Recusa com locação aberta (CA-438-08, 09, 10) ---


def test_vei_11_trocar_tipo_com_locacao_aberta_409(cenario) -> None:  # noqa: F811
    """CA-438-08: com a LOC-2856 ativa, o tipo vem travado com a frase, e a troca para carro
    responde 409 `tipo_com_locacao_aberta`; o veículo continua moto."""
    _ativa(cenario)
    frase = "Este veículo está na LOC-2856. Troque o tipo depois da devolução."
    assert _ficha(cenario.moto, cenario.sak)["acoes"]["motivo_trocar_tipo"] == frase
    resposta = _patch(cenario.moto, cenario.sak, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"
    assert resposta.json()["mensagem"] == frase
    assert _tipo(cenario.sak) == "moto"
    assert not EventoAuditoria.objects.filter(
        acao="veiculo.editar", objeto_id=cenario.sak.pk
    ).exists()


def test_vei_11_recusa_com_reserva(cenario) -> None:  # noqa: F811
    """CA-438-09: o veículo `reservado` pela locação confirmada recusa a troca de tipo, com o
    código da locação que o reservou."""
    criada = cenario.confirmada()
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "reservado"
    resposta = _patch(cenario.moto, cenario.sak, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"
    assert resposta.json()["mensagem"] == (
        f"Este veículo está na {criada['codigo']}. Troque o tipo depois da devolução."
    )


def test_vei_11_mesmo_tipo_continua_livre_com_locacao_aberta(cenario) -> None:  # noqa: F811
    """CA-438-10: alugado, mandar o mesmo tipo (moto) não é troca: 200, e a locação aberta mantém
    o semanal que já tinha (LOC-15)."""
    criada = _ativa(cenario)
    semanal = Locacao.objects.get(pk=criada["id"]).valor_periodo_centavos
    resposta = _patch(cenario.moto, cenario.sak, {"tipo_veiculo": "moto", "cor": "preta"})
    assert resposta.status_code == 200, resposta.json()
    assert _tipo(cenario.sak) == "moto"
    assert Locacao.objects.get(pk=criada["id"]).valor_periodo_centavos == semanal


def test_vei_11_alugado_sem_a_locacao_tambem_recusa(moto, frota) -> None:
    """Dado antigo: o QXA-4B21 `alugado` sem a locação gravada também não troca de tipo."""
    qxa = frota.veiculos["QXA4B21"]
    frase = "Este veículo está numa locação aberta. Troque o tipo depois da devolução."
    assert _ficha(moto, qxa)["acoes"]["motivo_trocar_tipo"] == frase
    resposta = _patch(moto, qxa, {"tipo_veiculo": "carro"})
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "tipo_com_locacao_aberta"


# --- Quem troca e auditoria (CA-438-13, 14) ---


def test_vei_11_quem_troca(moto, frota) -> None:
    """CA-438-13: vendedor, vistoriador e financeiro não editam (403), e não recebem o motivo."""
    sak = frota.veiculos["SAK1D39"]
    for pessoa in SEM_EDITAR:
        resposta = _patch(moto, sak, {"tipo_veiculo": "carro"}, pessoa)
        assert resposta.status_code == 403, pessoa
        assert resposta.json()["codigo"] == "permissao"
    qxa = frota.veiculos["QXA4B21"]
    for pessoa in SEM_EDITAR:
        assert _ficha(moto, qxa, pessoa)["acoes"]["motivo_trocar_tipo"] is None, pessoa
    assert _tipo(sak) == "moto"


def test_vei_11_auditoria(moto, frota) -> None:
    """CA-438-14: o `veiculo.editar` do Rodrigo leva o tipo de antes e depois, sem categoria."""
    sak = frota.veiculos["SAK1D39"]
    assert _patch(moto, sak, {"tipo_veiculo": "carro"}).status_code == 200
    evento = EventoAuditoria.objects.filter(acao="veiculo.editar", objeto_id=sak.pk).latest("id")
    assert evento.antes == {"tipo_veiculo": "moto"}
    assert evento.depois == {"tipo_veiculo": "carro"}
