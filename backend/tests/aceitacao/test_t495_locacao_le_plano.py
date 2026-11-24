"""T-495 · A locação lê o plano do veículo (ADR 0041, parte 2).

Regras: LOC-01, LOC-03, LOC-04, LOC-05, LOC-08, LOC-09, LOC-10, LOC-12, LOC-15, LOC-16, VEI-12,
VEI-15, VEI-16. Moto Rápida, Filial Centro, 07 out 2026: o SAK-1D39 (Street) com os planos do
modelo (diária R$ 54,90, semanal R$ 329,00, mensal R$ 1.190,00, caução R$ 300,00) e a Pop 110i
TBC-5H21 dos casos "Locação com compra" de `docs/regras/dados-de-teste.md`.
"""

import importlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.apps import apps as django_apps
from django.core.management import call_command
from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.contratos import prontos
from apps.contratos.models import ModeloContrato
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber, Despesa
from apps.locacoes import services
from apps.locacoes.models import Locacao, PlanoCompra
from apps.plataforma.models import Empresa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import (
    HistoricoPrecoVeiculo,
    HistoricoStatusVeiculo,
    PlanoCompraVeiculo,
    PlanoVeiculo,
    RegrasVeiculo,
    Veiculo,
)
from comum import relogio as relogio_do_giro
from comum.erros import Conflito

from .frota import criar_veiculo
from .test_t015_locacoes import INICIO, LISTA, SIMULAR, Cenario, _assinar, _vistoriar
from .test_t015_locacoes import cenario as cenario

FUSO = ZoneInfo("America/Sao_Paulo")
AVISO = veiculos_services.AVISO_PRECO
STREET = "Street 150–160"
URBANA = "Urbana 110–125"
COMPRA_POP: dict[str, Any] = {
    "ligado": True,
    "periodicidade": "semanal",
    "parcelas": 104,
    "entrada_centavos": 100000,
    "juros_mes_pct": "1.00",
    "modo": "calcular",
    "adicional_centavos": 2977,
    "caucao_centavos": 30000,
}


def _plano(veiculo: Veiculo, tipo: str) -> PlanoVeiculo:
    return PlanoVeiculo.ativos.get(veiculo=veiculo, tipo=tipo)


def _mudar_plano(veiculo: Veiculo, tipo: str, **campos: Any) -> PlanoVeiculo:
    """Preparação do teste: o plano direto no banco (o serviço tem testes próprios, T-494)."""
    PlanoVeiculo.ativos.filter(veiculo=veiculo, tipo=tipo).update(**campos)
    return _plano(veiculo, tipo)


def _mudar_regras(veiculo: Veiculo, **campos: Any) -> None:
    RegrasVeiculo.objects.filter(veiculo=veiculo).update(**campos)


def _corpo_do_plano(cenario: Cenario, plano: PlanoVeiculo, **campos: Any) -> dict[str, Any]:
    corpo = cenario.corpo(veiculo=plano.veiculo, plano_veiculo_id=plano.pk, **campos)
    corpo.pop("periodicidade")
    return corpo


def _contas(locacao_id: int, tipo: str) -> list[ContaReceber]:
    return list(
        ContaReceber.objects.filter(
            origem_tipo="locacao", origem_id=locacao_id, tipo=tipo
        ).order_by("vencimento", "numero_parcela", "id")
    )


def _retirar(locacao_id: int) -> Locacao:
    """Vistoria, assinatura e o 1º pagamento (parcela 1, a 1ª da caução e a entrada)."""
    _vistoriar(locacao_id)
    _assinar(locacao_id)
    for conta in ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao_id):
        primeira = conta.numero_parcela in (None, 1)
        if conta.status == "aberta" and primeira and conta.tipo in ("parcela", "caucao", "entrada"):
            financeiro.marcar_paga(conta, forma="pix")
    locacao = Locacao.objects.get(pk=locacao_id)
    assert locacao.status == "ativa"
    return locacao


