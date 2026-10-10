"""T-111 · Código das decisões da T-091 (docs/qa/criterios/T-015.md, CA-015-26 a 29).

Decisões do dono do produto em 09 out 2026 (T-110, opção A): a renovação feita depois do prazo
começa na hora da renovação e o atraso continua cobrado (`LOC-08`); período e extras da
renovação pelo preço de hoje (`LOC-08`, `LOC-15`); dias usados da diária em blocos de 24 h
(`LOC-12`); mensal em 4 semanais com o mesmo saldo do mês à vista (`LOC-13`, com a T-113: o
encerramento cancela só as parcelas que vencem depois do dia).

Cenário da T-016 (Moto Rápida, Filial Centro seg a sex 8h–18h, sáb 8h–12h); o relógio anda para
a data de cada caso.
"""

from datetime import UTC, date, timedelta
from typing import Any

import pytest

from apps.aprovacoes.models import PedidoAprovacao
from apps.financeiro.models import ContaReceber
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes import services
from apps.locacoes.models import Locacao
from apps.veiculos.models import Extra, Veiculo

from . import carteira
from .frota import montar_frota
from .test_t012_filiais import MotoRapida
from .test_t015_locacoes import LISTA, Cenario, _assinar, _pagar, _plano, _vistoriar
from .test_t016_vistorias import (
    _abrir_devolucao,
    _chegada,
    _encerrar,
    _ir_para,
    _item,
    _saida_direta,
)
from .test_t091_locacao_fim import _cancelar, _parcelas, _simular_cancelamento

STREET = "Street 150–160"
URBANA = "Urbana 110–125"
STREET_DIARIA = 5490


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
def da_carteira(cenario, relogio) -> dict[str, Locacao]:
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)


def _ativa(cenario: Cenario, quando: str, quem: str = "Bruna", **campos: Any) -> Locacao:
    """Confirmada em `quando` (hora local), com início nessa hora, e retirada: `ativa`."""
    criada = cenario.confirmada(quem, inicio=carteira.momento(quando).isoformat(), **campos)
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    locacao = Locacao.objects.get(pk=criada["id"])
    assert locacao.status == "ativa"
    return locacao


