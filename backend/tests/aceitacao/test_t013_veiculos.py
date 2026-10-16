"""T-013 · Veículos, categorias, documentos, histórico de status (docs/qa/criterios/T-013.md).

Roda na `empresa_a` (host `empresa-a.localhost`) com o plano Profissional, as pessoas do seed e a
frota da Moto Rápida (`frota.py`), com o relógio em 07 out 2026, 10:00.
"""

from datetime import date, datetime, timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.filiais import selectors as filiais_selectors
from apps.filiais import services as filiais
from apps.filiais.models import Filial
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa, UsoEmpresa
from apps.plataforma.services import recalcular_uso
from apps.veiculos import selectors, services
from apps.veiculos.models import (
    Categoria,
    DocumentoVeiculo,
    HistoricoStatusVeiculo,
    LeituraKm,
    TransferenciaVeiculo,
    Veiculo,
)
from apps.veiculos.tasks import aut_06_vencimento_de_documentos
from comum import arquivos, eventos, leituras
from comum.erros import Conflito, ErroDeValidacao, TransicaoInvalida
from seed.ator import como

from .apoio import CONTAGENS_FROTA_SEED, PRECOS_SEED
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
    for nome in ("Bruna", "Lúcia"):
        corpo = moto.api(nome).get(_url(sak)).json()
        assert (corpo["valor_compra_centavos"], corpo["data_compra"]) == (None, None), nome
        lista = moto.api(nome).get("/api/veiculos/", {"busca": "SAK1D39"}).json()
        assert lista["resultados"][0]["valor_compra_centavos"] is None
    # O vistoriador não recebe nem a chave (test_usr_09_vistoriador_ve_veiculo_sem_valores).
    assert "valor_compra_centavos" not in moto.api("João").get(_url(sak)).json()


def _chaves(dados: Any) -> set[str]:
    if isinstance(dados, dict):
        return set(dados) | {c for v in dados.values() for c in _chaves(v)}
    if isinstance(dados, list):
        return {c for v in dados for c in _chaves(v)}
    return set()


SO_VALORES = {"preco_vigente", "proximo_preco", "indicadores_financeiros", "data_compra"}


def test_usr_09_vistoriador_ve_veiculo_sem_valores(moto, frota):
    """D-25: João consulta a frota e a ficha sem diária, preço, venda nem compra; preços e
    extras são só dinheiro e respondem 403 para ele."""
    sak = frota.veiculos["SAK1D39"]
    joao = moto.api("João")
    lista = joao.get("/api/veiculos/").json()
    ficha = joao.get(_url(sak)).json()
    categorias = joao.get("/api/categorias/").json()
    for corpo in (lista, ficha, categorias):
        chaves = _chaves(corpo)
        assert not [c for c in chaves if c.endswith("_centavos")]
        assert not SO_VALORES & chaves
    assert ficha["placa"] == "SAK1D39" and ficha["km_atual"] == sak.km_atual
    assert lista["contagens"]["todos"] > 0
    assert joao.get(f"/api/categorias/{sak.categoria_id}/precos/").status_code == 403
    assert joao.get("/api/extras/").status_code == 403

    # Os demais perfis continuam com a diária (coluna da Frota).
    for nome in ("Mariana", "Rodrigo", "Bruna", "Lúcia"):
        api = moto.api(nome)
        assert api.get(_url(sak)).json()["preco_vigente"]["diaria_centavos"] == 5490, nome
        assert api.get(f"/api/categorias/{sak.categoria_id}/precos/").status_code == 200
        assert api.get("/api/extras/").status_code == 200


