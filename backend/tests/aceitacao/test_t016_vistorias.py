"""T-016 e T-109 · Vistoria de saída e devolução com acerto (docs/qa/criterios/T-016.md).

Parte 1 (T-016, divisão de 09 out): a vistoria de saída e de chegada como entidade, a agenda e as
avarias abertas: CA-016-01 a 08 e 21. Parte 2 (T-109): a devolução e o acerto, CA-016-09 a 14, 16,
17, 19 e 20. A troca de veículo (CA-016-15) fica com a T-092 e a devolução em dinheiro (CA-016-18)
com o caixa da T-017; esses ficam `xfail` aqui.

Cenário da T-015: Moto Rápida em 07 out 2026, 10:00, Filial Centro, com a LOC-2856 de Lucas
(SAK1D39, Street semanal) e a carteira de outubro quando o caso é do seed.
"""

import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente, TipoDocumentoCliente
from apps.contratos.models import Contrato
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro_services
from apps.financeiro.models import ContaReceber, Reembolso
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import LeituraKm, Veiculo
from apps.vistorias import acerto, recibo, services
from apps.vistorias.models import Avaria, Devolucao, FotoVistoria, Vistoria
from comum import arquivos, eventos
from integracoes.whatsapp import falso as whatsapp

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
    frota = montar_frota(moto)
    frota.centro.preco_litro_centavos = 550  # seed: litro a R$ 5,50 na Filial Centro (DEV-01)
    frota.centro.save(update_fields=["preco_litro_centavos"])
    return Cenario(moto, frota)


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
    assert lote["LOC-2836"].fim_previsto == carteira.momento("2026-10-14 18:00")  # LOC-06
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
    # Sem a LOC-2836: nenhuma devolução prevista no seed em 07 out (T-104).
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


# --- Parte 2 (T-109): devolução e acerto (DEV-01 a DEV-06, LOC-10 a LOC-13) ---
#
# A LOC-2836 da carteira sai de 30 set a 14 out 18:00 (caso "Fim previsto da LOC-2836", até a
# T-105 levar ao seed) e com a PNB7C04 em 18.402 km na saída, como no critério; a carteira não
# tem a vistoria de saída, e o teste grava a dela, com o tanque cheio. LOC-2841 e LOC-2812 não
# têm a caução paga na carteira: o teste grava a de cada uma (30000 e 50000).

DEVOLUCOES = "/api/devolucoes/"
DIA_TODO = {
    d: [{"abre": "08:00", "fecha": "22:00"}]
    for d in ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
}


def _ir_para(cenario: Cenario, relogio: Any, quando: str) -> None:
    relogio.em(quando)
    cenario.moto._tokens.clear()  # o token do dia anterior venceu


def _saida_direta(locacao: Locacao, km: int, combustivel: str, quando: str) -> Vistoria:
    """A vistoria de saída que a carteira não tem, concluída e com todos os itens ok."""
    veiculo = Veiculo.objects.select_related("categoria").get(pk=locacao.veiculo_id)
    itens = [{**i, "ok": True} for i in services.itens_iniciais(locacao, veiculo)]
    return Vistoria.objects.create(
        locacao=locacao,
        veiculo=veiculo,
        tipo="saida",
        status="concluida",
        km=km,
        combustivel=combustivel,
        itens=itens,
        concluida_em=carteira.momento(quando),
    )


def _caucao_paga(locacao: Locacao, valor: int) -> None:
    ContaReceber.objects.create(
        filial=locacao.filial,
        cliente=locacao.cliente,
        origem_tipo="locacao",
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        tipo="caucao",
        vencimento=locacao.inicio.date(),
        valor_centavos=valor,
        status="paga",
        forma="pix",
        pago_em=locacao.inicio,
    )


@pytest.fixture
def da_carteira(cenario, relogio) -> dict[str, Locacao]:
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)


@pytest.fixture
def juliana(cenario, da_carteira) -> Locacao:
    locacao = da_carteira["LOC-2836"]
    Locacao.objects.filter(pk=locacao.pk).update(fim_previsto=carteira.momento("2026-10-14 18:00"))
    Veiculo.objects.filter(pk=locacao.veiculo_id).update(km_atual=18402)
    _saida_direta(locacao, 18402, "cheio", "2026-10-01 09:10")
    locacao.refresh_from_db()
    assert (locacao.caucao_centavos, locacao.diaria_centavos) == (30000, 5490)
    return locacao


def _lucas_ativo(cenario: Cenario) -> dict[str, Any]:
    """LOC-2856 retirada em 07 out: saída com 3.125 km e tanque cheio, contrato e 1º pagamento.
    Os casos daqui devolvem em 07 out; o fim previsto passa para 07 out 18:00, para a devolução
    não ser antecipada (DEV-07, que tem os casos dela no CA-016-23)."""
    criada = _lucas_2856(cenario)
    vistoria = _saida(cenario, criada["id"])
    _preencher(cenario, vistoria, 3125)
    assert _concluir(cenario, vistoria["id"]).status_code == 200
    _assinar(criada["id"])
    _pagar(criada["id"])
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"
    Locacao.objects.filter(pk=criada["id"]).update(
        fim_previsto=carteira.momento("2026-10-07 18:00")
    )
    return criada


def _abrir_devolucao(cenario: Cenario, locacao_id: int, quem: str = "João") -> dict[str, Any]:
    resposta = cenario.moto.api(quem).post(f"{LISTA}{locacao_id}/devolucao/")
    assert resposta.status_code in (200, 201), resposta.json()
    return dict(resposta.json())


