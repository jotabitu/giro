"""T-081 · Aprovações: lista e decisão (docs/api/aprovacoes.md, ADR 0011 e 0019).

Roda na `empresa_a` com as pessoas e a frota da Moto Rápida (`frota.py`), com o relógio em 07 out
2026, 10:00. O pedido de ponta a ponta é o APR-06 do CA-013-16: João (vistoriador) pede a
correção da SAK1D39 de 3.500 para 3.400 km, e Rodrigo (gerente da Filial Centro) decide.
"""

from typing import Any

import pytest
from django.conf import settings
from django.db import connection

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.filiais.models import Filial
from apps.plataforma.models import Empresa
from apps.veiculos.models import LeituraKm, Veiculo
from comum import aprovacoes, eventos

from .frota import Frota, montar_frota
from .test_t012_filiais import MotoRapida
from .test_t013_veiculos import MOTIVO, _acao, _caucaia

LISTA = "/api/aprovacoes/"


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


@pytest.fixture
def decisoes():
    recebidas: list[dict[str, Any]] = []

    def guardar(**dados: Any) -> None:
        recebidas.append(dados)

    eventos.assinar("aprovacoes.pedido_decidido", guardar)
    yield recebidas
    eventos.remover_assinante("aprovacoes.pedido_decidido", guardar)


@pytest.fixture
def sak(moto, frota) -> Veiculo:
    sak = frota.veiculos["SAK1D39"]
    assert _acao(moto, "João", sak, "km", {"km": 3500}).status_code == 200
    return sak


def _pedir_km(moto: MotoRapida, sak: Veiculo, km: int = 3400) -> int:
    resposta = _acao(moto, "João", sak, "corrigir-km", {"km": km, "motivo": MOTIVO})
    assert resposta.status_code == 202, resposta.json()
    return int(resposta.json()["pedido_aprovacao"]["id"])


def _decidir(moto: MotoRapida, nome: str, pedido_id: int, acao: str, corpo: Any = None):
    return moto.api(nome).post(f"{LISTA}{pedido_id}/{acao}/", corpo or {}, format="json")


def _pedido(
    tipo: str,
    solicitante: Any,
    filial: Filial,
    origem_id: int = 801,
    **campos: Any,
) -> int:
    """Pedido de outro módulo, aberto pela porta (ADR 0019), para testar a tabela "Quem
    decide" antes de locações, clientes e financeiro existirem."""
    origem = {"APR-01": "locacao", "APR-02": "locacao", "APR-03": "despesa"}.get(tipo, "caixa")
    return aprovacoes.pedir(
        tipo=tipo,
        origem_tipo=origem,
        origem_id=origem_id,
        origem_codigo=None,
        filial_id=filial.pk,
        solicitante=solicitante,
        titulo=campos.pop("titulo", "Pedido"),
        detalhe=campos.pop("detalhe", "Detalhe"),
        **campos,
    ).id


def _ids(resposta) -> list[int]:
    assert resposta.status_code == 200, resposta.json()
    return [p["id"] for p in resposta.json()["resultados"]]


# --- De ponta a ponta: APR-06 (CA-013-16) ---


