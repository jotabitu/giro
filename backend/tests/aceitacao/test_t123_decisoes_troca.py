"""T-123 · Decisões da troca de veículo (LOC-08, LOC-09, LOC-12, DEV-01, DEV-02; T-121, T-122).

O preço da nova categoria guardado no pedido, a parcela refeita inteira, a diferença do período
em curso no acerto (crédito na categoria mais barata), o cancelamento da troca pendente com cada
peça e o 409 `troca_pendente` no cancelamento da locação. O caso novo é "Troca de veículo
LOC-2836" (regras, "Dados de referência para testes"): devolver R$ 263,00.

Cenário da T-016: Moto Rápida em 07 out 2026, 10:00, Filial Centro, litro a R$ 5,50, com a
LOC-2836 da carteira de 30 set 18:00 a 14 out 18:00 (Factor 150, PNB7C04, 16 L).
"""

from datetime import date
from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.financeiro import services as financeiro_services
from apps.financeiro.models import ContaReceber, Reembolso
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao, TrocaVeiculo
from apps.veiculos.models import PrecoCategoria, Veiculo
from apps.vistorias.models import Devolucao, Vistoria
from comum import relogio as relogio_do_giro

from . import carteira
from .frota import montar_frota
from .test_t012_filiais import MotoRapida
from .test_t015_locacoes import LISTA, Cenario, _assinar, _pagar, _parcelas, _plano, _vistoriar
from .test_t016_vistorias import (
    VISTORIAS,
    _abrir_devolucao,
    _caucao_da_troca,
    _caucao_paga,
    _chegada,
    _completar,
    _encerrar,
    _forma,
    _ir_para,
    _item,
    _nmax,
    _patch,
    _saida_direta,
    _troca_pedida,
    _valor_do_item,
    _ver,
)
from .test_t016_vistorias import (
    _vistoriar as _vistoriar_pela_api,
)

STREET = "Street 150–160"
SCOOTER = "Scooter premium"


@pytest.fixture
def cenario(empresa_a, planos, relogio) -> Cenario:
    """O cenário da T-016 (`test_t016_vistorias.py`), com o litro a R$ 5,50 na Filial Centro."""
    locacoes_leituras.registrar()
    moto = MotoRapida(empresa_a, planos["Profissional"])
    frota = montar_frota(moto)
    frota.centro.preco_litro_centavos = 550
    frota.centro.save(update_fields=["preco_litro_centavos"])
    return Cenario(moto, frota)


@pytest.fixture
def juliana(cenario, relogio) -> Locacao:
    """A LOC-2836 da carteira, de 30 set 18:00 a 14 out 18:00, com a saída da Factor (18.402 km,
    tanque cheio), como na T-016."""
    locacao = carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)["LOC-2836"]
    Locacao.objects.filter(pk=locacao.pk).update(fim_previsto=carteira.momento("2026-10-14 18:00"))
    Veiculo.objects.filter(pk=locacao.veiculo_id).update(km_atual=18402)
    _saida_direta(locacao, 18402, "cheio", "2026-10-01 09:10")
    locacao.refresh_from_db()
    return locacao


def _cancelar_troca(cenario: Cenario, locacao_id: int, quem: str = "Bruna", **corpo: Any) -> Any:
    return cenario.moto.api(quem).post(
        f"{LISTA}{locacao_id}/trocar-veiculo/cancelar/",
        corpo if corpo else {"motivo": "Cliente desistiu da scooter"},
        format="json",
    )


