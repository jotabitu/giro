"""S-12 · Sanitização do logo (ADR 0022; T-153). Um teste por vetor, e os que passam.

`limpar_logo` é função pura: nada aqui toca o banco.
"""

import io
import logging
import struct
import zlib

import pytest
from PIL import Image, ImageFile, PngImagePlugin

from apps.empresas import logo
from apps.empresas.logo import LogoInvalido, limpar_logo

NS = 'xmlns="http://www.w3.org/2000/svg"'
XLINK = 'xmlns:xlink="http://www.w3.org/1999/xlink"'


def _svg(corpo: str, raiz: str = 'viewBox="0 0 120 36"', extra: str = "") -> bytes:
    return f"<svg {NS} {extra} {raiz}>{corpo}</svg>".encode()


def _recusado(conteudo: bytes) -> LogoInvalido:
    with pytest.raises(LogoInvalido) as erro:
        limpar_logo(conteudo)
    return erro.value


def _png(imagem: Image.Image, **opcoes) -> bytes:
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", **opcoes)
    return saida.getvalue()


# --- SVG: conteúdo ativo é recusado (item 3) ---

ATIVOS = {
    "script": _svg('<script>alert(1)</script><rect width="1" height="1"/>'),
    "onload": _svg('<rect width="1" height="1"/>', extra='onload="alert(1)"'),
    "ONLOAD": _svg('<rect width="1" height="1" ONLOAD="alert(1)"/>'),
    "foreignObject": _svg(
        '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">oi</div></foreignObject>'
        '<rect width="1" height="1"/>'
    ),
    "href_javascript": _svg('<use href="javascript:alert(1)"/><rect width="1" height="1"/>'),
    "xlink_externo": _svg(
        '<use xlink:href="https://mal.example/x.svg#a"/><rect width="1" height="1"/>', extra=XLINK
    ),
    "image_data": _svg('<image href="data:image/png;base64,iVBORw0KGgo="/>'),
    "animate_href": _svg(
        '<rect id="r" width="1" height="1"><animate attributeName="href" '
        'values="javascript:alert(1)"/></rect>'
    ),
    "set_href": _svg(
        '<rect width="1" height="1"><set attributeName="href" to="javascript:alert(1)"/></rect>'
    ),
    "url_externa_no_fill": _svg('<rect width="1" height="1" fill="url(http://mal.example/a)"/>'),
    "url_externa_no_style": _svg(
        '<rect width="1" height="1" style="fill: url(https://mal.example/a)"/>'
    ),
    "javascript_com_espacos": _svg('<use href="java&#9;script:alert(1)"/>'),
}


@pytest.mark.parametrize("vetor", ATIVOS)
def test_s_12_svg_com_conteudo_ativo_recusado(vetor):
    erro = _recusado(ATIVOS[vetor])
    assert erro.mensagem == logo.MENSAGEM_ATIVO
    assert erro.suspeito


def test_s_12_svg_bilhao_de_risadas_recusado():
    bomba = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "ha"><!ENTITY b "&a;&a;&a;&a;">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><text>&b;</text></svg>'
    )
    erro = _recusado(bomba)
    assert erro.mensagem == logo.MENSAGEM_LER_SVG
    assert erro.suspeito


def test_s_12_svg_entidade_externa_recusada():
    externa = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><text>&x;</text></svg>'
    )
    assert _recusado(externa).mensagem == logo.MENSAGEM_LER_SVG


def test_s_12_svg_quebrado_ou_raiz_errada():
    assert _recusado(b"<svg><rect></svg>").mensagem == logo.MENSAGEM_LER_SVG
    assert _recusado(b"<svg>sem namespace</svg>").mensagem == logo.MENSAGEM_LER_SVG


def test_s_12_svg_style_com_import_sai_em_silencio():
    limpo = limpar_logo(
        _svg(
            "<style>@import url(https://mal.example/a.css); rect { fill: red }</style>"
            '<style>.a { fill: #000 }</style><rect class="a" width="1" height="1" '
            'style="fill: red; behavior: x\\0"/>'
        )
    )
    texto = limpo.conteudo.decode()
    assert "@import" not in texto and "mal.example" not in texto
    assert ".a { fill: #000 }" in texto
    assert "style=" not in texto  # o atributo com `\` sai inteiro