def _ver(cenario: Cenario, devolucao_id: int, quem: str = "Bruna") -> dict[str, Any]:
    resposta = cenario.moto.api(quem).get(f"{DEVOLUCOES}{devolucao_id}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _chegada(
    cenario: Cenario,
    devolucao: dict[str, Any],
    km: int,
    combustivel: str = "cheio",
    avarias: tuple[tuple[str, dict[str, Any]], ...] = (),
    concluir: bool = True,
) -> dict[str, Any]:
    """João preenche a vistoria de chegada, marca as avarias e conclui."""
    vistoria = devolucao["vistoria"]
    _preencher(cenario, vistoria, km, combustivel=combustivel)
    for descricao, extra in avarias:
        foto = _foto(cenario, vistoria["id"], "avaria").json()
        resposta = cenario.moto.api("João").post(
            f"{VISTORIAS}{vistoria['id']}/avarias/",
            {"descricao": descricao, "foto_id": foto["id"], **extra},
            format="json",
        )
        assert resposta.status_code == 201, resposta.json()
    if concluir:
        resposta = _concluir(cenario, vistoria["id"])
        assert resposta.status_code == 200, resposta.json()
    return _ver(cenario, devolucao["id"])


def _item(corpo: dict[str, Any], tipo: str) -> dict[str, Any]:
    return next(i for i in corpo["acerto"]["itens"] if i["tipo"] == tipo)


def _valor_do_item(cenario: Cenario, devolucao_id: int, item_id: int, valor: int) -> Any:
    return cenario.moto.api("Bruna").patch(
        f"{DEVOLUCOES}{devolucao_id}/acerto/itens/{item_id}/",
        {"valor_centavos": valor},
        format="json",
    )


def _forma(cenario: Cenario, devolucao_id: int, forma: str = "pix", quem: str = "Bruna") -> Any:
    return cenario.moto.api(quem).patch(
        f"{DEVOLUCOES}{devolucao_id}/acerto/", {"forma_devolucao": forma}, format="json"
    )


def _encerrar(cenario: Cenario, devolucao_id: int, quem: str = "Bruna") -> Any:
    return cenario.moto.api(quem).post(f"{DEVOLUCOES}{devolucao_id}/encerrar/")