def _renovar(cenario: Cenario, locacao: Locacao) -> None:
    resposta = cenario.moto.api("Bruna").post(
        f"{LISTA}{locacao.pk}/renovar/", {"periodos": 1}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()


def _parcela(locacao: Locacao, numero: int) -> ContaReceber:
    return ContaReceber.objects.get(
        origem_tipo="locacao", origem_id=locacao.pk, tipo="parcela", numero_parcela=numero
    )


def _troca(locacao: Locacao) -> TrocaVeiculo:
    return TrocaVeiculo.objects.filter(locacao=locacao).latest("id")


def _juliana_pede_a_nmax(cenario: Cenario, juliana: Locacao, relogio: Any) -> dict[str, Any]:
    """Caso "Troca de veículo LOC-2836": em 07 out, renova por 1 semana (parcela 3 de 32900
    vencendo em 14 out, fim 21 out 18:00) e pede a troca pela NMax às 18:00."""
    _completar(juliana.cliente)
    _renovar(cenario, juliana)
    _ir_para(cenario, relogio, "2026-10-07 18:00")
    return _troca_pedida(cenario, juliana.pk, _nmax(cenario))


# --- Caso "Troca de veículo LOC-2836" (LOC-09, LOC-08, DEV-01, DEV-02) ---


def test_loc_09_troca_de_veiculo_loc_2836(cenario, juliana, relogio):
    troca = _juliana_pede_a_nmax(cenario, juliana, relogio)
    nmax = _troca(juliana).veiculo_novo
    assert _parcelas(juliana.pk)[-1] == (date(2026, 10, 14), 32900)
    # A Factor volta com o retrovisor quebrado (sem oficina) e 3/4 do tanque.
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    resposta = _vistoriar_pela_api(
        cenario, troca["devolucao_vistoria_id"], 18900, "tres_quartos", avarias=("Retrovisor",)
    )
    assert resposta.status_code == 200, resposta.json()
    retrovisor = _item(_ver(cenario, devolucao["id"]), "avaria")
    assert _valor_do_item(cenario, devolucao["id"], retrovisor["id"], 8500).status_code == 200
    financeiro_services.marcar_paga(_caucao_da_troca(juliana), forma="pix")
    resposta = _vistoriar_pela_api(cenario, troca["saida_vistoria_id"], nmax.km_atual)
    assert resposta.status_code == 200, resposta.json()

    # Na troca: parcela 3 refeita, caução total 50000, diária do atraso 7990.
    juliana.refresh_from_db()
    assert (juliana.veiculo_id, juliana.caucao_centavos, juliana.diaria_centavos) == (
        nmax.pk,
        50000,
        7990,
    )
    assert _parcelas(juliana.pk)[-1] == (date(2026, 10, 14), 44900)
    assert Veiculo.objects.get(placa="PNB7C04").status == "disponivel"
    assert Veiculo.objects.get(pk=nmax.pk).status == "alugado"
    guardada = _troca(juliana)
    assert (guardada.periodo_inicio, guardada.periodo_fim) == (
        date(2026, 10, 7),
        date(2026, 10, 14),
    )
    assert (guardada.dias_do_periodo, guardada.dias_restantes) == (7, 7)
    assert (guardada.periodo_antigo_centavos, guardada.periodo_novo_centavos) == (32900, 44900)
    assert (guardada.ja_refeito_centavos, guardada.diferenca_centavos) == (0, 12000)

    # A parcela 3 é paga em 14 out; a NMax volta em 21 out 18:00, cheia e sem avaria.
    _ir_para(cenario, relogio, "2026-10-14 10:00")
    financeiro_services.marcar_paga(_parcela(juliana, 3), forma="pix")
    _ir_para(cenario, relogio, "2026-10-21 18:00")
    corpo = _abrir_devolucao(cenario, juliana.pk)
    assert corpo["vistoria"]["veiculo"]["id"] == nmax.pk
    corpo = _chegada(cenario, corpo, nmax.km_atual + 400)
    acerto = corpo["acerto"]
    assert sorted((i["tipo"], i["valor_centavos"]) for i in acerto["itens"]) == [
        ("atraso", 0),
        ("avaria", 8500),
        ("combustivel", 0),  # a NMax voltou cheia
        ("combustivel", 3200),  # a Factor: 4 L × R$ 5,50 + R$ 10,00
        ("diferenca_troca", 12000),
        ("km_excedente", 0),
    ]
    diferenca = _item(corpo, "diferenca_troca")
    assert diferenca["descricao"] == (
        "Diferença do período de 07/10 a 14/10 na troca pela Yamaha NMax 160 "
        f"{nmax.placa} ((R$ 449,00 − R$ 329,00) ÷ 7 × 7 dias)"
    )
    assert diferenca["modo"] == "calculado"
    assert acerto["creditos"] == []
    assert (acerto["total_cobrancas_centavos"], acerto["caucao_centavos"]) == (23700, 50000)
    assert acerto["resultado"]["tipo"] == "devolver"
    assert acerto["resultado"]["valor_centavos"] == 26300
    # O item calculado não se edita (409 `item_calculado`).
    resposta = _valor_do_item(cenario, corpo["id"], diferenca["id"], 0)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "item_calculado")

    assert _forma(cenario, corpo["id"]).status_code == 200
    resposta = _encerrar(cenario, corpo["id"])
    assert resposta.status_code == 200, resposta.json()
    juliana.refresh_from_db()
    assert juliana.status == "encerrada"
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=corpo["id"])
    assert (reembolso.valor_centavos, reembolso.forma) == (26300, "pix")