def _em(cenario: Cenario, relogio: Any, quando: str) -> None:
    relogio.em(quando)
    cenario.moto._tokens.clear()


# --- Nova locação pelo plano do veículo (LOC-01, VEI-15) ---


def test_loc_01_rascunho_e_confirmacao_pelo_plano_do_veiculo(cenario: Cenario) -> None:
    """O plano semanal do SAK-1D39: o valor, a caução, o dia de atraso e as regras do veículo,
    congelados na confirmação (LOC-15, ADR 0041, item 5)."""
    semanal = _plano(cenario.sak, "semanal")
    api = cenario.moto.api("Bruna")
    simulada = api.post(SIMULAR, _corpo_do_plano(cenario, semanal, periodos=2), format="json")
    assert simulada.status_code == 200, simulada.json()
    corpo = simulada.json()
    assert (corpo["valor_periodo_centavos"], corpo["caucao_centavos"]) == (32900, 30000)
    assert (corpo["diaria_centavos"], corpo["hoje_na_retirada_centavos"]) == (5490, 62900)
    assert corpo["plano"]["id"] == semanal.pk
    assert (corpo["plano"]["rotulo"], corpo["plano"]["multa_minima_centavos"]) == ("Semanal", 5490)
    criada = api.post(LISTA, _corpo_do_plano(cenario, semanal, periodos=2), format="json")
    assert criada.status_code == 201, criada.json()
    assert cenario.confirmar(criada.json()["id"]).status_code == 200
    locacao = Locacao.objects.get(pk=criada.json()["id"])
    assert (locacao.plano_veiculo_id, locacao.periodicidade) == (semanal.pk, "semanal")
    assert (locacao.valor_periodo_centavos, locacao.caucao_centavos) == (32900, 30000)
    assert (locacao.diaria_centavos, locacao.multa_minima_centavos) == (5490, 5490)
    assert (locacao.caucao_parcelas, locacao.franquia_km, locacao.km_excedente_centavos) == (
        1,
        None,
        0,
    )
    assert locacao.desconto_sem_aprovacao_pct == Decimal("5.00")
    detalhe = cenario.detalhe(locacao.pk)
    assert detalhe["plano_veiculo"] == {"id": semanal.pk, "nome": "Semanal"}
    assert (detalhe["km_livre"], detalhe["precos"]["multa_minima_centavos"]) == (True, 5490)


def test_loc_01_caminho_antigo_pela_periodicidade(cenario: Cenario) -> None:
    """Sem `plano_veiculo_id` (a Nova locação de hoje, até a T-497), a periodicidade escolhe o
    plano do veículo do mesmo nome."""
    criada = cenario.confirmada(periodos=1)
    locacao = Locacao.objects.get(pk=criada["id"])
    assert locacao.plano_veiculo_id == _plano(cenario.sak, "semanal").pk
    assert locacao.valor_periodo_centavos == 32900


def test_vei_15_veiculo_sem_plano_ligado_nao_entra_na_locacao(cenario: Cenario) -> None:
    """409 `VEI-15` com o aviso da tabela não preenchida, na simulação e no rascunho."""
    PlanoVeiculo.objects.filter(veiculo=cenario.sak).update(ligado=False)
    for rota in (SIMULAR, LISTA):
        resposta = cenario.moto.api("Bruna").post(rota, cenario.corpo(), format="json")
        assert resposta.status_code == 409, resposta.json()
        assert (resposta.json()["codigo"], resposta.json()["mensagem"]) == ("VEI-15", AVISO)
    assert not Locacao.objects.exists()


