"""Arquivos privados (ADR 0009, AUD-05): validação pelo conteúdo, caminho e URL assinada."""

import io
from datetime import timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from PIL.PngImagePlugin import PngInfo

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


def _png(imagem: Image.Image, **opcoes: Any) -> SimpleUploadedFile:
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", **opcoes)
    return SimpleUploadedFile("foto.png", saida.getvalue())


@pytest.mark.parametrize("transparencia", [None, 0])
def test_vis_02_png_com_paleta_mantem_as_cores(transparencia):
    """T-165: o PNG em modo `P` (com paleta e, num caso, `tRNS`) sai com as mesmas cores, sem
    os metadados (AUD-05)."""
    original = Image.new("P", (4, 2))
    original.putpalette([0, 0, 0, 220, 30, 40, 20, 160, 60, 30, 60, 200])
    original.putdata([0, 1, 2, 3, 3, 2, 1, 0])
    texto = PngInfo()
    texto.add_text("Comment", "GPS -3.73,-38.52")
    opcoes: dict[str, Any] = {"pnginfo": texto}
    if transparencia is not None:
        opcoes["transparency"] = transparencia
    arquivo = _png(original, **opcoes)
    with Image.open(io.BytesIO(arquivo.read())) as enviada:
        esperados = list(enviada.convert("RGBA").getdata())

    limpo = arquivos.sem_metadados(arquivo, arquivos.validar(arquivo))
    with Image.open(io.BytesIO(limpo.read())) as resultado:
        pixels = list(resultado.convert("RGBA").getdata())
        assert pixels == esperados
        assert "Comment" not in resultado.info and "transparency" not in resultado.info
        assert resultado.mode == ("RGB" if transparencia is None else "RGBA")
    # O índice 0 continua transparente só com o `tRNS`; o 1 é vermelho e opaco.
    assert pixels[0] == ((0, 0, 0, 255) if transparencia is None else (0, 0, 0, 0))
    assert pixels[1] == (220, 30, 40, 255)


def test_aud_05_armazenamento_desconhecido_falha(settings):
    settings.GIRO_ARMAZENAMENTO = "disco"
    with pytest.raises(ValueError, match="disco"):
        arquivos.provedor()