def test_apr_06_ca_013_16_gerente_aprova_e_o_km_e_corrigido(moto, frota, sak, decisoes):
    pedido_id = _pedir_km(moto, sak)

    # Rodrigo vê o pedido no sino e na lista, e pode decidir.
    corpo = moto.api("Rodrigo").get(LISTA).json()
    assert corpo["contagens"]["pendente"] == 1
    [item] = corpo["resultados"]
    assert item == {
        "id": pedido_id,
        "tipo": "APR-06",
        "status": "pendente",
        "titulo": "Correção de km para baixo",
        "detalhe": "SAK1D39 · 3.500 → 3.400 km · Erro de digitação",
        "origem": {"tipo": "veiculo", "id": sak.pk, "codigo": "SAK1D39"},
        "filial": {"id": frota.centro.pk, "nome": "Filial Centro"},
        "solicitante": {"id": moto.pessoas["João"].pk, "nome": "João"},
        "pedido_em": item["pedido_em"],
        "motivo_pedido": MOTIVO,
        "valor_centavos": None,
        "pct": None,
        "decidido_por": None,
        "decidido_em": None,
        "motivo_recusa": None,
        "resumo": {  # T-202: as células do cartão (APR-06)
            "celulas": [
                {"rotulo": "Km atual", "valor": "3.500 km"},
                {"rotulo": "Km pedido", "valor": "3.400 km"},
                {"rotulo": "Diferença", "valor": "−100 km"},
            ],
            "nota": None,
        },
        "pode_decidir": True,
        "pode_cancelar": False,
        "proprio_pedido": False,
    }

    resposta = _decidir(moto, "Rodrigo", pedido_id, "aprovar")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "aprovado"
    assert resposta.json()["decidido_por"] == {"id": moto.pessoas["Rodrigo"].pk, "nome": "Rodrigo"}
    assert resposta.json()["decidido_em"] is not None
    assert resposta.json()["pode_decidir"] is False

    # O assinante de veículos corrigiu o km, com a aprovação como origem da leitura.
    sak.refresh_from_db()
    assert sak.km_atual == 3400
    leitura = LeituraKm.objects.filter(veiculo=sak).latest("id")
    assert (leitura.km, leitura.correcao, leitura.motivo) == (3400, True, MOTIVO)
    assert (leitura.origem_tipo, leitura.origem_id) == ("aprovacao", pedido_id)
    assert leitura.por_id == moto.pessoas["Rodrigo"].pk
    assert EventoAuditoria.objects.filter(acao="veiculo.corrigir_km", objeto_id=sak.pk).exists()

    # O evento e a auditoria da decisão (APR-10).
    assert [(d["pedido_id"], d["status"], d["decidido_por_id"]) for d in decisoes] == [
        (pedido_id, "aprovado", moto.pessoas["Rodrigo"].pk)
    ]
    assert decisoes[0]["dados"] == {"km_novo": 3400, "km_anterior": 3500}
    evento = EventoAuditoria.objects.get(acao="pedido_aprovacao.aprovar", objeto_id=pedido_id)
    assert evento.regra == "APR-10"
    assert evento.depois["status"] == "aprovado"
    assert evento.depois["aprovador_id"] == moto.pessoas["Rodrigo"].pk

    # Decidido não se decide de novo; a lista padrão (pendentes) esvaziou.
    resposta = _decidir(moto, "Rodrigo", pedido_id, "recusar", {"motivo": "Não"})
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "transicao_pedido"
    assert moto.api("Rodrigo").get(LISTA).json()["contagens"]["pendente"] == 0
    assert _ids(moto.api("Rodrigo").get(LISTA, {"status": "aprovado"})) == [pedido_id]


def test_apr_07_recusar_exige_motivo_e_o_km_fica(moto, frota, sak, decisoes):
    pedido_id = _pedir_km(moto, sak)
    resposta = _decidir(moto, "Rodrigo", pedido_id, "recusar")
    assert resposta.status_code == 400
    assert "motivo" in resposta.json()["campos"]

    resposta = _decidir(moto, "Rodrigo", pedido_id, "recusar", {"motivo": "Hodômetro conferido"})
    assert resposta.status_code == 200, resposta.json()
    assert (resposta.json()["status"], resposta.json()["motivo_recusa"]) == (
        "recusado",
        "Hodômetro conferido",
    )
    sak.refresh_from_db()
    assert sak.km_atual == 3500
    assert [(d["status"], d["motivo"]) for d in decisoes] == [("recusado", "Hodômetro conferido")]
    assert EventoAuditoria.objects.filter(
        acao="pedido_aprovacao.recusar", objeto_id=pedido_id, regra="APR-10"
    ).exists()

    # João vê o próprio pedido recusado com o motivo; e pode pedir de novo.
    [meu] = (
        moto.api("João").get(LISTA, {"minhas": "true", "status": "recusado"}).json()["resultados"]
    )
    assert (meu["id"], meu["motivo_recusa"], meu["pode_decidir"]) == (
        pedido_id,
        "Hodômetro conferido",
        False,
    )
    assert _pedir_km(moto, sak) != pedido_id


