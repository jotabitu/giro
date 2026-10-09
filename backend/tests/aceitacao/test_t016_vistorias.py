"""T-016 · Vistoria de saída e devolução com acerto (docs/qa/criterios/T-016.md).

Parte 1 (divisão de 09 out): a vistoria de saída e de chegada como entidade, a agenda e as avarias
abertas: CA-016-01 a 08 e 21. A devolução e o acerto (CA-016-09 a 14, 16, 17, 19 e 20) ficam com a
parte 2, a troca de veículo (CA-016-15) com a T-092 e a devolução em dinheiro (CA-016-18) com o
caixa da T-017; esses ficam `xfail` aqui.

Cenário da T-015: Moto Rápida em 07 out 2026, 10:00, Filial Centro, com a LOC-2856 de Lucas
(SAK1D39, Street semanal) e a carteira de outubro quando o caso é do seed.
"""

import io
from datetime import date, timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente, TipoDocumentoCliente
from apps.financeiro.models import ContaReceber
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import LeituraKm, Veiculo
from apps.vistorias import services
from apps.vistorias.models import Avaria, FotoVistoria, Vistoria
from comum import arquivos

from . import carteira
from .apoio import aguarda, pendente
from .frota import montar_frota
from .test_t012_filiais import MotoRapida
from .test_t013_veiculos import _caucaia
from .test_t015_locacoes import LISTA, Cenario, _assinar, _pagar

VISTORIAS = "/api/vistorias/"
AGENDA = "/api/vistorias/agenda/"
POSICOES = ("frente", "traseira", "lado_esquerdo", "lado_direito", "painel")
ITENS = ["pneus_freios", "luzes_buzina", "retrovisores", "documento_chave", "acessorios"]
ENDERECO = {
    "cep": "60325000",
    "logradouro": "Rua Padre Mororó",
    "numero": "145",
    "complemento": None,
    "bairro": "Centro",
    "cidade": "Fortaleza",
    "uf": "CE",
}


def _jpg(nome: str = "foto.jpg", gps: bool = False) -> SimpleUploadedFile:
    imagem = Image.new("RGB", (8, 8), "red")
    saida = io.BytesIO()
    exif = Image.Exif()
    if gps:
        exif[0x8825] = {1: "S", 2: (3.0, 43.0, 12.0), 3: "W", 4: (38.0, 32.0, 6.0)}
    imagem.save(saida, format="JPEG", exif=exif.tobytes())
    return SimpleUploadedFile(nome, saida.getvalue(), content_type="image/jpeg")


def _completar(cliente: Cliente) -> None:
    """CLI-03: endereço e os documentos enviados; o cadastro fica `ativo`."""
    clientes_services.editar(cliente, {"endereco": ENDERECO})
    for tipo in TipoDocumentoCliente:
        clientes_services.enviar_documento(cliente, tipo.value, _jpg(f"{tipo.value}.jpg"))
    cliente.refresh_from_db()
    assert cliente.status == "ativo", clientes_services.selectors.pendencias(cliente)


@pytest.fixture
def cenario(empresa_a, planos, relogio) -> Cenario:
    locacoes_leituras.registrar()
    moto = MotoRapida(empresa_a, planos["Profissional"])
    return Cenario(moto, montar_frota(moto))


@pytest.fixture
def lucas(cenario) -> Cliente:
    cliente = cenario.cliente("Lucas")
    _completar(cliente)
    return cliente


def _abrir(cenario: Cenario, locacao_id: int, quem: str = "João") -> Any:
    return cenario.moto.api(quem).post(
        f"{LISTA}{locacao_id}/vistorias/", {"tipo": "saida"}, format="json"
    )


def _saida(cenario: Cenario, locacao_id: int, quem: str = "João") -> dict[str, Any]:
    resposta = _abrir(cenario, locacao_id, quem)
    assert resposta.status_code in (200, 201), resposta.json()
    return dict(resposta.json())


def _foto(cenario: Cenario, vistoria_id: int, posicao: str, quem: str = "João", **kw: Any) -> Any:
    return cenario.moto.api(quem).post(
        f"{VISTORIAS}{vistoria_id}/fotos/",
        {"posicao": posicao, "arquivo": kw.get("arquivo") or _jpg(f"{posicao}.jpg")},
        format="multipart",
    )