def test_s_12_svg_do_inkscape_passa_sem_metadados():
    inkscape = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n<!-- Criado com Inkscape -->\n'
        b'<svg xmlns="http://www.w3.org/2000/svg" '
        b'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        b'xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" '
        b'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        b'viewBox="0 0 120.4 36" inkscape:version="1.3" sodipodi:docname="logo.svg">'
        b'<sodipodi:namedview id="nv" pagecolor="#fff"/>'
        b"<metadata><rdf:RDF><rdf:Description>autor</rdf:Description></rdf:RDF></metadata>"
        b'<g inkscape:label="Camada 1" inkscape:groupmode="layer" data-x="1">'
        b'<path d="M0 0h10v10z" fill="#111114" inkscape:connector-curvature="0"/></g></svg>'
    )
    limpo = limpar_logo(inkscape)
    texto = limpo.conteudo.decode()
    assert limpo.extensao == "svg"
    assert (limpo.largura, limpo.altura) == (120, 36)
    for fora in ("inkscape", "sodipodi", "metadata", "rdf", "Criado", "data-x", "<?xml"):
        assert fora not in texto
    assert texto.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert 'viewBox="0 0 120.4 36"' in texto
    assert 'width="120.4"' in texto and 'height="36"' in texto
    assert '<path d="M0 0h10v10z" fill="#111114"' in texto


def test_s_12_svg_sem_viewbox_com_largura_e_altura():
    limpo = limpar_logo(_svg('<circle cx="5" cy="5" r="5"/>', raiz='width="80px" height="24"'))
    assert (limpo.largura, limpo.altura) == (80, 24)
    assert 'viewBox="0 0 80 24"' in limpo.conteudo.decode()


def test_s_12_svg_gradiente_e_use_com_referencia_interna_passam():
    limpo = limpar_logo(
        _svg(
            '<defs><linearGradient id="g"><stop offset="0" stop-color="#C8F04A"/>'
            '</linearGradient><rect id="r" width="5" height="5"/></defs>'
            '<rect width="10" height="10" fill="url(#g)"/><use href="#r"/>'
            '<use xlink:href="#r" x="5"/>',
            extra=XLINK,
        )
    )
    texto = limpo.conteudo.decode()
    assert 'fill="url(#g)"' in texto
    assert '<use href="#r"' in texto
    assert 'xlink:href="#r"' in texto


def test_s_12_svg_sem_tamanho_sem_desenho_e_grande_demais():
    assert _recusado(_svg('<rect width="1" height="1"/>', raiz="")).mensagem == (
        logo.MENSAGEM_SEM_TAMANHO
    )
    assert _recusado(_svg("<title>Logo</title><g/>")).mensagem == logo.MENSAGEM_SEM_DESENHO
    muitos = "<g/>" * logo.ELEMENTOS_MAXIMOS
    assert _recusado(_svg(muitos)).mensagem == logo.MENSAGEM_GRANDE
    fundo = "<g>" * logo.PROFUNDIDADE_MAXIMA + "</g>" * logo.PROFUNDIDADE_MAXIMA
    assert _recusado(_svg(fundo)).mensagem == logo.MENSAGEM_GRANDE


def test_s_12_formato_e_tamanho_do_enviado():
    assert _recusado(b"GIF89a....").mensagem == logo.MENSAGEM_FORMATO
    assert _recusado(b"\xff\xd8\xff\xe0 jpeg").mensagem == logo.MENSAGEM_FORMATO
    grande = _svg('<rect width="1" height="1"/>' + " " * logo.TAMANHO_MAXIMO)
    assert _recusado(grande).mensagem == logo.MENSAGEM_TAMANHO
    # BOM e espaços antes do `<svg` valem.
    assert limpar_logo(b"\xef\xbb\xbf \n" + _svg('<rect width="1" height="1"/>')).extensao == (
        "svg"
    )


# --- PNG (item 6 e a nota de 13 out 2026) ---


def test_s_12_png_passa_sem_metadados():
    imagem = Image.new("RGBA", (40, 20), (200, 240, 74, 128))
    texto = PngImagePlugin.PngInfo()
    texto.add_text("Author", "segredo-do-autor")
    texto.add_itxt("Comment", "outro-segredo")
    exif = Image.Exif()
    exif[0x010E] = "descricao-escondida"
    enviado = _png(imagem, pnginfo=texto, exif=exif, dpi=(300, 300))
    assert b"segredo-do-autor" in enviado and b"eXIf" in enviado

    limpo = limpar_logo(enviado)
    assert limpo.extensao == "png"
    assert (limpo.largura, limpo.altura) == (40, 20)
    for bloco in (b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"iCCP", b"tIME", b"pHYs"):
        assert bloco not in limpo.conteudo
    assert b"segredo" not in limpo.conteudo and b"escondida" not in limpo.conteudo
    with Image.open(io.BytesIO(limpo.conteudo)) as gravado:
        assert gravado.mode == "RGBA"
        assert gravado.getpixel((0, 0)) == (200, 240, 74, 128)