def test_vei_15_plano_desligado_e_plano_de_outro_veiculo(cenario: Cenario) -> None:
    semanal = _mudar_plano(cenario.sak, "semanal", ligado=False)
    resposta = cenario.moto.api("Bruna").post(
        SIMULAR, _corpo_do_plano(cenario, semanal), format="json"
    )
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "VEI-15")
    outro = _plano(cenario.veiculo(STREET, exceto=(cenario.sak.placa,)), "semanal")
    corpo = {**cenario.corpo(), "plano_veiculo_id": outro.pk}
    resposta = cenario.moto.api("Bruna").post(SIMULAR, corpo, format="json")
    assert resposta.status_code == 400, resposta.json()
    assert resposta.json()["campos"]["plano_veiculo_id"] == ["Escolha um plano deste veículo."]


def test_loc_01_plano_especial_saiu_da_nova_locacao(cenario: Cenario) -> None:
    resposta = cenario.simular(plano_especial_id=1)
    assert resposta.status_code == 400, resposta.json()
    assert resposta.json()["campos"]["plano_especial_id"] == [services.PLANO_ESPECIAL_SAIU]


def test_vei_12_prazo_minimo_e_formas_aceitas(cenario: Cenario) -> None:
    semanal = _mudar_plano(cenario.sak, "semanal", prazo_minimo_periodos=4, formas_aceitas=["pix"])
    api = cenario.moto.api("Bruna")
    curto = api.post(SIMULAR, _corpo_do_plano(cenario, semanal, periodos=2), format="json")
    assert curto.status_code == 400, curto.json()
    assert curto.json()["campos"]["periodos"] == ["Este plano pede no mínimo 4 semanas."]
    boleto = api.post(
        SIMULAR,
        _corpo_do_plano(cenario, semanal, periodos=4, forma_pagamento="boleto"),
        format="json",
    )
    assert boleto.status_code == 400, boleto.json()
    assert boleto.json()["campos"]["forma_pagamento"] == ["Este plano não aceita Boleto."]
    certo = api.post(SIMULAR, _corpo_do_plano(cenario, semanal, periodos=4), format="json")
    assert certo.status_code == 200, certo.json()


def test_loc_15_confirmacao_le_o_preco_do_dia(cenario: Cenario, relogio, relogio_jwt) -> None:
    """O agendado de R$ 349,00 a partir de 08 out: o rascunho de 07 out sai por R$ 329,00, e a
    confirmação em 08 out congela R$ 349,00 (`valor_em(dia)`, ADR 0041, item 1)."""
    semanal = _mudar_plano(
        cenario.sak,
        "semanal",
        valor_agendado_centavos=34900,
        caucao_agendada_centavos=35000,
        agendado_para=date(2026, 10, 8),
    )
    criada = cenario.moto.api("Bruna").post(LISTA, _corpo_do_plano(cenario, semanal), format="json")
    assert criada.status_code == 201, criada.json()
    locacao = Locacao.objects.get(pk=criada.json()["id"])
    assert (locacao.valor_periodo_centavos, locacao.caucao_centavos) == (32900, 30000)
    _em(cenario, relogio, "2026-10-08 09:00")
    assert cenario.confirmar(locacao.pk).status_code == 200
    locacao.refresh_from_db()
    assert (locacao.valor_periodo_centavos, locacao.caucao_centavos) == (34900, 35000)
    assert locacao.precos_de == date(2026, 10, 8)


# --- Regras do veículo congeladas (LOC-03, LOC-10, LOC-12) ---


def test_loc_03_limite_de_desconto_do_veiculo(cenario: Cenario) -> None:
    """Com "desconto sem aprovação" de 10% no veículo, 8% passa sem pedido e 12% pede o APR-01."""
    _mudar_regras(cenario.sak, desconto_sem_aprovacao_pct=Decimal("10.00"))
    assert cenario.simular(desconto_pct="8.00").json()["precisa_aprovacao_desconto"] is False
    assert cenario.simular(desconto_pct="12.00").json()["precisa_aprovacao_desconto"] is True
    locacao = Locacao.objects.get(pk=cenario.confirmada(desconto_pct="8.00")["id"])
    assert (locacao.desconto_pct, locacao.desconto_status) == (Decimal("8.00"), "")
    assert locacao.desconto_sem_aprovacao_pct == Decimal("10.00")