def test_apr_06_km_mudou_depois_do_pedido(moto, frota, sak):
    pedido_id = _pedir_km(moto, sak)
    assert _acao(moto, "João", sak, "km", {"km": 3600}).status_code == 200

    resposta = _decidir(moto, "Rodrigo", pedido_id, "aprovar")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "km_mudou"
    assert resposta.json()["detalhes"] == {"km_anterior": 3500, "km_atual": 3600}
    # A aprovação voltou inteira: o pedido continua pendente e o km, 3.600.
    assert PedidoAprovacao.objects.get(pk=pedido_id).status == "pendente"
    sak.refresh_from_db()
    assert sak.km_atual == 3600
    assert not EventoAuditoria.objects.filter(acao="pedido_aprovacao.aprovar").exists()


# --- Quem pediu nunca decide (APR-09) ---


def test_apr_09_quem_pediu_nao_decide_o_proprio_pedido(moto, frota):
    rodrigo = moto.pessoas["Rodrigo"]
    pedido_id = _pedido("APR-03", rodrigo, frota.centro, valor_centavos=120000)

    # Fora da lista dele, mesmo sendo gerente da filial.
    assert _ids(moto.api("Rodrigo").get(LISTA)) == []
    assert moto.api("Rodrigo").get(LISTA).json()["contagens"]["pendente"] == 0
    meus = moto.api("Rodrigo").get(LISTA, {"minhas": "true"}).json()["resultados"]
    assert [(p["id"], p["pode_decidir"]) for p in meus] == [(pedido_id, False)]

    for acao, corpo in (("aprovar", {}), ("recusar", {"motivo": "Não"})):
        resposta = _decidir(moto, "Rodrigo", pedido_id, acao, corpo)
        assert resposta.status_code == 403
        assert resposta.json() == {
            "codigo": "APR-09",
            "mensagem": "Outra pessoa precisa decidir este pedido",
            "detalhes": None,
        }
    assert PedidoAprovacao.objects.get(pk=pedido_id).status == "pendente"

    # A administradora decide.
    assert _decidir(moto, "Mariana", pedido_id, "aprovar").json()["status"] == "aprovado"


# --- Quem decide e escopo de filial ---


def test_apr_01_a_apr_06_quem_decide_cada_tipo(moto, frota):
    joao, centro = moto.pessoas["João"], frota.centro
    ids = {
        tipo: _pedido(tipo, joao, centro, origem_id=900 + n)
        for n, tipo in enumerate(["APR-01", "APR-02", "APR-03", "APR-04", "APR-05", "APR-06"])
    }
    todos = sorted(ids.values())
    assert _ids(moto.api("Rodrigo").get(LISTA)) == todos
    assert _ids(moto.api("Mariana").get(LISTA, HTTP_X_FILIAL="todas")) == todos
    # Vendedor, vistoriador e financeiro não decidem nada.
    for nome in ("Bruna", "João", "Lúcia"):
        assert _ids(moto.api(nome).get(LISTA)) == []
        assert _decidir(moto, nome, ids["APR-03"], "aprovar").status_code in (403, 404)
    assert _decidir(moto, "Bruna", ids["APR-01"], "aprovar").status_code == 404

    # Com as extras (USR-03), a vendedora decide desconto e cancelamento, e só eles.
    bruna = moto.pessoas["Bruna"]
    bruna.permissoes_extras = ["aprovar_desconto", "cancelar_contrato"]
    bruna.save(update_fields=["permissoes_extras"])
    assert _ids(moto.api("Bruna").get(LISTA)) == [ids["APR-01"], ids["APR-02"]]
    assert _decidir(moto, "Bruna", ids["APR-03"], "aprovar").status_code == 404
    resposta = _decidir(moto, "Bruna", ids["APR-01"], "aprovar")
    assert resposta.status_code == 200, resposta.json()
    assert _ids(moto.api("Bruna").get(LISTA, {"tipo": "APR-02"})) == [ids["APR-02"]]


