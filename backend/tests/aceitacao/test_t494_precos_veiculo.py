"""T-494 · Preços do veículo: planos, regras, custos, compra e histórico (VEI-12 a VEI-17, LOC-15).

Desenho na ADR 0041; contrato em docs/api/veiculos.md, seção "Preços do veículo". A frota da
Moto Rápida nasce com os planos do modelo (o preço da categoria em 07 out): a Street tem diária
R$ 54,90, semanal R$ 329,00, mensal R$ 1.190,00 e caução R$ 300,00. Os números da compra são os
de `dados-de-teste.md` (Pop 110i TBC-5H21).
"""

import importlib
from datetime import date
from typing import Any

import pytest
from django.apps import apps as django_apps
from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.financeiro.models import Despesa
from apps.plataforma.models import Empresa
from apps.veiculos import selectors, services
from apps.veiculos.models import (
    HistoricoPrecoVeiculo,
    PlanoCompraVeiculo,
    PlanoVeiculo,
    PrecoCategoria,
    RegrasVeiculo,
    Veiculo,
)
from comum.erros import TransicaoInvalida

from .frota import Frota, criar_veiculo, montar_frota
from .test_t012_filiais import MotoRapida

VEICULOS = "/api/veiculos/"
AVISO = services.AVISO_PRECO


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _precos(moto: MotoRapida, veiculo: Veiculo, quem: str = "Mariana") -> Any:
    return moto.api(quem).get(f"{VEICULOS}{veiculo.pk}/precos/")


def _put(moto: MotoRapida, veiculo: Veiculo, corpo: dict[str, Any], quem: str = "Mariana") -> Any:
    return moto.api(quem).put(f"{VEICULOS}{veiculo.pk}/precos/", corpo, format="json")


def _plano(veiculo: Veiculo, tipo: str) -> PlanoVeiculo:
    return PlanoVeiculo.ativos.get(veiculo=veiculo, tipo=tipo)


def _ligado(moto: MotoRapida, veiculo: Veiculo, plano: PlanoVeiculo, ligado: bool) -> Any:
    return moto.api("Mariana").post(
        f"{VEICULOS}{veiculo.pk}/precos/planos/{plano.pk}/ligado/",
        {"ligado": ligado},
        format="json",
    )


def _desligar_todos(moto: MotoRapida, veiculo: Veiculo) -> None:
    for plano in PlanoVeiculo.ativos.filter(veiculo=veiculo, ligado=True):
        assert _ligado(moto, veiculo, plano, False).status_code == 200


def _pop(moto: MotoRapida, frota: Frota) -> Veiculo:
    """A Pop 110i TBC-5H21: compra R$ 13.490,00 e R$ 310,00 de despesas (mais uma recusada, que
    não entra no pago na moto, FIN-17)."""
    pop = criar_veiculo(
        900,
        frota.categorias["Urbana 110–125"],
        frota.centro,
        placa="TBC5H21",
        chassi="9C2JC7110RR000900",
        valor_compra_centavos=1349000,
    )
    services.aplicar_modelo_de_preco([pop], "cadastro")
    for valor, status in ((31000, "paga"), (50000, "recusada")):
        Despesa.objects.create(
            filial=frota.centro,
            data=date(2026, 10, 2),
            descricao="Revisão",
            categoria="manutencao",
            valor_centavos=valor,
            vencimento=date(2026, 10, 2),
            veiculo=pop,
            status=status,
            lancada_por=moto.pessoas["Mariana"],
        )
    return pop


COMPRA_POP = {
    "ligado": True,
    "periodicidade": "semanal",
    "parcelas": 104,
    "entrada_centavos": 100000,
    "juros_mes_pct": "1.00",
    "modo": "calcular",
    "adicional_centavos": 2977,
    "caucao_centavos": 30000,
}


# --- Migração (ADR 0041, item 3, passo 3) ---


def _migracao() -> Any:
    return importlib.import_module("apps.veiculos.migrations.0010_copiar_precos_da_categoria")


