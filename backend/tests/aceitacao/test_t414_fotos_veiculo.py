"""T-414 · Fotos do veículo: galeria própria e fotos da última vistoria (VEI-10, VIS-01, AUD-01,
AUD-05, PLT-07).

Critérios em docs/qa/criterios/T-414.md (CA-414-01 a 14); contrato em docs/api/veiculos.md,
"Fotos do veículo"; ADR 0036. A galeria do QXA-4B21 é a do seed (`seed/fotos.py`): lateral,
frente (capa) e painel, enviadas pela Mariana em 12 mar 2025.
"""

import io
import struct
import zlib
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import RequestFactory
from django_tenants.utils import schema_context
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.plataforma.services import abrir_acesso_suporte
from apps.veiculos import selectors as veiculos_selectors
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import TRANSICOES_VEICULO, FotoVeiculo, Veiculo
from apps.vistorias import leituras as vistorias_leituras
from apps.vistorias.models import Avaria, Vistoria
from comum import arquivos
from comum.arquivos_dev import servir
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from comum.erros import ErroDeValidacao
from seed import fotos as fotos_do_seed

from . import carteira
from .conftest import cliente as cliente_http
from .frota import Frota, montar_frota
from .test_t012_filiais import HOST, MotoRapida
from .test_t015_locacoes import Cenario
from .test_t016_vistorias import (  # noqa: F401 - fixtures
    _carlos_na_devolucao,
    cenario,
    da_carteira,
)
from .test_t317_varredura_suporte import _suporte

VEICULOS = "/api/veiculos/"
FOTO_INVALIDA = ["Envie uma foto JPG ou PNG de até 10 MB."]
LIMITE = ["O veículo já tem 20 fotos. Apague uma para enviar outra."]
NAO_EDITAM = ("Bruna", "João", "Lúcia")  # vendedor, vistoriador e financeiro


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto, relogio) -> Frota:
    frota = montar_frota(moto)
    assert fotos_do_seed.garantir_fotos_do_qxa(relogio)  # a galeria do QXA-4B21 (seed)
    return frota


def _jpg(nome: str = "moto.jpg", gps: bool = False, cor: str = "red") -> SimpleUploadedFile:
    imagem = Image.new("RGB", (16, 12), cor)
    saida = io.BytesIO()
    exif = Image.Exif()
    if gps:
        exif[0x8825] = {1: "S", 2: (3.0, 43.0, 12.0), 3: "W", 4: (38.0, 32.0, 6.0)}
    imagem.save(saida, format="JPEG", exif=exif.tobytes())
    return SimpleUploadedFile(nome, saida.getvalue(), content_type="image/jpeg")


def _png(nome: str = "moto.png") -> SimpleUploadedFile:
    saida = io.BytesIO()
    Image.new("RGB", (16, 12), "blue").save(saida, format="PNG")
    return SimpleUploadedFile(nome, saida.getvalue(), content_type="image/png")


def _grande() -> SimpleUploadedFile:
    """11 MB que começam como JPG: recusado pelo tamanho."""
    return SimpleUploadedFile("grande.jpg", b"\xff\xd8\xff" + b"0" * (11 * 1024 * 1024))


def _heic() -> SimpleUploadedFile:
    return SimpleUploadedFile("moto.heic", b"\x00\x00\x00\x18ftypheic" + b"0" * 64)


def _pdf() -> SimpleUploadedFile:
    return SimpleUploadedFile("documento.pdf", b"%PDF-1.4\n%fim\n", content_type="application/pdf")


def _fotos(veiculo: Veiculo) -> str:
    return f"{VEICULOS}{veiculo.pk}/fotos/"


def _enviar(moto: MotoRapida, veiculo: Veiculo, arquivo: Any, pessoa: str = "Mariana") -> Any:
    return moto.api(pessoa).post(_fotos(veiculo), {"arquivo": arquivo}, format="multipart")


def _acao(moto: MotoRapida, veiculo: Veiculo, foto_id: int, acao: str, pessoa: str = "Rodrigo"):
    return moto.api(pessoa).post(f"{_fotos(veiculo)}{foto_id}/{acao}/", format="multipart")


def _trocar(moto: MotoRapida, veiculo: Veiculo, foto_id: int, arquivo: Any, pessoa="Rodrigo"):
    return moto.api(pessoa).post(
        f"{_fotos(veiculo)}{foto_id}/trocar/", {"arquivo": arquivo}, format="multipart"
    )