def test_loc_09_preco_guardado_no_pedido(cenario, juliana, relogio):
    """A tabela da Scooter premium muda entre o pedido (07 out) e a conclusão (08 out): vale a
    do pedido na caução, nas parcelas, na diária e na diferença (LOC-09, LOC-15)."""
    _completar(juliana.cliente)
    _renovar(cenario, juliana)
    nmax = _nmax(cenario)
    troca = locacoes_services.pedir_troca(juliana, nmax.pk, "Barulho no motor", None)
    assert (troca.valor_periodo_centavos, troca.diaria_centavos, troca.caucao_centavos) == (
        44900,
        7990,
        50000,
    )
    assert troca.preco_do_dia == date(2026, 10, 7)
    assert _caucao_da_troca(juliana).valor_centavos == 20000
    PrecoCategoria.objects.create(
        categoria=cenario.frota.categorias[SCOOTER],
        vigente_desde=date(2026, 10, 8),
        diaria_centavos=8990,
        semanal_centavos=49900,
        mensal_centavos=179000,
        caucao_centavos=60000,
    )

    _ir_para(cenario, relogio, "2026-10-08 10:00")
    locacoes_services.concluir_troca(troca, km_saida=nmax.km_atual, momento=relogio_do_giro.agora())
    juliana.refresh_from_db()
    assert (juliana.valor_periodo_centavos, juliana.diaria_centavos) == (44900, 7990)
    assert juliana.caucao_centavos == 50000
    assert _parcelas(juliana.pk)[-1] == (date(2026, 10, 14), 44900)
    troca.refresh_from_db()
    # Em 08 out faltam 6 dos 7 dias do período: 12000 × 6 ÷ 7 = 10285,71 → 10286.
    assert (troca.dias_do_periodo, troca.dias_restantes) == (7, 6)
    assert troca.diferenca_centavos == 10286


# --- Parcela refeita inteira (LOC-09, como na renovação, LOC-08) ---


def _mensal_ativa(cenario: Cenario, **campos: Any) -> Locacao:
    """Lucas, Street mensal (119000), retirada em 07 out 09:00."""
    criada = cenario.confirmada(
        inicio=carteira.momento("2026-10-07 09:00").isoformat(),
        periodicidade="mensal",
        **campos,
    )
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    locacao = Locacao.objects.get(pk=criada["id"])
    assert locacao.status == "ativa"
    return locacao


def _troca_concluida(cenario: Cenario, locacao: Locacao, relogio: Any, quando: str) -> TrocaVeiculo:
    nmax = cenario.veiculo(SCOOTER)
    troca = locacoes_services.pedir_troca(locacao, nmax.pk, "Cliente pediu scooter", None)
    _ir_para(cenario, relogio, quando)
    momento = relogio_do_giro.agora()
    concluida = locacoes_services.concluir_troca(troca, km_saida=nmax.km_atual, momento=momento)
    concluida.refresh_from_db()
    return concluida


def test_loc_09_parcela_refeita_mensal_fidelidade_3o_mes(cenario, relogio):
    fidelidade = _plano(
        cenario,
        nome="Mensal fidelidade",
        periodicidade="mensal",
        regra="desconto",
        desconto_pct="10.00",
        a_partir_do_periodo=3,
    )
    locacao = _mensal_ativa(
        cenario, periodos=4, plano_especial_id=fidelidade["id"], parcelamento_mensal="a_vista"
    )
    assert [v for _, v in _parcelas(locacao.pk)] == [119000, 119000, 107100, 107100]

    troca = _troca_concluida(cenario, locacao, relogio, "2026-10-08 10:00")
    # Street → Scooter premium: o 2º mês sem desconto (159000); do 3º em diante, 1.590,00 −
    # 10% = 143100 (antes, 1.190,00 − 10% = 107100). A paga não muda.
    assert [v for _, v in _parcelas(locacao.pk)] == [119000, 159000, 143100, 143100]
    # O período em curso é o 1º mês (07 out a 07 nov, 31 dias), sem desconto: faltam 30.
    assert (troca.periodo_antigo_centavos, troca.periodo_novo_centavos) == (119000, 159000)
    assert (troca.dias_do_periodo, troca.dias_restantes) == (31, 30)
    assert troca.diferenca_centavos == 38710  # 40000 × 30 ÷ 31 = 38709,68