def test_loc_10_dia_de_atraso_do_veiculo(cenario: Cenario) -> None:
    _mudar_regras(cenario.sak, dia_atraso_centavos=6000)
    locacao = Locacao.objects.get(pk=cenario.confirmada()["id"])
    assert (locacao.diaria_centavos, locacao.multa_minima_centavos) == (6000, 5490)


def test_loc_12_multa_minima_congelada(cenario: Cenario) -> None:
    """Semanal de R$ 329,00 de 07 a 21 out, encerrada em 13 out (1 dia restante do período de 07
    a 14 out): 20% de R$ 47,00 = R$ 9,40, abaixo da multa mínima de R$ 100,00 congelada. Mudar a
    regra depois não muda a locação; nas locações de antes (campo nulo), vale a diária."""
    _mudar_regras(cenario.sak, multa_minima_centavos=10000)
    locacao = _retirar(cenario.confirmada(periodos=2)["id"])
    assert locacao.multa_minima_centavos == 10000
    _mudar_regras(cenario.sak, multa_minima_centavos=50000)
    assert services.calcular_encerramento(locacao, date(2026, 10, 13)).multa_centavos == 10000
    Locacao.objects.filter(pk=locacao.pk).update(multa_minima_centavos=None)
    locacao.refresh_from_db()
    assert services.calcular_encerramento(locacao, date(2026, 10, 13)).multa_centavos == 5490


# --- Caução parcelada e o calendário (LOC-04, LOC-05) ---


def test_loc_04_caucao_parcelada_com_as_proximas_parcelas(cenario: Cenario) -> None:
    """Caução de R$ 500,00 em 2 × R$ 250,00 no semanal: a 1ª na retirada (07 out), a 2ª com a
    parcela 2 (14 out). O 1º pagamento é a parcela 1 e a 1ª da caução."""
    semanal = _mudar_plano(cenario.sak, "semanal", caucao_centavos=50000, caucao_parcelas=2)
    api = cenario.moto.api("Bruna")
    simulada = api.post(SIMULAR, _corpo_do_plano(cenario, semanal, periodos=2), format="json")
    assert simulada.json()["caucoes_previstas"] == [
        {"numero": 1, "vencimento": "2026-10-07", "valor_centavos": 25000},
        {"numero": 2, "vencimento": "2026-10-14", "valor_centavos": 25000},
    ]
    assert simulada.json()["hoje_na_retirada_centavos"] == 57900
    criada = api.post(LISTA, _corpo_do_plano(cenario, semanal, periodos=2), format="json").json()
    assert cenario.confirmar(criada["id"]).status_code == 200
    caucoes = _contas(criada["id"], "caucao")
    assert [
        (c.vencimento, c.valor_centavos, c.numero_parcela, c.total_parcelas) for c in caucoes
    ] == [
        (date(2026, 10, 7), 25000, 1, 2),
        (date(2026, 10, 14), 25000, 2, 2),
    ]
    locacao = _retirar(criada["id"])
    assert locacao.primeiro_pagamento_em is not None
    assert locacao.caucao_parcelas == 2
    assert [c.status for c in _contas(criada["id"], "caucao")] == ["paga", "aberta"]


