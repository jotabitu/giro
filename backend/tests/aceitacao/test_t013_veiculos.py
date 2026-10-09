"""T-013 · Veículos, categorias, documentos, histórico de status (docs/qa/criterios/T-013.md).

Roda na `empresa_a` (host `empresa-a.localhost`) com o plano Profissional, as pessoas do seed e a
frota da Moto Rápida (`frota.py`), com o relógio em 07 out 2026, 10:00. Os documentos (CA-013-17
a 20) entram na T-079.
"""

from datetime import date, timedelta
from typing import Any

import pytest
from django.db import connection

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.filiais import selectors as filiais_selectors
from apps.filiais import services as filiais
from apps.filiais.models import Filial
from apps.plataforma.models import Empresa, UsoEmpresa
from apps.plataforma.services import recalcular_uso
from apps.veiculos import selectors, services
from apps.veiculos.models import (
    Categoria,
    HistoricoStatusVeiculo,
    LeituraKm,
    TransferenciaVeiculo,
    Veiculo,
)
from comum import eventos, leituras
from comum.erros import TransicaoInvalida

from .apoio import CONTAGENS_FROTA_SEED, PRECOS_SEED, pendente
from .frota import Frota, criar_veiculo, montar_frota
from .test_t012_filiais import MotoRapida, _filial

MOTIVO = "Erro de digitação"


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _caucaia(moto: MotoRapida, *pessoas: str) -> Filial:
    resposta = moto.criar(_filial("Filial Caucaia"))
    assert resposta.status_code == 201, resposta.json()
    caucaia = Filial.objects.get(pk=resposta.json()["id"])
    for nome in pessoas:
        atuais = filiais_selectors.filiais_do_usuario(moto.pessoas[nome])
        filiais.definir_filiais_do_usuario(moto.pessoas[nome].pk, atuais | {caucaia.pk})
    return caucaia


def _url(veiculo: Veiculo, acao: str = "") -> str:
    return f"/api/veiculos/{veiculo.pk}/{acao + '/' if acao else ''}"


def _acao(moto: MotoRapida, nome: str, veiculo: Veiculo, acao: str, corpo: Any = None):
    return moto.api(nome).post(_url(veiculo, acao), corpo or {}, format="json")


def _novo(**campos: Any) -> dict[str, Any]:
    return {
        "placa": "QAB1C23",
        "chassi": "9C2JC4820TR000123",
        "marca": "Honda",
        "modelo": "Biz 125",
        "ano_fabricacao": 2026,
        "ano_modelo": 2026,
        "cor": "branca",
        "km_atual": 0,
        **campos,
    }


def _cadastro(frota: Frota, **campos: Any) -> dict[str, Any]:
    padrao = {
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
    }
    return _novo(**{**padrao, **campos})


def _vender(veiculo: Veiculo) -> None:
    origem = services.OrigemDaMudanca("venda", 177, "VEN-0177")
    services.transicionar(veiculo, "a_venda", origem=origem)
    services.transicionar(veiculo, "vendido", origem=origem)


def _vigente(categoria: Categoria, data: date) -> Any:
    preco = selectors.preco_vigente(categoria, data)
    assert preco is not None
    return preco


def _veiculos_no_plano(moto: MotoRapida) -> int:
    return int(moto.api().get("/api/assinatura/").json()["uso"]["veiculos"]["usado"])


# --- Frota ---


def test_vei_06_ca_013_01_contagens_do_seed(moto, frota):
    for nome in ("Mariana", "Rodrigo", "Bruna", "João", "Lúcia"):
        corpo = moto.api(nome).get("/api/veiculos/").json()
        assert corpo["contagens"] == CONTAGENS_FROTA_SEED, nome

    api = moto.api("Rodrigo")
    disponiveis = api.get("/api/veiculos/?status=disponivel").json()
    assert disponiveis["contagens"] == CONTAGENS_FROTA_SEED
    assert len(disponiveis["resultados"]) == 16
    assert {v["status"] for v in disponiveis["resultados"]} == {"disponivel"}

    urbana = frota.categorias["Urbana 110–125"]
    _vender(criar_veiculo(900, urbana, frota.centro))
    services.baixar(criar_veiculo(901, urbana, frota.centro, "indisponivel"), "sucata", "")
    corpo = api.get("/api/veiculos/?tamanho=100").json()
    assert corpo["contagens"] == CONTAGENS_FROTA_SEED
    assert len(corpo["resultados"]) == 86
    for status, placa in (("vendido", "GEN0900"), ("baixado", "GEN0901")):
        lista = api.get(f"/api/veiculos/?status={status}").json()["resultados"]
        assert [v["placa"] for v in lista] == [placa]

    # As contagens seguem o tipo: só os carros.
    carros = api.get("/api/veiculos/?tipo_veiculo=carro").json()["contagens"]
    assert (carros["todos"], carros["motos"], carros["carros"]) == (6, 0, 6)