def test_usr_09_vendedor_sem_custo_do_veiculo(moto, frota):
    """T-156: rendimento e custo de manutenção (VEI-05) só para administrador, gerente e
    financeiro; para a vendedora a chave vem ausente, não nula, e o resto da ficha não muda."""
    sak = frota.veiculos["SAK1D39"]
    fichas = {
        nome: moto.api(nome).get(_url(sak)).json() for nome in ("Mariana", "Rodrigo", "Lúcia")
    }
    indicadores = {nome: ficha["indicadores_financeiros"] for nome, ficha in fichas.items()}
    esperado = leituras.blocos(selectors.ALVO, sak)["indicadores_financeiros"]
    assert set(esperado) == {"rendeu_no_ano_centavos", "custo_manutencao_ano_centavos"}
    assert indicadores == dict.fromkeys(fichas, esperado)

    bruna = moto.api("Bruna").get(_url(sak))
    assert bruna.status_code == 200
    ficha = bruna.json()
    assert "indicadores_financeiros" not in ficha
    mariana = fichas["Mariana"]
    for chave in (
        "situacao",
        "ocupacao",
        "km_atual",
        "documentos_resumo",
        "preco_vigente",
        "valor_venda_centavos",
        "historico_status",
    ):
        assert ficha[chave] == mariana[chave], chave

    # D-25: o vistoriador continua sem o bloco.
    assert "indicadores_financeiros" not in moto.api("João").get(_url(sak)).json()


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
        # MOV-02, MOV-03 (T-288): "Movimentar" e o motivo quando não pode.
        "movimentar": True,
        "motivo_movimentar": None,
        "aviso_baixar": None,
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


def _transferir(moto: MotoRapida, veiculo: Veiculo, filial_id: int, **campos: Any) -> Veiculo:
    """A transferência pela chegada da movimentação ou pela importação: a rota saiu (ADR 0028)."""
    with como(moto.pessoas["Rodrigo"]):
        return services.transferir(veiculo, filial_id, **campos)


def test_vei_04_mov_06_rota_transferir_saiu(moto, frota):
    """'Transferir' abre a Nova movimentação (MOV-06); a rota antiga não existe mais."""
    caucaia = _caucaia(moto, "Rodrigo")
    sak = frota.veiculos["SAK1D39"]
    resposta = _acao(moto, "Rodrigo", sak, "transferir", {"filial_destino_id": caucaia.pk})
    assert resposta.status_code == 404
    sak.refresh_from_db()
    assert sak.filial_id == frota.centro.pk


def test_vei_04_ca_013_13_transferencia_so_disponivel(moto, frota):
    caucaia = _caucaia(moto, "Rodrigo")
    sak, qxa = frota.veiculos["SAK1D39"], frota.veiculos["QXA4B21"]

    _transferir(moto, sak, caucaia.pk, motivo="Falta moto na Caucaia")
    assert sak.filial_id == caucaia.pk
    transferencia = TransferenciaVeiculo.objects.get(veiculo=sak)
    assert (transferencia.filial_origem_id, transferencia.filial_destino_id) == (
        frota.centro.pk,
        caucaia.pk,
    )
    assert transferencia.por_id == moto.pessoas["Rodrigo"].pk
    assert EventoAuditoria.objects.filter(acao="veiculo.transferir", regra="VEI-04").exists()
    # Categoria da empresa passa direto (CA-013-27): continua na Street 150–160.
    street = frota.categorias["Street 150–160"]
    assert sak.categoria_id == street.pk
    assert (transferencia.categoria_origem, transferencia.categoria_destino) == (street, street)

    with pytest.raises(Conflito) as erro:
        _transferir(moto, qxa, caucaia.pk)
    assert erro.value.codigo == "VEI-04"
    assert erro.value.mensagem == "Só é possível transferir um veículo disponível"

    pop = Veiculo.objects.filter(status="disponivel", filial=frota.centro).order_by("id")[0]
    with pytest.raises(ErroDeValidacao):
        _transferir(moto, pop, frota.centro.pk)
    messejana = moto.criar(_filial("Filial Messejana", cidade="Fortaleza")).json()
    filiais.desativar(Filial.objects.get(pk=messejana["id"]), "Fechou")
    with pytest.raises(ErroDeValidacao):
        _transferir(moto, pop, messejana["id"])
    pop.refresh_from_db()
    assert pop.filial_id == frota.centro.pk


def _categoria_de_filial(moto: MotoRapida, nome: str, filial: Filial, diaria: int) -> int:
    corpo = {
        "nome": nome,
        "tipo_veiculo": "moto",
        "filial_id": filial.pk,
        "preco": {
            "diaria_centavos": diaria,
            "semanal_centavos": diaria * 6,
            "mensal_centavos": diaria * 22,
            "caucao_centavos": 30000,
        },
    }
    resposta = moto.api("Mariana").post("/api/categorias/", corpo, format="json")
    assert resposta.status_code == 201, resposta.json()
    return int(resposta.json()["id"])