def test_loc_05_mensal_em_duas_quinzenais(cenario: Cenario) -> None:
    """Mensal de R$ 1.190,00 em "2 quinzenais": 2 × R$ 595,00 por mês, a cada 15 dias do começo
    de cada mês do contrato (VEI-12, LOC-05)."""
    mensal = _mudar_plano(cenario.sak, "mensal", como_paga="mes_duas_quinzenais")
    criada = cenario.moto.api("Bruna").post(
        LISTA, _corpo_do_plano(cenario, mensal, periodos=2), format="json"
    )
    assert criada.status_code == 201, criada.json()
    assert cenario.confirmar(criada.json()["id"]).status_code == 200
    locacao = Locacao.objects.get(pk=criada.json()["id"])
    assert (locacao.periodicidade, locacao.parcelamento_mensal) == ("mensal", "duas_quinzenais")
    parcelas = _contas(locacao.pk, "parcela")
    assert [(p.vencimento, p.valor_centavos) for p in parcelas] == [
        (date(2026, 10, 7), 59500),
        (date(2026, 10, 22), 59500),
        (date(2026, 11, 7), 59500),
        (date(2026, 11, 22), 59500),
    ]


# --- Renovação e troca (LOC-08, LOC-09) ---


def test_loc_08_renovacao_pelo_mesmo_plano_com_o_preco_de_hoje(cenario: Cenario) -> None:
    locacao = _retirar(cenario.confirmada(periodos=1)["id"])
    _mudar_plano(cenario.sak, "semanal", valor_centavos=34900)
    services.renovar(locacao, {"periodos": 1}, cenario.pessoas["Bruna"])
    locacao.refresh_from_db()
    assert locacao.valor_periodo_centavos == 34900
    assert [p.valor_centavos for p in _contas(locacao.pk, "parcela")] == [32900, 34900]


def test_loc_08_renovacao_com_o_plano_desligado_vei_15(cenario: Cenario) -> None:
    locacao = _retirar(cenario.confirmada(periodos=1)["id"])
    _mudar_plano(cenario.sak, "semanal", ligado=False)
    with pytest.raises(Conflito) as erro:
        services.renovar(locacao, {"periodos": 1}, cenario.pessoas["Bruna"])
    assert (erro.value.codigo, erro.value.mensagem) == ("VEI-15", AVISO)


def test_loc_09_troca_pede_plano_do_mesmo_tipo(cenario: Cenario) -> None:
    """O veículo novo sem o semanal ligado é recusado (409 `VEI-15`), mesmo com a diária ligada;
    com ele, a troca guarda o valor, a caução e o dia de atraso do plano dele."""
    locacao = _retirar(cenario.confirmada(periodos=2)["id"])
    novo = cenario.veiculo(STREET, exceto=(cenario.sak.placa,))
    _mudar_plano(novo, "semanal", ligado=False)
    with pytest.raises(Conflito) as erro:
        services.pedir_troca(locacao, novo.pk, "Pneu furado", cenario.pessoas["Bruna"])
    assert (erro.value.codigo, erro.value.mensagem) == ("VEI-15", AVISO)
    assert Veiculo.objects.get(pk=novo.pk).status == "disponivel"
    _mudar_plano(novo, "semanal", ligado=True, valor_centavos=34900, caucao_centavos=40000)
    _mudar_regras(novo, dia_atraso_centavos=6500)
    troca = services.pedir_troca(locacao, novo.pk, "Pneu furado", cenario.pessoas["Bruna"])
    assert (troca.valor_periodo_centavos, troca.caucao_centavos, troca.diaria_centavos) == (
        34900,
        40000,
        6500,
    )


# --- Locação com compra pelo plano do veículo (LOC-16, VEI-16) ---


@pytest.fixture
def pop(cenario: Cenario) -> Veiculo:
    """A Pop 110i TBC-5H21: compra R$ 13.490,00, R$ 310,00 de despesas, venda R$ 15.900,00 e a
    locação com compra ligada (dados-de-teste.md), com o modelo da compra publicado."""
    veiculo = criar_veiculo(
        900,
        cenario.frota.categorias[URBANA],
        cenario.frota.centro,
        placa="TBC5H21",
        chassi="9C2JC7110RR000900",
        valor_compra_centavos=1349000,
    )
    veiculos_services.aplicar_modelo_de_preco([veiculo], "cadastro")
    Despesa.objects.create(
        filial=cenario.frota.centro,
        data=date(2026, 8, 12),
        descricao="Revisão",
        categoria="manutencao",
        valor_centavos=31000,
        vencimento=date(2026, 8, 12),
        veiculo=veiculo,
        status="paga",
        lancada_por=cenario.pessoas["Mariana"],
    )
    veiculos_services.salvar_precos(
        veiculo, {"valor_venda_centavos": 1590000, "plano_compra": COMPRA_POP}
    )
    ModeloContrato.objects.create(
        nome="Locação com intenção de compra",
        finalidade="locacao_compra",
        texto=prontos.TEXTO_COMPRA,
        publicado=True,
        publicado_em=relogio_do_giro.agora(),
    )
    return veiculo