def test_vei_01_ca_013_02_busca(moto, frota):
    api = moto.api("Bruna")
    for busca in ("SAK1D39", "sak-1d39", "9C2KC2210RR004417"):
        resultados = api.get("/api/veiculos/", {"busca": busca}).json()["resultados"]
        assert [(v["marca"], v["modelo"], v["cor"], v["placa"]) for v in resultados] == [
            ("Honda", "CG 160 Fan", "vermelha", "SAK1D39")
        ], busca
        assert resultados[0]["preco_vigente"]["diaria_centavos"] == 5490


def test_vei_01_ca_013_03_valor_de_compra_so_para_gestao(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    for nome in ("Mariana", "Rodrigo"):
        corpo = moto.api(nome).get(_url(sak)).json()
        assert (corpo["valor_compra_centavos"], corpo["data_compra"]) == (1390000, "2025-03-10")
    for nome in ("Bruna", "João", "Lúcia"):
        corpo = moto.api(nome).get(_url(sak)).json()
        assert (corpo["valor_compra_centavos"], corpo["data_compra"]) == (None, None), nome
        lista = moto.api(nome).get("/api/veiculos/", {"busca": "SAK1D39"}).json()
        assert lista["resultados"][0]["valor_compra_centavos"] is None


def test_vei_01_ca_013_04_escopo_de_filial(moto, frota):
    caucaia = _caucaia(moto)
    de_caucaia = criar_veiculo(
        500,
        frota.categorias["Street 150–160"],
        caucaia,
        placa="CAU1A00",
        chassi="9C2CAUCAIA0000001",
    )
    rodrigo = moto.api("Rodrigo")
    placas = {v["placa"] for v in rodrigo.get("/api/veiculos/?tamanho=100").json()["resultados"]}
    assert "CAU1A00" not in placas
    assert rodrigo.get(_url(de_caucaia)).status_code == 404
    assert _acao(moto, "Rodrigo", de_caucaia, "bloquear", {"motivo": "x"}).status_code == 404
    com_cabecalho = moto.api("Rodrigo", HTTP_X_FILIAL=str(caucaia.pk))
    assert com_cabecalho.get("/api/veiculos/").status_code == 403
    # Mariana (todas as filiais) escolhe a Caucaia.
    mariana = moto.api("Mariana", HTTP_X_FILIAL=str(caucaia.pk)).get("/api/veiculos/").json()
    assert [v["placa"] for v in mariana["resultados"]] == ["CAU1A00"]


# --- Cadastro (VEI-01, PLT-03) ---


def test_vei_01_ca_013_05_cadastrar(moto, frota):
    assert _veiculos_no_plano(moto) == 86
    resposta = moto.api("Rodrigo").post("/api/veiculos/", _cadastro(frota), format="json")
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    assert (corpo["placa"], corpo["status"], corpo["km_atual"]) == ("QAB1C23", "disponivel", 0)
    assert corpo["categoria"]["nome"] == "Urbana 110–125"
    assert corpo["filial"]["nome"] == "Filial Centro"
    assert corpo["preco_vigente"]["diaria_centavos"] == 4490
    assert corpo["entrou_na_frota_em"] == "2026-10-07"
    veiculo = Veiculo.objects.get(placa="QAB1C23")
    assert list(veiculo.historico.values_list("de", "para", "origem_tipo")) == [
        ("", "disponivel", "cadastro")
    ]
    assert list(veiculo.leituras_km.values_list("km", "correcao")) == [(0, False)]
    assert EventoAuditoria.objects.filter(acao="veiculo.cadastrar", objeto_id=veiculo.pk).exists()
    assert _veiculos_no_plano(moto) == 87

    for nome in ("Bruna", "João", "Lúcia"):
        outra = _cadastro(frota, placa="QAB1C24", chassi="9C2JC4820TR000124")
        assert moto.api(nome).post("/api/veiculos/", outra, format="json").status_code == 403


def test_vei_01_ca_013_06_placa_e_chassi_unicos_em_qualquer_estado(moto, frota):
    api = moto.api("Rodrigo")
    sak = frota.veiculos["SAK1D39"]
    resposta = api.post("/api/veiculos/", _cadastro(frota, placa="SAK-1D39"), format="json")
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "VEI-01",
        "mensagem": "Já existe um veículo com esta placa",
        "detalhes": {"campo": "placa", "veiculo_id": sak.pk},
    }

    urbana = frota.categorias["Urbana 110–125"]
    vendido = criar_veiculo(700, urbana, frota.centro)
    _vender(vendido)
    baixado = criar_veiculo(701, urbana, frota.centro)
    services.baixar(baixado, "roubo", "Boletim 123")
    for veiculo in (vendido, baixado):
        corpo = _cadastro(frota, chassi=veiculo.chassi)
        resposta = api.post("/api/veiculos/", corpo, format="json")
        assert resposta.status_code == 409, veiculo.status
        assert resposta.json()["codigo"] == "VEI-01"
        assert resposta.json()["detalhes"]["campo"] == "chassi"
        repetida = _cadastro(frota, placa=veiculo.placa)
        assert api.post("/api/veiculos/", repetida, format="json").status_code == 409


