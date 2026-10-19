"""Sanitização do logo da empresa (ADR 0022, S-12; T-153).

`limpar_logo(conteudo)` é função pura: o arquivo gravado é sempre um arquivo novo, montado aqui.
O SVG é lido com `defusedxml` (sem DTD, entidade nem recurso externo), recusado se tiver conteúdo
ativo e serializado de novo só com o que está nas listas fechadas abaixo. O PNG é decodificado e
codificado de novo em RGBA, sem metadados (item 6 e a nota de 13 out 2026).

As listas são iguais às da ADR 0022: mudar uma delas é mudar a decisão (ADR nova ou nota datada,
com a Segurança).
"""

import io
import re
import warnings

# Só monta e serializa: a leitura é sempre a do defusedxml.
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import defusedxml.ElementTree as DefusedET
from defusedxml import DefusedXmlException

TAMANHO_MAXIMO = 2 * 1024 * 1024  # 2 MB, o enviado e o PNG codificado de novo
LADO_MAXIMO = 4096  # PNG: pixels de lado (e área até 4.096 x 4.096)
ELEMENTOS_MAXIMOS = 5000
PROFUNDIDADE_MAXIMA = 32

ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"
BOM = b"\xef\xbb\xbf"

NS_SVG = "http://www.w3.org/2000/svg"
NS_XLINK = "http://www.w3.org/1999/xlink"
NS_XML = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("xlink", NS_XLINK)

MENSAGEM_FORMATO = "Envie o logo em SVG ou PNG."
MENSAGEM_TAMANHO = "O logo passa de 2 MB."
MENSAGEM_LER_SVG = (
    "Não conseguimos ler este SVG. Exporte o logo de novo pelo seu programa de desenho."
)
MENSAGEM_LER_PNG = (
    "Não conseguimos ler este PNG. Exporte o logo de novo pelo seu programa de desenho."
)
MENSAGEM_ATIVO = (
    "O SVG tem conteúdo que não aceitamos, como script ou link externo. "
    "Exporte o logo de novo, só com o desenho."
)
MENSAGEM_SEM_TAMANHO = "O SVG precisa de tamanho definido (viewBox)."
MENSAGEM_SEM_DESENHO = "Não encontramos desenho neste SVG."
MENSAGEM_GRANDE = "O logo é grande demais. Use até 4.096 pixels de lado."

# Item 3: recusa o arquivo inteiro.
ELEMENTOS_PROIBIDOS = frozenset(
    {
        "script",
        "foreignObject",
        "iframe",
        "object",
        "embed",
        "a",
        "image",
        "feImage",
        "animate",
        "animateMotion",
        "animateTransform",
        "set",
        "handler",
        "listener",
    }
)