def _corpo_da_compra(cenario: Cenario, veiculo: Veiculo) -> dict[str, Any]:
    return {
        "tipo": "intencao_compra",
        "cliente_id": cenario.cliente("Lucas").pk,
        "veiculo_id": veiculo.pk,
        "inicio": INICIO,
        "forma_pagamento": "pix",
    }


def test_loc_16_compra_pelo_plano_do_veiculo_pop_tbc_5h21(cenario: Cenario, pop: Veiculo) -> None:
    """104 × R$ 191,01 (R$ 161,24 da moto + R$ 29,77 de adicional), entrada de R$ 1.000,00 e
    caução de R$ 300,00 maior que a parcela: a última nasce R$ 0,00, e sobram R$ 108,99. Na
    retirada, entrada, 1ª parcela e caução: R$ 1.491,01."""
    api = cenario.moto.api("Bruna")
    simulada = api.post(SIMULAR, _corpo_da_compra(cenario, pop), format="json")
    assert simulada.status_code == 200, simulada.json()
    corpo = simulada.json()
    assert corpo["compra"] == {
        "periodicidade": "semanal",
        "parcelas_total": 104,
        "valor_parcela_centavos": 19101,
        "parcela_moto_centavos": 16124,
        "adicional_centavos": 2977,
        "entrada_centavos": 100000,
        "ultima_parcela_centavos": 0,
        "sobra_caucao_centavos": 10899,
    }
    assert corpo["linhas"][0] == {"rotulo": "Entrada", "valor_centavos": 100000}
    assert corpo["hoje_na_retirada_centavos"] == 149101
    assert corpo["texto_retirada"] == "Na retirada: entrada, primeira parcela e caução."
    criada = api.post(LISTA, _corpo_da_compra(cenario, pop), format="json")
    assert criada.status_code == 201, criada.json()
    assert cenario.confirmar(criada.json()["id"]).status_code == 200
    locacao = Locacao.objects.get(pk=criada.json()["id"])
    compra = PlanoCompraVeiculo.objects.get(veiculo=pop)
    assert (locacao.plano_compra_veiculo_id, locacao.plano_compra_id) == (compra.pk, None)
    assert (locacao.compra_parcelas, locacao.compra_valor_parcela_centavos) == (104, 19101)
    assert (locacao.compra_entrada_centavos, locacao.compra_adicional_centavos) == (100000, 2977)
    assert (locacao.compra_valor_venda_centavos, locacao.compra_juros_mes_pct) == (
        1590000,
        Decimal("1.00"),
    )
    assert locacao.fim_previsto - locacao.inicio == timedelta(days=728)
    assert len(_contas(locacao.pk, "parcela")) == 103  # a 104ª de R$ 0,00 a caução paga
    [entrada] = _contas(locacao.pk, "entrada")
    assert (entrada.valor_centavos, entrada.vencimento) == (100000, date(2026, 10, 7))
    detalhe = cenario.detalhe(locacao.pk)["compra"]
    assert (detalhe["plano"]["nome"], detalhe["entrada_centavos"]) == ("Locação com compra", 100000)