def test_vei_01_ca_013_07_formato(moto, frota):
    api = moto.api("Rodrigo")
    caucaia = _caucaia(moto)
    so_de_caucaia = Categoria.objects.create(
        nome="Street Caucaia", tipo_veiculo="moto", filial=caucaia
    )
    recusados = {
        "chassi": _cadastro(frota, chassi="9C2JC4820TR00012"),
        "placa": _cadastro(frota, placa="AB1234"),
        "categoria_id": _cadastro(frota, categoria_id=so_de_caucaia.pk),
    }
    for campo, corpo in recusados.items():
        resposta = api.post("/api/veiculos/", corpo, format="json")
        assert resposta.status_code == 400, campo
        assert resposta.json()["codigo"] == "validacao"
        assert campo in resposta.json()["campos"], resposta.json()

    antiga = api.post("/api/veiculos/", _cadastro(frota, placa="ABC1234"), format="json")
    assert antiga.status_code == 201, antiga.json()
    mercosul = _cadastro(frota, placa="abc-1d23", chassi="9C2JC4820TR000999")
    resposta = api.post("/api/veiculos/", mercosul, format="json")
    assert resposta.status_code == 201, resposta.json()
    assert resposta.json()["placa"] == "ABC1D23"


def test_plt_03_ca_013_08_limite_de_veiculos(moto, frota):
    urbana = frota.categorias["Urbana 110–125"]
    for numero in range(200, 264):  # 86 + 64 = 150
        criar_veiculo(numero, urbana, frota.centro)
    recalcular_uso(moto.empresa)
    assert _veiculos_no_plano(moto) == 150

    api = moto.api("Rodrigo")
    resposta = api.post("/api/veiculos/", _cadastro(frota), format="json")
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "PLT-03"
    assert not Veiculo.objects.filter(placa="QAB1C23").exists()

    # Com 150, sendo 1 deles baixado, o cadastro passa.
    services.baixar(Veiculo.objects.get(placa="GEN0200"), "perda_total", "")
    assert _veiculos_no_plano(moto) == 149
    assert api.post("/api/veiculos/", _cadastro(frota), format="json").status_code == 201
    assert _veiculos_no_plano(moto) == 150


def test_vei_01_ca_013_09_corrigir_placa_ou_chassi(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    corpo = {"placa": "SAK1D38", "motivo": MOTIVO}
    assert _acao(moto, "Rodrigo", sak, "corrigir-identificacao", corpo).status_code == 403
    sem_motivo = _acao(moto, "Mariana", sak, "corrigir-identificacao", {"placa": "SAK1D38"})
    assert sem_motivo.status_code == 400

    resposta = _acao(moto, "Mariana", sak, "corrigir-identificacao", corpo)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["placa"] == "SAK1D38"
    evento = EventoAuditoria.objects.get(acao="veiculo.corrigir_identificacao")
    assert (evento.antes, evento.depois, evento.motivo, evento.regra) == (
        {"placa": "SAK1D39"},
        {"placa": "SAK1D38"},
        MOTIVO,
        "VEI-01",
    )

    # PATCH com placa não muda a placa.
    patch = moto.api("Mariana").patch(
        _url(sak), {"placa": "ZZZ9Z99", "cor": "preta"}, format="json"
    )
    assert patch.status_code == 200
    assert (patch.json()["placa"], patch.json()["cor"]) == ("SAK1D38", "preta")

    usada = {"placa": "QXA4B21", "motivo": MOTIVO}
    resposta = _acao(moto, "Mariana", sak, "corrigir-identificacao", usada)
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEI-01"


# --- Status e transições ---


def _resultado(resposta) -> tuple[int, str]:
    corpo = resposta.json()
    return resposta.status_code, corpo.get("status") or corpo["codigo"]


def test_vei_02_ca_013_10_acoes_permitidas(moto, frota):
    sak, qxa = frota.veiculos["SAK1D39"], frota.veiculos["QXA4B21"]
    pmz, rht = frota.veiculos["PMZ3E17"], frota.veiculos["RHT9F02"]

    bloqueio = {"motivo": "Retrovisor quebrado"}
    assert _resultado(_acao(moto, "Rodrigo", sak, "bloquear", bloqueio)) == (200, "indisponivel")
    assert _resultado(_acao(moto, "Rodrigo", sak, "desbloquear")) == (200, "disponivel")
    venda = {"valor_venda_centavos": 1650000}
    assert _resultado(_acao(moto, "Rodrigo", sak, "colocar-a-venda", venda)) == (200, "a_venda")
    na_lista = moto.api("Rodrigo").get("/api/veiculos/", {"busca": "SAK1D39"}).json()
    assert na_lista["resultados"][0]["valor_venda_centavos"] == 1650000
    assert na_lista["resultados"][0]["situacao"]["codigo"] == "a_venda"
    assert _resultado(_acao(moto, "Rodrigo", sak, "voltar-para-frota")) == (200, "disponivel")

    resposta = _acao(moto, "Rodrigo", qxa, "bloquear", bloqueio)
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "transicao_veiculo",
        "mensagem": "Não é possível bloquear um veículo alugado",
        "detalhes": {"de": "alugado", "para": "indisponivel"},
    }
    para_venda = _acao(moto, "Rodrigo", pmz, "colocar-a-venda", venda)
    assert _resultado(para_venda) == (409, "transicao_veiculo")
    baixa = {"motivo": "roubo", "descricao": "Boletim 4471"}
    assert _resultado(_acao(moto, "Mariana", qxa, "baixar", baixa)) == (409, "transicao_veiculo")
    assert _acao(moto, "Rodrigo", rht, "baixar", baixa).status_code == 403
    assert _resultado(_acao(moto, "Mariana", rht, "baixar", baixa)) == (200, "baixado")

    assert list(sak.historico.values_list("de", "para", "origem_tipo")) == [
        ("disponivel", "indisponivel", "manual"),
        ("indisponivel", "disponivel", "manual"),
        ("disponivel", "a_venda", "manual"),
        ("a_venda", "disponivel", "manual"),
    ]
    assert sak.historico.first().por_id == moto.pessoas["Rodrigo"].pk
    acoes = EventoAuditoria.objects.filter(objeto_tipo="veiculo", objeto_id=sak.pk).order_by("id")
    assert list(acoes.values_list("acao", flat=True)) == [
        "veiculo.bloquear",
        "veiculo.desbloquear",
        "veiculo.colocar_a_venda",
        "veiculo.definir_valor_venda",
        "veiculo.voltar_para_frota",
    ]
    rht.refresh_from_db()
    assert (rht.status, rht.motivo_status) == ("baixado", "Roubo: Boletim 4471")

    # Nenhum endpoint muda o status por PATCH.
    patch = moto.api("Mariana").patch(_url(sak), {"status": "alugado"}, format="json")
    assert patch.status_code == 200
    assert patch.json()["status"] == "disponivel"


