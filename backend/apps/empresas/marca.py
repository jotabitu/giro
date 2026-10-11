"""Cores e iniciais da marca, calculadas na leitura (ADR 0004, `docs/api/empresas.md`, T-129).

Funções puras, sem dependência nova. A fórmula das cores suaves é a do design-system
(`giro-produto/cores-da-marca.md`, 10 out 2026): OKLCH com a matriz de Björn Ottosson, mantendo
o matiz da marca, L 0,96 no tema claro e 0,31 no escuro, croma 0,31 x o da marca, depois clamp
de cada canal em [0, 1] e `round()`. Para a cor padrão valem os valores fixos do
`wl-theme.css` (#EEF9CC e #2B3510).
"""

import math
import re
import unicodedata

COR_PADRAO = "#C8F04A"
SUAVE_PADRAO = "#EEF9CC"  # --brand-soft do wl-theme.css (a regra daria #EBF9CD)
SUAVE_ESCURO_PADRAO = "#2B3510"  # --brand-soft escuro do wl-theme.css (a regra dá o mesmo)
INK = "#111114"
BRANCO = "#FFFFFF"
L_SUAVE = 0.96
L_SUAVE_ESCURO = 0.31
FATOR_DE_CROMA = 0.31
FORMATO = re.compile(r"^#[0-9A-F]{6}$")
SEM_INICIAL = frozenset({"de", "da", "do", "das", "dos", "e"})

Rgb = tuple[float, float, float]


def normalizar(cor: str | None) -> str:
    """`#rrggbb` em maiúsculas; vazio, a cor padrão do design system."""
    if not cor:
        return COR_PADRAO
    cor = cor.strip().upper()
    if not FORMATO.match(cor):
        raise ValueError(f"Cor fora do formato #RRGGBB: {cor}")
    return cor


def _canais(cor: str) -> Rgb:
    return (int(cor[1:3], 16) / 255, int(cor[3:5], 16) / 255, int(cor[5:7], 16) / 255)


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _codificar(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * math.copysign(abs(c) ** (1 / 2.4), c) - 0.055


def _hex(rgb: Rgb) -> str:
    return "#" + "".join(f"{round(min(1.0, max(0.0, c)) * 255):02X}" for c in rgb)


# --- Contraste (WCAG) ---


def luminancia(cor: str) -> float:
    r, g, b = (_linear(c) for c in _canais(cor))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(uma: str, outra: str) -> float:
    claro, escuro = sorted((luminancia(uma), luminancia(outra)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def cor_sobre(cor: str) -> str:
    """Texto sobre a marca: `#111114` ou `#FFFFFF`, o de maior contraste (nunca abaixo de
    4,69:1)."""
    return INK if contraste(cor, INK) >= contraste(cor, BRANCO) else BRANCO


# --- OKLCH (Ottosson) ---


def oklch(cor: str) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in _canais(cor))
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    luz = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return luz, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def de_oklch(luz: float, croma: float, matiz: float) -> str:
    a = croma * math.cos(math.radians(matiz))
    b = croma * math.sin(math.radians(matiz))
    l_ = (luz + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (luz - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (luz - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    r, g, bb = (_codificar(c) for c in linear)
    return _hex((r, g, bb))


def _suave(cor: str, luz: float) -> str:
    _, croma, matiz = oklch(cor)
    return de_oklch(luz, FATOR_DE_CROMA * croma, matiz)


def cor_suave(cor: str) -> str:
    """Fundo suave no tema claro (`--brand-soft`)."""
    return SUAVE_PADRAO if cor == COR_PADRAO else _suave(cor, L_SUAVE)


def cor_suave_escuro(cor: str) -> str:
    """Fundo suave no tema escuro."""
    return SUAVE_ESCURO_PADRAO if cor == COR_PADRAO else _suave(cor, L_SUAVE_ESCURO)


def cores(cor: str | None) -> dict[str, str]:
    cor = normalizar(cor)
    return {
        "cor": cor,
        "cor_sobre": cor_sobre(cor),
        "cor_suave": cor_suave(cor),
        "cor_suave_escuro": cor_suave_escuro(cor),
    }


# --- Iniciais ---


def iniciais(nome: str) -> str:
    """As duas primeiras iniciais, sem "de", "da", "do", "das", "dos" e "e" ("Moto Rápida" →
    "MR"); nome de uma palavra só → as duas primeiras letras."""
    palavras = [p for p in re.findall(r"\w+", nome) if p.lower() not in SEM_INICIAL]
    if not palavras:
        return ""
    texto = palavras[0][:2] if len(palavras) == 1 else palavras[0][0] + palavras[1][0]
    return unicodedata.normalize("NFC", texto.upper())