def _renovar(cenario: Cenario, locacao: Locacao, quem: str = "Bruna", **corpo: Any) -> Any:
    resposta = cenario.moto.api(quem).post(
        f"{LISTA}{locacao.pk}/renovar/", corpo or {"periodos": 1}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    locacao.refresh_from_db()
    return resposta.json()


# --- CA-015-26 · Renovação depois do prazo (LOC-08, LOC-10, LOC-11) ---


@pytest.mark.parametrize(
    ("renovacao", "atraso", "inicio", "fim", "vencimento"),
    [
        ("2026-10-07 09:30", 0, "2026-10-07 10:00", "2026-10-14 10:00", date(2026, 10, 7)),
        ("2026-10-07 11:00", 0, "2026-10-07 10:00", "2026-10-14 10:00", date(2026, 10, 7)),
        ("2026-10-07 11:01", 5490, "2026-10-07 11:01", "2026-10-14 11:01", date(2026, 10, 7)),
        ("2026-10-09 10:00", 10980, "2026-10-09 10:00", "2026-10-16 10:00", date(2026, 10, 9)),
    ],
)
def test_loc_08_ca_015_26_renovacao_depois_do_prazo(
    cenario, relogio, renovacao, atraso, inicio, fim, vencimento
):
    _ir_para(cenario, relogio, "2026-09-30 10:00")
    street = _ativa(cenario, "2026-09-30 10:00", periodos=1)
    assert street.fim_previsto == carteira.momento("2026-10-07 10:00")

    if renovacao.startswith("2026-10-09"):  # a aut_02 a leva para devolucao_atrasada em 08 out
        _ir_para(cenario, relogio, "2026-10-08 00:00")
        assert services.marcar_devolucoes_atrasadas() == 1
    _ir_para(cenario, relogio, renovacao)
    street.refresh_from_db()
    # Às 11:01 de 07 out a locação ainda está ativa; em 09 out, já com a devolução atrasada.
    antes = "devolucao_atrasada" if renovacao.startswith("2026-10-09") else "ativa"
    assert street.status == antes

    simulacao = cenario.moto.api("Bruna").post(
        f"{LISTA}{street.pk}/renovar/simular/", {"periodos": 1}, format="json"
    )
    assert simulacao.status_code == 200, simulacao.json()
    fim_utc = carteira.momento(fim).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert simulacao.json()["fim_previsto"] == fim_utc

    _renovar(cenario, street)
    assert street.status == "ativa"
    assert street.fim_previsto == carteira.momento(fim)
    assert street.fim_previsto - timedelta(days=7) == carteira.momento(inicio)
    assert street.atraso_anterior_centavos == atraso
    nova = _parcelas(street.pk)[-1]
    assert (nova.valor_centavos, nova.vencimento) == (32900, vencimento)
    if atraso == 10980:
        assert nova.valor_centavos + street.atraso_anterior_centavos == 43880


def test_loc_08_ca_015_26_devolvida_em_16_out_cobra_so_o_atraso_anterior(cenario, relogio):
    _ir_para(cenario, relogio, "2026-09-30 10:00")
    street = _ativa(cenario, "2026-09-30 10:00", periodos=1)
    _ir_para(cenario, relogio, "2026-10-08 00:00")
    assert services.marcar_devolucoes_atrasadas() == 1
    _ir_para(cenario, relogio, "2026-10-09 10:00")
    _renovar(cenario, street)
    assert street.fim_previsto == carteira.momento("2026-10-16 10:00")

    atraso = services.calcular_atraso(street, carteira.momento("2026-10-16 10:30"))
    assert (atraso["dias"], atraso["valor_centavos"]) == (2, 10980)  # nenhum atraso novo


# --- CA-015-27 · Desconto, extras e plano especial na renovação (LOC-08, LOC-15) ---


def _street_de_23_set(cenario: Cenario, relogio: Any, **campos: Any) -> Locacao:
    """Street semanal confirmada em 23 set (tabela 29940), 3 semanas, renovada em 07 out."""
    _ir_para(cenario, relogio, "2026-09-23 09:00")
    locacao = _ativa(cenario, "2026-09-23 09:00", periodos=3, **campos)
    _ir_para(cenario, relogio, "2026-10-07 10:00")
    return locacao


def test_loc_08_ca_015_27_extras_pelo_preco_de_hoje(cenario, relogio):
    capacete = Extra.objects.create(
        nome="Capacete extra", valor_centavos=1500, cobranca="por_periodo"
    )
    street = _street_de_23_set(
        cenario, relogio, extras=[{"extra_id": capacete.pk, "quantidade": 1}]
    )
    capacete.valor_centavos = 2000  # desde 01 out
    capacete.save(update_fields=["valor_centavos"])

    _renovar(cenario, street, periodos=2)
    valores = [p.valor_centavos for p in _parcelas(street.pk)]
    assert valores == [31440, 31440, 31440, 34900, 34900]  # 29940 + 1500; 32900 + 2000


def test_loc_08_ca_015_27_extra_desativado_continua(cenario, relogio):
    """Decisão do dono em 09 out 2026 (T-115, opção A): o extra desativado no cadastro antes da
    renovação continua na renovação, pelo último valor do cadastro."""
    capacete = Extra.objects.create(
        nome="Capacete extra", valor_centavos=1500, cobranca="por_periodo"
    )
    street = _street_de_23_set(
        cenario, relogio, extras=[{"extra_id": capacete.pk, "quantidade": 1}]
    )
    capacete.valor_centavos = 2000  # desde 01 out
    capacete.save(update_fields=["valor_centavos"])
    resposta = cenario.moto.api("Mariana").post(f"/api/extras/{capacete.pk}/desativar/")
    assert resposta.status_code == 200, resposta.json()
    assert Extra.objects.get(pk=capacete.pk).ativo is False

    _renovar(cenario, street, periodos=2)
    assert [p.valor_centavos for p in _parcelas(street.pk)][-2:] == [34900, 34900]  # 32900 + 2000


@pytest.mark.parametrize(
    ("quem", "pct", "nova"), [("Bruna", "5.00", 31255), ("Rodrigo", "8.00", 30268)]
)
def test_loc_08_ca_015_27_mesmo_percentual_de_desconto_sem_apr_01(
    cenario, relogio, quem, pct, nova
):
    street = _street_de_23_set(cenario, relogio, quem=quem, desconto_pct=pct)
    pedidos = PedidoAprovacao.objects.count()
    _renovar(cenario, street, "Bruna", periodos=2)
    assert [p.valor_centavos for p in _parcelas(street.pk)][-2:] == [nova, nova]
    assert PedidoAprovacao.objects.count() == pedidos  # a Bruna renova os 8% sem APR-01


@pytest.mark.parametrize(("desativado", "nova"), [(False, 27900), (True, 32900)])
def test_loc_08_ca_015_27_plano_entregador(cenario, relogio, desativado, nova):
    entregador = _plano(
        cenario,
        nome="Entregador",
        periodicidade="semanal",
        regra="preco_fixo",
        preco_centavos=27900,
    )
    street = _street_de_23_set(cenario, relogio, plano_especial_id=entregador["id"])
    if desativado:
        resposta = cenario.moto.api("Mariana").post(
            f"/api/planos-especiais/{entregador['id']}/desativar/"
        )
        assert resposta.status_code == 200, resposta.json()
    _renovar(cenario, street, periodos=2)
    assert [p.valor_centavos for p in _parcelas(street.pk)][-2:] == [nova, nova]


def test_loc_08_ca_015_27_mensal_fidelidade_conta_os_meses_desde_o_comeco(cenario, relogio):
    fidelidade = _plano(
        cenario,
        nome="Mensal fidelidade",
        periodicidade="mensal",
        regra="desconto",
        desconto_pct="10.00",
        a_partir_do_periodo=3,
    )
    urbana = cenario.veiculo(URBANA)
    _ir_para(cenario, relogio, "2026-10-05 10:00")
    locacao = _ativa(
        cenario,
        "2026-10-05 10:00",
        veiculo_id=urbana.pk,
        periodicidade="mensal",
        periodos=2,
        plano_especial_id=fidelidade["id"],
    )
    _ir_para(cenario, relogio, "2026-10-07 10:00")
    _renovar(cenario, locacao, periodos=2)
    assert [p.valor_centavos for p in _parcelas(locacao.pk)] == [109000, 109000, 98100, 98100]


# --- CA-015-28 · Diária encerrada antes do fim (LOC-12) ---


@pytest.fixture
def urbana_diaria(cenario, relogio) -> Locacao:
    """Urbana, 5 diárias (22450) de segunda, 05 out, 10:00 a sábado, 10 out, 10:00, paga."""
    urbana = cenario.veiculo(URBANA)
    _ir_para(cenario, relogio, "2026-10-05 10:00")
    locacao = _ativa(
        cenario, "2026-10-05 10:00", veiculo_id=urbana.pk, periodicidade="diaria", periodos=5
    )
    assert [p.valor_centavos for p in _parcelas(locacao.pk)] == [22450]
    assert locacao.fim_previsto == carteira.momento("2026-10-10 10:00")
    _ir_para(cenario, relogio, "2026-10-07 08:00")
    return locacao


def test_loc_12_ca_015_28_simulacao_so_com_a_data_avisa(cenario, urbana_diaria):
    simulacao = _simular_cancelamento(cenario, urbana_diaria.pk, "2026-10-07")
    assert simulacao["multa_centavos"] == 0
    assert simulacao["credito_dias"] == {"dias": 3, "valor_centavos": 13470}
    assert simulacao["devolver_centavos"] == 13470
    assert simulacao["avisos"] == [
        {"codigo": "LOC-12", "mensagem": "O acerto final usa a hora da devolução."}
    ]


@pytest.mark.parametrize(
    ("devolucao", "devolve"),
    [
        ("2026-10-07 09:00", 13470),  # 47 h: 2 dias usados
        ("2026-10-07 10:00", 13470),  # 48 h: 2 dias usados
        ("2026-10-07 10:01", 8980),  # 48 h 01: 3 dias usados, sem tolerância
        ("2026-10-07 15:00", 8980),  # 53 h: 3 dias usados
    ],
)
def test_loc_12_ca_015_28_dias_usados_em_blocos_de_24_h(cenario, urbana_diaria, devolucao, devolve):
    resposta = _cancelar(cenario, urbana_diaria.pk, "Rodrigo", data="2026-10-07")
    assert resposta.status_code == 200, resposta.json()
    urbana_diaria.refresh_from_db()
    credito = services.credito_do_encerramento(urbana_diaria, carteira.momento(devolucao))
    assert credito.valor_centavos == devolve


def test_loc_12_ca_015_28_acerto_usa_a_hora_da_devolucao(cenario, relogio, urbana_diaria):
    resposta = _cancelar(cenario, urbana_diaria.pk, "Rodrigo", data="2026-10-07")
    assert resposta.status_code == 200, resposta.json()
    veiculo = Veiculo.objects.get(pk=urbana_diaria.veiculo_id)
    _saida_direta(urbana_diaria, veiculo.km_atual, "cheio", "2026-10-05 09:50")

    _ir_para(cenario, relogio, "2026-10-07 15:00")
    devolucao = _abrir_devolucao(cenario, urbana_diaria.pk)
    corpo = _chegada(cenario, devolucao, veiculo.km_atual + 80)
    creditos = [(c["tipo"], c["valor_centavos"]) for c in corpo["acerto"]["creditos"]]
    assert creditos == [("dias_nao_usados", 8980)]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 0


# --- CA-015-29 · Mensal em 4 semanais encerrado antes do fim (LOC-13, LOC-12) ---


@pytest.fixture
def nmax_semanais(cenario, da_carteira) -> Any:
    """NMax mensal de 159000 em 4 semanais de 39750 (15, 22, 29 set e 06 out), 15 set a 15 out:
    a LOC-2812 do seed com a parcela do mês trocada pelas 4 semanais, as `pagas` primeiras pagas."""

    def montar(pagas: int) -> Locacao:
        locacao = da_carteira["LOC-2812"]
        locacao.diaria_centavos = 7990
        locacao.parcelamento_mensal = "quatro_semanais"
        locacao.save(update_fields=["diaria_centavos", "parcelamento_mensal"])
        ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk).delete()
        for numero in range(1, 5):
            paga = numero <= pagas
            ContaReceber.objects.create(
                filial=locacao.filial,
                cliente=locacao.cliente,
                origem_tipo="locacao",
                origem_id=locacao.pk,
                origem_codigo=locacao.codigo,
                tipo="parcela",
                numero_parcela=numero,
                total_parcelas=4,
                vencimento=date(2026, 9, 15) + timedelta(days=7 * (numero - 1)),
                valor_centavos=39750,
                status="paga" if paga else "aberta",
                forma="pix" if paga else "",
                pago_em=locacao.inicio if paga else None,
            )
        assert [p.vencimento.day for p in _parcelas(locacao.pk)] == [15, 22, 29, 6]
        return locacao

    return montar