def _patch(cenario: Cenario, vistoria_id: int, quem: str = "João", **corpo: Any) -> Any:
    return cenario.moto.api(quem).patch(f"{VISTORIAS}{vistoria_id}/", corpo, format="json")


def _preencher(
    cenario: Cenario,
    vistoria: dict[str, Any],
    km: int,
    *,
    quem: str = "João",
    posicoes: tuple[str, ...] = POSICOES,
    sem_resposta: tuple[str, ...] = (),
    combustivel: str | None = "cheio",
) -> None:
    for posicao in posicoes:
        assert _foto(cenario, vistoria["id"], posicao, quem).status_code == 201
    itens = [
        {"codigo": i["codigo"], "ok": None if i["codigo"] in sem_resposta else True}
        for i in vistoria["itens"]
    ]
    resposta = _patch(cenario, vistoria["id"], quem, km=km, itens=itens, combustivel=combustivel)
    assert resposta.status_code == 200, resposta.json()


def _concluir(cenario: Cenario, vistoria_id: int, quem: str = "João") -> Any:
    return cenario.moto.api(quem).post(f"{VISTORIAS}{vistoria_id}/concluir/")


def _lucas_2856(cenario: Cenario, **campos: Any) -> dict[str, Any]:
    criada = cenario.confirmada(**campos)
    assert criada["codigo"] == "LOC-2856"
    return criada


def _chaves(dados: Any) -> set[str]:
    if isinstance(dados, dict):
        return set(dados) | {c for v in dados.values() for c in _chaves(v)}
    if isinstance(dados, list):
        return {c for v in dados for c in _chaves(v)}
    return set()


def _avaria_anterior(cenario: Cenario, veiculo: Veiculo, descricao: str) -> Avaria:
    """Uma avaria aberta registrada numa locação anterior do mesmo veículo."""
    anterior = Locacao.objects.create(
        filial=cenario.frota.centro,
        cliente=cenario.cliente("Carlos"),
        veiculo=veiculo,
        vendedor=cenario.pessoas["Bruna"],
        periodicidade="semanal",
        inicio=carteira.momento("2026-09-01 09:00"),
        fim_previsto=carteira.momento("2026-09-08 09:00"),
        forma_pagamento="pix",
        status="encerrada",
    )
    vistoria = Vistoria.objects.create(
        locacao=anterior,
        veiculo=veiculo,
        tipo="devolucao",
        status="concluida",
        km=3000,
        concluida_em=carteira.momento("2026-09-08 09:30"),
    )
    foto = FotoVistoria.objects.create(
        vistoria=vistoria, posicao="avaria", tirada_em=carteira.momento("2026-09-08 09:20")
    )
    return Avaria.objects.create(vistoria=vistoria, veiculo=veiculo, descricao=descricao, foto=foto)


# --- CA-016-01 · Lista pronta ao criar (VIS-01, VIS-02) ---


def test_vis_02_ca_016_01_lista_pronta_ao_criar(cenario):
    capacete = veiculos_services.criar_extra(
        {"nome": "Capacete extra", "valor_centavos": 1500, "cobranca": "por_periodo"}
    )
    criada = _lucas_2856(cenario, extras=[{"extra_id": capacete.pk, "quantidade": 1}])
    risco = _avaria_anterior(cenario, cenario.sak, "Risco no tanque, lado esquerdo")

    resposta = _abrir(cenario, criada["id"])
    assert resposta.status_code == 201, resposta.json()
    vistoria = resposta.json()
    assert (vistoria["tipo"], vistoria["status"]) == ("saida", "rascunho")
    assert vistoria["locacao"] == {"id": criada["id"], "codigo": "LOC-2856"}
    assert vistoria["veiculo"]["placa"] == "SAK1D39"
    assert [i["rotulo"] for i in vistoria["itens"]] == [
        "Pneus e freios",
        "Luzes e buzina",
        "Retrovisores",
        "Documento e chave",
        "Acessórios entregues",
        "Capacete extra",
    ]
    assert all(i["ok"] is None for i in vistoria["itens"])
    assert vistoria["avarias"] == [
        {
            "id": risco.pk,
            "descricao": "Risco no tanque, lado esquerdo",
            "preexistente": True,
            "foto_id": risco.foto_id,
            "vai_para_oficina": False,
            "origem": "Registrado na vistoria anterior; não será cobrado do cliente na devolução.",
        }
    ]
    assert vistoria["fotos_obrigatorias"] == {"feitas": 0, "total": 5, "faltam": list(POSICOES)}
    assert vistoria["km_ultima_leitura"]["km"] == 3120

    # Criar de novo devolve o mesmo rascunho.
    de_novo = _abrir(cenario, criada["id"], "Bruna")
    assert de_novo.status_code == 200
    assert de_novo.json()["id"] == vistoria["id"]
    assert Vistoria.objects.filter(locacao_id=criada["id"]).count() == 1