def test_vei_02_ca_013_11_acoes_combina_perfil_e_estado(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    rodrigo = moto.api("Rodrigo").get(_url(sak)).json()["acoes"]
    assert rodrigo == {
        "editar": True,
        "bloquear": True,
        "colocar_a_venda": True,
        "transferir": True,
        "desbloquear": False,
        "voltar_para_frota": False,
        "baixar": False,
        "registrar_km": True,
        "corrigir_km": True,
    }
    assert moto.api("Mariana").get(_url(sak)).json()["acoes"]["baixar"] is True
    bruna = moto.api("Bruna").get(_url(sak)).json()["acoes"]
    assert not any(bruna.values())
    joao = moto.api("João").get(_url(sak)).json()["acoes"]
    assert [chave for chave, valor in joao.items() if valor] == ["registrar_km", "corrigir_km"]


def test_vei_07_ca_013_12_servico_de_transicao(moto, frota):
    urbana = frota.categorias["Urbana 110–125"]
    venda = services.OrigemDaMudanca("venda", 177, "VEN-0177")

    cancelada = criar_veiculo(800, urbana, frota.centro)
    _vender(cancelada)
    services.transicionar(cancelada, "a_venda", origem=venda)  # venda cancelada (VEN-07)
    assert cancelada.status == "a_venda"

    recomprada = criar_veiculo(801, urbana, frota.centro)
    _vender(recomprada)
    antes = recomprada.historico.count()
    devolvida = services.receber_na_troca(recomprada.chassi.lower(), {"venda_id": 180})
    assert (devolvida.pk, devolvida.status) == (recomprada.pk, "indisponivel")
    assert recomprada.historico.count() == antes + 1
    assert list(recomprada.historico.order_by("-id").values_list("de", "para")[:1]) == [
        ("vendido", "indisponivel")
    ]

    nova = services.receber_na_troca(
        "9C2TROCA000000001",
        {
            **_novo(placa="TRC1A23"),
            "categoria_id": urbana.pk,
            "filial_id": frota.centro.pk,
            "venda_id": 181,
            "venda_codigo": "VEN-0181",
        },
    )
    assert (nova.status, nova.chassi) == ("indisponivel", "9C2TROCA000000001")
    assert list(nova.historico.values_list("de", "para", "origem_codigo")) == [
        ("", "indisponivel", "VEN-0181")
    ]

    with pytest.raises(TransicaoInvalida) as erro:
        services.transicionar(frota.veiculos["QXA4B21"], "a_venda", origem=services.MANUAL)
    assert erro.value.codigo == "transicao_veiculo"
    assert erro.value.detalhes == {"de": "alugado", "para": "a_venda"}


# --- Transferência (VEI-04, FIL-05) ---


def test_vei_04_ca_013_13_transferencia_so_disponivel(moto, frota):
    caucaia = _caucaia(moto, "Rodrigo")
    sak, qxa = frota.veiculos["SAK1D39"], frota.veiculos["QXA4B21"]
    destino = {"filial_destino_id": caucaia.pk, "motivo": "Falta moto na Caucaia"}

    assert _acao(moto, "Bruna", sak, "transferir", destino).status_code == 403
    resposta = _acao(moto, "Rodrigo", sak, "transferir", destino)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["filial"] == {"id": caucaia.pk, "nome": "Filial Caucaia"}
    transferencia = TransferenciaVeiculo.objects.get(veiculo=sak)
    assert (transferencia.filial_origem_id, transferencia.filial_destino_id) == (
        frota.centro.pk,
        caucaia.pk,
    )
    assert transferencia.por_id == moto.pessoas["Rodrigo"].pk
    assert EventoAuditoria.objects.filter(acao="veiculo.transferir", regra="VEI-04").exists()

    resposta = _acao(moto, "Rodrigo", qxa, "transferir", destino)
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEI-04"
    assert resposta.json()["mensagem"] == "Só é possível transferir um veículo disponível"

    pop = Veiculo.objects.filter(status="disponivel", filial=frota.centro).order_by("id")[0]
    igual = {"filial_destino_id": frota.centro.pk}
    assert _acao(moto, "Rodrigo", pop, "transferir", igual).status_code == 400
    messejana = moto.criar(_filial("Filial Messejana", cidade="Fortaleza")).json()
    filiais.desativar(Filial.objects.get(pk=messejana["id"]), "Fechou")
    inativa = {"filial_destino_id": messejana["id"]}
    assert _acao(moto, "Rodrigo", pop, "transferir", inativa).status_code == 400
    pop.refresh_from_db()
    assert pop.filial_id == frota.centro.pk


def test_fil_06_ca_013_14_veto_a_desativacao_da_filial(moto, frota):
    caucaia = _caucaia(moto, "Rodrigo")
    sak = frota.veiculos["SAK1D39"]
    services.transferir(sak, caucaia.pk)
    desativar = {"motivo": "Fechamento"}
    api = moto.api("Mariana")
    resposta = api.post(f"/api/filiais/{caucaia.pk}/desativar/", desativar, format="json")
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "FIL-06"
    assert resposta.json()["detalhes"]["operacao"]["veiculos"] == 1

    services.baixar(sak, "perda_total", "Colisão")
    resposta = api.post(f"/api/filiais/{caucaia.pk}/desativar/", desativar, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["ativo"] is False


# --- Km (VEI-01, VEI-02, APR-06) ---


@pytest.fixture
def leituras_publicadas():
    recebidas: list[dict[str, Any]] = []

    def guardar(**dados: Any) -> None:
        recebidas.append(dados)

    eventos.assinar("veiculos.km_atualizado", guardar)
    yield recebidas
    eventos.remover_assinante("veiculos.km_atualizado", guardar)


def test_vei_01_ca_013_15_km_nunca_diminui(moto, frota, leituras_publicadas):
    sak = frota.veiculos["SAK1D39"]
    resposta = _acao(moto, "João", sak, "km", {"km": 3500})
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["km_atual"] == 3500
    assert leituras_publicadas == [{"veiculo_id": sak.pk, "km": 3500}]

    resposta = _acao(moto, "João", sak, "km", {"km": 3000})
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "VEI-01",
        "mensagem": "O km informado é menor que o atual (3.500). Para corrigir, use Corrigir km.",
        "detalhes": {"km_atual": 3500},
    }
    assert list(sak.leituras_km.values_list("km", flat=True)) == [3500]
    assert len(leituras_publicadas) == 1
    assert _acao(moto, "Bruna", sak, "km", {"km": 3600}).status_code == 403

    # Vistoria e OS usam o serviço (VEI-02), com a origem.
    os_118 = services.OrigemDaMudanca("ordem_servico", 118, "OS-118")
    services.atualizar_km(sak, 3550, origem=os_118)
    assert sak.km_atual == 3550
    assert sak.leituras_km.order_by("-id").first().origem_codigo == "OS-118"


def test_apr_06_ca_013_16_correcao_para_baixo(moto, frota, leituras_publicadas):
    sak = frota.veiculos["SAK1D39"]
    assert _acao(moto, "João", sak, "km", {"km": 3500}).status_code == 200
    corpo = {"km": 3400, "motivo": MOTIVO}

    # O vistoriador pede (APR-06, ADR 0019): 202 com o pedido, e o km continua 3.500.
    resposta = _acao(moto, "João", sak, "corrigir-km", corpo)
    assert resposta.status_code == 202, resposta.json()
    pedido_ref = resposta.json()["pedido_aprovacao"]
    assert {k: pedido_ref[k] for k in ("tipo", "status")} == {
        "tipo": "APR-06",
        "status": "pendente",
    }
    pedido = PedidoAprovacao.objects.get(pk=pedido_ref["id"])
    assert (pedido.origem_tipo, pedido.origem_id, pedido.origem_codigo) == (
        "veiculo",
        sak.pk,
        "SAK1D39",
    )
    assert (pedido.filial_id, pedido.solicitante_id) == (frota.centro.pk, moto.pessoas["João"].pk)
    assert pedido.dados == {"km_novo": 3400, "km_anterior": 3500}
    assert (pedido.titulo, pedido.detalhe) == (
        "Correção de km para baixo",
        "SAK1D39 · 3.500 → 3.400 km · Erro de digitação",
    )
    assert EventoAuditoria.objects.filter(
        acao="pedido_aprovacao.pedir", objeto_id=pedido.pk, regra="APR-10"
    ).exists()
    sak.refresh_from_db()
    assert sak.km_atual == 3500
    assert len(leituras_publicadas) == 1  # só a leitura de 3.500

    # Pedir de novo, com o primeiro pendente: 409.
    repetido = _acao(moto, "João", sak, "corrigir-km", corpo)
    assert repetido.status_code == 409
    assert repetido.json() == {
        "codigo": "pedido_pendente",
        "mensagem": "Já existe um pedido aguardando o gerente",
        "detalhes": {"pedido_id": pedido.pk},
    }
    assert _acao(moto, "João", sak, "corrigir-km", {"km": 3600, "motivo": MOTIVO}).status_code == (
        400
    )

    # O gerente corrige na hora, com leitura de correção e auditoria.
    assert _acao(moto, "Bruna", sak, "corrigir-km", corpo).status_code == 403
    assert _acao(moto, "Rodrigo", sak, "corrigir-km", {"km": 3400}).status_code == 400
    resposta = _acao(moto, "Rodrigo", sak, "corrigir-km", corpo)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["km_atual"] == 3400
    leitura = LeituraKm.objects.filter(veiculo=sak).latest("id")
    assert (leitura.km, leitura.correcao, leitura.motivo) == (3400, True, MOTIVO)
    evento = EventoAuditoria.objects.get(acao="veiculo.corrigir_km")
    assert (evento.antes["km_atual"], evento.depois["km_atual"], evento.motivo) == (
        3500,
        3400,
        MOTIVO,
    )
    assert leituras_publicadas[-1] == {"veiculo_id": sak.pk, "km": 3400}


# --- Documentos (VEI-03, AUD-05): T-079 ---


def _aguarda_t079(funcao):
    return pytest.mark.xfail(
        reason="T-079 (backend): documentos, arquivo privado e AUT-06",
        strict=True,
        raises=NotImplementedError,
    )(funcao)


@_aguarda_t079
def test_vei_03_ca_013_17_situacao_do_documento():
    pendente(
        hoje="2026-10-07",
        seguro={
            "2026-10-25": ("vence_em_breve", 18),
            "2026-11-06": ("vence_em_breve", 30),
            "2026-11-07": ("em_dia", 31),
            "2026-10-06": ("vencido", None),
        },
    )


@_aguarda_t079
def test_vei_03_ca_013_18_vencimento_tira_da_frota_disponivel():
    pendente(
        tarefa="aut_06_vencimento_de_documentos",
        as_="2026-10-25 07:00",
        sak1d39_seguro="indisponivel, motivo Seguro vencido",
        qxa4b21_crlv="continua alugado, tarefa urgente para gerentes da Centro",
        ipva_rastreador="não mudam status",
        trinta_dias_antes="alerta aos gerentes, sem mudar status",
        duas_vezes="sem alerta duplicado",
    )


@_aguarda_t079
def test_vei_03_ca_013_19_renovar_nao_libera_sozinho():
    pendente(
        novo_seguro=201,
        anterior="inativo no histórico",
        status="continua indisponivel",
        desbloquear_renovado=200,
        desbloquear_crlv_vencido=(422, "VEI-03"),
    )


@_aguarda_t079
def test_aud_05_ca_013_20_arquivo_privado():
    pendente(
        url_vence_minutos=15,
        cada_get="nova URL",
        invalidos=["11 MB", ".exe"],
        status=400,
        vendedor_envia=403,
    )


# --- Categorias e preços (LOC-01, LOC-15) ---


def test_loc_01_ca_013_21_tabela_do_seed(moto, frota):
    for nome in ("Mariana", "Bruna", "João"):
        corpo = moto.api(nome).get("/api/categorias/", {"filial": frota.centro.pk}).json()
        tabela = {
            c["nome"]: (
                c["veiculos"],
                c["preco_vigente"]["diaria_centavos"],
                c["preco_vigente"]["semanal_centavos"],
                c["preco_vigente"]["mensal_centavos"],
                c["preco_vigente"]["caucao_centavos"],
            )
            for c in corpo["resultados"]
        }
        assert tabela == PRECOS_SEED, nome
        assert {c["preco_vigente"]["vigente_desde"] for c in corpo["resultados"]} == {"2026-10-01"}
    street = next(c for c in corpo["resultados"] if c["nome"] == "Street 150–160")
    assert street["modelos_resumo"] == "CG 160 Fan, Factor 150"
    assert street["proximo_preco"] is None


def test_loc_15_ca_013_22_preco_vigente_na_data(moto, frota):
    street = frota.categorias["Street 150–160"]
    assert _vigente(street, date(2026, 9, 30)).semanal_centavos == 29940
    assert _vigente(street, date(2026, 10, 1)).semanal_centavos == 32900

    historico = moto.api("Bruna").get(f"/api/categorias/{street.pk}/precos/").json()
    assert [
        (p["vigente_desde"], p["semanal_centavos"], p["alterado_por"])
        for p in historico["resultados"]
    ] == [("2026-10-01", 32900, "Mariana"), ("2026-09-01", 29940, "Mariana")]

    mudancas = moto.api("Mariana").get("/api/precos/historico/").json()["resultados"]
    assert {
        "categoria": {"id": street.pk, "nome": "Street 150–160"},
        "vigente_desde": "2026-10-01",
        "campo": "semanal_centavos",
        "antes_centavos": 29940,
        "depois_centavos": 32900,
    }.items() <= next(m for m in mudancas if m["antes_centavos"]).items()
    assert len(mudancas) == 4 * 4 + 1  # o primeiro preço de cada categoria e a Street nova
    assert moto.api("Rodrigo").get("/api/precos/historico/").status_code == 403


def test_loc_15_ca_013_23_preco_novo_nao_reescreve_o_passado(moto, frota, relogio):
    urbana = frota.categorias["Urbana 110–125"]
    api = moto.api("Mariana")
    url = f"/api/categorias/{urbana.pk}/precos/"
    valores = {
        "diaria_centavos": 4990,
        "semanal_centavos": 29940,
        "mensal_centavos": 109000,
        "caucao_centavos": 30000,
    }
    passado = api.post(url, {**valores, "vigente_desde": "2026-10-06"}, format="json")
    assert passado.status_code == 400
    ja_existe = api.post(url, {**valores, "vigente_desde": "2026-10-01"}, format="json")
    assert ja_existe.status_code == 409
    assert ja_existe.json()["codigo"] == "preco_ja_definido"
    assert moto.api("Rodrigo").post(url, valores, format="json").status_code == 403

    leituras.registrar_contador(services.ALVO_CATEGORIA, "locacoes_em_andamento", lambda _: 20)
    try:
        novo = api.post(url, {**valores, "vigente_desde": "2026-11-01"}, format="json")
    finally:
        leituras.remover_contador(services.ALVO_CATEGORIA, "locacoes_em_andamento")
    assert novo.status_code == 201, novo.json()
    assert (novo.json()["diaria_centavos"], novo.json()["locacoes_em_andamento_mantidas"]) == (
        4990,
        20,
    )
    categoria = next(
        c for c in api.get("/api/categorias/").json()["resultados"] if c["id"] == urbana.pk
    )
    assert categoria["preco_vigente"]["diaria_centavos"] == 4490
    assert categoria["proximo_preco"]["vigente_desde"] == "2026-11-01"
    assert categoria["proximo_preco"]["diaria_centavos"] == 4990
    assert _vigente(urbana, date(2026, 10, 7)).diaria_centavos == 4490

    # O preço futuro pode ser trocado até 31 out.
    agendado = f"{url}2026-11-01/"
    relogio.em("2026-10-31 18:00")
    moto._tokens.clear()  # a sessão segue o relógio dos testes
    api = moto.api("Mariana")
    trocado = api.put(agendado, {**valores, "diaria_centavos": 4890}, format="json")
    assert trocado.status_code == 200, trocado.json()
    assert trocado.json()["diaria_centavos"] == 4890
    relogio.em("2026-11-01 08:00")
    moto._tokens.clear()
    api = moto.api("Mariana")
    assert api.put(agendado, valores, format="json").status_code == 409
    assert _vigente(urbana, date(2026, 11, 1)).diaria_centavos == 4890


def test_loc_01_ca_013_24_categoria(moto, frota):
    api = moto.api("Mariana")
    preco = {
        "diaria_centavos": 5490,
        "semanal_centavos": 32900,
        "mensal_centavos": 119000,
        "caucao_centavos": 30000,
    }
    repetida = {"nome": "street 150–160", "tipo_veiculo": "moto", "preco": preco}
    resposta = api.post("/api/categorias/", repetida, format="json")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "categoria_nome_em_uso"

    street = frota.categorias["Street 150–160"]
    resposta = api.patch(f"/api/categorias/{street.pk}/", {"tipo_veiculo": "carro"}, format="json")
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "categoria_com_veiculos"
    resposta = api.post(f"/api/categorias/{street.pk}/desativar/")
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "categoria_com_veiculos"

    rodrigo = moto.api("Rodrigo")
    nova = {"nome": "Trail 300", "tipo_veiculo": "moto", "preco": preco}
    assert rodrigo.post("/api/categorias/", nova, format="json").status_code == 403
    renomear = rodrigo.patch(f"/api/categorias/{street.pk}/", {"nome": "X"}, format="json")
    assert renomear.status_code == 403

    criada = api.post("/api/categorias/", nova, format="json")
    assert criada.status_code == 201, criada.json()
    trail = criada.json()
    assert (trail["veiculos"], trail["preco_vigente"]["vigente_desde"]) == (0, "2026-10-07")
    vazia = api.post(f"/api/categorias/{trail['id']}/desativar/")
    assert vazia.status_code == 200
    assert vazia.json()["ativo"] is False
    cadastro = _cadastro(frota, categoria_id=trail["id"])
    assert rodrigo.post("/api/veiculos/", cadastro, format="json").status_code == 400


def test_loc_02_ca_013_25_extras(moto, frota):
    api = moto.api("Mariana")
    capacete = {"nome": "Capacete extra", "valor_centavos": 1500, "cobranca": "por_periodo"}
    assert moto.api("Rodrigo").post("/api/extras/", capacete, format="json").status_code == 403
    resposta = api.post("/api/extras/", capacete, format="json")
    assert resposta.status_code == 201, resposta.json()
    extra = resposta.json()
    assert {chave: extra[chave] for chave in capacete} == capacete

    mudado = api.patch(f"/api/extras/{extra['id']}/", {"valor_centavos": 1800}, format="json")
    assert (mudado.status_code, mudado.json()["valor_centavos"]) == (200, 1800)
    assert EventoAuditoria.objects.get(acao="extra.editar").antes == {"valor_centavos": 1500}

    escolha = moto.api("Bruna").get("/api/extras/").json()["resultados"]
    assert [e["nome"] for e in escolha] == ["Capacete extra"]
    assert api.post(f"/api/extras/{extra['id']}/desativar/").status_code == 200
    assert moto.api("Bruna").get("/api/extras/").json()["resultados"] == []
    desativados = api.get("/api/extras/?ativo=false").json()["resultados"]
    assert [e["ativo"] for e in desativados] == [False]


# --- Ocupação (VEI-06) ---


def _historico(veiculo: Veiculo, relogio, passos: list[tuple[int, str]]) -> None:
    """`passos`: (dias atrás, status a partir dali)."""
    anterior = ""
    for dias_atras, para in passos:
        HistoricoStatusVeiculo.objects.create(
            veiculo=veiculo,
            de=anterior,
            para=para,
            em=relogio.agora - timedelta(days=dias_atras),
            origem_tipo="manual",
        )
        anterior = para


def test_vei_06_ca_013_26_ocupacao_de_90_dias(moto, frota, relogio):
    urbana = frota.categorias["Urbana 110–125"]
    antigo = criar_veiculo(600, urbana, frota.centro, "a_venda")
    _historico(
        antigo,
        relogio,
        [(120, "disponivel"), (90, "alugado"), (30, "disponivel"), (10, "a_venda")],
    )
    novo = criar_veiculo(601, urbana, frota.centro)
    _historico(novo, relogio, [(30, "disponivel"), (15, "alugado")])

    api = moto.api("Rodrigo")
    assert api.get(_url(antigo)).json()["ocupacao"] == {"pct": "75.00", "periodo_dias": 90}
    assert api.get(_url(novo)).json()["ocupacao"] == {"pct": "50.00", "periodo_dias": 90}
    ficha = api.get(_url(antigo)).json()
    assert [(h["de"], h["para"]) for h in ficha["historico_status"]][:2] == [
        ("disponivel", "a_venda"),
        ("alugado", "disponivel"),
    ]

    # Ocupação da filial, ponderada pelos dias: (60 + 15) ÷ (80 + 30) = 68,18%. Os outros 86
    # veículos vão para a Caucaia (direto no banco) para a conta ficar só com os dois.
    caucaia = _caucaia(moto)
    Veiculo.objects.exclude(pk__in=[antigo.pk, novo.pk]).update(filial=caucaia)
    assert selectors.ocupacao_da_frota(frota.centro.pk) == "68.18"
    lista = moto.api().get("/api/filiais/").json()["resultados"]
    centro = next(f for f in lista if f["id"] == frota.centro.pk)
    assert (centro["indicadores"]["veiculos"], centro["indicadores"]["ocupacao_pct"]) == (
        2,
        "68.18",
    )


# --- Plano e isolamento ---


def test_plt_03_uso_do_plano_conta_so_fora_de_vendido_e_baixado(moto, frota):
    uso = UsoEmpresa.objects.get(empresa=moto.empresa)
    assert uso.veiculos == 86
    sak = frota.veiculos["SAK1D39"]
    _vender(sak)
    uso.refresh_from_db()
    assert uso.veiculos == 85
    services.transicionar(sak, "a_venda", origem=services.OrigemDaMudanca("venda"))
    uso.refresh_from_db()
    assert uso.veiculos == 86


def test_vei_01_veiculo_da_empresa_a_nao_aparece_na_b(moto, frota):
    assert Veiculo.objects.count() == 86
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Veiculo.objects.exists()
    assert not Categoria.objects.exists()