@pytest.mark.parametrize(
    ("dia", "pagas", "restantes", "credito", "canceladas", "multa", "devolver", "cobrar"),
    [
        ("2026-09-25", 2, 20, 74200, 79500, 21200, 0, 26500),
        ("2026-10-05", 3, 10, 37100, 39750, 10600, 0, 13250),
        ("2026-10-07", 4, 8, 37100, 0, 8480, 28620, 0),
    ],
)
def test_loc_13_ca_015_29_mensal_em_4_semanais_mesmo_saldo_do_mes_a_vista(
    cenario,
    relogio,
    nmax_semanais,
    dia,
    pagas,
    restantes,
    credito,
    canceladas,
    multa,
    devolver,
    cobrar,
):
    nmax_semanais = nmax_semanais(pagas)
    _ir_para(cenario, relogio, f"{dia} 09:00")
    simulacao = _simular_cancelamento(cenario, nmax_semanais.pk, dia)
    assert simulacao["dias_restantes"] == restantes
    assert simulacao["credito_semanas"]["valor_centavos"] == credito
    assert simulacao["parcelas_canceladas_centavos"] == canceladas
    assert simulacao["multa_centavos"] == multa
    assert (simulacao["devolver_centavos"], simulacao["cobrar_centavos"]) == (devolver, cobrar)
    assert simulacao["avisos"] == []

    resposta = _cancelar(cenario, nmax_semanais.pk, "Rodrigo", data=dia)
    assert resposta.status_code == 200, resposta.json()
    situacao = [p.status for p in _parcelas(nmax_semanais.pk)]
    assert situacao == ["paga"] * pagas + ["cancelada"] * (4 - pagas)
    detalhe = cenario.detalhe(nmax_semanais.pk)["cancelamento"]
    assert (detalhe["devolver_centavos"], detalhe["cobrar_centavos"]) == (devolver, cobrar)
    nmax_semanais.refresh_from_db()
    assert nmax_semanais.credito_encerramento_centavos == credito - canceladas