def test_vis_01_saida_so_para_locacao_aguardando_retirada(cenario):
    rascunho = cenario.criar()
    resposta = _abrir(cenario, rascunho["id"])
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "transicao_locacao"


def test_vis_01_avaria_da_saida_e_preexistente_e_sem_valor(cenario, lucas):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    foto = _foto(cenario, vistoria["id"], "avaria").json()
    api = cenario.moto.api("Bruna")
    url = f"{VISTORIAS}{vistoria['id']}/avarias/"
    com_valor = api.post(
        url,
        {"descricao": "Banco rasgado", "foto_id": foto["id"], "valor_centavos": 5000},
        format="json",
    )
    assert com_valor.status_code == 400
    assert "valor_centavos" in com_valor.json()["campos"]
    sem_foto = api.post(url, {"descricao": "Banco rasgado", "foto_id": 999999}, format="json")
    assert sem_foto.status_code == 400
    criada = api.post(url, {"descricao": "Banco rasgado", "foto_id": foto["id"]}, format="json")
    assert criada.status_code == 201, criada.json()
    assert criada.json()["preexistente"] is True

    # Avaria nova do rascunho pode ser removida (ainda não é registro de negócio).
    removida = api.delete(f"{url}{criada.json()['id']}/")
    assert removida.status_code == 204
    assert not Avaria.objects.filter(vistoria_id=vistoria["id"]).exists()