def test_vei_04_fil_04_ca_013_27_categoria_so_da_filial_na_transferencia(moto, frota):
    caucaia = _caucaia(moto, "Rodrigo")
    sak = frota.veiculos["SAK1D39"]
    street_centro = _categoria_de_filial(moto, "Street Centro", frota.centro, 4490)
    street_caucaia = _categoria_de_filial(moto, "Street Caucaia", caucaia, 4990)
    caucaia_inativa = _categoria_de_filial(moto, "Street Caucaia antiga", caucaia, 3990)
    desativar = moto.api("Mariana").post(
        f"/api/categorias/{caucaia_inativa}/desativar/", {}, format="json"
    )
    assert desativar.status_code == 200, desativar.json()
    resposta = moto.api("Rodrigo").patch(_url(sak), {"categoria_id": street_centro}, format="json")
    assert resposta.status_code == 200, resposta.json()
    sak.refresh_from_db()

    # Sem a categoria no destino: recusa em `categoria_id`, e o veículo não sai da Centro.
    with pytest.raises(ErroDeValidacao) as erro:
        _transferir(moto, sak, caucaia.pk)
    assert "categoria_id" in erro.value.campos
    invalidas = [street_centro, caucaia_inativa, frota.categorias["Carro compacto"].pk]
    for categoria_id in invalidas:
        with pytest.raises(ErroDeValidacao) as erro:
            _transferir(moto, sak, caucaia.pk, categoria_id=categoria_id)
        assert "categoria_id" in erro.value.campos, categoria_id
    sak.refresh_from_db()
    assert (sak.filial_id, sak.categoria_id) == (frota.centro.pk, street_centro)
    assert not TransferenciaVeiculo.objects.filter(veiculo=sak).exists()

    # Com a Street Caucaia: vai, com o preço dela.
    _transferir(moto, sak, caucaia.pk, categoria_id=street_caucaia)
    ficha = moto.api("Rodrigo").get(_url(sak)).json()
    assert ficha["filial"]["id"] == caucaia.pk
    assert ficha["categoria"] == {"id": street_caucaia, "nome": "Street Caucaia"}
    assert ficha["preco_vigente"]["diaria_centavos"] == 4990
    transferencia = TransferenciaVeiculo.objects.get(veiculo=sak)
    assert (transferencia.categoria_origem_id, transferencia.categoria_destino_id) == (
        street_centro,
        street_caucaia,
    )
    evento = EventoAuditoria.objects.get(acao="veiculo.transferir", objeto_id=sak.pk)
    assert (evento.antes["categoria_id"], evento.depois["categoria_id"]) == (
        street_centro,
        street_caucaia,
    )

    # De volta para a Centro com a Street 150–160, da empresa: diária 5490.
    empresa = frota.categorias["Street 150–160"].pk
    _transferir(moto, sak, frota.centro.pk, categoria_id=empresa)
    ficha = moto.api("Rodrigo").get(_url(sak)).json()
    assert ficha["categoria"]["nome"] == "Street 150–160"
    assert ficha["preco_vigente"]["diaria_centavos"] == 5490


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


# --- Documentos (VEI-03, AUT-06, AUD-05) ---

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _pdf(nome: str = "apolice.pdf", conteudo: bytes = PDF) -> SimpleUploadedFile:
    return SimpleUploadedFile(nome, conteudo, content_type="application/pdf")


def _enviar(moto: MotoRapida, nome: str, veiculo: Veiculo, tipo: str, validade: str, **extra):
    corpo = {"tipo": tipo, "validade": validade, **extra}
    return moto.api(nome).post(_url(veiculo, "documentos"), corpo, format="multipart")


def _documento(veiculo: Veiculo, tipo: str, validade: str) -> DocumentoVeiculo:
    return services.enviar_documento(veiculo, tipo, date.fromisoformat(validade))