def test_loc_16_entrada_entra_no_primeiro_pagamento(cenario: Cenario, pop: Veiculo) -> None:
    api = cenario.moto.api("Bruna")
    criada = api.post(LISTA, _corpo_da_compra(cenario, pop), format="json").json()
    assert cenario.confirmar(criada["id"]).status_code == 200
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    for conta in ContaReceber.objects.filter(origem_tipo="locacao", origem_id=criada["id"]):
        if conta.tipo == "caucao" or (conta.tipo == "parcela" and conta.numero_parcela == 1):
            financeiro.marcar_paga(conta, forma="pix")
    assert Locacao.objects.get(pk=criada["id"]).status == "aguardando_retirada"
    [entrada] = _contas(criada["id"], "entrada")
    financeiro.marcar_paga(entrada, forma="pix")
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"


def test_loc_16_quinzenal_a_cada_14_dias(cenario: Cenario, pop: Veiculo) -> None:
    """VEI-16: a quinzenal vence a cada 14 dias, e 52 quinzenais são 728 dias."""
    veiculos_services.salvar_precos(
        pop, {"plano_compra": {**COMPRA_POP, "periodicidade": "quinzenal", "parcelas": 52}}
    )
    compra = PlanoCompraVeiculo.objects.get(veiculo=pop)
    simulada = cenario.moto.api("Bruna").post(
        SIMULAR, _corpo_da_compra(cenario, pop), format="json"
    )
    assert simulada.status_code == 200, simulada.json()
    previstas = simulada.json()["parcelas_previstas"]
    assert [p["vencimento"] for p in previstas[:3]] == ["2026-10-07", "2026-10-21", "2026-11-04"]
    assert (
        previstas[0]["valor_centavos"] == compra.parcela_moto_centavos + compra.adicional_centavos
    )
    inicio = datetime.fromisoformat(INICIO.replace("Z", "+00:00"))
    assert datetime.fromisoformat(simulada.json()["fim_previsto"]) == inicio + timedelta(days=728)


def test_loc_16_compra_desligada_vei_15(cenario: Cenario, pop: Veiculo) -> None:
    PlanoCompraVeiculo.objects.filter(veiculo=pop).update(ligado=False)
    resposta = cenario.moto.api("Bruna").post(
        SIMULAR, _corpo_da_compra(cenario, pop), format="json"
    )
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "VEI-15")


# --- Cadastro antigo: 410 (ADR 0041, item 2) ---


def test_vei_16_cadastro_antigo_de_plano_de_compra_responde_410(cenario: Cenario) -> None:
    antigo = services.criar_plano_compra(
        {
            "nome": "Compra Street 24 meses",
            "categoria_id": cenario.frota.categorias[STREET].pk,
            "periodicidade": "mensal",
            "parcelas": 24,
            "valor_parcela_centavos": 119000,
        }
    )
    api = cenario.moto.api("Mariana")
    corpo = {"nome": "Outro", "periodicidade": "mensal", "parcelas": 24}
    for resposta in (
        api.post("/api/planos-compra/", corpo, format="json"),
        api.patch(f"/api/planos-compra/{antigo.pk}/", {"parcelas": 12}, format="json"),
    ):
        assert resposta.status_code == 410, resposta.json()
        assert resposta.json()["codigo"] == "VEI-16"
        assert resposta.json()["mensagem"] == (
            "O plano de compra agora é de cada veículo. Use Planos e preços do veículo."
        )
    assert api.get("/api/planos-compra/").status_code == 200
    assert PlanoCompra.objects.get(pk=antigo.pk).parcelas == 24


def test_vei_12_cadastro_antigo_de_plano_especial_responde_410(cenario: Cenario) -> None:
    api = cenario.moto.api("Mariana")
    corpo = {"nome": "Entregador", "periodicidade": "semanal", "regra": "preco_fixo"}
    resposta = api.post("/api/planos-especiais/", corpo, format="json")
    assert (resposta.status_code, resposta.json()["codigo"]) == (410, "VEI-12")
    assert api.get("/api/planos-especiais/").status_code == 200