def _galeria(moto: MotoRapida, veiculo: Veiculo, pessoa: str = "Rodrigo") -> dict[str, Any]:
    resposta = moto.api(pessoa).get(_fotos(veiculo))
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _ficha(moto: MotoRapida, veiculo: Veiculo, pessoa: str = "Rodrigo") -> dict[str, Any]:
    resposta = moto.api(pessoa).get(f"{VEICULOS}{veiculo.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _levar(veiculo: Veiculo, destino: str) -> None:
    """Leva o veículo ao `destino` pelo serviço (a máquina de estados recusa `update()`), pelo
    caminho mais curto da tabela de transições."""
    caminhos: dict[str, list[str]] = {veiculo.status: []}
    fila = [veiculo.status]
    while fila and destino not in caminhos:
        atual = fila.pop(0)
        for proximo in TRANSICOES_VEICULO[atual]:
            if proximo not in caminhos:
                caminhos[proximo] = [*caminhos[atual], proximo]
                fila.append(proximo)
    for status in caminhos[destino]:
        veiculo = veiculos_services.transicionar(veiculo, status, origem=veiculos_services.MANUAL)


def _ids(galeria: dict[str, Any]) -> list[int]:
    return [foto["id"] for foto in galeria["fotos"]]


def _do_seed(veiculo: Veiculo) -> dict[str, int]:
    """Lateral, frente e painel do QXA-4B21, pela ordem de envio."""
    ordem = FotoVeiculo.ativos.filter(veiculo=veiculo).order_by("ordem")
    return dict(
        zip(("Lateral", "Frente", "Painel"), ordem.values_list("pk", flat=True), strict=True)
    )


def _baixar(url: str) -> Any:
    """Abre o link assinado pelo servidor do armazenamento falso, como o navegador faria."""
    partes = urlsplit(url)
    pedido = RequestFactory().get(partes.path, dict(parse_qsl(partes.query)))
    return servir(pedido, partes.path.lstrip("/"))


# --- Galeria no editar ---


def test_vei_10_seed_galeria_do_qxa(moto, frota) -> None:
    """3 fotos, a frente primeiro (`numero` 1) e capa; o editar aceita mais 17. Rodar o seed de
    novo não duplica."""
    qxa = frota.veiculo("QXA4B21")
    galeria = _galeria(moto, qxa)
    seed = _do_seed(qxa)
    assert (galeria["total"], galeria["limite"], galeria["editar"], galeria["motivo"]) == (
        3,
        20,
        True,
        None,
    )
    assert _ids(galeria) == [seed["Frente"], seed["Lateral"], seed["Painel"]]
    assert [(f["numero"], f["capa"], f["rotulo"]) for f in galeria["fotos"]] == [
        (1, True, None),
        (2, False, None),
        (3, False, None),
    ]
    mariana = moto.pessoas["Mariana"]
    assert galeria["fotos"][0]["enviada_por"] == {"id": mariana.pk, "nome": mariana.nome}
    assert galeria["fotos"][0]["enviada_em"].startswith("2025-03-12")
    assert not fotos_do_seed.garantir_fotos_do_qxa(cast(Any, SimpleNamespace(agora=None, em=None)))
    assert FotoVeiculo.objects.filter(veiculo=qxa).count() == 3


def test_vei_10_ca_414_01_enviar(moto, frota) -> None:
    """A Mariana envia `moto-1.jpg` e `moto.png`: 5 fotos, na ordem de envio, e a capa continua a
    frente. Evento `veiculo.foto_enviar` sem a imagem."""
    qxa = frota.veiculo("QXA4B21")
    seed = _do_seed(qxa)
    primeira = _enviar(moto, qxa, _jpg("moto-1.jpg"))
    assert primeira.status_code == 201, primeira.json()
    segunda = _enviar(moto, qxa, _png())
    assert segunda.status_code == 201, segunda.json()
    corpo = segunda.json()
    assert corpo["total"] == 5
    assert _ids(corpo)[:3] == [seed["Frente"], seed["Lateral"], seed["Painel"]]
    assert _ids(corpo)[3:] == [primeira.json()["foto_id"], corpo["foto_id"]]
    assert corpo["fotos"][0]["capa"] and not any(f["capa"] for f in corpo["fotos"][1:])
    assert corpo["fotos"][4]["nome_arquivo"] == "QXA-4B21-galeria-5.png"
    evento = EventoAuditoria.objects.filter(acao="veiculo.foto_enviar", objeto_id=qxa.pk).latest(
        "id"
    )
    assert evento.depois == {"foto_id": corpo["foto_id"], "numero": 5, "capa": False}
    assert evento.ator_nome == moto.pessoas["Mariana"].nome
    assert evento.regra == "VEI-10"


def test_vei_10_ca_414_02_arquivo_recusado_e_os_outros_seguem(moto, frota) -> None:
    qxa = frota.veiculo("QXA4B21")
    for arquivo in (_grande(), _heic(), _pdf(), SimpleUploadedFile("vazia.jpg", b"")):
        resposta = _enviar(moto, qxa, arquivo)
        assert resposta.status_code == 400, arquivo.name
        assert resposta.json()["campos"] == {"arquivo": FOTO_INVALIDA}
    # JPG com o nome de PNG vale pelo conteúdo; imagem que não abre é recusada.
    quebrada = SimpleUploadedFile("quebrada.jpg", b"\xff\xd8\xff" + b"lixo" * 10)
    assert _enviar(moto, qxa, quebrada).json()["campos"] == {"arquivo": FOTO_INVALIDA}
    sem_arquivo = moto.api().post(_fotos(qxa), {}, format="multipart")
    assert sem_arquivo.json()["campos"] == {"arquivo": FOTO_INVALIDA}
    assert _enviar(moto, qxa, _jpg("moto-1.jpg")).status_code == 201
    assert _galeria(moto, qxa)["total"] == 4


def test_vei_10_ca_414_03_limite_de_20(moto, frota) -> None:
    qxa = frota.veiculo("QXA4B21")
    for numero in range(1, 18):
        resposta = _enviar(moto, qxa, _jpg(f"moto-{numero}.jpg"))
        assert resposta.status_code == 201, (numero, resposta.json())
    assert resposta.json()["total"] == 20
    recusada = _enviar(moto, qxa, _jpg("moto-18.jpg"))
    assert recusada.status_code == 400
    assert recusada.json()["campos"] == {"arquivo": LIMITE}
    assert FotoVeiculo.ativos.filter(veiculo=qxa).count() == 20
    # Trocar não conta no limite; apagar abre vaga.
    primeira = _galeria(moto, qxa)["fotos"][0]["id"]
    assert _trocar(moto, qxa, primeira, _jpg("nova.jpg")).status_code == 200
    ultima = _galeria(moto, qxa)["fotos"][-1]["id"]
    assert _acao(moto, qxa, ultima, "apagar").status_code == 200
    assert _enviar(moto, qxa, _jpg("moto-18.jpg")).status_code == 201


def test_vei_10_ca_414_04_sem_localizacao(moto, frota) -> None:
    """A foto baixada pela ficha não tem EXIF nem GPS (AUD-05)."""
    qxa = frota.veiculo("QXA4B21")
    resposta = _enviar(moto, qxa, _jpg("moto-gps.jpg", gps=True))
    assert resposta.status_code == 201
    foto = next(f for f in _ficha(moto, qxa)["galeria"]["fotos"] if f["numero"] == 4)
    baixada = _baixar(foto["url_download"])
    assert baixada.status_code == 200
    with Image.open(io.BytesIO(baixada.content)) as imagem:
        assert imagem.format == "JPEG"
        assert not imagem.getexif()
        assert "exif" not in imagem.info


def test_vei_10_ca_414_05_capa(moto, frota) -> None:
    """PNB-7C04 sem galeria: a 1ª enviada vira capa; "Usar como capa" na 2ª; apagada a 2ª, a 1ª
    volta a ser capa."""
    pnb = frota.veiculo("PNB7C04")
    assert _galeria(moto, pnb)["total"] == 0
    um = _enviar(moto, pnb, _jpg("moto-1.jpg"), "Rodrigo").json()["foto_id"]
    dois = _enviar(moto, pnb, _jpg("moto-2.jpg"), "Rodrigo").json()["foto_id"]
    galeria = _galeria(moto, pnb)
    assert _ids(galeria) == [um, dois] and galeria["fotos"][0]["capa"]

    capa = _acao(moto, pnb, dois, "capa")
    assert capa.status_code == 200, capa.json()
    assert _ids(capa.json()) == [dois, um]
    assert [f["numero"] for f in capa.json()["fotos"]] == [1, 2]
    assert _ids(_ficha(moto, pnb)["galeria"]) == [dois, um]
    evento = EventoAuditoria.objects.filter(acao="veiculo.foto_capa", objeto_id=pnb.pk).get()
    assert evento.depois == {"foto_id": dois, "capa_anterior_id": um}
    # Já capa: nada muda e não há evento.
    assert _acao(moto, pnb, dois, "capa").status_code == 200
    assert EventoAuditoria.objects.filter(acao="veiculo.foto_capa", objeto_id=pnb.pk).count() == 1

    apagada = _acao(moto, pnb, dois, "apagar")
    assert apagada.status_code == 200
    assert _ids(apagada.json()) == [um]
    assert apagada.json()["fotos"][0]["capa"]
    evento = EventoAuditoria.objects.filter(acao="veiculo.foto_apagar", objeto_id=pnb.pk).get()
    assert evento.depois == {"foto_id": dois, "era_capa": True, "nova_capa_id": um}


def test_vei_10_ca_414_06_trocar(moto, frota) -> None:
    """A frente (capa) trocada: a nova fica na mesma posição e continua capa; continua com 3."""
    qxa = frota.veiculo("QXA4B21")
    seed = _do_seed(qxa)
    resposta = _trocar(moto, qxa, seed["Frente"], _png("moto-1.png"))
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    nova = corpo["foto_id"]
    assert corpo["total"] == 3
    assert _ids(corpo) == [nova, seed["Lateral"], seed["Painel"]]
    assert corpo["fotos"][0]["capa"]
    assert corpo["fotos"][0]["nome_arquivo"] == "QXA-4B21-galeria-1.png"
    antiga = FotoVeiculo.objects.get(pk=seed["Frente"])
    assert (antiga.ativo, antiga.substituida_por_id, antiga.capa) == (False, nova, True)
    assert FotoVeiculo.objects.get(pk=nova).ordem == antiga.ordem
    evento = EventoAuditoria.objects.filter(acao="veiculo.foto_trocar", objeto_id=qxa.pk).get()
    assert evento.depois == {"foto_id_antiga": seed["Frente"], "foto_id_nova": nova}
    # A antiga não se troca de novo; arquivo inválido não mexe na galeria.
    assert _trocar(moto, qxa, seed["Frente"], _jpg()).status_code == 404
    invalida = _trocar(moto, qxa, nova, _pdf())
    assert invalida.status_code == 400
    assert invalida.json()["campos"] == {"arquivo": FOTO_INVALIDA}
    assert _ids(_galeria(moto, qxa)) == _ids(corpo)


def test_vei_10_ca_414_07_apagar(moto, frota) -> None:
    """O painel some da galeria e da ficha e não volta; o arquivo fica guardado, inativo, e o
    evento diz quem apagou."""
    qxa = frota.veiculo("QXA4B21")
    seed = _do_seed(qxa)
    resposta = _acao(moto, qxa, seed["Painel"], "apagar")
    assert resposta.status_code == 200
    assert resposta.json()["total"] == 2
    assert seed["Painel"] not in _ids(_ficha(moto, qxa, "Bruna")["galeria"])
    painel = FotoVeiculo.objects.get(pk=seed["Painel"])
    rodrigo = moto.pessoas["Rodrigo"]
    assert (painel.ativo, painel.apagada_por_id) == (False, rodrigo.pk)
    assert arquivos.provedor().existe(painel.arquivo.name)
    evento = EventoAuditoria.objects.filter(acao="veiculo.foto_apagar", objeto_id=qxa.pk).get()
    assert (evento.ator_id, evento.ator_nome) == (rodrigo.pk, rodrigo.nome)
    assert evento.depois == {"foto_id": seed["Painel"], "era_capa": False, "nova_capa_id": None}
    assert "url" not in str(evento.depois) and "arquivo" not in evento.depois
    # Não volta: apagar, trocar e capa da apagada respondem 404.
    for acao in ("apagar", "capa"):
        assert _acao(moto, qxa, seed["Painel"], acao).status_code == 404
    assert _trocar(moto, qxa, seed["Painel"], _jpg()).status_code == 404


def test_vei_10_ca_414_08_quem_mexe(relogio_jwt, moto, frota) -> None:
    # `relogio_jwt` antes da frota: o token da Mariana sai no `montar_frota`, já no relógio
    # congelado.
    """Vendedor, vistoriador e financeiro veem e recebem 403 nas mudanças; o suporte em "ver e
    editar" vê e recebe 403 `PLT-07`."""
    qxa = frota.veiculo("QXA4B21")
    frente = _do_seed(qxa)["Frente"]
    for pessoa in NAO_EDITAM:
        galeria = _galeria(moto, qxa, pessoa)
        assert (galeria["total"], galeria["editar"], galeria["motivo"]) == (3, False, None)
        assert _ficha(moto, qxa, pessoa)["acoes"]["editar_fotos"] is False
        assert _enviar(moto, qxa, _jpg(), pessoa).status_code == 403
        assert _trocar(moto, qxa, frente, _jpg(), pessoa).status_code == 403
        for acao in ("capa", "apagar"):
            assert _acao(moto, qxa, frente, acao, pessoa).status_code == 403
    assert _ficha(moto, qxa, "Mariana")["acoes"]["editar_fotos"] is True

    suporte = _suporte(cast(Any, SimpleNamespace(moto=moto, frota=frota)))
    vista = suporte.get(_fotos(qxa))
    assert vista.status_code == 200
    assert (vista.json()["total"], vista.json()["editar"], vista.json()["motivo"]) == (
        3,
        False,
        None,
    )
    assert suporte.get(f"{VEICULOS}{qxa.pk}/").json()["acoes"]["editar_fotos"] is False
    respostas = [
        suporte.post(_fotos(qxa), {"arquivo": _jpg()}, format="multipart"),
        suporte.post(f"{_fotos(qxa)}{frente}/trocar/", {"arquivo": _jpg()}, format="multipart"),
        suporte.post(f"{_fotos(qxa)}{frente}/capa/"),
        suporte.post(f"{_fotos(qxa)}{frente}/apagar/"),
    ]
    assert [(r.status_code, r.json()["codigo"]) for r in respostas] == [(403, "PLT-07")] * 4
    assert FotoVeiculo.ativos.filter(veiculo=qxa).count() == 3


@pytest.mark.parametrize("status", ["baixado", "vendido"])
def test_vei_10_ca_414_09_vendido_e_baixado_so_para_ver(moto, frota, status) -> None:
    qxa = frota.veiculo("QXA4B21")
    frente = _do_seed(qxa)["Frente"]
    _levar(qxa, status)
    mensagem = (
        "A galeria de veículo baixado fica só para ver."
        if status == "baixado"
        else "A galeria de veículo vendido fica só para ver."
    )
    galeria = _galeria(moto, qxa)
    assert (galeria["total"], galeria["editar"], galeria["motivo"]) == (3, False, mensagem)
    assert _galeria(moto, qxa, "Bruna")["motivo"] is None
    ficha = _ficha(moto, qxa)
    assert ficha["galeria"]["total"] == 3 and ficha["acoes"]["editar_fotos"] is False
    # O status vem antes do arquivo: o PDF também recebe o 409.
    respostas = [
        _enviar(moto, qxa, _pdf(), "Rodrigo"),
        _trocar(moto, qxa, frente, _jpg()),
        _acao(moto, qxa, frente, "capa"),
        _acao(moto, qxa, frente, "apagar"),
    ]
    assert [(r.status_code, r.json()) for r in respostas] == [
        (409, {"codigo": "VEI-10", "mensagem": mensagem, "detalhes": None})
    ] * 4


@pytest.mark.parametrize("status", ["a_venda", "alugado", "em_manutencao"])
def test_vei_10_ca_414_09_outros_estados_mudam(moto, frota, status) -> None:
    pnb = frota.veiculo("PNB7C04")
    _levar(pnb, status)
    assert _galeria(moto, pnb)["editar"] is True
    assert _enviar(moto, pnb, _jpg(), "Rodrigo").status_code == 201


def test_vei_10_escopo_de_filial_e_foto_de_outro_veiculo(moto, frota) -> None:
    """Foto de outro veículo: 404. Veículo fora do escopo de filial: 404 (USR-07)."""
    qxa = frota.veiculo("QXA4B21")
    pnb = frota.veiculo("PNB7C04")
    frente = _do_seed(qxa)["Frente"]
    assert _acao(moto, pnb, frente, "capa").status_code == 404
    assert _acao(moto, pnb, frente, "apagar").status_code == 404
    assert _trocar(moto, pnb, frente, _jpg()).status_code == 404
    assert FotoVeiculo.objects.get(pk=frente).ativo
    assert moto.api("Rodrigo").get(f"{VEICULOS}999999/fotos/").status_code == 404


# --- Ficha ---


def test_vei_10_ca_414_10_galeria_na_ficha(moto, frota) -> None:
    """Bruna, Lúcia e Rodrigo veem as 3 fotos, a frente primeiro, com os dois links."""
    qxa = frota.veiculo("QXA4B21")
    seed = _do_seed(qxa)
    for pessoa in ("Bruna", "Lúcia", "Rodrigo"):
        galeria = _ficha(moto, qxa, pessoa)["galeria"]
        assert (galeria["total"], galeria["limite"]) == (3, 20)
        assert _ids(galeria) == [seed["Frente"], seed["Lateral"], seed["Painel"]]
        for foto in galeria["fotos"]:
            assert foto["url"] != foto["url_download"]
            assert foto["url_expira_em"]
    assert "galeria" not in moto.api("Rodrigo").get(VEICULOS).json()["resultados"][0]


def test_vei_10_ca_414_12_baixar_com_o_nome_e_link_de_15_minutos(moto, frota, relogio) -> None:
    """`url_download` baixa como "QXA-4B21-galeria-1.jpg"; `url` abre sem baixar. Depois de 15
    minutos o link não abre, e a ficha recarregada gera outro."""
    qxa = frota.veiculo("QXA4B21")
    frente = _ficha(moto, qxa)["galeria"]["fotos"][0]
    assert frente["nome_arquivo"] == "QXA-4B21-galeria-1.jpg"
    assert dict(parse_qsl(urlsplit(frente["url_download"]).query))["baixar"] == (
        "QXA-4B21-galeria-1.jpg"
    )
    baixada = _baixar(frente["url_download"])
    assert baixada.status_code == 200
    assert baixada["Content-Disposition"] == 'attachment; filename="QXA-4B21-galeria-1.jpg"'
    vista = _baixar(frente["url"])
    assert vista.status_code == 200 and "Content-Disposition" not in vista
    # O nome entra na assinatura: trocar o nome derruba o link.
    adulterada = frente["url_download"].replace("galeria-1.jpg", "galeria-9.jpg")
    assert _baixar(adulterada).status_code == 403

    relogio.em("2026-10-07 10:16")
    assert _baixar(frente["url_download"]).status_code == 403
    nova = _ficha(moto, qxa)["galeria"]["fotos"][0]
    assert nova["url_download"] != frente["url_download"]
    assert _baixar(nova["url_download"]).status_code == 200


def test_vei_10_ca_414_13_sem_fotos(moto, frota) -> None:
    """PNB-7C04 sem galeria: bloco vazio; "Adicionar fotos" só com `editar_fotos`. Sem vistoria
    concluída, a seção da vistoria não vem."""
    pnb = frota.veiculo("PNB7C04")
    ficha = _ficha(moto, pnb)
    assert ficha["galeria"] == {"total": 0, "limite": 20, "fotos": []}
    assert ficha["acoes"]["editar_fotos"] is True
    assert _ficha(moto, pnb, "Bruna")["acoes"]["editar_fotos"] is False
    assert ficha["vistoria_recente"] is None


def test_vei_10_isolamento_entre_empresas(moto, frota) -> None:
    """A galeria da empresa A não aparece na empresa B."""
    assert FotoVeiculo.objects.count() == 3
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not FotoVeiculo.objects.exists()


# --- Fotos da última vistoria (CA-414-11, 14) ---


@pytest.fixture
def carlos(cenario, da_carteira, relogio) -> Locacao:  # noqa: F811
    """LOC-2841 com a saída concluída em 23 set e as 12 fotos do seed (5 fixas e 7 de avaria)."""
    vistorias_leituras.registrar()
    locacao = _carlos_na_devolucao(da_carteira)
    assert fotos_do_seed.garantir_fotos_do_qxa(relogio)
    return locacao


def test_vei_10_ca_414_11_fotos_da_vistoria(cenario: Cenario, carlos) -> None:  # noqa: F811
    """Rodrigo, Bruna e João veem "Vistoria de saída · LOC-2841" com as 12 fotos; a Lúcia não
    recebe o bloco."""
    qxa = Veiculo.objects.get(pk=carlos.veiculo_id)
    saida = Vistoria.objects.get(locacao=carlos, tipo="saida")
    da_frente = saida.fotos.get(posicao="frente")
    de_avaria = saida.fotos.filter(posicao="avaria").order_by("tirada_em")[1]
    avaria = Avaria.objects.create(
        vistoria=saida,
        veiculo=qxa,
        descricao="Retrovisor riscado",
        preexistente=True,
        foto=de_avaria,
    )
    for pessoa in ("Rodrigo", "Bruna", "João"):
        recente = _ficha(cenario.moto, qxa, pessoa)["vistoria_recente"]
        assert (recente["id"], recente["rotulo_tipo"], recente["locacao_codigo"]) == (
            saida.pk,
            "Vistoria de saída",
            "LOC-2841",
        )
        assert recente["total_fotos"] == 12 == len(recente["fotos"])
        assert [f["numero"] for f in recente["fotos"]] == list(range(1, 13))
        assert [f["rotulo"] for f in recente["fotos"]] == [
            "Frente",
            "Traseira",
            "Lado esquerdo",
            "Lado direito",
            "Painel",
            *[f"Avaria {n}" for n in range(1, 8)],
        ]
        nomes = [f["nome_arquivo"] for f in recente["fotos"]]
        assert nomes[0] == "QXA-4B21-vistoria-saida-frente.jpg"
        assert nomes[2] == "QXA-4B21-vistoria-saida-lado-esquerdo.jpg"
        assert nomes[5] == "QXA-4B21-vistoria-saida-avaria-1.jpg"
        assert recente["fotos"][0]["id"] == da_frente.pk
        assert [f["avaria_id"] for f in recente["fotos"]] == [None] * 6 + [avaria.pk] + [None] * 5
    frente = _ficha(cenario.moto, qxa)["vistoria_recente"]["fotos"][0]
    baixada = _baixar(frente["url_download"])
    assert baixada["Content-Disposition"] == (
        'attachment; filename="QXA-4B21-vistoria-saida-frente.jpg"'
    )
    assert "vistoria_recente" not in _ficha(cenario.moto, qxa, "Lúcia")


def test_vei_10_ca_414_14_origens_separadas(cenario: Cenario, carlos, relogio) -> None:  # noqa: F811
    """Nenhuma foto da vistoria entra na galeria; a vistoria nova concluída passa a ser a da
    ficha, e a galeria continua igual."""
    qxa = Veiculo.objects.get(pk=carlos.veiculo_id)
    ficha = _ficha(cenario.moto, qxa)
    da_vistoria = {f["id"] for f in ficha["vistoria_recente"]["fotos"]}
    galeria = _ids(ficha["galeria"])
    assert len(galeria) == 3 and not FotoVeiculo.objects.filter(pk__in=da_vistoria).exists()
    assert veiculos_selectors.galeria(qxa)[0].pk == galeria[0]
    assert veiculos_selectors.capa(qxa) is not None

    relogio.em("2026-10-07 10:00")
    chegada = Vistoria.objects.create(
        locacao=carlos,
        veiculo=qxa,
        tipo="devolucao",
        status="concluida",
        km=qxa.km_atual,
        combustivel="cheio",
        itens=[],
        concluida_em=carteira.momento("2026-10-07 10:00"),
    )
    foto = chegada.fotos.create(posicao="frente", tirada_em=carteira.momento("2026-10-07 09:55"))
    foto.arquivo.save("frente.jpg", _jpg("frente.jpg"), save=True)
    depois = _ficha(cenario.moto, qxa)
    recente = depois["vistoria_recente"]
    assert (recente["id"], recente["rotulo_tipo"], recente["total_fotos"]) == (
        chegada.pk,
        "Vistoria de chegada",
        1,
    )
    assert recente["fotos"][0]["nome_arquivo"] == "QXA-4B21-vistoria-chegada-frente.jpg"
    assert _ids(depois["galeria"]) == galeria


# --- Links (ADR 0036, item 4) ---


def test_vei_10_nome_de_download_so_com_caracteres_seguros() -> None:
    for nome in ('a"b.jpg', "a b.jpg", "a\r\nX: y.jpg", "ção.jpg", "../x.jpg", ""):
        with pytest.raises(ValueError):
            arquivos.url_assinada("x/y.jpg", baixar_como=nome)
    assert arquivos.url_assinada("x/y.jpg", baixar_como="QXA-4B21-galeria-1.jpg").url


def test_vei_10_link_s3_leva_o_content_disposition(monkeypatch) -> None:
    """No S3, o nome vai em `ResponseContentDisposition`, que entra na assinatura."""
    chamadas: list[dict[str, Any]] = []

    class Cliente:
        def generate_presigned_url(
            self, operacao: str, Params: dict[str, Any], ExpiresIn: int
        ) -> str:
            chamadas.append({"operacao": operacao, "params": Params, "expira": ExpiresIn})
            return "https://s3.invalid/assinada"

    provedor = arquivos.ProvedorS3.__new__(arquivos.ProvedorS3)
    provedor.bucket = "giro"
    provedor.cliente = Cliente()
    monkeypatch.setattr(arquivos, "provedor", lambda: provedor)
    arquivos.url_assinada("a/b.jpg", baixar_como="QXA-4B21-galeria-1.jpg")
    arquivos.url_assinada("a/b.jpg")
    assert chamadas[0]["params"] == {
        "Bucket": "giro",
        "Key": "a/b.jpg",
        "ResponseContentDisposition": 'attachment; filename="QXA-4B21-galeria-1.jpg"',
    }
    assert chamadas[1]["params"] == {"Bucket": "giro", "Key": "a/b.jpg"}
    assert chamadas[0]["expira"] == int(timedelta(minutes=15).total_seconds())


# --- Revisão da segurança de 10 nov 2026 (docs/seguranca/2026-11-10-t414-fotos-do-veiculo.md) ---


def _suporte_no_modo(moto: MotoRapida, centro: Any, permissao: str) -> Any:
    """O suporte Giro na Moto Rápida, em "ver" (só ver) ou "ver_editar"."""
    with schema_context("public"):
        diego = Usuario.objects.filter(email="diego@girolocadoras.com.br").first()
        if diego is None:
            diego = Usuario.objects.create_user(
                "diego@girolocadoras.com.br",
                "senha-forte-123",
                nome="Diego Santos",
                funcao_plataforma="suporte",
            )
    _, token = abrir_acesso_suporte(
        Empresa.objects.get(pk=moto.empresa.pk),
        diego,
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao=permissao,
    )
    connection.set_tenant(moto.empresa)
    api = cliente_http(HOST, str(token))
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", HTTP_X_FILIAL=str(centro.pk))
    return api


LINKS = ("url", "url_download", "url_expira_em")


def test_plt_07_suporte_so_ver_nao_recebe_link_de_foto(
    relogio_jwt,
    cenario: Cenario,  # noqa: F811
    carlos,
) -> None:
    """M-01 · ADR 0013, item 2: no "só ver", nada de URL assinada de foto, nem em leitura. A ficha
    traz a galeria e a vistoria com número, rótulo e nome, e os links nulos; `GET .../fotos/`
    responde 403 `PLT-07`. Em "ver e editar", os links vêm."""
    qxa = Veiculo.objects.get(pk=carlos.veiculo_id)
    so_ver = _suporte_no_modo(cenario.moto, cenario.frota.centro, "ver")
    ficha = so_ver.get(f"{VEICULOS}{qxa.pk}/")
    assert ficha.status_code == 200
    galeria = ficha.json()["galeria"]
    recente = ficha.json()["vistoria_recente"]
    assert (galeria["total"], len(galeria["fotos"])) == (3, 3)
    assert (recente["total_fotos"], len(recente["fotos"])) == (12, 12)
    for foto in [*galeria["fotos"], *recente["fotos"]]:
        assert [foto[campo] for campo in LINKS] == [None, None, None]
        assert foto["numero"] and foto["nome_arquivo"]
    assert recente["fotos"][0]["rotulo"] == "Frente"
    galeria_do_editar = so_ver.get(_fotos(qxa))
    assert galeria_do_editar.status_code == 403
    assert galeria_do_editar.json()["codigo"] == "PLT-07"
    assert "url" not in galeria_do_editar.content.decode()

    ver_editar = _suporte_no_modo(cenario.moto, cenario.frota.centro, "ver_editar")
    completa = ver_editar.get(f"{VEICULOS}{qxa.pk}/").json()
    for foto in [*completa["galeria"]["fotos"], *completa["vistoria_recente"]["fotos"]]:
        assert all(foto[campo] for campo in LINKS)
    assert ver_editar.get(_fotos(qxa)).status_code == 200


def _png_com_tamanho(largura: int, altura: int, nome: str = "gigante.png") -> SimpleUploadedFile:
    """PNG de poucos bytes que declara `largura × altura` no cabeçalho: o teto em pixels tem que
    recusar antes de decodificar."""
    saida = io.BytesIO()
    Image.new("L", (1, 1)).save(saida, format="PNG")
    conteudo = bytearray(saida.getvalue())
    # IHDR logo depois da assinatura: 4 de tamanho, 4 do tipo, 13 de dados e 4 do CRC.
    dados = struct.pack(">II", largura, altura) + bytes(conteudo[24:29])
    conteudo[16:29] = dados
    conteudo[29:33] = struct.pack(">I", zlib.crc32(b"IHDR" + dados))
    return SimpleUploadedFile(nome, bytes(conteudo), content_type="image/png")


@pytest.mark.parametrize(("largura", "altura"), [(10000, 6000), (12000, 10000)])
def test_aud_05_foto_gigante_em_pixels_recusada(moto, frota, largura, altura) -> None:
    """M-02: 60 MP (acima do teto de 50 MP) e 120 MP (em que o Pillow só avisa) voltam 400 com a
    mensagem da galeria, e nada é gravado."""
    pnb = frota.veiculo("PNB7C04")
    resposta = _enviar(moto, pnb, _png_com_tamanho(largura, altura))
    assert resposta.status_code == 400
    assert resposta.json()["campos"] == {"arquivo": FOTO_INVALIDA}
    assert not FotoVeiculo.objects.filter(veiculo=pnb).exists()


def test_aud_05_teto_em_pixels_vale_para_toda_foto(monkeypatch) -> None:
    """O teto fica em `comum.arquivos.sem_metadados`, que serve a vistoria, os documentos e as
    notas: acima de 50 MP, a imagem nem chega a ser decodificada."""
    from PIL import ImageFile

    decodificadas: list[Any] = []
    carregar = ImageFile.ImageFile.load

    def load(imagem: Any) -> Any:
        decodificadas.append(imagem.size)
        return carregar(imagem)

    monkeypatch.setattr(ImageFile.ImageFile, "load", load)
    formato = arquivos.Formato("png", "image/png")
    with pytest.raises(ErroDeValidacao):
        arquivos.sem_metadados(_png_com_tamanho(7072, 7072), formato)  # 50,01 MP
    assert decodificadas == []
    assert arquivos.sem_metadados(_png("ok.png"), formato).size > 0


@pytest.mark.parametrize("erro", [SyntaxError("broken PNG file"), EOFError()])
def test_aud_05_png_quebrado_volta_400_e_nao_500(moto, frota, monkeypatch, erro) -> None:
    """B-01: o `SyntaxError` ("broken PNG file") e o `EOFError` do Pillow viram a recusa da
    galeria, e não 500."""
    import PIL.Image

    def abrir(*_: Any, **__: Any) -> Any:
        raise erro

    monkeypatch.setattr(PIL.Image, "open", abrir)
    pnb = frota.veiculo("PNB7C04")
    resposta = _enviar(moto, pnb, _png())
    assert resposta.status_code == 400
    assert resposta.json()["campos"] == {"arquivo": FOTO_INVALIDA}


def test_vei_10_isolamento_entre_empresas_pela_rota(moto, frota, planos) -> None:
    """B-02: a administradora da empresa B, no host dela, não lê nem muda a galeria da A pelos
    ids: 404, e a foto da A continua ativa. O arquivo da A mora no prefixo do schema dela."""
    qxa = frota.veiculo("QXA4B21")
    frente = FotoVeiculo.objects.get(pk=_do_seed(qxa)["Frente"])
    assert frente.arquivo.name.startswith("empresa_a/veiculos/fotoveiculo/")

    empresa_b = Empresa.objects.get(schema_name="empresa_b")
    connection.set_tenant(empresa_b)
    outra = MotoRapida(empresa_b, planos["Profissional"])
    token = str(emitir_tokens(outra.pessoas["Mariana"], AMR_SENHA_E_CODIGO).access_token)
    api_b = cliente_http("empresa-b.localhost", token)
    caminho = f"{VEICULOS}{qxa.pk}/fotos/"
    respostas = [
        api_b.get(caminho),
        api_b.get(f"{VEICULOS}{qxa.pk}/"),
        api_b.post(f"{caminho}{frente.pk}/trocar/", {"arquivo": _jpg()}, format="multipart"),
        api_b.post(f"{caminho}{frente.pk}/capa/"),
        api_b.post(f"{caminho}{frente.pk}/apagar/"),
    ]
    assert [r.status_code for r in respostas] == [404] * 5
    assert not FotoVeiculo.objects.exists()

    connection.set_tenant(moto.empresa)
    frente.refresh_from_db()
    assert (frente.ativo, frente.capa) == (True, True)
    assert FotoVeiculo.ativos.filter(veiculo=qxa).count() == 3