def test_s_12_png_em_paleta_mantem_cores_e_transparencia():
    imagem = Image.new("P", (4, 2))
    imagem.putpalette([0, 0, 0, 200, 240, 74, 47, 111, 237] + [0] * (256 * 3 - 9))
    imagem.putdata([0, 1, 2, 1, 2, 0, 1, 1])
    enviado = _png(imagem, transparency=0)  # índice 0 transparente (tRNS)
    with Image.open(io.BytesIO(enviado)) as original:
        esperado = list(original.convert("RGBA").getdata())

    limpo = limpar_logo(enviado)
    with Image.open(io.BytesIO(limpo.conteudo)) as gravado:
        assert gravado.mode == "RGBA"
        assert list(gravado.getdata()) == esperado
    assert esperado[0] == (0, 0, 0, 0)
    assert esperado[1] == (200, 240, 74, 255)


def test_s_12_png_acima_de_4096_recusado_sem_decodificar(monkeypatch):
    enviado = _png(Image.new("L", (logo.LADO_MAXIMO + 1, 1)))

    def nao_decodifica(*_args, **_kwargs):
        raise AssertionError("decodificou os pixels")

    monkeypatch.setattr(ImageFile.ImageFile, "load", nao_decodifica)
    erro = _recusado(enviado)
    assert erro.mensagem == logo.MENSAGEM_GRANDE
    assert Image.MAX_IMAGE_PIXELS != logo.LADO_MAXIMO**2  # o limite global não muda


def test_s_12_png_assinatura_forjada():
    gif = io.BytesIO()
    Image.new("RGB", (2, 2)).save(gif, format="GIF")
    erro = _recusado(logo.ASSINATURA_PNG + gif.getvalue())
    assert erro.mensagem == logo.MENSAGEM_LER_PNG
    assert erro.suspeito


def test_s_12_png_truncado():
    enviado = _png(Image.effect_noise((64, 64), 50).convert("RGB"))
    erro = _recusado(enviado[: len(enviado) // 2])
    assert erro.mensagem == logo.MENSAGEM_LER_PNG


def _bloco(tipo: bytes, dados: bytes) -> bytes:
    return (
        struct.pack(">I", len(dados))
        + tipo
        + dados
        + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    )


def test_s_12_png_poliglota():
    """PNG que também é HTML: script num bloco privado e depois do IEND. Só os pixels ficam."""
    valido = _png(Image.new("RGBA", (3, 3), (255, 0, 0, 255)))
    fim = valido.rindex(b"IEND") - 4
    script = b"<html><script>alert(document.cookie)</script></html>"
    poliglota = valido[:fim] + _bloco(b"prVt", script) + valido[fim:] + script
    limpo = limpar_logo(poliglota)
    assert b"<script" not in limpo.conteudo and b"prVt" not in limpo.conteudo
    assert limpo.conteudo.endswith(b"IEND\xaeB`\x82")


def test_s_12_png_animado_grava_primeiro_quadro():
    quadros = [Image.new("RGBA", (8, 8), cor) for cor in ((255, 0, 0, 255), (0, 0, 255, 255))]
    enviado = _png(quadros[0], save_all=True, append_images=quadros[1:], duration=100, loop=0)
    assert b"acTL" in enviado

    limpo = limpar_logo(enviado)
    assert b"acTL" not in limpo.conteudo and b"fcTL" not in limpo.conteudo
    with Image.open(io.BytesIO(limpo.conteudo)) as gravado:
        assert getattr(gravado, "n_frames", 1) == 1
        assert gravado.getpixel((0, 0)) == (255, 0, 0, 255)


def test_s_12_png_recusa_nao_vai_para_o_log_com_conteudo(caplog):
    # A função é pura: o `WARNING` (schema e usuário, sem conteúdo) é do serviço.
    with caplog.at_level(logging.DEBUG):
        _recusado(logo.ASSINATURA_PNG + b"<script>segredo</script>")
    assert "segredo" not in caplog.text