# --- Migração do plano de compra (ADR 0041, item 3, passo 4) ---


def _migracao() -> Any:
    return importlib.import_module("apps.locacoes.migrations.0009_copiar_planos_de_compra")


def test_loc_16_migracao_copia_o_plano_de_compra_da_categoria(cenario: Cenario) -> None:
    """O plano ativo mais recente da Street vai, desligado e no modo digitar, para cada Street
    sem plano de compra, com a caução da categoria; rodar de novo não duplica nem sobrescreve."""
    street = cenario.frota.categorias[STREET]
    for nome, parcela in (("Compra antiga", 99000), ("Compra Street 24 meses", 119000)):
        services.criar_plano_compra(
            {
                "nome": nome,
                "categoria_id": street.pk,
                "periodicidade": "mensal",
                "parcelas": 24,
                "valor_parcela_centavos": parcela,
            }
        )
    _migracao().copiar(django_apps, None)
    da_street = Veiculo.objects.filter(categoria=street)
    compras = PlanoCompraVeiculo.objects.filter(veiculo__in=da_street)
    assert compras.count() == da_street.count()
    valores = set(
        compras.values_list(
            "ligado",
            "modo",
            "periodicidade",
            "parcelas",
            "parcela_moto_centavos",
            "caucao_centavos",
        )
    )
    assert valores == {(False, "digitar", "mensal", 24, 119000, 30000)}
    assert HistoricoPrecoVeiculo.objects.filter(
        veiculo=cenario.sak, origem="migracao", alvo="plano_compra"
    ).exists()
    assert not PlanoCompraVeiculo.objects.exclude(veiculo__in=da_street).exists()
    PlanoCompraVeiculo.objects.filter(veiculo=cenario.sak).update(parcela_moto_centavos=125000)
    _migracao().copiar(django_apps, None)
    assert PlanoCompraVeiculo.objects.filter(veiculo__in=da_street).count() == da_street.count()
    assert PlanoCompraVeiculo.objects.get(veiculo=cenario.sak).parcela_moto_centavos == 125000


# --- alinhar_veiculos_sem_preco (VEI-15, ADR 0041, item 3, passo 6) ---


def test_vei_15_alinhar_veiculos_sem_preco(cenario: Cenario) -> None:
    """O disponível sem plano ligado vai para `indisponivel` "sem preço", com o histórico de
    status e o evento do Sistema; rodar de novo não muda nada."""
    veiculo = cenario.veiculo(URBANA)
    PlanoVeiculo.objects.filter(veiculo=veiculo).update(ligado=False)
    call_command("alinhar_veiculos_sem_preco", "empresa_a")
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    veiculo.refresh_from_db()
    assert (veiculo.status, veiculo.motivo_status) == (
        "indisponivel",
        veiculos_services.MOTIVO_SEM_PRECO,
    )
    ultimo = HistoricoStatusVeiculo.objects.filter(veiculo=veiculo).order_by("-id").first()
    assert ultimo is not None and (ultimo.de, ultimo.para) == ("disponivel", "indisponivel")
    evento = EventoAuditoria.objects.filter(acao="veiculo.sem_preco", objeto_id=veiculo.pk).get()
    assert evento.ator_tipo == "sistema"
    antes = HistoricoStatusVeiculo.objects.count()
    call_command("alinhar_veiculos_sem_preco", "empresa_a")
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert HistoricoStatusVeiculo.objects.count() == antes
    assert Veiculo.objects.filter(status="disponivel", planos__ligado=True).exists()


# --- Isolamento entre empresas ---


def test_loc_01_isolamento_do_plano_do_veiculo(cenario: Cenario) -> None:
    cenario.confirmada()
    assert Locacao.objects.filter(plano_veiculo__isnull=False).count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Locacao.objects.exists()
    assert not PlanoVeiculo.objects.exists()
