"""T-275: os blocos da ficha do veículo que a API não mandava ("Blocos da ficha", veiculos.md).

O plano e o pagamento da locação atual (LOC-01, FIN-01, FIN-03, T-293), a vistoria recente
(VIS-01, AUD-05) e o botão Movimentar (MOV-02, MOV-03), no caso do QXA-4B21 em 07 out.
"""

from typing import Any

import pytest

from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo
from apps.vistorias import leituras as vistorias_leituras
from apps.vistorias.models import Avaria, FotoVistoria, Vistoria
from comum.estados import transicionar

from . import carteira
from .test_t015_locacoes import Cenario
from .test_t016_vistorias import (  # noqa: F401 - fixtures
    POSICOES,
    _carlos_na_devolucao,
    _contrato_com_juros,
    _ir_para,
    _parcela,
    cenario,
    da_carteira,
)

LISTA = "/api/veiculos/"


@pytest.fixture
def carlos(cenario, da_carteira, relogio) -> Locacao:  # noqa: F811
    """LOC-2841 em 07 out ao meio-dia: parcela 2 (29940) venceu em 30 set, a 3 vence hoje."""
    vistorias_leituras.registrar()
    locacao = _carlos_na_devolucao(da_carteira)
    _contrato_com_juros(locacao)
    _ir_para(cenario, relogio, "2026-10-07 12:00")
    return locacao