def test_loc_13_ca_015_29_acerto_cobra_26500_em_conta_de_3_dias(cenario, relogio, nmax_semanais):
    nmax_semanais = nmax_semanais(2)
    _ir_para(cenario, relogio, "2026-09-25 09:00")
    resposta = _cancelar(cenario, nmax_semanais.pk, "Rodrigo", data="2026-09-25")
    assert resposta.status_code == 200, resposta.json()
    veiculo = Veiculo.objects.get(pk=nmax_semanais.veiculo_id)
    _saida_direta(nmax_semanais, veiculo.km_atual, "cheio", "2026-09-15 09:00")

    devolucao = _abrir_devolucao(cenario, nmax_semanais.pk)
    corpo = _chegada(cenario, devolucao, veiculo.km_atual + 120)
    semanas = _item(corpo, "semanas_nao_usadas")
    assert semanas["valor_centavos"] == 5300
    assert semanas["descricao"] == (
        "2 semanas não usadas (R$ 742,00) − 2 parcelas canceladas (R$ 795,00)"
    )
    assert corpo["acerto"]["creditos"] == []
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 21200
    assert corpo["acerto"]["resultado"]["tipo"] == "cobrar"
    assert corpo["acerto"]["resultado"]["valor_centavos"] == 26500

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    conta = ContaReceber.objects.get(origem_tipo="devolucao", status="aberta")
    assert (conta.tipo, conta.valor_centavos, conta.vencimento) == (
        "acerto",
        26500,
        date(2026, 9, 28),
    )


def test_loc_13_ca_015_21_patricia_mes_a_vista_nao_muda(cenario, da_carteira):
    patricia = da_carteira["LOC-2812"]
    patricia.diaria_centavos = 7990
    patricia.save(update_fields=["diaria_centavos"])
    simulacao = _simular_cancelamento(cenario, patricia.pk, "2026-10-07")
    assert simulacao["parcelas_canceladas_centavos"] == 0
    assert (simulacao["devolver_centavos"], simulacao["cobrar_centavos"]) == (28620, 0)