def test_vis_01_saida_de_locacao_cancelada_nao_conclui(cenario, lucas):
    criada = _lucas_2856(cenario)
    vistoria = _saida(cenario, criada["id"])
    _preencher(cenario, vistoria, 3125)
    resposta = cenario.moto.api("Rodrigo").post(
        f"{LISTA}{criada['id']}/cancelar/", {"motivo": "Cliente desistiu"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    concluir = _concluir(cenario, vistoria["id"])
    assert concluir.status_code == 409
    assert concluir.json()["codigo"] == "transicao_locacao"
    assert Vistoria.objects.get(pk=vistoria["id"]).status == "rascunho"
    assert Veiculo.objects.get(pk=cenario.sak.pk).km_atual == 3120


# --- CA-016-02 · O que impede concluir (VIS-01, VIS-02, VIS-03, VEI-01) ---


def test_vis_01_vis_02_vis_03_vei_01_ca_016_02_todas_as_pendencias(cenario, lucas):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    _preencher(
        cenario,
        vistoria,
        3000,
        posicoes=("frente", "traseira", "lado_esquerdo"),
        sem_resposta=("retrovisores",),
        combustivel=None,
    )
    corpo = cenario.moto.api("João").get(f"{VISTORIAS}{vistoria['id']}/").json()
    assert corpo["pendencias"] == ["fotos", "itens", "combustivel", "km"]
    assert corpo["pode_concluir"] is False
    assert corpo["fotos_obrigatorias"]["faltam"] == ["lado_direito", "painel"]

    resposta = _concluir(cenario, vistoria["id"])
    assert resposta.status_code == 422
    erro = resposta.json()
    pendencias = erro["detalhes"]["pendencias"]
    assert [p["codigo"] for p in pendencias] == ["VIS-01", "VIS-02", "VIS-03", "VEI-01"]
    assert pendencias[0]["faltam"] == ["lado_direito", "painel"]
    assert pendencias[0]["mensagem"] == "Faltam as fotos: lado direito e painel."
    assert pendencias[1]["itens"] == ["retrovisores"]
    assert "Corrigir km" in pendencias[3]["mensagem"]
    assert pendencias[3]["corrigir_km"] == f"/api/veiculos/{cenario.sak.pk}/corrigir-km/"
    assert erro["mensagem"] == "Resolva as 4 pendências antes de concluir."

    # Com tudo preenchido, conclui.
    _preencher(cenario, vistoria, 3125, posicoes=("lado_direito", "painel"))
    concluida = _concluir(cenario, vistoria["id"])
    assert concluida.status_code == 200, concluida.json()
    assert concluida.json()["status"] == "concluida"


# --- CA-016-03 · Cliente precisa estar liberado (CLI-03, CLI-02, CLI-05) ---


def _so_o_cliente(resposta: Any) -> list[str]:
    assert resposta.status_code == 422, resposta.json()
    return [p["codigo"] for p in resposta.json()["detalhes"]["pendencias"]]


def test_cli_03_cli_02_cli_05_ca_016_03_cliente_liberado(cenario, relogio):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    _preencher(cenario, vistoria, 3125)
    lucas = cenario.cliente("Lucas")
    assert lucas.status == "incompleto"
    resposta = _concluir(cenario, vistoria["id"])
    assert _so_o_cliente(resposta) == ["CLI-03"]
    assert resposta.json()["codigo"] == "CLI-03"

    _completar(lucas)
    hoje = relogio.agora.date()
    Cliente.objects.filter(pk=lucas.pk).update(cnh_validade=hoje - timedelta(days=31))
    assert _so_o_cliente(_concluir(cenario, vistoria["id"])) == ["CLI-02"]

    Cliente.objects.filter(pk=lucas.pk).update(cnh_validade=hoje - timedelta(days=20))
    clientes_services.bloquear(Cliente.objects.get(pk=lucas.pk), "Cheque devolvido")
    assert _so_o_cliente(_concluir(cenario, vistoria["id"])) == ["CLI-05"]

    clientes_services.desbloquear(Cliente.objects.get(pk=lucas.pk), "Acertou o cheque")
    concluida = _concluir(cenario, vistoria["id"])
    assert concluida.status_code == 200, concluida.json()


# --- CA-016-21 · Documento do veículo vencido na retirada (VEI-03) ---


def test_vei_03_ca_016_21_documento_vencido_na_retirada(cenario, relogio):
    rht = cenario.frota.veiculos["RHT9F02"]
    veiculos_services.transicionar(rht, "disponivel", origem=veiculos_services.MANUAL)
    diego = cenario.cliente("Diego")
    _completar(diego)
    criada = cenario.confirmada(
        cliente="Diego", veiculo=rht, inicio="2026-10-26T12:00:00Z", periodicidade="diaria"
    )
    rht.refresh_from_db()
    assert (criada["status"], rht.status) == ("aguardando_retirada", "reservado")
    veiculos_services.enviar_documento(rht, "crlv", date(2026, 10, 25))
    veiculos_services.enviar_documento(rht, "ipva", date(2026, 10, 25))
    veiculos_services.enviar_documento(rht, "rastreador", date(2026, 10, 25))

    relogio.em("2026-10-26 09:00")
    vistoria = _saida(cenario, criada["id"])
    _preencher(cenario, vistoria, 52400)
    resposta = _concluir(cenario, vistoria["id"])
    assert resposta.status_code == 422
    erro = resposta.json()
    assert erro["codigo"] == "VEI-03"
    assert erro["detalhes"]["documentos"] == ["crlv"]
    assert erro["mensagem"] == "Renove o CRLV vencido antes da retirada."
    locacao = Locacao.objects.get(pk=criada["id"])
    rht.refresh_from_db()
    assert (locacao.status, rht.status) == ("aguardando_retirada", "reservado")
    assert rht.km_atual == 52310  # nada mudou

    veiculos_services.enviar_documento(rht, "seguro", date(2026, 10, 25))
    assert _concluir(cenario, vistoria["id"]).json()["detalhes"]["documentos"] == [
        "crlv",
        "seguro",
    ]

    # Renovados (IPVA e rastreador continuam vencidos e não impedem).
    veiculos_services.enviar_documento(rht, "crlv", date(2027, 10, 25))
    veiculos_services.enviar_documento(rht, "seguro", date(2027, 10, 25))
    concluida = _concluir(cenario, vistoria["id"])
    assert concluida.status_code == 200, concluida.json()
    _assinar(criada["id"])
    _pagar(criada["id"])
    locacao.refresh_from_db()
    rht.refresh_from_db()
    assert (locacao.status, rht.status) == ("ativa", "alugado")


# --- CA-016-04 · Concluída não se edita (VIS-04) ---


def test_vis_04_ca_016_04_concluida_nao_se_edita_e_correcao(cenario, lucas):
    criada = _lucas_2856(cenario)
    vistoria = _saida(cenario, criada["id"])
    _preencher(cenario, vistoria, 3125)
    assert _concluir(cenario, vistoria["id"]).status_code == 200

    assert _patch(cenario, vistoria["id"], km=3200).status_code == 409
    assert _foto(cenario, vistoria["id"], "frente").status_code == 409
    avaria = cenario.moto.api("João").post(
        f"{VISTORIAS}{vistoria['id']}/avarias/", {"descricao": "Risco", "foto_id": 1}, format="json"
    )
    assert avaria.status_code == 409
    assert avaria.json()["codigo"] == "vistoria_concluida"

    url = f"{VISTORIAS}{vistoria['id']}/corrigir/"
    for quem in ("João", "Bruna"):
        assert (
            cenario.moto.api(quem).post(url, {"motivo": "km errado"}, format="json").status_code
            == 403
        )
    sem_motivo = cenario.moto.api("Rodrigo").post(url, {"motivo": " "}, format="json")
    assert sem_motivo.status_code == 400
    resposta = cenario.moto.api("Rodrigo").post(url, {"motivo": "km errado"}, format="json")
    assert resposta.status_code == 201, resposta.json()
    nova = resposta.json()
    assert (nova["status"], nova["substitui"], nova["km"]) == ("rascunho", vistoria["id"], 3125)
    assert nova["motivo_correcao"] == "km errado"
    assert nova["fotos_obrigatorias"]["feitas"] == 5

    assert _patch(cenario, nova["id"], "Rodrigo", km=3130).status_code == 200
    assert _concluir(cenario, nova["id"], "Rodrigo").status_code == 200
    anterior = Vistoria.objects.get(pk=vistoria["id"])
    vigente = Vistoria.objects.get(pk=nova["id"])
    assert (anterior.status, anterior.vigente) == ("concluida", False)  # guardada
    assert (vigente.status, vigente.vigente) == ("concluida", True)
    assert EventoAuditoria.objects.filter(
        acao="vistoria.corrigir", objeto_id=nova["id"], motivo="km errado"
    ).exists()
    # A anterior não se corrige mais: só a vigente.
    assert (
        cenario.moto.api("Rodrigo").post(url, {"motivo": "de novo"}, format="json").status_code
        == 409
    )


# --- CA-016-05 · Efeitos da saída (VEI-02) ---


def test_vei_02_ca_016_05_efeitos_da_saida(cenario, lucas):
    criada = _lucas_2856(cenario)
    vistoria = _saida(cenario, criada["id"])
    _preencher(cenario, vistoria, 3125)
    assert _concluir(cenario, vistoria["id"]).status_code == 200

    sak = Veiculo.objects.get(pk=cenario.sak.pk)
    assert sak.km_atual == 3125
    leitura = LeituraKm.objects.filter(veiculo=sak).latest("id")
    assert (leitura.km, leitura.origem_tipo, leitura.origem_codigo) == (
        3125,
        "vistoria",
        "LOC-2856",
    )
    locacao = Locacao.objects.get(pk=criada["id"])
    assert locacao.vistoria_saida_ok_em is not None and locacao.km_saida == 3125
    assert EventoAuditoria.objects.filter(
        acao="vistoria.concluir_saida", objeto_id=vistoria["id"]
    ).exists()

    # Com o contrato assinado e o 1º pagamento, a locação fica ativa (CA-015-14).
    _assinar(criada["id"])
    _pagar(criada["id"])
    locacao.refresh_from_db()
    sak.refresh_from_db()
    assert (locacao.status, sak.status) == ("ativa", "alugado")


def test_vei_01_ca_016_05_km_igual_ao_atual_nao_grava_leitura(cenario, lucas):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    _preencher(cenario, vistoria, 3120)
    leituras = LeituraKm.objects.count()
    assert _concluir(cenario, vistoria["id"]).status_code == 200
    assert LeituraKm.objects.count() == leituras


# --- CA-016-06 · Fotos privadas (AUD-05) ---


def test_aud_05_ca_016_06_fotos_privadas(cenario, lucas):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    enviada = _foto(cenario, vistoria["id"], "painel", arquivo=_jpg("painel.jpg", gps=True))
    assert enviada.status_code == 201, enviada.json()
    foto = FotoVistoria.objects.get(pk=enviada.json()["id"])
    assert foto.arquivo.name.startswith(f"empresa_a/vistorias/fotovistoria/{foto.pk}/")
    gravada = Image.open(io.BytesIO(arquivos.provedor().ler(foto.arquivo.name)))
    assert not gravada.getexif().get_ifd(0x8825)  # sem GPS

    api = cenario.moto.api("João")
    primeira = api.get(f"{VISTORIAS}{vistoria['id']}/").json()["fotos"][0]
    segunda = api.get(f"{VISTORIAS}{vistoria['id']}/").json()["fotos"][0]
    assert primeira["url"] != segunda["url"]
    assert primeira["url_expira_em"] is not None

    # A nova foto da mesma posição substitui a anterior, que fica guardada.
    assert _foto(cenario, vistoria["id"], "painel").status_code == 201
    assert FotoVistoria.ativos.filter(vistoria_id=vistoria["id"], posicao="painel").count() == 1
    assert FotoVistoria.objects.filter(vistoria_id=vistoria["id"], posicao="painel").count() == 2

    grande = SimpleUploadedFile(
        "grande.jpg", b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024), content_type="image/jpeg"
    )
    assert _foto(cenario, vistoria["id"], "frente", arquivo=grande).status_code == 400
    pdf = SimpleUploadedFile("frente.pdf", b"%PDF-1.4 teste", content_type="application/pdf")
    assert _foto(cenario, vistoria["id"], "frente", arquivo=pdf).status_code == 400


# --- CA-016-07 · Vistoriador não vê valores ---


def test_vis_ca_016_07_vistoriador_nao_ve_valores(cenario, lucas):
    criada = _lucas_2856(cenario)
    saida = _saida(cenario, criada["id"])
    joao = cenario.moto.api("João")
    corpo = joao.get(f"{VISTORIAS}{saida['id']}/").json()
    assert not [c for c in _chaves(corpo) if c.endswith("_centavos")]
    assert "acerto" not in _chaves(corpo)
    da_bruna = cenario.moto.api("Bruna").get(f"{VISTORIAS}{saida['id']}/").json()
    assert da_bruna["resumo_locacao"]["caucao_centavos"] == 30000
    assert not [c for c in _chaves(joao.get(AGENDA).json()) if c.endswith("_centavos")]

    _preencher(cenario, saida, 3125)
    assert _concluir(cenario, saida["id"]).status_code == 200
    _assinar(criada["id"])
    _pagar(criada["id"])
    chegada, _ = services.criar(
        Locacao.objects.get(pk=criada["id"]), "devolucao", cenario.pessoas["João"]
    )
    foto = _foto(cenario, chegada.pk, "avaria").json()
    corpo = {
        "descricao": "Retrovisor esquerdo riscado",
        "foto_id": foto["id"],
        "valor_centavos": 8500,
    }
    recusada = joao.post(f"{VISTORIAS}{chegada.pk}/avarias/", corpo, format="json")
    assert recusada.status_code == 400
    assert "valor_centavos" in recusada.json()["campos"]
    sem_valor = joao.post(
        f"{VISTORIAS}{chegada.pk}/avarias/",
        {"descricao": "Retrovisor esquerdo riscado", "foto_id": foto["id"]},
        format="json",
    )
    assert sem_valor.status_code == 201
    assert "valor_centavos" not in sem_valor.json()
    da_bruna = cenario.moto.api("Bruna").post(
        f"{VISTORIAS}{chegada.pk}/avarias/", corpo, format="json"
    )
    assert da_bruna.status_code == 201
    assert da_bruna.json()["valor_centavos"] == 8500


def test_vis_financeiro_nao_faz_vistoria(cenario, lucas):
    criada = _lucas_2856(cenario)
    lucia = cenario.moto.api("Lúcia")
    assert _abrir(cenario, criada["id"], "Lúcia").status_code == 403
    vistoria = _saida(cenario, criada["id"])
    assert lucia.get(f"{VISTORIAS}{vistoria['id']}/").status_code == 403
    assert lucia.get(AGENDA).status_code == 403


# --- CA-016-08 · Agenda de 07 out (VIS-05) ---


def test_vis_05_ca_016_08_agenda(cenario, relogio):
    relogio.em("2026-10-07 08:00")
    lote = carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)
    # T-104, decisão B: a LOC-2836 vai até 14 out 18:00 (o seed muda na T-105).
    Locacao.objects.filter(pk=lote["LOC-2836"].pk).update(
        fim_previsto=carteira.momento("2026-10-14 18:00")
    )
    # Na carteira, a LOC-2856 já está ativa; no CA-016-08 ela aguarda a retirada das 09:15.
    ContaReceber.objects.filter(origem_tipo="locacao", origem_id=lote["LOC-2856"].pk).delete()
    Locacao.objects.filter(pk=lote["LOC-2856"].pk).delete()
    criada = _lucas_2856(cenario, inicio="2026-10-07T12:15:00Z")  # 09:15 em Fortaleza
    caucaia = _caucaia(cenario.moto, "João")
    outra = Veiculo.objects.filter(status="disponivel").exclude(pk=cenario.sak.pk).first()
    assert outra is not None
    Locacao.objects.create(
        filial=caucaia,
        cliente=cenario.cliente("Carlos"),
        veiculo=outra,
        vendedor=cenario.pessoas["Bruna"],
        periodicidade="semanal",
        inicio=carteira.momento("2026-10-07 11:00"),
        fim_previsto=carteira.momento("2026-10-14 11:00"),
        forma_pagamento="pix",
        status="aguardando_retirada",
    )

    relogio.em("2026-10-07 09:00")
    joao = cenario.moto.api("João", HTTP_X_FILIAL=str(cenario.frota.centro.pk))
    agenda = joao.get(AGENDA).json()
    assert agenda["resumo"] == "Quarta, 07 out · 1 saída e 1 devolução"
    assert [i["id"] for i in agenda["resultados"]] == ["devolucao-2790", "saida-2856"]
    rafael, lucas = agenda["resultados"]
    assert rafael["situacao"]["codigo"] == "atrasada" and rafael["acao"]["codigo"] == "abrir"
    assert rafael["locacao"]["codigo"] == "LOC-2790"
    assert lucas["situacao"]["codigo"] == "hoje" and lucas["acao"]["codigo"] == "iniciar"
    assert lucas["cliente"] == {"nome": "Lucas Ferreira"}
    assert agenda["proxima"] == {"item_id": "saida-2856", "em_minutos": 15}

    # Passou do horário: atrasada. Com a vistoria em rascunho: em andamento, "Continuar".
    relogio.em("2026-10-07 10:00")
    assert joao.get(AGENDA).json()["resultados"][1]["situacao"]["codigo"] == "atrasada"
    vistoria = _saida(cenario, criada["id"])
    item = joao.get(AGENDA).json()["resultados"][1]
    assert item["situacao"] == {"codigo": "em_andamento", "rotulo": "Em andamento", "tom": "aviso"}
    assert item["acao"] == {"codigo": "continuar", "rotulo": "Continuar"}
    assert item["vistoria_id"] == vistoria["id"]

    # A devolução da LOC-2836 está na agenda de 14 out.
    relogio.em("2026-10-14 08:00")
    cenario.moto._tokens.clear()  # o token de 07 out venceu
    joao = cenario.moto.api("João", HTTP_X_FILIAL=str(cenario.frota.centro.pk))
    dia_14 = {i["id"]: i for i in joao.get(AGENDA).json()["resultados"]}
    assert dia_14["devolucao-2836"]["situacao"]["codigo"] == "hoje"
    assert dia_14["devolucao-2836"]["cliente"] == {"nome": "Juliana Rocha"}