def _ficha(cenario: Cenario, veiculo_id: int, quem: str = "Rodrigo") -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(f"{LISTA}{veiculo_id}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _disponivel() -> Veiculo:
    veiculo: Veiculo = Veiculo.objects.filter(status="disponivel").order_by("id")[0]
    return veiculo


def test_vei_ficha_pagamento_da_locacao(cenario, carlos):  # noqa: F811
    """'Parcela 2 atrasada' pelo valor do dia: 29940 + 599 de multa + 70 de juros (T-293)."""
    atual = _ficha(cenario, carlos.veiculo_id)["locacao_atual"]
    assert atual["codigo"] == "LOC-2841"
    assert atual["plano"] == {
        "periodicidade": "semanal",
        "plano_especial": None,
        "valor_periodo_centavos": carlos.valor_periodo_centavos,
    }
    assert atual["pagamento"] == {
        "situacao": "atrasado",
        "rotulo": "Parcela 2 atrasada",
        "conta_id": _parcela(carlos, 2).pk,
        "valor_centavos": 30609,
        "atrasadas": 1,
        "cobrar": True,
    }
    assert _ficha(cenario, carlos.veiculo_id, "Bruna")["locacao_atual"]["pagamento"]["cobrar"]

    # O vistoriador vê o plano sem o valor e não recebe o pagamento (USR-09).
    do_joao = _ficha(cenario, carlos.veiculo_id, "João")["locacao_atual"]
    assert "pagamento" not in do_joao
    assert do_joao["plano"] == {"periodicidade": "semanal", "plano_especial": None}

    # Paga a 2, sobra a que vence hoje, pelo principal.
    paga = _parcela(carlos, 2)
    paga.forma = "pix"
    transicionar(paga, "paga", mais_campos=("forma",))
    pagamento = _ficha(cenario, carlos.veiculo_id)["locacao_atual"]["pagamento"]
    assert (pagamento["situacao"], pagamento["rotulo"], pagamento["valor_centavos"]) == (
        "vence_hoje",
        "Parcela 3 vence hoje",
        29940,
    )
    assert pagamento["conta_id"] == _parcela(carlos, 3).pk


def _avaria_anterior(cenario: Cenario, veiculo: Veiculo, descricao: str) -> Avaria:  # noqa: F811
    """Aberta desde a chegada de uma locação de julho do mesmo veículo (a LOC-2700)."""
    anterior = Locacao.objects.create(
        numero=2700,
        codigo="LOC-2700",
        filial=cenario.frota.centro,
        cliente=cenario.cliente("Carlos"),
        veiculo=veiculo,
        vendedor=cenario.pessoas["Bruna"],
        periodicidade="semanal",
        inicio=carteira.momento("2026-07-05 09:00"),
        fim_previsto=carteira.momento("2026-07-12 09:00"),
        forma_pagamento="pix",
        status="encerrada",
    )
    chegada = Vistoria.objects.create(
        locacao=anterior,
        veiculo=veiculo,
        tipo="devolucao",
        status="concluida",
        km=3000,
        concluida_em=carteira.momento("2026-07-12 11:00"),
    )
    foto = _foto(chegada, "avaria")
    return Avaria.objects.create(vistoria=chegada, veiculo=veiculo, descricao=descricao, foto=foto)


def _foto(vistoria: Vistoria, posicao: str) -> FotoVistoria:
    return FotoVistoria.objects.create(
        vistoria=vistoria,
        posicao=posicao,
        arquivo=f"vistorias/{vistoria.pk}/{posicao}.jpg",
        tirada_em=carteira.momento("2026-09-23 09:00"),
    )


def test_vei_ficha_vistoria_recente(cenario, carlos):  # noqa: F811
    """A saída da LOC-2841: as 5 fotos fixas na ordem, a avaria de antes e a da saída."""
    veiculo = Veiculo.objects.get(pk=carlos.veiculo_id)
    antiga = _avaria_anterior(cenario, veiculo, "Risco no tanque, lado esquerdo")
    saida = Vistoria.objects.get(locacao=carlos, tipo="saida")
    saida.responsavel = cenario.pessoas["João"]
    saida.save(update_fields=["responsavel"])
    for posicao in reversed(POSICOES):
        _foto(saida, posicao)
    foto_avaria = _foto(saida, "avaria")
    da_saida = Avaria.objects.create(
        vistoria=saida,
        veiculo=veiculo,
        descricao="Retrovisor direito trincado",
        preexistente=True,
        foto=foto_avaria,
    )

    recente = _ficha(cenario, veiculo.pk)["vistoria_recente"]
    assert (recente["id"], recente["tipo"], recente["locacao_codigo"]) == (
        saida.pk,
        "saida",
        "LOC-2841",
    )
    joao = cenario.pessoas["João"]
    assert recente["vistoriador"] == {"id": joao.pk, "nome": joao.nome}
    assert recente["total_fotos"] == 6
    assert [f["posicao"] for f in recente["fotos"]] == list(POSICOES)
    assert all(f["url"] and f["url_expira_em"] for f in recente["fotos"])
    assert recente["avarias"] == [
        {
            "id": antiga.pk,
            "descricao": "Risco no tanque, lado esquerdo",
            "registrada_em": "2026-07-12T14:00:00Z",
            "preexistente": False,
            "locacao_codigo": "LOC-2700",
            "foto_id": antiga.foto_id,
        },
        {
            "id": da_saida.pk,
            "descricao": "Retrovisor direito trincado",
            "registrada_em": "2026-09-23T12:00:00Z",
            "preexistente": True,
            "locacao_codigo": "LOC-2841",
            "foto_id": foto_avaria.pk,
        },
    ]
    # O vistoriador vê; sem valor em dinheiro em lugar nenhum do bloco.
    assert _ficha(cenario, veiculo.pk, "João")["vistoria_recente"]["id"] == saida.pk
    # O financeiro não faz vistoria: a chave vem ausente.
    assert "vistoria_recente" not in _ficha(cenario, veiculo.pk, "Lúcia")
    # Veículo que nunca teve vistoria: null.
    assert _ficha(cenario, _disponivel().pk)["vistoria_recente"] is None


def test_mov_03_acao_movimentar(cenario, carlos):  # noqa: F811
    """Alugado: o botão desativado com o motivo; disponível: ativo; vendedor: sem botão."""
    acoes = _ficha(cenario, carlos.veiculo_id)["acoes"]
    assert acoes["movimentar"] is False
    assert acoes["motivo_movimentar"] == (
        "Veículo alugado não se movimenta. O botão volta quando a LOC-2841 for devolvida."
    )
    livre = _disponivel()
    acoes = _ficha(cenario, livre.pk)["acoes"]
    assert (acoes["movimentar"], acoes["motivo_movimentar"]) == (True, None)
    acoes = _ficha(cenario, livre.pk, "Bruna")["acoes"]
    assert (acoes["movimentar"], acoes["motivo_movimentar"]) == (False, None)