def test_vei_03_ca_013_17_situacao_do_documento(moto, frota):
    sak = frota.veiculos["SAK1D39"]
    casos = {
        "2026-10-25": ("vence_em_breve", 18),
        "2026-11-06": ("vence_em_breve", 30),
        "2026-11-07": ("em_dia", 31),
        "2026-10-06": ("vencido", None),
    }
    for validade, esperado in casos.items():
        resposta = _enviar(moto, "Rodrigo", sak, "seguro", validade)
        assert resposta.status_code == 201, resposta.json()
        assert (resposta.json()["situacao"], resposta.json()["dias_para_vencer"]) == esperado
        [ativo] = moto.api("Bruna").get(_url(sak, "documentos")).json()["resultados"]
        assert (ativo["validade"], ativo["situacao"], ativo["dias_para_vencer"]) == (
            validade,
            *esperado,
        )
    # O resumo da Frota mostra a pior situação dos documentos ativos.
    _documento(sak, "crlv", "2027-03-31")
    ficha = moto.api("Rodrigo").get(_url(sak)).json()
    assert ficha["documentos_resumo"] == {"pior_situacao": "vencido"}
    linha = moto.api("Rodrigo").get("/api/veiculos/", {"busca": "SAK1D39"}).json()
    assert linha["resultados"][0]["documentos_resumo"] == {"pior_situacao": "vencido"}
    qxa = frota.veiculos["QXA4B21"]
    assert moto.api("Rodrigo").get(_url(qxa)).json()["documentos_resumo"] is None


def _avisos(pessoa: Any) -> list[tuple[str, bool]]:
    return list(
        Notificacao.objects.filter(destinatario=pessoa)
        .order_by("id")
        .values_list("tipo", "urgente")
    )


def test_vei_03_aut_06_ca_013_18_vencimento_tira_da_frota_disponivel(moto, frota, relogio):
    sak, qxa = frota.veiculos["SAK1D39"], frota.veiculos["QXA4B21"]
    pop = Veiculo.objects.filter(status="disponivel", filial=frota.centro).exclude(pk=sak.pk)[0]
    _documento(sak, "seguro", "2026-10-25")
    _documento(qxa, "crlv", "2026-10-25")
    _documento(pop, "ipva", "2026-10-25")
    _documento(pop, "rastreador", "2026-10-25")
    rodrigo, mariana = moto.pessoas["Rodrigo"], moto.pessoas["Mariana"]

    # 30 dias antes: o alerta vai aos gerentes da Filial Centro, e nada muda de status.
    relogio.em("2026-09-25 07:00")
    aut_06_vencimento_de_documentos("empresa_a")
    assert _avisos(rodrigo) == [("documento_vencendo", False)] * 4
    assert _avisos(mariana) == []
    assert set(
        Veiculo.objects.filter(pk__in=[sak.pk, pop.pk]).values_list("status", flat=True)
    ) == {"disponivel"}
    aut_06_vencimento_de_documentos("empresa_a")  # de novo no mesmo dia: sem alerta duplicado
    assert len(_avisos(rodrigo)) == 4
    titulos = Notificacao.objects.filter(destinatario=rodrigo).values_list("titulo", flat=True)
    assert "Seguro da SAK1D39 vence em 25/10/2026" in titulos

    # No dia, às 07:00.
    relogio.em("2026-10-25 07:00")
    aut_06_vencimento_de_documentos("empresa_a")
    sak.refresh_from_db()
    assert (sak.status, sak.motivo_status) == ("indisponivel", "Seguro vencido")
    historico = sak.historico.latest("id")
    assert (historico.origem_tipo, historico.motivo) == ("documento", "Seguro vencido")
    qxa.refresh_from_db()
    assert qxa.status == "alugado"
    urgentes = Notificacao.objects.filter(destinatario=rodrigo, urgente=True)
    assert list(urgentes.values_list("tipo", "titulo")) == [
        (
            "documento_vencido_alugado",
            "CRLV da QXA4B21 venceu com o veículo alugado. Regularize o documento.",
        )
    ]
    pop.refresh_from_db()
    assert pop.status == "disponivel"  # IPVA e rastreador não mudam o status

    aut_06_vencimento_de_documentos("empresa_a")  # de novo: nada se repete
    assert Notificacao.objects.filter(destinatario=rodrigo, urgente=True).count() == 1
    assert sak.historico.filter(para="indisponivel").count() == 1