def test_vei_12_migracao_copia_a_categoria_e_e_idempotente(moto, frota) -> None:
    """O veículo sem regras ganha diária, semanal e mensal da Street, ligados, à vista, com as
    quatro formas; regras com dia de atraso e multa mínima = diária; histórico `migracao`. Rodar
    de novo não duplica nem sobrescreve o que a locadora editou."""
    novo = criar_veiculo(901, frota.categorias["Street 150–160"], frota.centro)
    _migracao().copiar(django_apps, None)
    planos = {p.tipo: p for p in PlanoVeiculo.ativos.filter(veiculo=novo)}
    assert set(planos) == {"diaria", "semanal", "mensal"}
    assert planos["semanal"].valor_centavos == 32900
    assert planos["semanal"].caucao_centavos == 30000
    assert planos["semanal"].ligado is True
    assert planos["mensal"].como_paga == "mes_uma_parcela"
    assert planos["diaria"].formas_aceitas == ["pix", "boleto", "cartao", "dinheiro"]
    assert planos["diaria"].franquia_km is None
    regras = RegrasVeiculo.objects.get(veiculo=novo)
    assert regras.dia_atraso_centavos == regras.multa_minima_centavos == 5490
    assert str(regras.desconto_sem_aprovacao_pct) == "5.00"
    assert HistoricoPrecoVeiculo.objects.filter(veiculo=novo, origem="migracao").exists()

    plano = planos["semanal"]
    plano.valor_centavos = 34900
    plano.save()
    linhas = HistoricoPrecoVeiculo.objects.count()
    _migracao().copiar(django_apps, None)
    assert PlanoVeiculo.objects.filter(veiculo=novo).count() == 3
    assert _plano(novo, "semanal").valor_centavos == 34900
    assert HistoricoPrecoVeiculo.objects.count() == linhas


def test_vei_12_migracao_preco_futuro_vira_agendado(moto, frota) -> None:
    """O primeiro preço futuro da categoria entra como o agendado de cada plano, com a data."""
    street = frota.categorias["Street 150–160"]
    PrecoCategoria.objects.create(
        categoria=street,
        vigente_desde=date(2099, 1, 1),
        diaria_centavos=5990,
        semanal_centavos=34900,
        mensal_centavos=129000,
        caucao_centavos=35000,
    )
    novo = criar_veiculo(902, street, frota.centro)
    _migracao().copiar(django_apps, None)
    semanal = _plano(novo, "semanal")
    assert semanal.valor_centavos == 32900
    assert semanal.valor_agendado_centavos == 34900
    assert semanal.caucao_agendada_centavos == 35000
    assert semanal.agendado_para == date(2099, 1, 1)


def test_vei_12_migracao_categoria_sem_preco_nasce_desligada(moto, frota) -> None:
    from apps.veiculos.models import Categoria

    vazia = Categoria.objects.create(nome="Sem tabela", tipo_veiculo="moto")
    novo = criar_veiculo(903, vazia, frota.centro)
    _migracao().copiar(django_apps, None)
    assert not PlanoVeiculo.objects.filter(veiculo=novo, ligado=True).exists()
    assert services.tem_plano_ligado(novo) is False


# --- Leitura (VEI-12, VEI-13) ---