def _juliana_pronta(cenario: Cenario, juliana: Locacao, relogio: Any) -> dict[str, Any]:
    """CA-016-09: chega em 14 out às 17:40, 19.630 km, 3/4 e o retrovisor riscado (R$ 85,00)."""
    _ir_para(cenario, relogio, "2026-10-14 17:40")
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    corpo = _chegada(
        cenario, devolucao, 19630, "tres_quartos", avarias=(("Retrovisor esquerdo riscado", {}),)
    )
    retrovisor = _item(corpo, "avaria")
    assert (retrovisor["valor_centavos"], retrovisor["modo"]) == (0, "informado")
    resposta = _valor_do_item(cenario, devolucao["id"], retrovisor["id"], 8500)
    assert resposta.status_code == 200, resposta.json()
    resposta = _forma(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


# --- CA-016-09 · Juliana, LOC-2836 (DEV-03) ---


def test_dev_03_ca_016_09_acerto_loc_2836(cenario, juliana, relogio):
    corpo = _juliana_pronta(cenario, juliana, relogio)
    assert corpo["status"] == "rascunho"
    assert corpo["locacao"]["codigo"] == "LOC-2836"
    assert corpo["locacao"]["no_horario"] is True
    km = corpo["comparacao"]["km"]
    assert (km["saida"], km["agora"], km["rodou"]) == (18402, 19630, 1228)
    assert km["texto"] == "Rodou 1.228 km · plano com km livre"
    assert corpo["comparacao"]["combustivel"] == {
        "saida": "cheio",
        "agora": "tres_quartos",
        "faltou": "1/4 tanque",
        "litros_faltantes": "4.0",
    }

    acerto = corpo["acerto"]
    assert {i["tipo"]: i["valor_centavos"] for i in acerto["itens"]} == {
        "combustivel": 3200,
        "avaria": 8500,
        "atraso": 0,
        "km_excedente": 0,
    }
    combustivel = _item(corpo, "combustivel")
    assert combustivel["modo"] == "calculado"
    # A taxa de R$ 10,00 entra uma vez: 4 L × 550 + 1000.
    assert combustivel["descricao"] == "Combustível (faltou 1/4 tanque, 4 L × R$ 5,50 + R$ 10,00)"
    assert acerto["creditos"] == []
    assert (acerto["total_cobrancas_centavos"], acerto["caucao_centavos"]) == (11700, 30000)
    assert acerto["saldo_centavos"] == 18300
    assert acerto["resultado"] == {
        "tipo": "devolver",
        "valor_centavos": 18300,
        "texto": "Desconta R$ 117,00 da caução de R$ 300,00",
        "botao": "Encerrar e devolver R$ 183,00",
    }
    assert acerto["forma_devolucao"] == "pix"


# --- CA-016-10 · Combustível com outros níveis (DEV-01, VIS-03) ---


@pytest.mark.parametrize(
    ("saida", "chegada", "valor"),
    [
        ("cheio", "tres_quartos", 3200),
        ("cheio", "meio", 5400),  # 8 L
        ("cheio", "reserva", 9800),  # 16 L
        ("tres_quartos", "tres_quartos", 0),
        ("cheio", "cheio", 0),  # voltou cheio: sem a taxa
        ("meio", "cheio", 0),  # voltou mais cheio: nada a cobrar nem a devolver
    ],
)
def test_dev_01_vis_03_ca_016_10_combustivel_com_outros_niveis(saida, chegada, valor):
    conta = acerto.combustivel(
        capacidade_litros=Decimal("16.0"), preco_litro_centavos=550, saida=saida, chegada=chegada
    )
    assert conta.calculado is True
    assert conta.valor_centavos == valor


def test_dev_01_ca_016_10_sem_tanque_ou_sem_preco_vira_informado():
    sem_tanque = acerto.combustivel(
        capacidade_litros=None, preco_litro_centavos=550, saida="cheio", chegada="meio"
    )
    sem_preco = acerto.combustivel(
        capacidade_litros=Decimal("16.0"), preco_litro_centavos=None, saida="cheio", chegada="meio"
    )
    assert (sem_tanque.calculado, sem_preco.calculado) == (False, False)


def test_dev_01_ca_016_10_preco_da_filial_no_acerto(cenario, lucas):
    """O preço é o da filial no momento do acerto; depois de encerrar, não muda mais."""
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    corpo = _chegada(cenario, devolucao, 3200, "meio")
    assert _item(corpo, "combustivel")["valor_centavos"] == 5400
    centro = cenario.frota.centro
    centro.preco_litro_centavos = 600
    centro.save(update_fields=["preco_litro_centavos"])
    assert _item(_ver(cenario, devolucao["id"]), "combustivel")["valor_centavos"] == 5800

    assert _forma(cenario, devolucao["id"]).status_code == 200
    assert _encerrar(cenario, devolucao["id"]).status_code == 200
    centro.preco_litro_centavos = 700
    centro.save(update_fields=["preco_litro_centavos"])
    assert _item(_ver(cenario, devolucao["id"]), "combustivel")["valor_centavos"] == 5800
    assert Devolucao.objects.get(pk=devolucao["id"]).preco_litro_centavos == 600


# --- CA-016-11 · Saldo negativo vira conta (DEV-02) ---


def test_dev_02_ca_016_11_saldo_negativo_vira_conta(cenario, lucas):
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    corpo = _chegada(cenario, devolucao, 3200, "tres_quartos", avarias=(("Tanque amassado", {}),))
    valor = _valor_do_item(cenario, devolucao["id"], _item(corpo, "avaria")["id"], 40000)
    assert valor.status_code == 200, valor.json()
    corpo = _ver(cenario, devolucao["id"])
    assert corpo["acerto"]["saldo_centavos"] == -13200
    assert corpo["acerto"]["resultado"]["tipo"] == "cobrar"
    assert corpo["acerto"]["resultado"]["valor_centavos"] == 13200
    assert corpo["acerto"]["resultado"]["botao"] == "Encerrar e cobrar R$ 132,00"

    resposta = _encerrar(cenario, devolucao["id"])  # sem forma: não há o que devolver
    assert resposta.status_code == 200, resposta.json()
    saldo = ContaReceber.objects.get(origem_tipo="devolucao", status="aberta")
    assert (saldo.valor_centavos, saldo.tipo) == (13200, "acerto")
    assert saldo.vencimento == date(2026, 10, 10)  # encerrada em 07 out
    assert saldo.cliente_id == lucas.pk
    assert not Reembolso.objects.filter(origem_tipo="devolucao").exists()
    pagas = ContaReceber.objects.filter(origem_tipo="devolucao", status="paga")
    assert sorted(c.valor_centavos for c in pagas) == [3200, 26800]  # o que a caução cobriu
    assert {c.forma for c in pagas} == {"caucao"}


# --- CA-016-12 · Atraso no acerto (LOC-10, LOC-11, FIL-03) ---


def test_loc_10_loc_11_fil_03_ca_016_12_atraso_no_acerto(cenario, juliana, relogio):
    centro = cenario.frota.centro
    centro.horario = DIA_TODO
    centro.save(update_fields=["horario"])
    _ir_para(cenario, relogio, "2026-10-14 18:40")
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    _chegada(cenario, devolucao, 19630, concluir=False)

    # Às 19:00, dentro da tolerância de 1 h: sem atraso.
    _ir_para(cenario, relogio, "2026-10-14 19:00")
    assert _concluir(cenario, devolucao["vistoria"]["id"]).status_code == 200
    corpo = _ver(cenario, devolucao["id"])
    assert _item(corpo, "atraso")["valor_centavos"] == 0
    assert corpo["locacao"]["no_horario"] is True

    # A chegada corrigida e concluída às 19:01 conta 1 diária da Street (fração de dia).
    _ir_para(cenario, relogio, "2026-10-14 19:01")
    resposta = cenario.moto.api("Rodrigo").post(
        f"{VISTORIAS}{devolucao['vistoria']['id']}/corrigir/",
        {"motivo": "Hora da chegada"},
        format="json",
    )
    assert resposta.status_code == 201, resposta.json()
    assert _concluir(cenario, resposta.json()["id"]).status_code == 200
    corpo = _ver(cenario, devolucao["id"])
    atraso = _item(corpo, "atraso")
    assert (atraso["valor_centavos"], atraso["modo"]) == (5490, "calculado")
    assert atraso["descricao"] == "Atraso (1 diária)"
    assert corpo["locacao"]["no_horario"] is False
    assert corpo["vistoria"]["id"] == resposta.json()["id"]

    # O item calculado não se edita nem sai.
    editar = _valor_do_item(cenario, devolucao["id"], atraso["id"], 0)
    assert editar.status_code == 409
    assert editar.json()["codigo"] == "item_calculado"
    tirar = cenario.moto.api("Bruna").delete(
        f"{DEVOLUCOES}{devolucao['id']}/acerto/itens/{atraso['id']}/"
    )
    assert tirar.status_code == 409


# --- CA-016-13 · Parcelas em aberto no acerto (DEV-01, FIN-03) ---


def _contrato_com_juros(locacao: Locacao) -> None:
    """O contrato assinado com a cláusula de multa e juros (FIN-03), que a carteira não tem."""
    Contrato.objects.create(
        origem_tipo="locacao",
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        filial=locacao.filial,
        cliente=locacao.cliente,
        tipo="contrato",
        titulo="Contrato de locação",
        status="assinado",
        versao_texto_html="<p>Multa de 2% e juros de 1% ao mês.</p>",
        clausula_juros=True,
    )


def _parcela(locacao: Locacao, numero: int) -> ContaReceber:
    conta: ContaReceber = ContaReceber.objects.get(
        origem_tipo="locacao", origem_id=locacao.pk, tipo="parcela", numero_parcela=numero
    )
    return conta


def _carlos_na_devolucao(da_carteira: dict[str, Locacao]) -> Locacao:
    """LOC-2841: Street semanal de 23 set a 28 out, caução de 30000 paga e a saída cheia."""
    carlos = da_carteira["LOC-2841"]
    carlos.diaria_centavos = 5490  # Street
    carlos.periodos = 5  # 5 semanas; a carteira não grava
    carlos.save(update_fields=["diaria_centavos", "periodos"])
    _caucao_paga(carlos, 30000)
    veiculo = Veiculo.objects.get(pk=carlos.veiculo_id)
    _saida_direta(carlos, veiculo.km_atual, "cheio", "2026-09-23 09:00")
    return carlos


def _aprovar_encerramento(cenario: Cenario, locacao: Locacao) -> None:
    """Rodrigo (gerente) cancela direto: o encerramento antecipado vale (LOC-12, APR-02)."""
    resposta = cenario.moto.api("Rodrigo").post(
        f"{LISTA}{locacao.pk}/cancelar/", {"motivo": "Cliente vai mudar de cidade"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()


def _parcelas_do_acerto(corpo: dict[str, Any]) -> list[tuple[int, int | None]]:
    return [
        (i["valor_centavos"], i["conta_id"])
        for i in corpo["acerto"]["itens"]
        if i["tipo"] == "parcela_aberta"
    ]


def _km_de_volta(locacao: Locacao) -> int:
    return Veiculo.objects.get(pk=locacao.veiculo_id).km_atual + 50


def test_dev_01_ca_016_13_parcela_vencida_sem_multa_e_juros_no_contrato(cenario, da_carteira):
    """Sem a cláusula no contrato, a vencida entra pelo valor; a do dia entra também."""
    carlos = _carlos_na_devolucao(da_carteira)
    _aprovar_encerramento(cenario, carlos)
    vencida, do_dia = _parcela(carlos, 2), _parcela(carlos, 3)
    devolucao = _abrir_devolucao(cenario, carlos.pk)
    corpo = _chegada(cenario, devolucao, _km_de_volta(carlos))
    assert _parcelas_do_acerto(corpo) == [(29940, vencida.pk), (29940, do_dia.pk)]
    itens = {i["conta_id"]: i for i in corpo["acerto"]["itens"]}
    assert itens[vencida.pk]["modo"] == "calculado"
    assert itens[vencida.pk]["descricao"] == "Parcela 2 de 5 · venceu em 30/09"
    assert itens[do_dia.pk]["descricao"] == "Parcela 3 de 5 · vence hoje, 07/10"

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    vencida.refresh_from_db()
    # 30000 de caução: cabe a parcela 2 inteira; a 3 não cabe e vai para a conta do saldo.
    assert (vencida.status, vencida.forma, vencida.multa_centavos) == ("paga", "caucao", 0)


def test_dev_01_fin_03_ca_016_13_parcela_com_multa_e_juros(cenario, da_carteira):
    """2% + 1% ao mês: a de 29940 vencida em 30 set e devolvida em 07 out vale 30609."""
    carlos = _carlos_na_devolucao(da_carteira)
    _contrato_com_juros(carlos)
    devido = financeiro_selectors.devido_ate(_parcela(carlos, 2), date(2026, 10, 7))
    assert (devido.multa_centavos, devido.juros_centavos, devido.dias_atraso) == (599, 70, 7)
    assert devido.total_centavos == 30609
    do_dia = financeiro_selectors.devido_ate(_parcela(carlos, 3), date(2026, 10, 7))
    assert (do_dia.total_centavos, do_dia.multa_centavos, do_dia.juros_centavos) == (29940, 0, 0)


def test_dev_01_ca_016_13_parcela_do_dia_seguinte_fica_fora(cenario, juliana, relogio):
    """A LOC-2836 devolvida em 14 out: a parcela de 15 out não entra; a de 14 out entra."""
    amanha = _parcela_extra(juliana, 29940, date(2026, 10, 15))
    _ir_para(cenario, relogio, "2026-10-14 17:40")
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    corpo = _chegada(cenario, devolucao, 19630)
    assert _parcelas_do_acerto(corpo) == []
    do_dia = _parcela_extra(juliana, 29940, date(2026, 10, 14))
    parcelas = _parcelas_do_acerto(_ver(cenario, devolucao["id"]))
    assert parcelas == [(29940, do_dia.pk)]
    assert amanha.pk not in {c for _, c in parcelas}


# --- CA-016-22 · Parcela que não cabe na caução (DEV-02, FIN-01) ---


def _parcela_extra(locacao: Locacao, valor: int, vencimento: date) -> ContaReceber:
    """Uma parcela em aberto a mais na LOC-2836 (a carteira tem as duas pagas)."""
    conta: ContaReceber = ContaReceber.objects.create(
        filial=locacao.filial,
        cliente=locacao.cliente,
        origem_tipo="locacao",
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        tipo="parcela",
        numero_parcela=3,
        total_parcelas=3,
        vencimento=vencimento,
        valor_centavos=valor,
    )
    return conta


def _juliana_com_parcela(
    cenario: Cenario, juliana: Locacao, relogio: Any, parcela: int, combustivel: str
) -> tuple[dict[str, Any], ContaReceber]:
    """LOC-2836 devolvida em 14 out às 17:40 (sem atraso e sem contrato com juros), com uma
    parcela vencida em 10 out e o retrovisor de 8500."""
    conta = _parcela_extra(juliana, parcela, date(2026, 10, 10))
    _ir_para(cenario, relogio, "2026-10-14 17:40")
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    corpo = _chegada(
        cenario, devolucao, 19630, combustivel, avarias=(("Retrovisor esquerdo riscado", {}),)
    )
    resposta = _valor_do_item(cenario, devolucao["id"], _item(corpo, "avaria")["id"], 8500)
    assert resposta.status_code == 200, resposta.json()
    return _ver(cenario, devolucao["id"]), conta


def _conta_do_saldo(devolucao_id: int) -> ContaReceber:
    conta: ContaReceber = ContaReceber.objects.get(
        origem_tipo="devolucao", origem_id=devolucao_id, tipo="acerto", status="aberta"
    )  # o combustível pago com a caução também é `acerto`, mas `paga`
    return conta


def test_dev_02_ca_016_22_parcela_que_nao_cabe_vai_para_renegociada(cenario, juliana, relogio):
    corpo, parcela = _juliana_com_parcela(cenario, juliana, relogio, 32900, "cheio")
    acerto = corpo["acerto"]
    assert acerto["total_cobrancas_centavos"] == 41400
    assert acerto["saldo_centavos"] == -11400
    assert acerto["resultado"]["botao"] == "Encerrar e cobrar R$ 114,00"

    resposta = _encerrar(cenario, corpo["id"])
    assert resposta.status_code == 200, resposta.json()
    parcela.refresh_from_db()
    assert parcela.status == "renegociada"
    avaria = ContaReceber.objects.get(origem_tipo="devolucao", origem_id=corpo["id"], tipo="avaria")
    assert (avaria.valor_centavos, avaria.status, avaria.forma) == (8500, "paga", "caucao")
    saldo = _conta_do_saldo(corpo["id"])
    # Encerrada em 14 out: vence em 3 dias. A conta é igual ao que o acerto mostra.
    assert (saldo.valor_centavos, saldo.status) == (11400, "aberta")
    assert saldo.vencimento == date(2026, 10, 17)
    assert saldo.valor_centavos == -acerto["saldo_centavos"]
    # A conta do saldo substitui a parcela (extrato do cliente, CLI-05).
    assert saldo.nasceu_de is not None
    assert parcela.renegociada_em_id == saldo.nasceu_de_id
    assert saldo.nasceu_de.origem_tipo == "devolucao"
    assert not Reembolso.objects.filter(origem_tipo="devolucao").exists()
    assert EventoAuditoria.objects.filter(acao="conta_receber.renegociar", regra="DEV-02").exists()


def test_dev_02_ca_016_22_a_sobra_paga_parte_do_combustivel(cenario, juliana, relogio):
    corpo, parcela = _juliana_com_parcela(cenario, juliana, relogio, 29940, "tres_quartos")
    assert corpo["acerto"]["total_cobrancas_centavos"] == 41640
    assert corpo["acerto"]["saldo_centavos"] == -11640

    resposta = _encerrar(cenario, corpo["id"])
    assert resposta.status_code == 200, resposta.json()
    parcela.refresh_from_db()
    assert (parcela.status, parcela.forma) == ("paga", "caucao")
    pagas = ContaReceber.objects.filter(
        origem_tipo="devolucao", origem_id=corpo["id"], status="paga"
    )
    assert sorted(c.valor_centavos for c in pagas) == [60]  # os 60 da sobra no combustível
    saldo = _conta_do_saldo(corpo["id"])
    assert (saldo.valor_centavos, saldo.nasceu_de) == (11640, None)
    assert not Reembolso.objects.filter(origem_tipo="devolucao").exists()


# --- CA-016-23 · Devolução antes do fim previsto (DEV-07, LOC-12, APR-02) ---


def _contas_da(locacao: Locacao) -> list[tuple[int, str, int]]:
    return list(
        ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk)
        .order_by("id")
        .values_list("pk", "status", "valor_centavos")
    )


def test_dev_07_ca_016_23_antes_do_fim_sem_aprovacao_recusa(cenario, juliana):
    """LOC-2836 (fim 14 out 18:00) volta em 07 out sem o encerramento antecipado aprovado."""
    antes = _contas_da(juliana)
    devolucao = _abrir_devolucao(cenario, juliana.pk)
    corpo = _chegada(cenario, devolucao, 18500)  # a vistoria de chegada conclui
    assert corpo["vistoria"]["status"] == "concluida"
    mensagem = "A devolução é antes do fim do contrato. Peça o encerramento antecipado ao gerente."
    assert corpo["acerto"]["avisos"] == [{"codigo": "DEV-07", "mensagem": mensagem}]

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 422, resposta.json()
    erro = resposta.json()
    assert (erro["codigo"], erro["mensagem"]) == ("DEV-07", mensagem)
    assert erro["detalhes"] == {
        "fim_previsto": "2026-10-14T21:00:00Z",
        "devolvida_em": "2026-10-07T13:00:00Z",
    }
    assert Devolucao.objects.get(pk=devolucao["id"]).status == "rascunho"
    assert Locacao.objects.get(pk=juliana.pk).status == "ativa"
    assert Veiculo.objects.get(pk=juliana.veiculo_id).status == "alugado"
    assert _contas_da(juliana) == antes
    assert not ContaReceber.objects.filter(origem_tipo="devolucao").exists()


def test_dev_07_ca_016_23_no_dia_do_fim_antes_da_hora_nao_e_antecipada(cenario, juliana, relogio):
    corpo = _juliana_pronta(cenario, juliana, relogio)  # 14 out 17:40
    assert corpo["acerto"]["avisos"] == []
    resposta = _encerrar(cenario, corpo["id"])
    assert resposta.status_code == 200, resposta.json()


# --- CA-016-24 · Devolução antecipada do Carlos, LOC-2841 (DEV-01, DEV-02, DEV-07) ---


def test_dev_01_dev_02_dev_07_ca_016_24_devolucao_antecipada_do_carlos(cenario, da_carteira):
    carlos = _carlos_na_devolucao(da_carteira)
    _contrato_com_juros(carlos)
    _aprovar_encerramento(cenario, carlos)
    p2, p3, p4, p5 = (_parcela(carlos, n) for n in (2, 3, 4, 5))

    devolucao = _abrir_devolucao(cenario, carlos.pk)  # 07 out 10:00
    corpo = _chegada(cenario, devolucao, _km_de_volta(carlos))
    acerto = corpo["acerto"]
    assert _parcelas_do_acerto(corpo) == [(30609, p2.pk), (29940, p3.pk)]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 5988
    assert acerto["total_cobrancas_centavos"] == 66537
    assert (acerto["caucao_centavos"], acerto["saldo_centavos"]) == (30000, -36537)
    assert acerto["resultado"]["tipo"] == "cobrar"
    assert acerto["resultado"]["botao"] == "Encerrar e cobrar R$ 365,37"
    assert acerto["avisos"] == []  # o encerramento antecipado está aprovado

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    for conta in (p2, p3, p4, p5):
        conta.refresh_from_db()
    assert (p4.status, p5.status) == ("cancelada", "cancelada")
    # A parcela 2 não cabe inteira: ela e a 3 vão para `renegociada`, mesmo a 3 cabendo.
    assert (p2.status, p3.status) == ("renegociada", "renegociada")
    assert (p2.multa_centavos, p2.juros_centavos) == (599, 70)
    multa = ContaReceber.objects.get(origem_tipo="devolucao", tipo="multa")
    assert (multa.valor_centavos, multa.status, multa.forma) == (5988, "paga", "caucao")
    saldo = _conta_do_saldo(devolucao["id"])
    assert (saldo.valor_centavos, saldo.vencimento) == (36537, date(2026, 10, 10))
    assert saldo.nasceu_de is not None
    assert set(saldo.nasceu_de.originais.values_list("pk", flat=True)) == {p2.pk, p3.pk}
    assert not Reembolso.objects.filter(origem_tipo="devolucao").exists()
    assert Locacao.objects.get(pk=carlos.pk).status == "cancelada"
    assert Veiculo.objects.get(pk=carlos.veiculo_id).status == "disponivel"


# --- CA-016-14 · Encerramento antecipado da Patrícia (LOC-12, LOC-13) ---


def test_loc_12_loc_13_ca_016_14_encerramento_antecipado_da_patricia(cenario, da_carteira):
    patricia = da_carteira["LOC-2812"]
    patricia.diaria_centavos = 7990  # NMax (Scooter premium)
    patricia.save(update_fields=["diaria_centavos"])
    _caucao_paga(patricia, 50000)
    resposta = cenario.moto.api("Rodrigo").post(
        f"{LISTA}{patricia.pk}/cancelar/", {"motivo": "Cliente vai mudar de cidade"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    veiculo = Veiculo.objects.get(pk=patricia.veiculo_id)
    _saida_direta(patricia, veiculo.km_atual, "cheio", "2026-09-15 09:00")

    devolucao = _abrir_devolucao(cenario, patricia.pk)
    corpo = _chegada(cenario, devolucao, veiculo.km_atual + 120)  # sem avarias, tanque cheio
    acerto = corpo["acerto"]
    assert acerto["caucao_centavos"] == 50000
    assert [(c["tipo"], c["valor_centavos"]) for c in acerto["creditos"]] == [
        ("semanas_nao_usadas", 37100)
    ]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 8480
    assert acerto["total_cobrancas_centavos"] == 8480
    assert acerto["saldo_centavos"] == 78620
    assert acerto["resultado"]["texto"] == "Devolve a caução de R$ 500,00 e mais R$ 286,20"
    assert acerto["forma_devolucao"] == "pix"  # a do pedido de cancelamento

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["locacao"]["status"] == "cancelada"
    patricia.refresh_from_db()
    assert patricia.status == "cancelada"
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=devolucao["id"])
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status) == (
        78620,
        "pix",
        "a_fazer",
    )
    multa = ContaReceber.objects.get(origem_tipo="devolucao", tipo="multa")
    assert (multa.valor_centavos, multa.status, multa.forma) == (8480, "paga", "caucao")


# --- CA-016-16 · Salvar e continuar depois (DEV-05) ---


def test_dev_05_ca_016_16_salvar_e_continuar_depois(cenario, lucas):
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    assert devolucao["status"] == "rascunho"
    assert devolucao["vistoria"]["tipo"] == "devolucao"
    assert _patch(cenario, devolucao["vistoria"]["id"], km=3150).status_code == 200
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"

    de_novo = cenario.moto.api("João").post(f"{LISTA}{criada['id']}/devolucao/")
    assert de_novo.status_code == 200
    assert de_novo.json()["id"] == devolucao["id"]
    assert de_novo.json()["vistoria"]["km"] == 3150
    assert de_novo.json()["status"] == "rascunho"

    resposta = _encerrar(cenario, devolucao["id"])
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "vistoria_pendente"
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"


def test_dev_05_devolucao_so_de_locacao_ativa(cenario, lucas):
    criada = _lucas_2856(cenario)  # aguardando retirada
    resposta = cenario.moto.api("João").post(f"{LISTA}{criada['id']}/devolucao/")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "transicao_locacao"


# --- CA-016-17 · Encerrar (DEV-04, DEV-06) ---


def test_dev_04_dev_06_ca_016_17_encerrar(
    cenario, juliana, relogio, django_capture_on_commit_callbacks
):
    corpo = _juliana_pronta(cenario, juliana, relogio)
    encerradas: list[dict[str, Any]] = []

    def ouvir(**dados: Any) -> None:
        encerradas.append(dados)

    eventos.assinar("locacoes.locacao_encerrada", ouvir)
    enviadas = len(whatsapp.caixa_de_saida)
    try:
        with django_capture_on_commit_callbacks(execute=True):
            resposta = _encerrar(cenario, corpo["id"])
    finally:
        eventos.remover_assinante("locacoes.locacao_encerrada", ouvir)
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["status"] == "concluida"
    assert corpo["acerto"]["status"] == "concluido"
    assert corpo["devolvida_em"] == "2026-10-14T20:40:00Z"  # 17:40 em Fortaleza

    juliana.refresh_from_db()
    assert juliana.status == "encerrada"
    assert juliana.devolvida_em == carteira.momento("2026-10-14 17:40")
    factor = Veiculo.objects.get(pk=juliana.veiculo_id)
    assert (factor.km_atual, factor.status) == (19630, "disponivel")
    assert [e["locacao_id"] for e in encerradas] == [juliana.pk]

    # As cobranças são pagas com a caução, e o saldo vira um reembolso por Pix a fazer.
    pagas = ContaReceber.objects.filter(origem_tipo="devolucao", origem_id=corpo["id"])
    assert sorted((c.tipo, c.valor_centavos, c.status, c.forma) for c in pagas) == [
        ("acerto", 3200, "paga", "caucao"),
        ("avaria", 8500, "paga", "caucao"),
    ]
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=corpo["id"])
    assert (reembolso.valor_centavos, reembolso.forma) == (18300, "pix")
    assert reembolso.status == "a_fazer"
    assert reembolso.origem_codigo == "LOC-2836"
    assert reembolso.cliente_id == juliana.cliente_id
    financeiro_services.marcar_reembolso_feito(
        reembolso, usuario=cenario.pessoas["Lúcia"], comprovante=_jpg("comprovante.jpg")
    )
    assert reembolso.status == "feito" and reembolso.comprovante

    # Depois do commit: o recibo em PDF, com as fotos, sai por WhatsApp com a marca da locadora.
    devolucao = Devolucao.objects.get(pk=corpo["id"])
    assert devolucao.recibo and devolucao.recibo_enviado_em is not None
    _, imagens = recibo.corpo(devolucao)
    assert len(imagens) == 6  # as 5 posições e a foto do retrovisor
    novas = whatsapp.caixa_de_saida[enviadas:]
    assert [m.celular for m in novas] == ["85981142290"]
    marca = Empresa.objects.get(schema_name="empresa_a").nome_exibicao  # a da locadora
    assert novas[0].texto.startswith(f"{marca}: recibo da devolução da LOC-2836.")
    assert "Giro" not in novas[0].texto
    assert "Devolução de R$ 183,00 por Pix em até 1 dia útil." in novas[0].texto

    # O acerto concluído não se edita mais.
    retrovisor = next(i for i in corpo["acerto"]["itens"] if i["tipo"] == "avaria")
    editar = _valor_do_item(cenario, corpo["id"], retrovisor["id"], 9000)
    assert editar.status_code == 409
    assert editar.json()["codigo"] == "acerto_concluido"
    assert _encerrar(cenario, corpo["id"]).status_code == 409


def test_dev_04_vai_para_oficina_leva_a_em_manutencao(cenario, lucas):
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    corpo = _chegada(
        cenario, devolucao, 3200, avarias=(("Garfo empenado", {"vai_para_oficina": True}),)
    )
    avaria = _item(corpo, "avaria")
    oficina: list[dict[str, Any]] = []

    def ouvir(**dados: Any) -> None:
        oficina.append(dados)

    eventos.assinar("vistorias.devolucao_encerrada", ouvir)
    try:
        assert _forma(cenario, devolucao["id"]).status_code == 200
        assert _encerrar(cenario, devolucao["id"]).status_code == 200
    finally:
        eventos.remover_assinante("vistorias.devolucao_encerrada", ouvir)
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "em_manutencao"
    assert [e["avarias_para_oficina"] for e in oficina] == [[avaria["avaria_id"]]]
    assert Locacao.objects.get(pk=criada["id"]).status == "encerrada"


# --- CA-016-19 · Quem fecha a conta ---


def test_dev_ca_016_19_quem_fecha_a_conta(cenario, lucas):
    criada = _lucas_ativo(cenario)
    assert cenario.moto.api("Lúcia").post(f"{LISTA}{criada['id']}/devolucao/").status_code == 403
    devolucao = _abrir_devolucao(cenario, criada["id"])  # João faz a vistoria de chegada
    _chegada(cenario, devolucao, 3200)
    url = f"{DEVOLUCOES}{devolucao['id']}/"

    joao = cenario.moto.api("João")
    vista = joao.get(url)
    assert vista.status_code == 200
    assert "acerto" not in vista.json()
    assert not {c for c in _chaves(vista.json()) if c.endswith("_centavos")}
    multa = {"tipo": "multa_transito", "descricao": "Multa de 05 out", "valor_centavos": 13016}
    assert joao.post(f"{url}acerto/itens/", multa, format="json").status_code == 403
    assert _forma(cenario, devolucao["id"], quem="João").status_code == 403
    assert _encerrar(cenario, devolucao["id"], quem="João").status_code == 403
    assert joao.get(f"{url}recibo/").status_code == 403
    assert cenario.moto.api("Lúcia").get(url).status_code == 403

    incluida = cenario.moto.api("Bruna").post(f"{url}acerto/itens/", multa, format="json")
    assert incluida.status_code == 200, incluida.json()
    assert _item(incluida.json(), "multa_transito")["valor_centavos"] == 13016
    calculado = {"tipo": "atraso", "descricao": "Atraso", "valor_centavos": 100}
    recusado = cenario.moto.api("Bruna").post(f"{url}acerto/itens/", calculado, format="json")
    assert recusado.status_code == 400
    assert _forma(cenario, devolucao["id"], quem="Rodrigo").status_code == 200
    resposta = _encerrar(cenario, devolucao["id"], quem="Rodrigo")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["acerto"]["saldo_centavos"] == 30000 - 13016


# --- CA-016-20 · Recibo ---


def test_dev_ca_016_20_recibo(cenario, lucas, relogio, django_capture_on_commit_callbacks):
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    _chegada(cenario, devolucao, 3200, "tres_quartos")
    url = f"{DEVOLUCOES}{devolucao['id']}/recibo/"
    bruna = cenario.moto.api("Bruna")
    antes = bruna.get(url)
    assert antes.status_code == 409
    assert antes.json()["codigo"] == "devolucao_em_rascunho"

    assert _forma(cenario, devolucao["id"]).status_code == 200
    enviadas = len(whatsapp.caixa_de_saida)
    try:
        with django_capture_on_commit_callbacks(execute=True):
            assert _encerrar(cenario, devolucao["id"]).status_code == 200
        resposta = bruna.get(url)
        assert resposta.status_code == 200, resposta.json()
        expira = datetime.fromisoformat(resposta.json()["url_expira_em"].replace("Z", "+00:00"))
        assert expira - relogio.agora == timedelta(minutes=15)
        assert resposta.json()["url"] != bruna.get(url).json()["url"]  # cada GET, uma URL nova
        with django_capture_on_commit_callbacks(execute=True):
            reenviar = bruna.post(f"{url}reenviar/")
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert reenviar.status_code == 202
    assert len(whatsapp.caixa_de_saida) - enviadas == 2  # o envio e o reenvio

    html, _ = recibo.corpo(Devolucao.objects.get(pk=devolucao["id"]))
    textos = [html.lower(), *(m.texto.lower() for m in whatsapp.caixa_de_saida[enviadas:])]
    assert "devolução" in textos[0] and "caução" in textos[0]
    for texto in textos:
        assert "check-in" not in texto and "depósito" not in texto
    assert "Devolução de R$ 268,00 por Pix em até 1 dia útil." in html


# --- Isolamento ---


def test_dev_devolucao_da_empresa_a_nao_aparece_na_b(cenario, lucas):
    criada = _lucas_ativo(cenario)
    _abrir_devolucao(cenario, criada["id"])
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Devolucao.objects.exists()
    finally:
        connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert Devolucao.objects.count() == 1


def test_dev_devolucao_fora_da_filial_responde_404(cenario, lucas):
    criada = _lucas_ativo(cenario)
    devolucao = _abrir_devolucao(cenario, criada["id"])
    so_caucaia = cenario.moto.api("Mariana", HTTP_X_FILIAL=str(_caucaia(cenario.moto).pk))
    assert so_caucaia.get(f"{DEVOLUCOES}{devolucao['id']}/").status_code == 404


# --- Troca (T-092) e caixa (T-017) ---


@aguarda("T-092")
def test_loc_09_ca_016_15_troca_de_veiculo_acerto_unico(cenario):
    pendente(avaria=8500, diferenca_caucao=20000, caucao_final=50000)


@aguarda("T-017")
def test_fin_07_ca_016_18_devolucao_em_dinheiro_exige_caixa(cenario):
    pendente(codigo="FIN-07", saida_dinheiro=18300)