def test_vei_03_aut_06_ca_013_28_reservado_ou_em_manutencao_no_vencimento(moto, frota, relogio):
    rht, pmz = frota.veiculos["RHT9F02"], frota.veiculos["PMZ3E17"]
    assert (rht.status, pmz.status) == ("reservado", "em_manutencao")
    _documento(rht, "crlv", "2026-10-25")
    _documento(pmz, "seguro", "2026-10-25")
    _documento(rht, "ipva", "2026-10-25")
    _documento(pmz, "rastreador", "2026-10-25")
    rodrigo = moto.pessoas["Rodrigo"]

    # 30 dias antes, os quatro só geram alerta.
    relogio.em("2026-09-25 07:00")
    aut_06_vencimento_de_documentos("empresa_a")
    assert _avisos(rodrigo) == [("documento_vencendo", False)] * 4

    # No dia: os dois continuam como estão, e os gerentes recebem uma tarefa urgente para cada um.
    relogio.em("2026-10-25 07:00")
    aut_06_vencimento_de_documentos("empresa_a")
    rht.refresh_from_db()
    pmz.refresh_from_db()
    assert (rht.status, pmz.status) == ("reservado", "em_manutencao")
    urgentes = Notificacao.objects.filter(destinatario=rodrigo, urgente=True).order_by("id")
    assert list(urgentes.values_list("tipo", "titulo")) == [
        (
            "documento_vencido_reservado",
            "CRLV da RHT9F02 venceu com o veículo reservado. Regularize o documento.",
        ),
        (
            "documento_vencido_em_manutencao",
            "Seguro da PMZ3E17 venceu com o veículo em manutenção. Regularize o documento.",
        ),
    ]
    assert not Notificacao.objects.filter(destinatario=moto.pessoas["Mariana"]).exists()

    # De novo no mesmo dia: nada se repete. IPVA e rastreador não geram tarefa.
    aut_06_vencimento_de_documentos("empresa_a")
    assert urgentes.count() == 2
    assert Notificacao.objects.filter(destinatario=rodrigo).count() == 6


def test_vei_03_ca_013_19_renovar_nao_libera_sozinho(moto, frota, relogio):
    sak = frota.veiculos["SAK1D39"]
    antigo = _documento(sak, "seguro", "2026-10-25")
    _documento(sak, "crlv", "2027-03-31")
    relogio.em("2026-10-25 07:00")
    aut_06_vencimento_de_documentos("empresa_a")
    sak.refresh_from_db()
    assert sak.status == "indisponivel"

    resposta = _enviar(moto, "Rodrigo", sak, "seguro", "2027-10-25", arquivo=_pdf())
    assert resposta.status_code == 201, resposta.json()
    antigo.refresh_from_db()
    assert antigo.ativo is False
    sak.refresh_from_db()
    assert sak.status == "indisponivel"
    historico = moto.api("Rodrigo").get(_url(sak, "documentos/historico")).json()["resultados"]
    assert {(d["id"], d["ativo"]) for d in historico if d["tipo"] == "seguro"} == {
        (antigo.pk, False),
        (resposta.json()["id"], True),
    }
    assert EventoAuditoria.objects.filter(acao="documento_veiculo.enviar", regra="VEI-03").exists()

    assert _acao(moto, "Rodrigo", sak, "desbloquear").status_code == 200

    # Com o CRLV vencido, não desbloqueia.
    services.bloquear(sak, "Conferência")
    _documento(sak, "crlv", "2026-10-20")
    resposta = _acao(moto, "Rodrigo", sak, "desbloquear")
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "VEI-03",
        "mensagem": "Renove o CRLV vencido antes de desbloquear o veículo.",
        "detalhes": {"documentos": ["crlv"]},
    }
    sak.refresh_from_db()
    assert sak.status == "indisponivel"