def test_loc_09_diferenca_mensal_4_semanais_desconta_parcelas_refeitas(cenario, relogio):
    """T-122 (`[decisão]` confirmada pelo dono): no mensal em 4 semanais, as parcelas do mês
    que vencem depois do dia da troca já sobem pelo preço novo e não entram de novo."""
    locacao = _mensal_ativa(cenario, periodos=1, parcelamento_mensal="quatro_semanais")
    assert [v for _, v in _parcelas(locacao.pk)] == [29750] * 4

    troca = _troca_concluida(cenario, locacao, relogio, "2026-10-08 10:00")
    assert [v for _, v in _parcelas(locacao.pk)] == [29750, 39750, 39750, 39750]
    # 40000 × 30 ÷ 31 = 38710, menos as 3 semanas refeitas (3 × 10000) = 8710.
    assert troca.ja_refeito_centavos == 30000
    assert troca.diferenca_centavos == 8710


# --- Cancelar a troca pendente (LOC-09, T-122) ---


def test_loc_09_cancelar_troca_chegada_rascunho(cenario, juliana, relogio):
    troca = _juliana_pede_a_nmax(cenario, juliana, relogio)
    factor = juliana.veiculo_id
    devolucao = Devolucao.objects.get(locacao=juliana)
    assert devolucao.vistoria_id == troca["devolucao_vistoria_id"]

    resposta = _cancelar_troca(cenario, juliana.pk)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()["troca"]
    assert corpo["status"] == "cancelada"
    assert corpo["saida_vistoria"] == {"id": troca["saida_vistoria_id"], "status": "descartada"}
    assert corpo["devolucao_vistoria"] == {
        "id": troca["devolucao_vistoria_id"],
        "status": "descartada",
    }
    assert corpo["devolucao_id"] is None
    # Os rascunhos ficam guardados, com o motivo; não se editam mais.
    saida = Vistoria.objects.get(pk=troca["saida_vistoria_id"])
    assert (saida.motivo_descarte, saida.descartada_em is not None) == (
        "Cliente desistiu da scooter",
        True,
    )
    resposta = _patch(cenario, saida.pk, km=1)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "vistoria_descartada")
    # O cliente segue com a Factor; a NMax volta a `disponivel`; a locação não muda.
    juliana.refresh_from_db()
    assert (juliana.veiculo_id, juliana.caucao_centavos, juliana.valor_periodo_centavos) == (
        factor,
        30000,
        32900,
    )
    assert Veiculo.objects.get(pk=factor).status == "alugado"
    assert Veiculo.objects.get(pk=_troca(juliana).veiculo_novo_id).status == "disponivel"
    assert juliana.trechos.count() == 1
    devolucao.refresh_from_db()
    assert devolucao.vistoria_id is None
    detalhe = cenario.detalhe(juliana.pk)
    assert (detalhe["troca"], detalhe["devolucao"]["devolucao_id"]) == (None, None)
    assert detalhe["acoes"]["cancelar_troca"] is False
    assert detalhe["acoes"]["trocar_veiculo"] is True
    acoes = {e.acao for e in EventoAuditoria.objects.filter(regra="LOC-09")}
    assert {"locacao.cancelar_troca", "vistoria.descartar"} <= acoes

    # A devolução sem chegada mostra o acerto sem vistoria; quando a Factor voltar, abre uma
    # chegada nova.
    sem_chegada = _ver(cenario, devolucao.pk)
    assert (sem_chegada["vistoria"], sem_chegada["comparacao"]) == (None, None)
    assert _encerrar(cenario, devolucao.pk).json()["codigo"] == "vistoria_pendente"
    nova = _abrir_devolucao(cenario, juliana.pk)
    assert nova["id"] == devolucao.pk
    assert nova["vistoria"]["veiculo"]["id"] == factor
    assert nova["vistoria"]["id"] not in (troca["devolucao_vistoria_id"], saida.pk)
    assert cenario.detalhe(juliana.pk)["devolucao"]["devolucao_id"] == devolucao.pk