def test_apr_06_gerente_decide_so_as_suas_filiais(moto, frota):
    caucaia = _caucaia(moto)  # Rodrigo não é de Caucaia
    joao = moto.pessoas["João"]
    do_centro = _pedido("APR-04", joao, frota.centro, origem_id=1)
    de_caucaia = _pedido("APR-04", joao, caucaia, origem_id=2)

    assert _ids(moto.api("Rodrigo").get(LISTA)) == [do_centro]
    assert _decidir(moto, "Rodrigo", de_caucaia, "aprovar").status_code == 404
    assert _decidir(moto, "Rodrigo", de_caucaia, "recusar", {"motivo": "x"}).status_code == 404

    # A administradora vê por filial (X-Filial) ou todas, e decide qualquer uma.
    mariana = moto.api("Mariana", HTTP_X_FILIAL=str(caucaia.pk))
    assert _ids(mariana.get(LISTA)) == [de_caucaia]
    assert _ids(moto.api("Mariana", HTTP_X_FILIAL="todas").get(LISTA)) == [do_centro, de_caucaia]
    assert _decidir(moto, "Mariana", de_caucaia, "aprovar").status_code == 200


def test_apr_01_a_apr_06_lista_mais_antigo_primeiro_e_filtros(moto, frota, relogio):
    joao = moto.pessoas["João"]
    primeiro = _pedido("APR-04", joao, frota.centro, origem_id=1)
    segundo = _pedido("APR-03", joao, frota.centro, origem_id=2, valor_centavos=120000)
    terceiro = _pedido("APR-04", joao, frota.centro, origem_id=3)
    api = moto.api("Rodrigo")
    assert _ids(api.get(LISTA)) == [primeiro, segundo, terceiro]
    assert _ids(api.get(LISTA, {"tipo": "APR-04"})) == [primeiro, terceiro]
    assert _ids(api.get(LISTA, {"status": "recusado"})) == []
    assert api.get(LISTA, {"status": "recusado"}).json()["contagens"]["pendente"] == 3
    [despesa] = [p for p in api.get(LISTA).json()["resultados"] if p["id"] == segundo]
    assert despesa["valor_centavos"] == 120000


# --- Cancelar ---


def test_apr_10_quem_pediu_cancela(moto, frota, sak, decisoes):
    pedido_id = _pedir_km(moto, sak)
    assert _decidir(moto, "Rodrigo", pedido_id, "cancelar").status_code == 403

    resposta = _decidir(moto, "João", pedido_id, "cancelar")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "cancelado"
    assert [(d["status"], d["decidido_por_id"]) for d in decisoes] == [
        ("cancelado", moto.pessoas["João"].pk)
    ]
    sak.refresh_from_db()
    assert sak.km_atual == 3500
    assert _decidir(moto, "João", pedido_id, "cancelar").status_code == 409
    assert EventoAuditoria.objects.filter(
        acao="pedido_aprovacao.cancelar", objeto_id=pedido_id, regra="APR-10"
    ).exists()


# --- Módulo ativo e isolamento ---


def test_usr_05_aprovacoes_no_menu_do_gerente(moto, frota):
    assert "aprovacoes" in settings.GIRO_MODULOS_ATIVOS
    navegacao = moto.api("Rodrigo").get("/api/auth/eu/").json()["navegacao"]
    chaves = [item["chave"] for grupo in navegacao["menu_completo"] for item in grupo["itens"]]
    assert "aprovacoes" in chaves
    navegacao = moto.api("João").get("/api/auth/eu/").json()["navegacao"]
    chaves = [item["chave"] for grupo in navegacao["menu_completo"] for item in grupo["itens"]]
    assert "aprovacoes" not in chaves


def test_apr_10_pedido_da_empresa_a_nao_aparece_na_b(moto, frota, sak):
    _pedir_km(moto, sak)
    assert PedidoAprovacao.objects.count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not PedidoAprovacao.objects.exists()
