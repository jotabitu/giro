"""T-420 · Locação com intenção de compra, parte de locações (`docs/qa/criterios/T-420.md`).

Regras: LOC-16 (nova), LOC-04, LOC-05, LOC-10, LOC-12, LOC-15, IMP-04; ADR 0037. Valores de
teste, não do seed (preparação dos critérios): a Moto Rápida, Filial Centro; a Mariana cadastra
o plano "Compra Street 24 meses" (Street 150–160, mensal, 24 parcelas de R$ 1.190,00) e publica o
modelo "Locação com intenção de compra"; caução da Street R$ 300,00; o Lucas aluga o SAK-1D39 com
início em 10 nov 2026, 10:00. A venda da quitação (VEN-11) é do Backend 2: aqui, `compra.venda`
vem do fornecedor `compra_venda` (ADR 0015) e é nula sem ele.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, connection, transaction

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.contratos import marcadores, prontos
from apps.contratos.models import ModeloContrato
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber, Reembolso
from apps.locacoes import contrato as contrato_da_locacao
from apps.locacoes import selectors, services
from apps.locacoes.models import Locacao, PlanoCompra
from apps.plataforma.models import Empresa
from apps.veiculos.models import Veiculo
from apps.vendas import leituras as vendas_leituras
from comum import estados, eventos, leituras
from comum import relogio as relogio_do_giro
from comum.erros import Conflito

from .test_t015_locacoes import LISTA, SIMULAR, Cenario, _assinar, _vistoriar
from .test_t015_locacoes import cenario as cenario

PLANOS = "/api/planos-compra/"
FUSO = ZoneInfo("America/Sao_Paulo")
INICIO = "2026-11-10T13:00:00Z"  # 10 nov 2026, 10:00 em Fortaleza
STREET = "Street 150–160"
NAO_RENOVA = "A locação com intenção de compra não se renova."
NAO_TROCA = "A locação com intenção de compra não troca de veículo. Encerre esta e abra outra."
SEM_ATRASO = (
    "Esta locação não tem parcela atrasada. Para encerrar a pedido do cliente, use Cancelar "
    "locação."
)
SEM_MODELO = "Publique o modelo de contrato da locação com intenção de compra antes de confirmar."


def _em(cenario: Cenario, relogio: Any, quando: str) -> None:
    relogio.em(quando)
    cenario.moto._tokens.clear()


@pytest.fixture
def compra(cenario: Cenario, relogio, relogio_jwt) -> Cenario:
    """Em 10 nov 2026, 09:00, com o modelo da compra publicado."""
    _em(cenario, relogio, "2026-11-10 09:00")
    ModeloContrato.objects.create(
        nome="Locação com intenção de compra",
        finalidade="locacao_compra",
        texto=prontos.TEXTO_COMPRA,
        publicado=True,
        publicado_em=relogio_do_giro.agora(),
    )
    return cenario


def _criar_plano(cenario: Cenario, **campos: Any) -> dict[str, Any]:
    corpo = {
        "nome": "Compra Street 24 meses",
        "categoria_id": cenario.frota.categorias[STREET].pk,
        "periodicidade": "mensal",
        "parcelas": 24,
        "valor_parcela_centavos": 119000,
        **campos,
    }
    resposta = cenario.moto.api("Mariana").post(PLANOS, corpo, format="json")
    assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


@pytest.fixture
def plano(compra: Cenario) -> dict[str, Any]:
    return _criar_plano(compra)


def _corpo(cenario: Cenario, plano_id: int, **campos: Any) -> dict[str, Any]:
    return {
        "tipo": "intencao_compra",
        "plano_compra_id": plano_id,
        "cliente_id": cenario.cliente("Lucas").pk,
        "veiculo_id": cenario.sak.pk,
        "inicio": INICIO,
        "forma_pagamento": "pix",
        **campos,
    }


def _confirmada(cenario: Cenario, plano_id: int, **campos: Any) -> Locacao:
    api = cenario.moto.api("Bruna")
    criada = api.post(LISTA, _corpo(cenario, plano_id, **campos), format="json")
    assert criada.status_code == 201, criada.json()
    confirmada = api.post(f"{LISTA}{criada.json()['id']}/confirmar/", {}, format="json")
    assert confirmada.status_code == 200, confirmada.json()
    return Locacao.objects.get(pk=criada.json()["id"])


def _contas(locacao: Locacao, tipo: str = "parcela") -> list[ContaReceber]:
    return list(
        ContaReceber.objects.filter(
            origem_tipo="locacao", origem_id=locacao.pk, tipo=tipo
        ).order_by("numero_parcela", "id")
    )


def _pagar(locacao: Locacao, *numeros: int, caucao: bool = False) -> None:
    for conta in ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk):
        if conta.status != "aberta":
            continue
        if (conta.tipo == "parcela" and conta.numero_parcela in numeros) or (
            caucao and conta.tipo == "caucao"
        ):
            financeiro.marcar_paga(conta, forma="pix")


def _retirada(locacao: Locacao) -> Locacao:
    """Vistoria de saída, contrato assinado e o 1º pagamento (parcela 1 e caução)."""
    _vistoriar(locacao.pk)
    _assinar(locacao.pk)
    _pagar(locacao, 1, caucao=True)
    locacao.refresh_from_db()
    assert locacao.status == "ativa"
    return locacao


@pytest.fixture
def ativa(compra: Cenario, plano: dict[str, Any]) -> Locacao:
    return _retirada(_confirmada(compra, plano["id"]))


def _compra(cenario: Cenario, locacao: Locacao, quem: str = "Bruna") -> dict[str, Any]:
    return dict(cenario.detalhe(locacao.pk, quem)["compra"])


# --- Planos de compra (tela Precos) ---


def test_loc_16_plano_de_compra_na_tela_precos(compra: Cenario, plano: dict[str, Any]) -> None:
    """A Mariana cadastra o plano; a lista traz a caução vigente da categoria e a última parcela
    já abatida, para a tela mostrar sem conta. Quem cria locação lê; só o administrador grava."""
    assert {k: plano[k] for k in ("nome", "periodicidade", "parcelas", "ativo")} == {
        "nome": "Compra Street 24 meses",
        "periodicidade": "mensal",
        "parcelas": 24,
        "ativo": True,
    }
    assert plano["categoria"]["nome"] == STREET
    assert (plano["valor_parcela_centavos"], plano["caucao_centavos"]) == (119000, 30000)
    assert plano["ultima_parcela_centavos"] == 89000
    lista = compra.moto.api("Bruna").get(PLANOS, {"ativo": "true"}).json()["resultados"]
    assert [p["nome"] for p in lista] == ["Compra Street 24 meses"]
    corpo = {**plano, "nome": "Outro", "categoria_id": plano["categoria"]["id"]}
    assert compra.moto.api("Bruna").post(PLANOS, corpo, format="json").status_code == 403
    assert compra.moto.api("Rodrigo").post(PLANOS, corpo, format="json").status_code == 403
    assert compra.moto.api("João").get(PLANOS).status_code == 403  # vistoriador
    assert EventoAuditoria.objects.filter(acao="plano_compra.criar").exists()


@pytest.mark.parametrize(
    ("campos", "campo"),
    [
        ({"parcelas": 1}, "parcelas"),
        ({"parcelas": 261}, "parcelas"),
        ({"valor_parcela_centavos": 0}, "valor_parcela_centavos"),
        ({"nome": "compra street 24 meses"}, "nome"),
    ],
)
def test_loc_16_plano_de_compra_recusas(
    compra: Cenario, plano: dict[str, Any], campos: dict[str, Any], campo: str
) -> None:
    corpo = {
        "nome": "Outro plano",
        "categoria_id": plano["categoria"]["id"],
        "periodicidade": "mensal",
        "parcelas": 24,
        "valor_parcela_centavos": 119000,
        **campos,
    }
    resposta = compra.moto.api("Mariana").post(PLANOS, corpo, format="json")
    assert resposta.status_code == 400, resposta.json()
    assert campo in resposta.json()["campos"]


def test_loc_16_plano_desativado_sai_da_nova_locacao(
    compra: Cenario, plano: dict[str, Any]
) -> None:
    api = compra.moto.api("Mariana")
    assert api.post(f"{PLANOS}{plano['id']}/desativar/").json()["ativo"] is False
    assert api.get(PLANOS, {"ativo": "true"}).json()["resultados"] == []
    assert len(api.get(PLANOS).json()["resultados"]) == 1
    resposta = compra.moto.api("Bruna").post(SIMULAR, _corpo(compra, plano["id"]), format="json")
    assert resposta.status_code == 400
    assert "plano_compra_id" in resposta.json()["campos"]


def test_loc_16_isolamento_do_plano_entre_empresas(compra: Cenario, plano: dict[str, Any]) -> None:
    """O plano da empresa A não aparece na empresa B."""
    assert PlanoCompra.objects.count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not PlanoCompra.objects.exists()
    assert not Locacao.objects.filter(tipo="intencao_compra").exists()


# --- Criar e confirmar (CA-420-01 a 04) ---


def test_loc_16_ca_420_01_simulacao_plano_e_parcelas(
    compra: Cenario, plano: dict[str, Any]
) -> None:
    resposta = compra.moto.api("Bruna").post(SIMULAR, _corpo(compra, plano["id"]), format="json")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert datetime.fromisoformat(corpo["fim_previsto"]) == datetime(2028, 11, 10, 10, tzinfo=FUSO)
    assert corpo["linhas"] == [
        {"rotulo": "24 parcelas mensais × R$ 1.190,00", "valor_centavos": 2856000},
        {"rotulo": "Caução (abatida na última parcela)", "valor_centavos": 30000},
        {"rotulo": "Última parcela", "valor_centavos": 89000},
    ]
    assert (corpo["valor_periodo_centavos"], corpo["hoje_na_retirada_centavos"]) == (
        119000,
        149000,
    )
    assert corpo["texto_retirada"] == "Na retirada: primeira parcela mais caução."
    previstas = corpo["parcelas_previstas"]
    assert len(previstas) == 24
    assert previstas[0] == {"numero": 1, "vencimento": "2026-11-10", "valor_centavos": 119000}
    assert previstas[22] == {"numero": 23, "vencimento": "2028-09-10", "valor_centavos": 119000}
    assert previstas[23] == {"numero": 24, "vencimento": "2028-10-10", "valor_centavos": 89000}
    assert corpo["compra"] == {
        "parcelas_total": 24,
        "valor_parcela_centavos": 119000,
        "ultima_parcela_centavos": 89000,
        "sobra_caucao_centavos": 0,
    }
    assert corpo["caucao_centavos"] == 30000
    assert corpo["avisos"] == [] or all(a["codigo"] != "LOC-16" for a in corpo["avisos"])


def test_loc_16_ca_420_01_confirmar_com_o_plano(compra: Cenario, plano: dict[str, Any]) -> None:
    """Confirmada: 23 parcelas de R$ 1.190,00 e a 24ª de R$ 890,00, de 10 nov 2026 a 10 out
    2028; a caução de R$ 300,00; o fim previsto em 10 nov 2028, 10:00; a moto reservada; o
    plano congelado na locação; sem andamento antes do 1º pagamento."""
    locacao = _confirmada(compra, plano["id"])
    assert (locacao.status, locacao.tipo) == ("aguardando_retirada", "intencao_compra")
    assert (locacao.compra_parcelas, locacao.compra_valor_parcela_centavos) == (24, 119000)
    assert (locacao.periodicidade, locacao.periodos, locacao.desconto_pct) == ("mensal", 24, 0)
    assert locacao.fim_previsto == datetime(2028, 11, 10, 10, tzinfo=FUSO)
    parcelas = _contas(locacao)
    assert [p.valor_centavos for p in parcelas] == [119000] * 23 + [89000]
    assert (parcelas[0].vencimento, parcelas[-1].vencimento) == (
        date(2026, 11, 10),
        date(2028, 10, 10),
    )
    assert {p.total_parcelas for p in parcelas} == {24}
    [caucao] = _contas(locacao, "caucao")
    assert (caucao.valor_centavos, caucao.observacao) == (30000, "Abatida na última parcela")
    assert Veiculo.objects.get(pk=compra.sak.pk).status == "reservado"

    detalhe = compra.detalhe(locacao.pk)
    assert (detalhe["tipo"], detalhe["tipo_rotulo"]) == (
        "intencao_compra",
        "Com intenção de compra",
    )
    assert detalhe["compra"] == {
        "plano": {"id": plano["id"], "nome": "Compra Street 24 meses"},
        "parcelas_total": 24,
        "parcelas_pagas": 0,
        "valor_parcela_centavos": 119000,
        "ultima_parcela_centavos": 89000,
        "sobra_caucao_centavos": 0,
        "andamento": None,
        "falta_para_quitar": [],
        "quitada_em": None,
        "venda": None,
    }
    linha = compra.moto.api("Bruna").get(LISTA, {"tipo": "intencao_compra"}).json()["resultados"]
    assert [(x["codigo"], x["tipo_rotulo"]) for x in linha] == [
        (locacao.codigo, "Com intenção de compra")
    ]
    assert compra.moto.api("Bruna").get(LISTA, {"tipo": "comum"}).json()["resultados"] == []


@pytest.mark.parametrize(
    "campos",
    [
        {"desconto_pct": "5.00"},
        {"extras": [{"extra_id": 1, "quantidade": 1}]},
        {"plano_especial_id": 1},
        {"parcelamento_mensal": "quatro_semanais"},
        {"fim_previsto": "2027-11-10T13:00:00Z"},
        {"periodicidade": "semanal"},
        {"periodos": 12},
    ],
)
def test_loc_16_ca_420_02_sem_desconto_e_sem_extras(
    compra: Cenario, plano: dict[str, Any], campos: dict[str, Any]
) -> None:
    resposta = compra.moto.api("Bruna").post(
        SIMULAR, _corpo(compra, plano["id"], **campos), format="json"
    )
    assert resposta.status_code == 400, resposta.json()
    [campo] = campos
    assert resposta.json()["campos"][campo] == [
        "A locação com intenção de compra usa o valor do plano."
    ]


def test_loc_16_ca_420_02_periodicidade_igual_a_do_plano_passa(
    compra: Cenario, plano: dict[str, Any]
) -> None:
    corpo = _corpo(compra, plano["id"], periodicidade="mensal", periodos=24, desconto_pct="0.00")
    assert compra.moto.api("Bruna").post(SIMULAR, corpo, format="json").status_code == 200


def test_loc_16_veiculo_fora_da_categoria_do_plano(compra: Cenario, plano: dict[str, Any]) -> None:
    urbana = compra.veiculo("Urbana 110–125")
    resposta = compra.moto.api("Bruna").post(
        SIMULAR, _corpo(compra, plano["id"], veiculo_id=urbana.pk), format="json"
    )
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["veiculo_id"] == ["O veículo não é da categoria do plano."]


def test_loc_16_ca_420_03_sem_modelo_publicado(
    cenario: Cenario,
    relogio,
    relogio_jwt,
) -> None:
    """Sem o modelo da compra: a simulação avisa, a confirmação responde 422 `LOC-16` com o
    atalho, e nada muda. A comum continua confirmando com o modelo dela."""
    _em(cenario, relogio, "2026-11-10 09:00")
    plano = _criar_plano(cenario)
    api = cenario.moto.api("Bruna")
    simulada = api.post(SIMULAR, _corpo(cenario, plano["id"]), format="json").json()
    assert {"codigo": "LOC-16", "mensagem": SEM_MODELO, "link": "/admin/contratos"} in simulada[
        "avisos"
    ]
    criada = api.post(LISTA, _corpo(cenario, plano["id"]), format="json").json()
    resposta = api.post(f"{LISTA}{criada['id']}/confirmar/", {}, format="json")
    assert resposta.status_code == 422, resposta.json()
    assert (resposta.json()["codigo"], resposta.json()["mensagem"]) == ("LOC-16", SEM_MODELO)
    assert resposta.json()["detalhes"] == {"link": "/admin/contratos"}
    assert Locacao.objects.get(pk=criada["id"]).status == "rascunho"
    assert not ContaReceber.objects.exists()

    comum = cenario.confirmada(inicio=INICIO, periodos=1)
    assert comum["status"] == "aguardando_retirada"


def test_loc_16_ca_420_04_plano_congelado(compra: Cenario, plano: dict[str, Any]) -> None:
    locacao = _confirmada(compra, plano["id"])
    editado = compra.moto.api("Mariana").patch(
        f"{PLANOS}{plano['id']}/", {"valor_parcela_centavos": 125000}, format="json"
    )
    assert editado.status_code == 200, editado.json()
    assert editado.json()["valor_parcela_centavos"] == 125000
    assert _compra(compra, locacao)["valor_parcela_centavos"] == 119000
    assert {p.valor_centavos for p in _contas(locacao)[:-1]} == {119000}
    outra = compra.veiculo(STREET, exceto=(compra.sak.placa,))
    nova = compra.moto.api("Bruna").post(
        SIMULAR, _corpo(compra, plano["id"], veiculo_id=outra.pk), format="json"
    )
    assert nova.json()["valor_periodo_centavos"] == 125000
    assert EventoAuditoria.objects.filter(acao="plano_compra.editar").exists()


def test_loc_16_check_do_tipo_no_banco(compra: Cenario, plano: dict[str, Any]) -> None:
    """`locacao_tipo_campos`: a comum não leva plano de compra; a compra não leva desconto."""
    locacao = _confirmada(compra, plano["id"])
    with pytest.raises(IntegrityError), transaction.atomic():
        Locacao.objects.filter(pk=locacao.pk).update(desconto_pct="5.00")
    with pytest.raises(IntegrityError), transaction.atomic():
        Locacao.objects.filter(pk=locacao.pk).update(tipo="comum")
    with pytest.raises(IntegrityError), transaction.atomic():
        Locacao.objects.filter(pk=locacao.pk).update(compra_parcelas=None)


def test_loc_16_tipo_muda_no_rascunho(compra: Cenario, plano: dict[str, Any]) -> None:
    """O rascunho da compra vira comum pelo PATCH, e os campos da compra saem."""
    api = compra.moto.api("Bruna")
    criada = api.post(LISTA, _corpo(compra, plano["id"]), format="json").json()
    assert criada["compra"]["parcelas_total"] == 24
    comum = {"tipo": "comum", "periodicidade": "semanal", "periodos": 2, "plano_compra_id": None}
    resposta = api.patch(f"{LISTA}{criada['id']}/", comum, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert (resposta.json()["tipo"], resposta.json()["compra"]) == ("comum", None)
    locacao = Locacao.objects.get(pk=criada["id"])
    assert (locacao.plano_compra_id, locacao.compra_parcelas) == (None, None)


# --- Retirada e andamento (CA-420-05, 06) ---


def test_loc_16_ca_420_05_retirada_e_andamento(compra: Cenario, ativa: Locacao) -> None:
    assert Veiculo.objects.get(pk=compra.sak.pk).status == "alugado"
    detalhe = compra.detalhe(ativa.pk)
    assert detalhe["tipo_rotulo"] == "Com intenção de compra"
    assert detalhe["compra"]["parcelas_pagas"] == 1
    assert detalhe["compra"]["andamento"] == "Parcela 1 de 24 · faltam 23 para a transferência"
    assert detalhe["devolucao"]["prevista_para"] is None
    assert detalhe["devolucao"]["aviso_atraso"] is None
    assert detalhe["sinais"]["devolve_hoje"] is False


def test_loc_16_ca_420_06_sem_renovacao_e_sem_troca(compra: Cenario, ativa: Locacao) -> None:
    acoes = compra.detalhe(ativa.pk)["acoes"]
    assert (acoes["renovar"], acoes["trocar_veiculo"]) == (False, False)
    api = compra.moto.api("Bruna")
    for caminho in ("renovar/simular/", "renovar/"):
        resposta = api.post(f"{LISTA}{ativa.pk}/{caminho}", {"periodos": 1}, format="json")
        assert resposta.status_code == 409, caminho
        assert (resposta.json()["codigo"], resposta.json()["mensagem"]) == ("LOC-16", NAO_RENOVA)
    outra = compra.veiculo(STREET, exceto=(compra.sak.placa,))
    troca = api.post(
        f"{LISTA}{ativa.pk}/trocar-veiculo/",
        {"veiculo_novo_id": outra.pk, "motivo": "Pneu furado"},
        format="json",
    )
    assert troca.status_code == 409, troca.json()
    assert (troca.json()["codigo"], troca.json()["mensagem"]) == ("LOC-16", NAO_TROCA)


# --- Atraso e encerramento (CA-420-08 a 10, 19) ---


def test_loc_16_ca_420_19_encerrar_por_atraso_sem_parcela_atrasada(
    compra: Cenario, ativa: Locacao
) -> None:
    assert compra.detalhe(ativa.pk, "Rodrigo")["acoes"]["encerrar_por_atraso"] is False
    resposta = compra.moto.api("Rodrigo").post(
        f"{LISTA}{ativa.pk}/encerrar-por-atraso/", {"motivo": "Atraso"}, format="json"
    )
    assert resposta.status_code == 409
    assert (resposta.json()["codigo"], resposta.json()["mensagem"]) == ("LOC-16", SEM_ATRASO)
    ativa.refresh_from_db()
    assert (ativa.status, ativa.cancelamento_status, ativa.encerrada_por_atraso) == (
        "ativa",
        "",
        False,
    )


def test_loc_16_ca_420_08_encerrar_por_atraso(
    compra: Cenario,
    ativa: Locacao,
    relogio,
) -> None:
    """Em 26 dez, com a parcela 2 (10 dez) sem pagar, o Rodrigo encerra por atraso, com
    motivo, sem APR-02. Sem multa nem crédito; as parcelas 3 a 24 saem na devolução; o atraso
    da LOC-10 só corre depois do dia do encerramento."""
    _em(compra, relogio, "2026-12-26 10:00")
    assert compra.detalhe(ativa.pk, "Rodrigo")["acoes"]["encerrar_por_atraso"] is True
    assert compra.detalhe(ativa.pk, "Bruna")["acoes"]["encerrar_por_atraso"] is False
    caminho = f"{LISTA}{ativa.pk}/encerrar-por-atraso/"
    corpo = {"motivo": "Parcela 2 com 16 dias de atraso"}
    assert compra.moto.api("Bruna").post(caminho, corpo, format="json").status_code == 403
    sem_motivo = compra.moto.api("Rodrigo").post(caminho, {"motivo": ""}, format="json")
    assert sem_motivo.status_code == 400

    resposta = compra.moto.api("Rodrigo").post(caminho, corpo, format="json")
    assert resposta.status_code == 200, resposta.json()
    cancelamento = resposta.json()["cancelamento"]
    assert {k: cancelamento[k] for k in ("status", "pedido_aprovacao_id", "por_atraso")} == {
        "status": "aprovado",
        "pedido_aprovacao_id": None,
        "por_atraso": True,
    }
    assert (cancelamento["multa_centavos"], cancelamento["devolver_centavos"]) == (0, 0)
    assert cancelamento["data"] == "2026-12-26"
    assert resposta.json()["acoes"]["registrar_devolucao"] is True
    assert resposta.json()["acoes"]["encerrar_por_atraso"] is False
    assert resposta.json()["devolucao"]["prevista_para"] is not None
    evento = EventoAuditoria.objects.get(objeto_id=ativa.pk, acao="locacao.encerrar_por_atraso")
    assert evento.regra == "LOC-16"
    assert not PedidoAprovacao.objects.exists()

    de_novo = compra.moto.api("Rodrigo").post(caminho, corpo, format="json")
    assert (de_novo.status_code, de_novo.json()["codigo"]) == (409, "cancelamento_em_andamento")

    ativa.refresh_from_db()
    assert services.encerramento_antecipado_vale(ativa, relogio_do_giro.agora())
    na_devolucao = services.encerramento_na_devolucao(ativa, relogio_do_giro.agora())
    assert (na_devolucao.multa_centavos, na_devolucao.credito_centavos) == (0, 0)
    simulado = services.calcular_encerramento(ativa, date(2026, 12, 26))
    assert simulado.parcelas_canceladas_centavos == 21 * 119000 + 89000  # parcelas 3 a 24
    assert simulado.credito_liquido_centavos == 0
    no_dia = datetime(2026, 12, 26, 18, tzinfo=FUSO)
    assert services.calcular_atraso(ativa, no_dia)["dias"] == 0
    assert services.calcular_atraso(ativa, datetime(2026, 12, 28, 12, tzinfo=FUSO))["dias"] > 0
    assert services.marcar_devolucoes_atrasadas(no_dia) == 0
    assert services.marcar_devolucoes_atrasadas(datetime(2026, 12, 28, 12, tzinfo=FUSO)) == 1


def test_loc_16_ca_420_09_encerramento_pedido_pelo_cliente(
    compra: Cenario, ativa: Locacao, relogio
) -> None:
    """Com tudo em dia, a simulação do encerramento não tem multa, crédito nem devolução, e
    avisa que o pago fica como aluguel."""
    _pagar(ativa, 2, 3)
    _em(compra, relogio, "2027-01-15 10:00")
    resposta = compra.moto.api("Rodrigo").post(
        f"{LISTA}{ativa.pk}/cancelamento/simular/", {}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["multa_centavos"], corpo["devolver_centavos"], corpo["cobrar_centavos"]) == (
        0,
        0,
        0,
    )
    assert corpo["credito_semanas"] == {"semanas": 0, "valor_centavos": 0}
    assert corpo["credito_dias"] == {"dias": 0, "valor_centavos": 0}
    assert corpo["parcelas_canceladas_centavos"] == 20 * 119000 + 89000  # 4 a 24
    assert corpo["avisos"] == [
        {"codigo": "LOC-16", "mensagem": "O que foi pago fica como aluguel do período usado."}
    ]
    cancelado = compra.moto.api("Rodrigo").post(
        f"{LISTA}{ativa.pk}/cancelar/", {"motivo": "Pedido do cliente"}, format="json"
    )
    assert cancelado.status_code == 200, cancelado.json()
    assert cancelado.json()["cancelamento"]["por_atraso"] is False
    assert cancelado.json()["cancelamento"]["multa_centavos"] == 0
    assert cancelado.json()["acoes"]["registrar_devolucao"] is True


def test_loc_16_ca_420_10_fim_previsto_sem_devolucao(compra: Cenario, ativa: Locacao) -> None:
    """No fim previsto + 1 dia, a locação continua ativa, sem diária de atraso, sem
    `devolucao_atrasada`, sem lembrete de devolução e fora de "Devolvem hoje"."""
    ativa.refresh_from_db()
    depois = datetime(2028, 11, 11, 12, tzinfo=FUSO)
    assert services.marcar_devolucoes_atrasadas(depois) == 0
    assert Locacao.objects.get(pk=ativa.pk).status == "ativa"
    assert services.calcular_atraso(ativa, depois) == {
        "dias": 0,
        "valor_centavos": 0,
        "devolucao_considerada_em": depois,
    }
    assert services.lembrar_devolucoes(datetime(2028, 11, 10, 8, tzinfo=FUSO)) == 0
    assert compra.detalhe(ativa.pk)["acoes"]["registrar_devolucao"] is False


# --- Quitação (CA-420-11, 13 a 15, 18) ---


@pytest.fixture
def quitadas() -> Any:
    recebidos: list[dict[str, Any]] = []

    def assinante(**dados: Any) -> None:
        recebidos.append(dados)

    eventos.assinar("locacoes.locacao_quitada", assinante)
    yield recebidos
    eventos.remover_assinante("locacoes.locacao_quitada", assinante)


def test_loc_16_ca_420_11_15_18_quitar(
    compra: Cenario, ativa: Locacao, quitadas: list[dict[str, Any]]
) -> None:
    """O Lucas paga as parcelas 2 a 23 de uma vez, antes do vencimento (CA-420-15): "Parcela
    23 de 24 · falta 1". Paga a 24ª, a locação quita na hora, pelo Sistema: `encerrada`, sem
    vistoria nem acerto, a caução não volta, e sai o evento para `vendas` com os 7 campos."""
    _pagar(ativa, *range(2, 24))
    assert _compra(compra, ativa)["andamento"] == "Parcela 23 de 24 · falta 1 para a transferência"
    assert quitadas == []

    _pagar(ativa, 24)
    ativa.refresh_from_db()
    assert (ativa.status, ativa.quitada_em) == ("encerrada", relogio_do_giro.agora())
    assert ativa.devolvida_em is None
    evento = EventoAuditoria.objects.get(objeto_id=ativa.pk, acao="locacao.quitar")
    assert (evento.ator_tipo, evento.ator_nome, evento.regra) == ("sistema", "Sistema", "LOC-16")
    assert quitadas == [
        {
            "locacao_id": ativa.pk,
            "codigo": ativa.codigo,
            "filial_id": ativa.filial_id,
            "cliente_id": ativa.cliente_id,
            "veiculo_id": ativa.veiculo_id,
            "vendedor_id": compra.pessoas["Bruna"].pk,
            "quitada_em": ativa.quitada_em,
        }
    ]
    [caucao] = _contas(ativa, "caucao")
    assert caucao.status == "paga"
    assert not Reembolso.objects.exists()
    assert not ativa.trechos.filter(fim__isnull=True).exists()
    detalhe = compra.detalhe(ativa.pk)
    assert detalhe["situacao"] == {"codigo": "quitada", "rotulo": "Quitada", "tom": "sucesso"}
    assert detalhe["compra"]["andamento"] == (
        "Quitada em 10/11/2026 · falta a transferência no Detran"
    )
    assert detalhe["acoes"]["registrar_devolucao"] is False
    historico = compra.moto.api("Bruna").get(f"{LISTA}{ativa.pk}/historico/").json()
    assert "Locação quitada" in [i["rotulo"] for i in historico["resultados"]]

    # Idempotente: outro pagamento da locação não quita de novo.
    assert services.quitar_se_pago(ativa.pk) is False
    assert len(quitadas) == 1


def test_loc_16_ca_420_12_venda_da_quitacao_no_detalhe(
    compra: Cenario, ativa: Locacao, django_capture_on_commit_callbacks
) -> None:
    """Com a parte de `vendas` na develop (PR #560), a quitação cria a venda de R$ 0,00, o
    veículo vai para `vendido`, e o detalhe traz `compra.venda` com "Transferência feita" só
    para o gerente."""
    vendas_leituras.registrar()
    with django_capture_on_commit_callbacks(execute=True):
        _pagar(ativa, *range(2, 25))
    assert Veiculo.objects.get(pk=compra.sak.pk).status == "vendido"
    venda = _compra(compra, ativa, "Rodrigo")["venda"]
    assert venda is not None
    assert venda["codigo"].startswith("VEN-")
    assert venda["transferencia"]["pendente"] is True
    assert venda["acoes"] == {"registrar_transferencia": True}
    assert _compra(compra, ativa, "Bruna")["venda"]["acoes"] == {"registrar_transferencia": False}
    assert _compra(compra, ativa)["andamento"] == (
        "Quitada em 10/11/2026 · falta a transferência no Detran"
    )


def test_loc_16_sem_venda_o_bloco_vazio_vira_nulo(compra: Cenario, ativa: Locacao) -> None:
    """`leituras.bloco` devolve `{}` quando o fornecedor não acha venda: `compra.venda` é nulo."""
    vendas_leituras.registrar()
    assert leituras.bloco("locacoes.Locacao", "compra_venda", ativa) == {}
    assert selectors._venda(ativa, compra.pessoas["Rodrigo"]) is None


# --- Revisão de segurança (docs/seguranca/2026-11-12-t420-locacao-com-compra.md) ---


CAUCAO_TRAVADA = (
    "A caução da locação com intenção de compra faz parte da última parcela e não se cancela "
    "nem se renegocia."
)


@pytest.mark.parametrize("status", ["aguardando_retirada", "ativa"])
def test_loc_16_caucao_da_compra_nao_se_cancela_nem_se_renegocia(
    compra: Cenario, plano: dict[str, Any], status: str
) -> None:
    """Padrão do produto (PR #564): 409 `LOC-16` pela rota do financeiro, nos dois estados."""
    locacao = _confirmada(compra, plano["id"])
    if status == "ativa":
        _vistoriar(locacao.pk)
        _assinar(locacao.pk)
        _pagar(locacao, 1)
        services.registrar_retirada(locacao, "Caução amanhã")
    [caucao] = _contas(locacao, "caucao")
    api = compra.moto.api("Rodrigo")
    cancelada = api.post(
        f"/api/financeiro/contas-receber/{caucao.pk}/cancelar/",
        {"motivo": "Dispensada"},
        format="json",
    )
    assert cancelada.status_code == 409, cancelada.json()
    assert (cancelada.json()["codigo"], cancelada.json()["mensagem"]) == ("LOC-16", CAUCAO_TRAVADA)
    with pytest.raises(Conflito):
        financeiro.renegociar(
            [caucao],
            [financeiro.ContaNova(date(2026, 12, 10), 30000)],
            motivo="Acordo",
            usuario=None,
        )
    caucao.refresh_from_db()
    assert caucao.status == "aberta"


def test_loc_16_caucao_da_comum_continua_cancelando(compra: Cenario) -> None:
    comum = compra.confirmada(inicio=INICIO, periodos=1)
    caucao = ContaReceber.objects.get(origem_tipo="locacao", origem_id=comum["id"], tipo="caucao")
    financeiro.cancelar(caucao, motivo="Dispensada")
    caucao.refresh_from_db()
    assert caucao.status == "cancelada"


def test_loc_16_m01_caucao_cancelada_nao_quita_nem_devolve_sobra(compra: Cenario) -> None:
    """M-01: a caução que não entrou (aqui cancelada pela máquina de estados, sem a trava da
    tela, como uma conta de antes dela) não abate nada. Pagas as 103 parcelas do plano semanal,
    a locação não quita e não nasce reembolso; a ficha diz que falta a caução."""
    plano = _criar_plano(
        compra,
        nome="Compra Street 104 semanas",
        periodicidade="semanal",
        parcelas=104,
        valor_parcela_centavos=19900,
    )
    locacao = _confirmada(compra, plano["id"])
    _vistoriar(locacao.pk)
    _assinar(locacao.pk)
    _pagar(locacao, 1)
    services.registrar_retirada(locacao, "Cliente sem a caução hoje")
    [caucao] = _contas(locacao, "caucao")
    estados.transicionar(caucao, "cancelada", motivo="Dispensada", acao="conta_receber.cancelar")
    _pagar(locacao, *range(2, 104))
    locacao.refresh_from_db()
    assert (locacao.status, locacao.quitada_em) == ("ativa", None)
    assert not Reembolso.objects.exists()
    bloco = _compra(compra, locacao)
    assert bloco["parcelas_pagas"] == 104
    assert bloco["falta_para_quitar"] == [
        {"conta_id": None, "rotulo": "Caução não paga", "valor_centavos": 30000}
    ]


def test_loc_16_m01_caucao_paga_depois_quita(compra: Cenario, plano: dict[str, Any]) -> None:
    """A caução em aberto segura a quitação; paga por último, a locação quita."""
    locacao = _confirmada(compra, plano["id"])
    _vistoriar(locacao.pk)
    _assinar(locacao.pk)
    _pagar(locacao, 1)
    services.registrar_retirada(locacao, "Caução amanhã")
    _pagar(locacao, *range(2, 25))
    locacao.refresh_from_db()
    assert locacao.quitada_em is None
    _pagar(locacao, caucao=True)
    locacao.refresh_from_db()
    assert locacao.status == "encerrada" and locacao.quitada_em is not None


def test_loc_16_m02_parcela_renegociada_e_paga_quita(compra: Cenario, ativa: Locacao) -> None:
    """M-02: a 24ª renegociada em duas contas, que nascem com os números 1 e 2. Pagas as duas,
    a locação quita (conta pela conta original, não pelo número)."""
    _pagar(ativa, *range(2, 24))
    [ultima] = [c for c in _contas(ativa) if c.numero_parcela == 24 and c.nasceu_de_id is None]
    novas = financeiro.renegociar(
        [ultima],
        [
            financeiro.ContaNova(date(2028, 10, 10), 44500),
            financeiro.ContaNova(date(2028, 11, 10), 44500),
        ],
        motivo="Acordo",
        usuario=None,
    )
    assert sorted(c.numero_parcela or 0 for c in novas) == [1, 2]
    financeiro.marcar_paga(novas[0], forma="pix")
    ativa.refresh_from_db()
    assert ativa.quitada_em is None
    assert services.parcelas_pagas(ativa) == 23
    financeiro.marcar_paga(novas[1], forma="pix")
    ativa.refresh_from_db()
    assert services.parcelas_pagas(ativa) == 24
    assert (ativa.status, ativa.quitada_em is not None) == ("encerrada", True)


def test_loc_16_m02_parcela_estornada_volta_a_dever(compra: Cenario, ativa: Locacao) -> None:
    """A parcela estornada não conta até a conta reaberta ser paga."""
    _pagar(ativa, 2)
    [segunda] = [c for c in _contas(ativa) if c.numero_parcela == 2]
    from apps.financeiro.selectors import paga_de_vez

    assert paga_de_vez(segunda)
    segunda.estornada_em = relogio_do_giro.agora()
    segunda.save(update_fields=["estornada_em"])
    reaberta = ContaReceber.objects.create(
        filial_id=segunda.filial_id,
        cliente_id=segunda.cliente_id,
        tipo="parcela",
        numero_parcela=2,
        vencimento=segunda.vencimento,
        valor_centavos=segunda.valor_centavos,
        estorno_de=segunda,
        origem_tipo="locacao",
        origem_id=ativa.pk,
        origem_codigo=ativa.codigo,
    )
    assert services.parcelas_pagas(ativa) == 1
    financeiro.marcar_paga(reaberta, forma="pix")
    assert services.parcelas_pagas(ativa) == 2


def test_loc_16_b01_quitacao_fecha_o_pedido_de_cancelamento(
    compra: Cenario, ativa: Locacao
) -> None:
    """B-01: o pedido APR-02 aberto pela Bruna é fechado na quitação; depois dela, um pedido
    novo é recusado."""
    pedido = compra.moto.api("Bruna").post(
        f"{LISTA}{ativa.pk}/cancelar/", {"motivo": "Cliente quer sair"}, format="json"
    )
    assert pedido.status_code == 202, pedido.json()
    _pagar(ativa, *range(2, 25))
    ativa.refresh_from_db()
    assert ativa.status == "encerrada"
    assert ativa.cancelamento_status == "cancelado"
    assert not PedidoAprovacao.objects.filter(status="pendente").exists()
    de_novo = compra.moto.api("Bruna").post(
        f"{LISTA}{ativa.pk}/cancelar/", {"motivo": "De novo"}, format="json"
    )
    assert de_novo.status_code == 409
    assert not PedidoAprovacao.objects.filter(status="pendente").exists()


@pytest.mark.parametrize("data", ["2026-12-27", "2028-12-26", "2026-12-20", "2026-11-09"])
def test_loc_16_b02_encerrar_por_atraso_so_hoje(
    compra: Cenario, ativa: Locacao, relogio, data: str
) -> None:
    """B-02, padrão do produto (PR #564): a data é sempre hoje; outra, 400, e nada muda."""
    _em(compra, relogio, "2026-12-26 10:00")
    resposta = compra.moto.api("Rodrigo").post(
        f"{LISTA}{ativa.pk}/encerrar-por-atraso/",
        {"motivo": "Atraso", "data": data},
        format="json",
    )
    assert resposta.status_code == 400, resposta.json()
    assert resposta.json()["campos"]["data"] == ["O encerramento por atraso vale a partir de hoje."]
    ativa.refresh_from_db()
    assert (ativa.cancelamento_status, ativa.encerrada_por_atraso) == ("", False)


def test_loc_16_b02_encerrar_por_atraso_com_a_data_de_hoje(
    compra: Cenario, ativa: Locacao, relogio
) -> None:
    _em(compra, relogio, "2026-12-26 10:00")
    resposta = compra.moto.api("Rodrigo").post(
        f"{LISTA}{ativa.pk}/encerrar-por-atraso/",
        {"motivo": "Atraso", "data": "2026-12-26"},
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["cancelamento"]["data"] == "2026-12-26"


def test_loc_16_ca_420_12_16_18_venda_e_transferencia_pelo_fornecedor(
    compra: Cenario, ativa: Locacao, monkeypatch
) -> None:
    """Com o fornecedor de `vendas` (aqui um falso, no formato combinado com o Backend 2),
    `compra.venda` traz a venda e "Transferência feita" só para gerente e administrador; com a
    transferência registrada, o andamento diz a data e o botão sai."""
    estado: dict[str, Any] = {"feita_em": None}

    def montar(locacao: Locacao) -> dict[str, Any] | None:
        if locacao.quitada_em is None:
            return None
        return {
            "id": 18,
            "codigo": "VEN-0178",
            "transferencia": {
                "feita_em": estado["feita_em"],
                "registrada_por": None,
                "pendente": estado["feita_em"] is None,
            },
        }

    atuais = [
        a for a in leituras._anotacoes.get("locacoes.Locacao", []) if a.bloco != "compra_venda"
    ]
    monkeypatch.setitem(
        leituras._anotacoes,
        "locacoes.Locacao",
        [*atuais, leituras.Anotacao("compra_venda", lambda qs: qs, montar)],
    )
    _pagar(ativa, *range(2, 25))
    venda = _compra(compra, ativa, "Rodrigo")["venda"]
    assert (venda["codigo"], venda["transferencia"]["pendente"]) == ("VEN-0178", True)
    assert venda["acoes"] == {"registrar_transferencia": True}
    assert _compra(compra, ativa, "Bruna")["venda"]["acoes"] == {"registrar_transferencia": False}

    estado["feita_em"] = "2026-11-15"
    feita = _compra(compra, ativa, "Rodrigo")
    assert feita["andamento"] == "Quitada em 10/11/2026 · transferência feita em 15/11/2026"
    assert feita["venda"]["acoes"] == {"registrar_transferencia": False}


def test_loc_16_ca_420_13_conta_aberta_segura_a_quitacao(compra: Cenario, ativa: Locacao) -> None:
    """Com uma avaria de R$ 120,00 aberta na locação, pagar a 24ª não quita: a ficha diz o que
    falta. Paga a avaria, a quitação acontece."""
    avaria = financeiro.lancar_avulsa(
        filial_id=ativa.filial_id,
        cliente_id=ativa.cliente_id,
        tipo="avaria",
        descricao="Retrovisor direito",
        vencimento=date(2026, 11, 20),
        valor_centavos=12000,
        origem=financeiro.Origem("locacao", ativa.pk, ativa.codigo),
    )
    _pagar(ativa, *range(2, 25))
    ativa.refresh_from_db()
    assert (ativa.status, ativa.quitada_em) == ("ativa", None)
    assert Veiculo.objects.get(pk=compra.sak.pk).status == "alugado"
    bloco = _compra(compra, ativa)
    assert bloco["andamento"] == (
        "24 de 24 parcelas pagas · faltam as contas abaixo para a transferência"
    )
    assert bloco["falta_para_quitar"] == [
        {"conta_id": avaria.pk, "rotulo": "Avaria · Retrovisor direito", "valor_centavos": 12000}
    ]
    financeiro.marcar_paga(avaria, forma="pix")
    ativa.refresh_from_db()
    assert ativa.status == "encerrada" and ativa.quitada_em is not None


def test_loc_16_ca_420_14_caucao_maior_que_a_parcela(compra: Cenario) -> None:
    """Plano semanal de 104 parcelas de R$ 199,00, caução de R$ 300,00: a última nasce R$ 0,00
    (e, zerada, não vira conta); paga a 103ª, quita, e os R$ 101,00 voltam como sobra."""
    plano = _criar_plano(
        compra,
        nome="Compra Street 104 semanas",
        periodicidade="semanal",
        parcelas=104,
        valor_parcela_centavos=19900,
    )
    assert plano["ultima_parcela_centavos"] == 0
    simulada = (
        compra.moto.api("Bruna").post(SIMULAR, _corpo(compra, plano["id"]), format="json").json()
    )
    assert simulada["compra"]["sobra_caucao_centavos"] == 10100
    assert simulada["parcelas_previstas"][-1]["valor_centavos"] == 0
    assert datetime.fromisoformat(simulada["fim_previsto"]) == datetime(
        2028, 11, 7, 10, tzinfo=FUSO
    )
    locacao = _retirada(_confirmada(compra, plano["id"]))
    assert len(_contas(locacao)) == 103
    bloco = _compra(compra, locacao)
    assert (bloco["ultima_parcela_centavos"], bloco["sobra_caucao_centavos"]) == (0, 10100)
    assert bloco["andamento"] == "Parcela 1 de 104 · faltam 103 para a transferência"
    _pagar(locacao, *range(2, 103))
    assert _compra(compra, locacao)["andamento"] == (
        "Parcela 102 de 104 · faltam 2 para a transferência"
    )
    _pagar(locacao, 103)
    locacao.refresh_from_db()
    assert locacao.status == "encerrada"
    reembolso = Reembolso.objects.get()
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status) == (
        10100,
        "pix",
        "a_fazer",
    )
    assert reembolso.motivo == f"Sobra da caução na quitação da {locacao.codigo}"


def test_loc_16_quitacao_com_tudo_pago_antes_da_retirada(
    compra: Cenario, plano: dict[str, Any]
) -> None:
    """Tudo pago antes da retirada: a quitação acontece na retirada, sem esperar outro
    pagamento."""
    locacao = _confirmada(compra, plano["id"])
    _pagar(locacao, *range(1, 25), caucao=True)
    _vistoriar(locacao.pk)
    _assinar(locacao.pk)
    locacao.refresh_from_db()
    assert (locacao.status, locacao.quitada_em is not None) == ("encerrada", True)


def test_loc_16_vistoriador_ve_a_compra_sem_valores(compra: Cenario, ativa: Locacao) -> None:
    bloco = compra.detalhe(ativa.pk, "João")["compra"]
    assert bloco["andamento"] == "Parcela 1 de 24 · faltam 23 para a transferência"
    assert not [chave for chave in bloco if chave.endswith("_centavos")]


# --- Contrato (finalidade locacao_compra) ---


def test_loc_16_modelo_pronto_e_marcadores_da_compra(compra: Cenario) -> None:
    """O modelo pronto "Locação com intenção de compra" cria um rascunho da finalidade
    `locacao_compra`; os marcadores `compra.*` só valem nele."""
    api = compra.moto.api("Mariana")
    prontos_api = api.get("/api/contratos/modelos-prontos/").json()["resultados"]
    pronto = next(p for p in prontos_api if p["chave"] == "locacao_compra")
    assert (pronto["nome"], pronto["finalidade"]) == (
        "Locação com intenção de compra",
        "locacao_compra",
    )
    criado = api.post("/api/contratos/modelos/", {"a_partir_de": "locacao_compra"}, format="json")
    assert criado.status_code == 201, criado.json()
    assert criado.json()["finalidade"] == "locacao_compra"
    assert set(marcadores.usados(prontos.TEXTO_COMPRA)) <= marcadores.CHAVES_COMPRA
    errado = api.post(
        "/api/contratos/modelos/",
        {"nome": "Locação", "finalidade": "locacao", "texto": "<p>{{compra.prazo}}</p>"},
        format="json",
    )
    assert (errado.status_code, errado.json()["codigo"]) == (400, "marcador_invalido")
    lista = api.get("/api/contratos/marcadores/").json()["resultados"]
    assert {"chave": "compra.prazo", "finalidade": "locacao_compra"}.items() <= next(
        m for m in lista if m["chave"] == "compra.prazo"
    ).items()


def test_loc_16_contrato_da_compra_com_os_valores_do_plano(
    compra: Cenario, plano: dict[str, Any]
) -> None:
    locacao = _confirmada(compra, plano["id"])
    valores = contrato_da_locacao.valores(Locacao.objects.get(pk=locacao.pk))
    assert {k: v for k, v in valores.items() if k.startswith("compra.")} == {
        "compra.plano": "Compra Street 24 meses",
        "compra.parcelas": "24",
        "compra.valor_parcela": "R$ 1.190,00",
        "compra.ultima_parcela": "R$ 890,00",
        "compra.prazo": "24 meses",
    }
    dados = contrato_da_locacao._dados(locacao)
    assert dados.finalidade == "locacao_compra"
    gerado = contrato_da_locacao.gerar(locacao)
    assert gerado.modelo is not None and gerado.modelo.finalidade == "locacao_compra"
    assert "24 meses" in gerado.versao_texto_html


def test_loc_16_selector_do_detalhe_sem_compra_na_comum(compra: Cenario) -> None:
    comum = compra.confirmada(inicio=INICIO, periodos=1)
    assert (comum["tipo"], comum["tipo_rotulo"], comum["compra"]) == ("comum", None, None)
    assert comum["acoes"]["encerrar_por_atraso"] is False
    assert selectors.compra(Locacao.objects.get(pk=comum["id"]), None, []) is None
