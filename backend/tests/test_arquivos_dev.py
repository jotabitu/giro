"""T-210: no desenvolvimento a URL assinada da foto é da mesma origem e abre no navegador."""

from datetime import timedelta
from urllib.parse import parse_qsl, urlsplit

import pytest
from django.test import RequestFactory, override_settings

from comum import arquivos, relogio
from comum.arquivos_dev import servir

CAMINHO = "motorapida/vistorias/fotovistoria/1/abc.jpg"


@pytest.fixture(autouse=True)
def _foto():
    arquivos.guardados[CAMINHO] = (b"\xff\xd8\xffjpeg", "image/jpeg")
    yield
    arquivos.guardados.pop(CAMINHO, None)


def _abrir(url: str):
    partes = urlsplit(url)
    pedido = RequestFactory().get(partes.path, dict(parse_qsl(partes.query)))
    return servir(pedido, partes.path.removeprefix("/api/arquivos-dev/"))


def test_t210_url_do_desenvolvimento_e_da_mesma_origem():
    with override_settings(GIRO_ARQUIVOS_FALSOS_BASE="/api/arquivos-dev"):
        url = arquivos.url_assinada(CAMINHO).url
        assert url.startswith("/api/arquivos-dev/")
        resposta = _abrir(url)
    assert resposta.status_code == 200
    assert resposta["Content-Type"] == "image/jpeg"
    assert resposta.content.startswith(b"\xff\xd8\xff")


def test_t210_nos_testes_a_base_continua_invalida():
    assert arquivos.url_assinada(CAMINHO).url.startswith("https://arquivos.invalid/")


def test_t210_assinatura_adulterada_e_recusada():
    with override_settings(GIRO_ARQUIVOS_FALSOS_BASE="/api/arquivos-dev"):
        url = arquivos.url_assinada(CAMINHO).url
    assert _abrir(url[:-1] + ("0" if url[-1] != "0" else "1")).status_code == 403


def test_t210_link_vencido_e_recusado(monkeypatch):
    with override_settings(GIRO_ARQUIVOS_FALSOS_BASE="/api/arquivos-dev"):
        url = arquivos.url_assinada(CAMINHO).url
    depois = relogio.agora() + timedelta(minutes=16)
    monkeypatch.setattr(relogio, "agora", lambda: depois)
    assert _abrir(url).status_code == 403


def test_t218_foto_em_disco_sobrevive_ao_reinicio(tmp_path):
    """Com a pasta definida, o conteúdo fica em disco e não depende do dicionário da memória."""
    caminho = "motorapida/vistorias/fotovistoria/2/def.jpg"
    with override_settings(
        GIRO_ARQUIVOS_FALSOS_BASE="/api/arquivos-dev",
        GIRO_ARQUIVOS_FALSOS_DIRETORIO=str(tmp_path),
    ):
        arquivos.ProvedorFalso().salvar(caminho, b"\xff\xd8\xffdisco", "image/jpeg")
        assert caminho not in arquivos.guardados
        guardados_antes = dict(arquivos.guardados)
        arquivos.guardados.clear()  # simula o backend recriado: a memória volta vazia
        try:
            resposta = _abrir(arquivos.url_assinada(caminho).url)
            assert resposta.status_code == 200
            assert resposta["Content-Type"] == "image/jpeg"
            assert resposta.content == b"\xff\xd8\xffdisco"
            arquivos.ProvedorFalso().apagar(caminho)
            assert not arquivos.ProvedorFalso().existe(caminho)
        finally:
            arquivos.guardados.update(guardados_antes)


def test_t218_caminho_fora_da_pasta_e_recusado(tmp_path):
    with override_settings(GIRO_ARQUIVOS_FALSOS_DIRETORIO=str(tmp_path)):
        assert arquivos.ler_falso("../fora.jpg") is None