def test_vis_05_agenda_com_todas_as_filiais_pede_uma(cenario):
    resposta = cenario.moto.api("Mariana", HTTP_X_FILIAL="todas").get(AGENDA)
    assert resposta.status_code == 400


# --- Avarias abertas (tela Vistoriador) ---


def test_vis_01_avarias_abertas(cenario):
    risco = _avaria_anterior(cenario, cenario.sak, "Risco no tanque, lado esquerdo")
    resposta = cenario.moto.api("João").get(f"{VISTORIAS}avarias/?veiculo={cenario.sak.pk}")
    assert resposta.status_code == 200
    assert [a["id"] for a in resposta.json()["resultados"]] == [risco.pk]
    assert "valor_centavos" not in resposta.json()["resultados"][0]
    risco.resolvida_em = carteira.momento("2026-10-06 10:00")
    risco.save(update_fields=["resolvida_em"])
    assert cenario.moto.api("João").get(f"{VISTORIAS}avarias/").json()["resultados"] == []


# --- Isolamento e escopo ---


def test_vis_vistoria_fora_da_filial_responde_404(cenario, lucas):
    vistoria = _saida(cenario, _lucas_2856(cenario)["id"])
    caucaia = _caucaia(cenario.moto)
    so_caucaia = cenario.moto.api("Mariana", HTTP_X_FILIAL=str(caucaia.pk))
    assert so_caucaia.get(f"{VISTORIAS}{vistoria['id']}/").status_code == 404