def test_vei_12_get_traz_os_quatro_tipos_e_as_regras(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    resposta = _precos(moto, sak, "Rodrigo")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert [p["tipo"] for p in corpo["planos"]] == ["diaria", "semanal", "mensal", "entregador"]
    semanal = corpo["planos"][1]
    assert (semanal["valor_centavos"], semanal["caucao_centavos"], semanal["ligado"]) == (
        32900,
        30000,
        True,
    )
    entregador = corpo["planos"][3]
    assert entregador["id"] is None and entregador["ligado"] is False
    assert corpo["regras"]["dia_atraso_centavos"] == 5490
    assert corpo["aviso_preco"] is None
    assert corpo["pode_editar"] is False  # o gerente vê e não edita
    assert "custos" in corpo and "pago_na_moto" in corpo


def test_vei_13_vendedor_nao_recebe_custo_e_vistoriador_nao_abre(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    corpo = _precos(moto, sak, "Bruna").json()
    assert "custos" not in corpo and "pago_na_moto" not in corpo
    assert all("margem" not in p for p in corpo["planos"])
    assert _precos(moto, sak, "João").status_code == 403


def test_vei_13_pago_na_moto_sem_as_recusadas(moto, frota) -> None:
    pop = _pop(moto, frota)
    corpo = _precos(moto, pop).json()
    assert corpo["pago_na_moto"] == {
        "total_centavos": 1380000,
        "compra_centavos": 1349000,
        "despesas_centavos": 31000,
    }


def test_vei_12_mensal_em_4_semanais(moto, frota) -> None:
    """R$ 990,00 em 4 semanais = 4 × R$ 247,50."""
    sak = frota.veiculos["SAK1D39"]
    resposta = _put(
        moto,
        sak,
        {
            "planos": [
                {"tipo": "mensal", "valor_centavos": 99000, "como_paga": "mes_quatro_semanais"}
            ]
        },
    )
    assert resposta.status_code == 200, resposta.json()
    mensal = resposta.json()["planos"][2]
    assert mensal["parcela_do_mes"] == {
        "parcelas": 4,
        "parcela_centavos": 24750,
        "ultima_parcela_centavos": 24750,
    }


def test_vei_12_caucao_em_parcelas_e_ipva_por_mes(moto, frota) -> None:
    """A API divide para a tela: caução de R$ 500,01 em 2 = R$ 250,00 + R$ 250,01 (a diferença
    vai para a última); IPVA de R$ 468,00 no ano = R$ 39,00 por mês, como entra no custo. O
    `simular` devolve os mesmos números sem gravar."""
    sak = frota.veiculos["SAK1D39"]
    corpo = {
        "planos": [{"tipo": "mensal", "caucao_centavos": 50001, "caucao_parcelas": 2}],
        "custos": {"ipva_ano_centavos": 46800},
    }
    simulado = moto.api("Mariana").post(f"{VEICULOS}{sak.pk}/precos/simular/", corpo, format="json")
    assert simulado.status_code == 200, simulado.json()
    for resposta in (simulado, _put(moto, sak, corpo)):
        dados = resposta.json()
        assert dados["planos"][2]["caucao_parcelada"] == {
            "parcelas": 2,
            "parcela_centavos": 25000,
            "ultima_parcela_centavos": 25001,
        }
        assert dados["planos"][1]["caucao_parcelada"] is None  # à vista
        assert dados["custos"]["ipva_mes_centavos"] == 3900
    assert "custos" not in _precos(moto, sak, "Bruna").json()


# --- Salvar (VEI-12, VEI-16, VEI-17) ---


def test_vei_17_salvar_grava_historico_e_um_evento(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    resposta = _put(moto, sak, {"planos": [{"tipo": "semanal", "valor_centavos": 34900}]})
    assert resposta.status_code == 200, resposta.json()
    linha = HistoricoPrecoVeiculo.objects.get(veiculo=sak, origem="tela_precos")
    assert (linha.alvo, linha.alvo_nome, linha.campo, linha.de, linha.para) == (
        "plano",
        "Semanal",
        "valor_centavos",
        32900,
        34900,
    )
    assert linha.por_id == moto.pessoas["Mariana"].pk
    evento = EventoAuditoria.objects.get(acao="veiculo.precos_salvar", objeto_id=sak.pk)
    assert evento.depois["lote"] == str(linha.lote)
    assert evento.regra == "VEI-17"


def test_vei_15_mudar_preco_nao_mexe_na_locacao_confirmada(moto, frota) -> None:
    """LOC-15: o plano do veículo não é lido pela locação aberta (a LOC-2841 do QXA-4B21 fica
    como está); salvar só grava o veículo."""
    qxa = frota.veiculos["QXA4B21"]
    resposta = _put(moto, qxa, {"planos": [{"tipo": "semanal", "valor_centavos": 34900}]})
    assert resposta.status_code == 200, resposta.json()
    assert Veiculo.objects.get(pk=qxa.pk).status == "alugado"


def test_vei_12_ligar_exige_valor_forma_e_caucao(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    resposta = _put(
        moto,
        sak,
        {
            "planos": [
                {"tipo": "entregador", "periodo": "semana", "ligado": True, "formas_aceitas": []}
            ]
        },
    )
    assert resposta.status_code == 400
    campos = resposta.json()["campos"]
    assert campos["planos.0.valor_centavos"] == [services.MENSAGEM_VALOR_PARA_LIGAR]
    assert campos["planos.0.formas_aceitas"] == [services.MENSAGEM_FORMA_PARA_LIGAR]
    assert campos["planos.0.caucao_centavos"] == [services.MENSAGEM_CAUCAO_PARA_LIGAR]
    assert not PlanoVeiculo.objects.filter(veiculo=sak, tipo="entregador").exists()


def test_vei_12_entregador_e_outro_novos(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    corpo = {
        "planos": [
            {
                "tipo": "entregador",
                "periodo": "semana",
                "ligado": True,
                "valor_centavos": 27900,
                "formas_aceitas": ["pix"],
                "caucao_centavos": 0,
                "caucao_parcelas": 3,
                "prazo_minimo_periodos": 12,
            },
            {"tipo": "outro", "nome": "Fim de semana", "periodo": "dia", "valor_centavos": 9900},
        ]
    }
    resposta = _put(moto, sak, corpo)
    assert resposta.status_code == 200, resposta.json()
    tipos = [p["tipo"] for p in resposta.json()["planos"]]
    assert tipos == ["diaria", "semanal", "mensal", "entregador", "outro"]
    outro = PlanoVeiculo.ativos.get(veiculo=sak, tipo="outro")
    # Retirar o `outro`: fica `ativo=False`, nada se apaga.
    resposta = _put(moto, sak, {"planos": [{"id": outro.pk, "ativo": False}]})
    assert resposta.status_code == 200, resposta.json()
    assert PlanoVeiculo.objects.get(pk=outro.pk).ativo is False
    # Tipo fixo não se retira.
    semanal = _plano(sak, "semanal")
    resposta = _put(moto, sak, {"planos": [{"id": semanal.pk, "ativo": False}]})
    assert resposta.status_code == 400


def test_vei_12_gerente_nao_salva_e_nao_simula(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    assert _put(moto, sak, {}, "Rodrigo").status_code == 403
    simular = moto.api("Rodrigo").post(f"{VEICULOS}{sak.pk}/precos/simular/", {}, format="json")
    assert simular.status_code == 403


def test_vei_16_pop_simular_sem_gravar(moto, frota) -> None:
    pop = _pop(moto, frota)
    corpo = {"valor_venda_centavos": 1590000, "plano_compra": COMPRA_POP}
    resposta = moto.api("Mariana").post(f"{VEICULOS}{pop.pk}/precos/simular/", corpo, format="json")
    assert resposta.status_code == 200, resposta.json()
    resultado = resposta.json()["plano_compra"]["resultado"]
    assert resultado["parcela_moto_centavos"] == 16124
    assert resultado["parcela_cliente_centavos"] == 19101
    assert resultado["recebe_pela_moto_centavos"] == 1776896
    assert resultado["lucro_centavos"] == 396896
    assert resultado["margem_sobre_pago_pct"] == "28.76"
    assert (resultado["pago_sobre_recebe_pct"], resultado["lucro_sobre_recebe_pct"]) == (
        "77.66",
        "22.34",
    )
    assert resposta.json()["pede_confirmacao_juros"] is False
    assert not PlanoCompraVeiculo.objects.filter(veiculo=pop).exists()


def test_vei_16_parcela_digitada_pede_confirmacao_dos_juros(moto, frota) -> None:
    """R$ 170,00 por semana = 1,46% ao mês: sem `confirmar_juros`, 409 `VEI-16`; com ele, grava
    e o evento leva quem confirmou."""
    pop = _pop(moto, frota)
    compra = {**COMPRA_POP, "modo": "digitar", "parcela_moto_centavos": 17000}
    corpo: dict[str, Any] = {"valor_venda_centavos": 1590000, "plano_compra": compra}
    resposta = _put(moto, pop, corpo)
    assert resposta.status_code == 409, resposta.json()
    assert resposta.json()["codigo"] == "VEI-16"
    assert resposta.json()["detalhes"] == {"juros_mes_pct": "1.46"}
    assert not PlanoCompraVeiculo.objects.filter(veiculo=pop).exists()

    resposta = _put(moto, pop, {**corpo, "confirmar_juros": True})
    assert resposta.status_code == 200, resposta.json()
    salvo = PlanoCompraVeiculo.objects.get(veiculo=pop)
    assert (str(salvo.juros_mes_pct), salvo.parcela_moto_centavos) == ("1.46", 17000)
    evento = EventoAuditoria.objects.filter(acao="veiculo.precos_salvar", objeto_id=pop.pk).last()
    assert evento is not None
    confirmados = evento.depois["juros_confirmados"]
    assert confirmados["pct"] == "1.46"
    assert confirmados["por"] == moto.pessoas["Mariana"].pk
    # Os mesmos juros de novo não pedem confirmação.
    assert _put(moto, pop, corpo).status_code == 200


def test_vei_16_ligar_compra_sem_valor_de_venda(moto, frota) -> None:
    pop = _pop(moto, frota)
    resposta = _put(moto, pop, {"valor_venda_centavos": None, "plano_compra": COMPRA_POP})
    assert resposta.status_code == 400
    campos = resposta.json()["campos"]
    assert campos["valor_venda_centavos"] == [services.MENSAGEM_VENDA_PARA_COMPRA]


def test_vei_16_cg_alerta_de_venda_abaixo_do_pago(moto, frota) -> None:
    pop = _pop(moto, frota)
    Veiculo.objects.filter(pk=pop.pk).update(valor_compra_centavos=1359000)  # pago 13.900,00
    compra = {**COMPRA_POP, "entrada_centavos": 0, "adicional_centavos": 0}
    corpo = {"valor_venda_centavos": 1248000, "plano_compra": compra}
    resposta = _put(moto, pop, corpo)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["plano_compra"]["resultado"]["parcela_moto_centavos"] == 13505
    assert resposta.json()["alertas"][0]["mensagem"] == (
        "Valor de venda abaixo do que foi pago: o lucro vem só dos juros."
    )


# --- Sem preço (VEI-15) ---


def test_vei_15_desligar_o_ultimo_plano_leva_a_indisponivel(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    _desligar_todos(moto, sak)
    sak.refresh_from_db()
    assert (sak.status, sak.motivo_status) == ("indisponivel", services.MOTIVO_SEM_PRECO)
    ficha = moto.api("Rodrigo").get(f"{VEICULOS}{sak.pk}/").json()
    assert ficha["aviso_preco"] == AVISO
    lista = moto.api("Rodrigo").get(VEICULOS, {"busca": "SAK1D39"}).json()["resultados"]
    assert lista[0]["aviso_preco"] == AVISO

    assert _ligado(moto, sak, _plano(sak, "semanal"), True).status_code == 200
    sak.refresh_from_db()
    assert (sak.status, sak.motivo_status) == ("disponivel", "")
    assert moto.api("Rodrigo").get(f"{VEICULOS}{sak.pk}/").json()["aviso_preco"] is None


def test_vei_15_bloqueio_nao_volta_sozinho(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    services.bloquear(sak, "Pneu furado")
    _desligar_todos(moto, sak)
    assert _ligado(moto, sak, _plano(sak, "semanal"), True).status_code == 200
    sak.refresh_from_db()
    assert (sak.status, sak.motivo_status) == ("indisponivel", "Pneu furado")


def test_vei_15_colocar_a_venda_sem_plano(moto, frota) -> None:
    """Veículo `disponivel` sem nenhum plano (tabela não preenchida, como na migração de uma
    categoria sem preço): "Colocar à venda" responde 409 `VEI-15` (VEN-01)."""
    sak = criar_veiculo(905, frota.categorias["Street 150–160"], frota.centro)
    assert sak.status == "disponivel" and not services.tem_plano_ligado(sak)
    resposta = moto.api("Rodrigo").post(
        f"{VEICULOS}{sak.pk}/colocar-a-venda/", {"valor_venda_centavos": 1500000}, format="json"
    )
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEI-15"
    assert resposta.json()["mensagem"] == AVISO


def test_vei_15_volta_do_alugado_sem_plano_vai_para_indisponivel(moto, frota) -> None:
    """O QXA-4B21 alugado fica alugado ao perder o último plano; na volta, vai para
    `indisponivel` "sem preço", e não para `disponivel`."""
    qxa = frota.veiculos["QXA4B21"]
    _desligar_todos(moto, qxa)
    qxa.refresh_from_db()
    assert qxa.status == "alugado"
    services.transicionar(
        qxa, "disponivel", origem=services.OrigemDaMudanca("locacao", 2841, "LOC-2841")
    )
    assert (qxa.status, qxa.motivo_status) == ("indisponivel", services.MOTIVO_SEM_PRECO)


def test_vei_15_os_concluida_sem_plano_vai_para_indisponivel(moto, frota) -> None:
    """MAN-05: o PMZ-3E17 em manutenção, sem plano ligado, sai da OS para `indisponivel`."""
    pmz = frota.veiculos["PMZ3E17"]
    _desligar_todos(moto, pmz)
    services.transicionar(pmz, "disponivel", origem=services.OrigemDaMudanca("ordem_servico", 1))
    assert (pmz.status, pmz.motivo_status) == ("indisponivel", services.MOTIVO_SEM_PRECO)


@pytest.mark.parametrize("placa", ["QXA4B21", "PMZ3E17"])
def test_vei_15_indisponivel_direto_de_alugado_ou_manutencao_continua_recusado(
    moto, frota, placa
) -> None:
    """A ida a `indisponivel` aberta para o "sem preço" não vira um bloqueio de alugado ou de
    veículo na oficina: o pedido direto continua 409 `transicao_veiculo`."""
    veiculo = frota.veiculos[placa]
    with pytest.raises(TransicaoInvalida):
        services.bloquear(veiculo, "Retrovisor quebrado")


def test_vei_15_desbloquear_sem_plano(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    services.bloquear(sak, "Pneu furado")
    _desligar_todos(moto, sak)
    resposta = moto.api("Rodrigo").post(f"{VEICULOS}{sak.pk}/desbloquear/", {}, format="json")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEI-15"


def test_vei_15_compra_ligada_conta_como_preco(moto, frota) -> None:
    pop = _pop(moto, frota)
    _put(moto, pop, {"valor_venda_centavos": 1590000, "plano_compra": COMPRA_POP})
    _desligar_todos(moto, pop)
    pop.refresh_from_db()
    assert pop.status == "disponivel"


# --- Preço agendado (VEI-12, ADR 0041, item 1) ---


def test_vei_12_preco_agendado_e_consolidacao(moto, frota, relogio) -> None:
    sak = frota.veiculos["SAK1D39"]
    agendado = {"valor_centavos": 34900, "a_partir_de": "2026-10-08"}
    resposta = _put(moto, sak, {"planos": [{"tipo": "semanal", "agendado": agendado}]})
    assert resposta.status_code == 200, resposta.json()
    semanal = resposta.json()["planos"][1]
    assert semanal["valor_centavos"] == 32900
    assert semanal["agendado"]["valor_centavos"] == 34900

    # Na data, a leitura já usa o novo, antes da rotina.
    relogio.em("2026-10-08 00:01")
    semanal = selectors.precos_do_veiculo(sak, moto.pessoas["Mariana"])["planos"][1]
    assert (semanal["valor_centavos"], semanal["agendado"]) == (34900, None)
    assert _plano(sak, "semanal").valor_em(date(2026, 10, 8)) == 34900

    assert services.consolidar_precos_agendados(date(2026, 10, 8)) == {"planos": 1, "veiculos": 1}
    plano = _plano(sak, "semanal")
    assert (plano.valor_centavos, plano.agendado_para) == (34900, None)
    linha = HistoricoPrecoVeiculo.objects.get(
        veiculo=sak, origem="agendamento", campo="valor_centavos"
    )
    assert (linha.de, linha.para, linha.por_id) == (32900, 34900, None)
    assert services.consolidar_precos_agendados(date(2026, 10, 8)) == {"planos": 0, "veiculos": 0}


def test_vei_12_agendado_so_a_partir_de_amanha(moto, frota) -> None:
    sak = frota.veiculos["SAK1D39"]
    agendado = {"valor_centavos": 34900, "a_partir_de": "2026-10-07"}
    resposta = _put(moto, sak, {"planos": [{"tipo": "semanal", "agendado": agendado}]})
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["planos.0.agendado.a_partir_de"] == [
        services.MENSAGEM_AGENDADO_DATA
    ]


def test_vei_12_consolidacao_liga_plano_que_so_tinha_o_agendado(moto, frota) -> None:
    """ADR 0041, item 3: o plano migrado só com preço futuro nasce desligado e liga no dia."""
    from apps.veiculos.models import Categoria

    futura = Categoria.objects.create(nome="Só futuro", tipo_veiculo="moto")
    PrecoCategoria.objects.create(
        categoria=futura,
        vigente_desde=date(2099, 1, 1),  # a migração usa a data real, não o relógio do domínio
        diaria_centavos=5990,
        semanal_centavos=34900,
        mensal_centavos=129000,
        caucao_centavos=35000,
    )
    novo = criar_veiculo(904, futura, frota.centro)
    _migracao().copiar(django_apps, None)
    assert not services.tem_plano_ligado(novo)
    services.consolidar_precos_agendados(date(2099, 1, 1))
    semanal = _plano(novo, "semanal")
    assert (semanal.ligado, semanal.valor_centavos, semanal.caucao_centavos) == (True, 34900, 35000)


# --- Isolamento entre empresas ---


def test_vei_12_planos_da_empresa_a_nao_aparecem_na_b(moto, frota) -> None:
    assert PlanoVeiculo.objects.exists()
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not PlanoVeiculo.objects.exists()
    assert not RegrasVeiculo.objects.exists()
    assert not HistoricoPrecoVeiculo.objects.exists()