def test_loc_09_cancelar_troca_caucao_aberta(cenario, juliana, relogio):
    _juliana_pede_a_nmax(cenario, juliana, relogio)
    conta = _caucao_da_troca(juliana)
    detalhe = cenario.detalhe(juliana.pk)
    assert detalhe["troca"]["caucao"] == {
        "conta_id": conta.pk,
        "valor_centavos": 20000,
        "status": "aberta",
    }
    resposta = _cancelar_troca(cenario, juliana.pk)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["troca"]["conta_caucao"] == {"id": conta.pk, "status": "cancelada"}
    conta.refresh_from_db()
    assert conta.status == "cancelada"
    assert _troca(juliana).status == "cancelada"


def test_loc_09_cancelar_troca_chegada_concluida(cenario, juliana, relogio):
    troca = _juliana_pede_a_nmax(cenario, juliana, relogio)
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    resposta = _vistoriar_pela_api(cenario, troca["devolucao_vistoria_id"], 18900)
    assert resposta.status_code == 200, resposta.json()
    assert cenario.detalhe(juliana.pk)["acoes"]["cancelar_troca"] is True

    resposta = _cancelar_troca(cenario, juliana.pk)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()["troca"]
    assert corpo["devolucao_vistoria"]["status"] == "concluida"
    assert corpo["saida_vistoria"]["status"] == "descartada"
    assert corpo["devolucao_id"] == devolucao["id"]
    # A chegada concluída fica como a chegada da devolução, com as regras de sempre: antes do
    # dia do fim previsto, encerrar pede o encerramento antecipado aprovado (DEV-07).
    assert Devolucao.objects.get(pk=devolucao["id"]).vistoria_id == troca["devolucao_vistoria_id"]
    assert Veiculo.objects.get(placa="PNB7C04").status == "alugado"
    acerto = _ver(cenario, devolucao["id"])["acerto"]
    assert [a["codigo"] for a in acerto["avisos"]] == ["DEV-07"]
    assert _forma(cenario, devolucao["id"]).status_code == 200
    resposta = _encerrar(cenario, devolucao["id"])
    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "DEV-07")


def test_loc_09_cancelar_troca_caucao_paga(cenario, juliana, relogio):
    _juliana_pede_a_nmax(cenario, juliana, relogio)
    conta = _caucao_da_troca(juliana)
    financeiro_services.marcar_paga(conta, forma="pix")
    resposta = _cancelar_troca(cenario, juliana.pk)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["troca"]["conta_caucao"] == {"id": conta.pk, "status": "paga"}
    conta.refresh_from_db()
    assert conta.status == "paga"
    # A diferença paga entra na caução total e volta no acerto final (DEV-02).
    financeiro_services.marcar_paga(_parcela(juliana, 3), forma="pix")
    _ir_para(cenario, relogio, "2026-10-21 17:00")
    corpo = _chegada(cenario, _abrir_devolucao(cenario, juliana.pk), 19630)
    assert corpo["acerto"]["caucao_centavos"] == 50000
    assert corpo["acerto"]["saldo_centavos"] == 50000
    assert not [i for i in corpo["acerto"]["itens"] if i["tipo"] == "diferenca_troca"]


def test_loc_09_cancelar_troca_recusas(cenario, juliana, relogio):
    resposta = _cancelar_troca(cenario, juliana.pk)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "transicao_troca")
    assert resposta.json()["mensagem"] == "Esta locação não tem troca de veículo pendente."

    troca = _juliana_pede_a_nmax(cenario, juliana, relogio)
    assert _cancelar_troca(cenario, juliana.pk, quem="João").status_code == 403
    assert _cancelar_troca(cenario, juliana.pk, quem="Lúcia").status_code == 403
    resposta = _cancelar_troca(cenario, juliana.pk, motivo="  ")
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["motivo"] == ["Informe o motivo do cancelamento da troca."]

    # Com a NMax já entregue (saída concluída), a troca não se cancela (T-122).
    financeiro_services.marcar_paga(_caucao_da_troca(juliana), forma="pix")
    km = _troca(juliana).veiculo_novo.km_atual
    resposta = _vistoriar_pela_api(cenario, troca["saida_vistoria_id"], km)
    assert resposta.status_code == 200, resposta.json()
    assert cenario.detalhe(juliana.pk)["acoes"]["cancelar_troca"] is False
    resposta = _cancelar_troca(cenario, juliana.pk)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "troca_saida_concluida")
    assert resposta.json()["mensagem"] == (
        "O veículo novo já foi entregue. Conclua a troca com a chegada do veículo antigo."
    )
    assert _troca(juliana).status == "pendente"