def test_vis_vistoria_da_empresa_a_nao_aparece_na_b(cenario, lucas):
    _saida(cenario, _lucas_2856(cenario)["id"])
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Vistoria.objects.exists()
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert Vistoria.objects.count() == 1


# --- Parte 2: devolução e acerto; troca (T-092); caixa (T-017) ---


@aguarda("T-109")
def test_dev_03_ca_016_09_acerto_loc_2836(cenario):
    pendente(combustivel=3200, avaria=8500, cobrancas=11700, caucao=30000, saldo=18300)


@aguarda("T-109")
def test_dev_01_vis_03_ca_016_10_combustivel_com_outros_niveis(cenario):
    pendente(meio=5400, reserva=9800, tres_quartos_igual=0)


@aguarda("T-109")
def test_dev_02_ca_016_11_saldo_negativo_vira_conta(cenario):
    pendente(saldo=-13200, vencimento="2026-10-10")


@aguarda("T-109")
def test_loc_10_loc_11_fil_03_ca_016_12_atraso_no_acerto(cenario):
    pendente(as_19_01=5490, as_19_00=0, editar="item_calculado")


@aguarda("T-109")
def test_dev_01_ca_016_13_parcelas_em_aberto_no_acerto(cenario):
    pendente(parcela_aberta=29940, forma="caucao")