# Item 4: o que estiver fora sai em silêncio.
ELEMENTOS_ACEITOS = frozenset(
    {
        "svg",
        "g",
        "defs",
        "symbol",
        "use",
        "title",
        "desc",
        "path",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "linearGradient",
        "radialGradient",
        "stop",
        "clipPath",
        "mask",
        "pattern",
        "style",
        "filter",
        "feGaussianBlur",
        "feOffset",
        "feFlood",
        "feComposite",
        "feBlend",
        "feColorMatrix",
        "feMerge",
        "feMergeNode",
    }
)
ATRIBUTOS_ACEITOS = frozenset(
    {
        "id",
        "class",
        "style",
        "viewBox",
        "preserveAspectRatio",
        "width",
        "height",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "fx",
        "fy",
        "fr",
        "d",
        "points",
        "transform",
        "fill",
        "fill-opacity",
        "fill-rule",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-miterlimit",
        "stroke-dasharray",
        "stroke-dashoffset",
        "stroke-opacity",
        "opacity",
        "color",
        "display",
        "visibility",
        "clip-path",
        "clip-rule",
        "clipPathUnits",
        "mask",
        "maskUnits",
        "maskContentUnits",
        "filter",
        "filterUnits",
        "primitiveUnits",
        "offset",
        "stop-color",
        "stop-opacity",
        "gradientUnits",
        "gradientTransform",
        "spreadMethod",
        "patternUnits",
        "patternContentUnits",
        "patternTransform",
        "font-family",
        "font-size",
        "font-weight",
        "font-style",
        "text-anchor",
        "dominant-baseline",
        "letter-spacing",
        "href",  # só `#id` (conferido no item 3)
        "stdDeviation",
        "in",
        "in2",
        "result",
        "dx",
        "dy",
        "mode",
        "operator",
        "k1",
        "k2",
        "k3",
        "k4",
        "flood-color",
        "flood-opacity",
        "version",
    }
)
# `xml:space` e `xlink:href` (só `#id`), fora do namespace vazio.
ATRIBUTOS_COM_NAMESPACE = frozenset({f"{{{NS_XML}}}space", f"{{{NS_XLINK}}}href"})
# Só em `feColorMatrix`.
ATRIBUTOS_DO_FECOLORMATRIX = frozenset({"type", "values"})
DESENHAVEIS = frozenset(
    {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text"}
)

REFERENCIA_INTERNA = re.compile(r"^#[A-Za-z_][\w.:-]*$")
URL_CSS = re.compile(r"url\(([^)]*)\)", re.IGNORECASE)
URL_INTERNA = re.compile(r"""^\s*(['"]?)#[A-Za-z_][\w.:-]*\1\s*$""")
INVISIVEIS = re.compile(r"[\s\x00-\x1f\x7f]+")
NUMERO = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
VIEWBOX = re.compile(rf"^\s*({NUMERO})[\s,]+({NUMERO})[\s,]+({NUMERO})[\s,]+({NUMERO})\s*$")
MEDIDA = re.compile(rf"^\s*({NUMERO})\s*(?:px)?\s*$")


class LogoInvalido(Exception):
    """Logo recusado, com a mensagem do contrato. `suspeito`: vai para o log como `WARNING`
    (conteúdo ativo ou arquivo que não se lê), sempre sem o conteúdo."""

    def __init__(self, mensagem: str, *, suspeito: bool = False) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.suspeito = suspeito


@dataclass(frozen=True)
class LogoLimpo:
    conteudo: bytes
    extensao: str  # "svg" ou "png"
    largura: int
    altura: int


def limpar_logo(conteudo: bytes) -> LogoLimpo:
    """O logo a gravar, montado de novo a partir do enviado. Levanta `LogoInvalido`."""
    if len(conteudo) > TAMANHO_MAXIMO:
        raise LogoInvalido(MENSAGEM_TAMANHO)
    if conteudo.startswith(ASSINATURA_PNG):
        return _limpar_png(conteudo)
    inicio = conteudo.removeprefix(BOM).lstrip()
    if inicio.startswith((b"<?xml", b"<svg")):
        return _limpar_svg(conteudo)
    raise LogoInvalido(MENSAGEM_FORMATO)


# --- SVG (itens 2 a 5) ---


def _local(nome: str) -> str:
    return nome.rsplit("}", 1)[-1]


def _namespace(nome: str) -> str:
    return nome[1:].split("}", 1)[0] if nome.startswith("{") else ""


def _valor_ativo(valor: str) -> bool:
    """Item 3: `javascript:`, `data:` ou `url(` que não seja `url(#id)`."""
    compacto = INVISIVEIS.sub("", valor).lower()
    if "javascript:" in compacto or "data:" in compacto:
        return True
    if "url(" not in compacto:
        return False
    urls = URL_CSS.findall(valor)
    return len(urls) != compacto.count("url(") or not all(URL_INTERNA.match(u) for u in urls)


def _recusar_ativo(raiz: Any) -> None:
    contados = 0
    pilha: list[tuple[Any, int]] = [(raiz, 1)]
    while pilha:
        elemento, nivel = pilha.pop()
        contados += 1
        if contados > ELEMENTOS_MAXIMOS or nivel > PROFUNDIDADE_MAXIMA:
            raise LogoInvalido(MENSAGEM_GRANDE)
        if _local(elemento.tag) in ELEMENTOS_PROIBIDOS:
            raise LogoInvalido(MENSAGEM_ATIVO, suspeito=True)
        for nome, valor in elemento.attrib.items():
            local = _local(nome)
            if local.lower().startswith("on"):
                raise LogoInvalido(MENSAGEM_ATIVO, suspeito=True)
            if local == "href" and not REFERENCIA_INTERNA.match(valor.strip()):
                raise LogoInvalido(MENSAGEM_ATIVO, suspeito=True)
            if _valor_ativo(valor):
                raise LogoInvalido(MENSAGEM_ATIVO, suspeito=True)
        pilha.extend((filho, nivel + 1) for filho in elemento)


def _css_aceito(css: str) -> bool:
    """Item 4: o bloco inteiro sai com `@`, `\\`, `expression`, `javascript:` ou `url(` externo."""
    compacto = INVISIVEIS.sub("", css).lower()
    if "@" in css or "\\" in css or "expression" in compacto:
        return False
    return not _valor_ativo(css)


def _atributos(elemento: Any) -> dict[str, str]:
    local = _local(elemento.tag)
    aceitos: dict[str, str] = {}
    for nome, valor in elemento.attrib.items():
        if nome in ATRIBUTOS_COM_NAMESPACE:
            aceitos[nome] = valor
        elif nome.startswith("{"):
            continue
        elif nome in ATRIBUTOS_ACEITOS or (
            local == "feColorMatrix" and nome in ATRIBUTOS_DO_FECOLORMATRIX
        ):
            if nome == "style" and not _css_aceito(valor):
                continue
            aceitos[nome] = valor
    return aceitos


def _copiar(elemento: Any) -> Any | None:
    """O elemento de novo, só com o que está nas listas; `None` se ele sai inteiro."""
    local = _local(elemento.tag)
    if _namespace(elemento.tag) != NS_SVG or local not in ELEMENTOS_ACEITOS:
        return None
    if local == "style":
        tipo = elemento.get("type", "text/css").strip().lower()
        if tipo != "text/css" or not _css_aceito(elemento.text or ""):
            return None
    atributos = _atributos(elemento)
    if local == "svg":  # tags sem prefixo, no namespace SVG padrão
        atributos = {"xmlns": NS_SVG, **atributos}
    novo = ET.Element(local, atributos)
    novo.text = elemento.text
    for filho in elemento:
        copia = _copiar(filho)
        if copia is not None:
            copia.tail = filho.tail
            novo.append(copia)
    return novo


def _tamanho(raiz: Any) -> tuple[float, float, str]:
    """Item 5: pelo `viewBox`; sem ele, `width` e `height` numéricos (sem unidade ou em px)."""
    caixa = VIEWBOX.match(raiz.get("viewBox", ""))
    if caixa:
        largura, altura = float(caixa.group(3)), float(caixa.group(4))
        if largura > 0 and altura > 0:
            return largura, altura, " ".join(caixa.groups())
        raise LogoInvalido(MENSAGEM_SEM_TAMANHO)
    largura_m = MEDIDA.match(raiz.get("width", ""))
    altura_m = MEDIDA.match(raiz.get("height", ""))
    if largura_m and altura_m:
        largura, altura = float(largura_m.group(1)), float(altura_m.group(1))
        if largura > 0 and altura > 0:
            return largura, altura, f"0 0 {largura_m.group(1)} {altura_m.group(1)}"
    raise LogoInvalido(MENSAGEM_SEM_TAMANHO)


def _tem_desenho(raiz: Any) -> bool:
    for elemento in raiz.iter():
        local = _local(elemento.tag)
        if local not in DESENHAVEIS:
            continue
        if local == "path" and not (elemento.get("d") or "").strip():
            continue
        if local in ("polyline", "polygon") and not (elemento.get("points") or "").strip():
            continue
        if local == "text" and not "".join(elemento.itertext()).strip():
            continue
        return True
    return False


def _numero(valor: float) -> str:
    return f"{valor:g}"


def _limpar_svg(conteudo: bytes) -> LogoLimpo:
    try:
        raiz = DefusedET.fromstring(
            conteudo, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except (DefusedXmlException, ET.ParseError, ValueError) as erro:
        raise LogoInvalido(MENSAGEM_LER_SVG, suspeito=True) from erro
    if raiz.tag != f"{{{NS_SVG}}}svg":
        raise LogoInvalido(MENSAGEM_LER_SVG, suspeito=True)
    _recusar_ativo(raiz)
    largura, altura, caixa = _tamanho(raiz)
    limpa = _copiar(raiz)
    if limpa is None or not _tem_desenho(limpa):
        raise LogoInvalido(MENSAGEM_SEM_DESENHO)
    limpa.set("viewBox", caixa)
    limpa.set("width", _numero(largura))
    limpa.set("height", _numero(altura))
    texto = ET.tostring(limpa, encoding="unicode", xml_declaration=False)
    return LogoLimpo(
        texto.encode("utf-8"),
        "svg",
        max(1, round(largura)),
        max(1, round(altura)),
    )


# --- PNG (item 6 e a nota de 13 out 2026) ---


def _conferir_pixels(tamanho: tuple[int, int]) -> None:
    largura, altura = tamanho
    if largura < 1 or altura < 1:
        raise LogoInvalido(MENSAGEM_LER_PNG, suspeito=True)
    if largura > LADO_MAXIMO or altura > LADO_MAXIMO or largura * altura > LADO_MAXIMO**2:
        raise LogoInvalido(MENSAGEM_GRANDE)


def _limpar_png(conteudo: bytes) -> LogoLimpo:
    from PIL import Image, UnidentifiedImageError

    erros_de_leitura = (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        EOFError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    )
    # Sem mexer em `Image.MAX_IMAGE_PIXELS` (global; as fotos da vistoria têm 48 MP): o tamanho
    # é conferido no cabeçalho, antes de decodificar, e o aviso de bomba vira erro só aqui.
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(io.BytesIO(conteudo)) as imagem:
                if imagem.format != "PNG":
                    raise LogoInvalido(MENSAGEM_LER_PNG, suspeito=True)
                _conferir_pixels(imagem.size)
                imagem.verify()
            with Image.open(io.BytesIO(conteudo)) as imagem:
                if imagem.format != "PNG":
                    raise LogoInvalido(MENSAGEM_LER_PNG, suspeito=True)
                _conferir_pixels(imagem.size)
                imagem.seek(0)  # PNG animado: só o primeiro quadro
                imagem.load()
                pixels = imagem.convert("RGBA")
        except erros_de_leitura as erro:
            raise LogoInvalido(MENSAGEM_LER_PNG, suspeito=True) from erro
    # Imagem nova, sem `info`: nada de `pnginfo`, `exif`, `icc_profile` nem `save_all`.
    limpa = Image.new("RGBA", pixels.size)
    limpa.paste(pixels)
    saida = io.BytesIO()
    limpa.save(saida, format="PNG", optimize=True)
    gravado = saida.getvalue()
    if len(gravado) > TAMANHO_MAXIMO:
        raise LogoInvalido(MENSAGEM_TAMANHO)
    return LogoLimpo(gravado, "png", limpa.width, limpa.height)