# --- Cancelamento e renovação com a troca pendente (LOC-12, LOC-08) ---


def test_loc_12_cancelamento_com_troca_pendente(cenario, juliana, relogio):
    _completar(juliana.cliente)
    antes = juliana.cancelamento_status
    _troca_pedida(cenario, juliana.pk, _nmax(cenario))
    for quem in ("Bruna", "Rodrigo"):  # o pedido do vendedor e o direto do gerente
        resposta = cenario.moto.api(quem).post(
            f"{LISTA}{juliana.pk}/cancelar/", {"motivo": "Cliente vai viajar"}, format="json"
        )
        assert (resposta.status_code, resposta.json()["codigo"]) == (409, "troca_pendente")
        assert resposta.json()["mensagem"] == "Conclua ou cancele a troca antes"
    juliana.refresh_from_db()
    assert juliana.cancelamento_status == antes
    # A simulação continua respondendo; a renovação continua permitida.
    simular = cenario.moto.api("Bruna").post(
        f"{LISTA}{juliana.pk}/cancelamento/simular/", {}, format="json"
    )
    assert simular.status_code == 200, simular.json()

    detalhe = cenario.detalhe(juliana.pk)
    acoes = detalhe["acoes"]
    assert (acoes["cancelar"], acoes["renovar"], acoes["cancelar_troca"]) == (False, True, True)
    troca = detalhe["troca"]
    assert troca["status"] == "pendente"
    assert troca["veiculo_novo"]["placa"] == _troca(juliana).veiculo_novo.placa
    assert troca["saida_vistoria"]["status"] == "rascunho"
    assert troca["preco"] == {
        "valor_periodo_centavos": 44900,
        "diaria_centavos": 7990,
        "caucao_centavos": 50000,
        "preco_do_dia": "2026-10-07",
    }
    # O vistoriador recebe a troca sem preço e sem caução.
    para_joao = cenario.detalhe(juliana.pk, quem="João")["troca"]
    assert "preco" not in para_joao and para_joao.get("caucao") is None
    _renovar(cenario, juliana)


def test_loc_09_vistoria_descartada_fora_da_agenda(cenario, juliana, relogio):
    """A chegada descartada não aparece na agenda nem conta como rascunho da locação."""
    troca = _juliana_pede_a_nmax(cenario, juliana, relogio)
    assert _cancelar_troca(cenario, juliana.pk).status_code == 200
    agenda = cenario.moto.api("João").get(f"{VISTORIAS}agenda/?dia=semana").json()
    ids = {i["vistoria_id"] for i in agenda["resultados"]}
    assert troca["devolucao_vistoria_id"] not in ids


# --- Forma da devolução pela hora do acerto (DEV-07; nota da T-119 na T-122) ---


def test_dev_07_forma_da_devolucao_pela_hora_do_acerto(cenario, relogio):
    """Patrícia, LOC-2812 (mensal, fim 15 out 18:00). A forma do pedido de encerramento só vem
    sugerida quando o encerramento antecipado vale no momento do acerto, e não na hora em que a
    devolução foi aberta."""
    patricia = carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)["LOC-2812"]
    _caucao_paga(patricia, 50000)
    veiculo = Veiculo.objects.get(pk=patricia.veiculo_id)
    _saida_direta(patricia, veiculo.km_atual, "cheio", "2026-09-15 09:00")
    # Aberta antes da aprovação: sem forma; aprovada depois, a do pedido (Pix).
    devolucao = _abrir_devolucao(cenario, patricia.pk)
    assert _ver(cenario, devolucao["id"])["acerto"]["forma_devolucao"] is None
    resposta = cenario.moto.api("Rodrigo").post(
        f"{LISTA}{patricia.pk}/cancelar/", {"motivo": "Cliente vai mudar de cidade"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    assert _ver(cenario, devolucao["id"])["acerto"]["forma_devolucao"] == "pix"
    # Concluída no dia do fim previsto, a devolução é comum: a forma é escolhida no acerto.
    _ir_para(cenario, relogio, "2026-10-15 10:00")
    corpo = _chegada(cenario, devolucao, veiculo.km_atual + 120)
    assert corpo["acerto"]["forma_devolucao"] is None
    assert Devolucao.objects.get(pk=devolucao["id"]).forma_devolucao == ""