@aguarda("T-109")
def test_loc_12_loc_13_ca_016_14_encerramento_antecipado_da_patricia(cenario):
    pendente(caucao=50000, credito=37100, multa=8480, saldo=78620, status="cancelada")


@aguarda("T-092")
def test_loc_09_ca_016_15_troca_de_veiculo_acerto_unico(cenario):
    pendente(avaria=8500, diferenca_caucao=20000, caucao_final=50000)


@aguarda("T-109")
def test_dev_05_ca_016_16_salvar_e_continuar_depois(cenario):
    pendente(status="rascunho", encerrar="vistoria_pendente")


@aguarda("T-109")
def test_dev_04_dev_06_ca_016_17_encerrar(cenario):
    pendente(km=19630, veiculo="disponivel", reembolso=18300)


@aguarda("T-017")
def test_fin_07_ca_016_18_devolucao_em_dinheiro_exige_caixa(cenario):
    pendente(codigo="FIN-07", saida_dinheiro=18300)


@aguarda("T-109")
def test_dev_ca_016_19_quem_fecha_a_conta(cenario):
    pendente(joao_acerto=403, joao_encerrar=403)


@aguarda("T-109")
def test_dev_ca_016_20_recibo(cenario):
    pendente(url_minutos=15, palavras=["devolução", "caução"])