def test_aud_05_ca_013_20_arquivo_privado(moto, frota, relogio):
    sak = frota.veiculos["SAK1D39"]
    resposta = _enviar(moto, "Rodrigo", sak, "seguro", "2027-10-25", arquivo=_pdf())
    assert resposta.status_code == 201, resposta.json()
    documento = DocumentoVeiculo.objects.get(pk=resposta.json()["id"])
    # Prefixo <schema>/<app>/<model>/<id>/ (ADR 0009); o nome original fica fora do caminho.
    assert documento.arquivo.name.startswith(f"empresa_a/veiculos/documentoveiculo/{documento.pk}/")
    assert documento.arquivo.name.endswith(".pdf")
    assert "apolice" not in documento.arquivo.name
    assert arquivos.guardados[documento.arquivo.name][0] == PDF

    api = moto.api("João")
    primeiro = api.get(_url(sak, "documentos")).json()["resultados"][0]["arquivo"]
    segundo = api.get(_url(sak, "documentos")).json()["resultados"][0]["arquivo"]
    assert primeiro["nome"] == "apolice.pdf"
    assert primeiro["url"] != segundo["url"]
    expira = datetime.fromisoformat(primeiro["url_expira_em"])
    assert expira - relogio.agora == timedelta(minutes=15)

    grande = _pdf(conteudo=PDF + b"0" * (10 * 1024 * 1024))
    exe = SimpleUploadedFile("apolice.exe", b"MZ\x90\x00" + b"0" * 100)
    disfarcado = _pdf("apolice.pdf", b"MZ\x90\x00" + b"0" * 100)
    for invalido in (grande, exe, disfarcado):
        resposta = _enviar(moto, "Rodrigo", sak, "crlv", "2027-03-31", arquivo=invalido)
        assert resposta.status_code == 400, resposta.json()
        assert "arquivo" in resposta.json()["campos"]
    assert not DocumentoVeiculo.objects.filter(veiculo=sak, tipo="crlv").exists()

    resposta = _enviar(moto, "Bruna", sak, "crlv", "2027-03-31", arquivo=_pdf())
    assert resposta.status_code == 403


# --- Categorias e preços (LOC-01, LOC-15) ---


def test_loc_01_ca_013_21_tabela_do_seed(moto, frota):
    for nome in ("Mariana", "Bruna", "Lúcia"):  # o vistoriador vê sem preço (USR-09)
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


def test_vei_06_ca_013_29_ocupacao_com_fracao_de_dia(moto, frota, relogio):
    """Na frota desde 27 set, alugado em 02 out às 14:00, relógio em 07 out 00:00: 44,17%."""
    relogio.em("2026-10-07 00:00")
    urbana = frota.categorias["Urbana 110–125"]
    api = moto.api("Rodrigo")

    def _historico_em(veiculo: Veiculo, passos: list[tuple[str, str]]) -> None:
        anterior = ""
        for quando, para in passos:
            HistoricoStatusVeiculo.objects.create(
                veiculo=veiculo,
                de=anterior,
                para=para,
                em=relogio.em(quando),
                origem_tipo="manual",
            )
            anterior = para
        relogio.em("2026-10-07 00:00")

    tarde = criar_veiculo(602, urbana, frota.centro)
    _historico_em(tarde, [("2026-09-27 00:00", "disponivel"), ("2026-10-02 14:00", "alugado")])
    # 4,4167 dias alugados ÷ 10 dias na frota; contar por dia daria 40,00 ou 50,00.
    assert api.get(_url(tarde)).json()["ocupacao"] == {"pct": "44.17", "periodo_dias": 90}

    # Mesmo veículo alugado às 00:00 de 02 out: 5 ÷ 10, igual a contar dias.
    cedo = criar_veiculo(603, urbana, frota.centro)
    _historico_em(cedo, [("2026-09-27 00:00", "disponivel"), ("2026-10-02 00:00", "alugado")])
    assert api.get(_url(cedo)).json()["ocupacao"] == {"pct": "50.00", "periodo_dias": 90}


def test_vei_06_veiculo_recem_cadastrado_sem_500(moto, frota, relogio):
    """T-240: a ficha lida meio segundo depois do cadastro tem menos de 1 s na frota; a
    ocupação é 0,00%, sem 500."""
    relogio.em("2026-10-07 10:00:00")
    criado = moto.api("Mariana").post("/api/veiculos/", _cadastro(frota), format="json")
    assert criado.status_code == 201, criado.json()
    relogio.em("2026-10-07 10:00:00.500")
    ficha = moto.api("Mariana").get(f"/api/veiculos/{criado.json()['id']}/")
    assert ficha.status_code == 200, ficha.content
    assert ficha.json()["ocupacao"] == {"pct": "0.00", "periodo_dias": 90}
    assert selectors._pct(timedelta(0), timedelta(milliseconds=500)) == "0.00"


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
