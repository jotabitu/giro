"""Arquivos privados (ADR 0009, AUD-05): validação pelo conteúdo, caminho e URL assinada."""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from comum import arquivos
from comum.erros import ErroDeValidacao

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"0" * 32


@pytest.mark.parametrize(
    ("nome", "conteudo", "tipo"),
    [
        ("foto.png", PNG, "image/png"),
        ("foto.JPEG", JPG, "image/jpeg"),
        ("cnh.pdf", b"%PDF-1.4", "application/pdf"),
    ],
)
def test_aud_05_aceita_pdf_jpg_e_png_pelo_conteudo(nome, conteudo, tipo):
    assert arquivos.validar(SimpleUploadedFile(nome, conteudo)).tipo_conteudo == tipo


@pytest.mark.parametrize(
    ("nome", "conteudo"),
    [
        ("virus.exe", b"MZ\x90\x00"),
        ("foto.png", b"MZ\x90\x00"),  # extensão certa, conteúdo errado
        ("foto.exe", PNG),  # conteúdo certo, extensão errada
        ("grande.png", PNG + b"0" * arquivos.TAMANHO_MAXIMO),
    ],
)
def test_aud_05_recusa_formato_ou_tamanho(nome, conteudo):
    with pytest.raises(ErroDeValidacao) as erro:
        arquivos.validar(SimpleUploadedFile(nome, conteudo))
    assert "arquivo" in erro.value.campos


def test_aud_05_url_assinada_vale_15_minutos_e_muda_a_cada_leitura(relogio):
    arquivos.ProvedorFalso().salvar("empresa_a/x/y/1/a.png", PNG, "image/png")
    primeira = arquivos.url_assinada("empresa_a/x/y/1/a.png")
    segunda = arquivos.url_assinada("empresa_a/x/y/1/a.png")
    assert primeira.expira_em - relogio.agora == timedelta(minutes=15)
    assert primeira.url != segunda.url
    assert "assinatura=" in primeira.url


def test_aud_05_caminho_exige_o_objeto_gravado():
    class SemId:
        pk = None

    with pytest.raises(ValueError, match="ADR 0009"):
        arquivos.caminho_privado(SemId(), "a.png")  # type: ignore[arg-type]


def test_aud_05_armazenamento_desconhecido_falha(settings):
    settings.GIRO_ARMAZENAMENTO = "disco"
    with pytest.raises(ValueError, match="disco"):
        arquivos.provedor()
