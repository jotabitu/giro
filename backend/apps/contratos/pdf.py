"""PDF do contrato com a marca da locadora (WeasyPrint; S-09).

O `url_fetcher` só entrega o logo da própria empresa, por um endereço interno fixo
(`giro-logo:empresa`), lido no schema atual. Qualquer outra URL (`http`, `https`, `file`,
`data`, IP interno) é recusada antes de abrir conexão. O texto do modelo já chega
sanitizado, sem `img`, `style` nem `link`; o CSS é só o daqui.
"""

import hashlib
import html
from dataclasses import dataclass
from typing import Any

URL_DO_LOGO = "giro-logo:empresa"

_CSS = """
@page { size: A4; margin: 22mm 18mm 20mm 18mm;
  @bottom-center { content: "Página " counter(page) " de " counter(pages);
    font-size: 8pt; color: #666; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 10pt; line-height: 1.45;
  color: #1f1f1f; }
header { display: flex; align-items: center; border-bottom: 2px solid %(cor)s;
  padding-bottom: 6pt; margin-bottom: 12pt; }
header img { height: 28pt; margin-right: 10pt; }
header .marca { font-size: 13pt; font-weight: bold; color: %(cor)s; }
h1 { font-size: 14pt; } h2 { font-size: 11pt; margin-top: 12pt; } h3 { font-size: 10pt; }
table { border-collapse: collapse; width: 100%%; margin: 6pt 0; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; text-align: left; }
.registro { page-break-before: always; }
.registro td:first-child { width: 35%%; font-weight: bold; }
"""


class UrlRecusada(ValueError):
    """O PDF tentou buscar uma URL que não é o logo da empresa (S-09)."""


@dataclass(frozen=True)
class Marca:
    nome: str
    cor: str = "#1f1f1f"
    logo_svg: bytes | None = None


# Imagem já lida do armazenamento privado por quem monta o PDF (ex.: as fotos do recibo da
# devolução): endereço interno `giro-imagem:<id>` → (conteúdo, tipo).
Imagens = dict[str, tuple[bytes, str]]


def buscador(marca: Marca, imagens: Imagens | None = None) -> Any:
    """O `url_fetcher` do WeasyPrint: só o logo da empresa, se ela tiver um, e as imagens
    entregues por quem monta o PDF, pelos endereços internos delas.

    A WeasyPrint 70 pede uma instância de `URLFetcher` (lê `_fail_on_errors` nela, T-333). O
    `fetch` daqui nunca chama o da classe-mãe, que abriria a conexão: o que não é endereço
    interno é recusado antes, e a recusa vira aviso, sem parar o PDF (`fail_on_errors=False`).
    """
    from weasyprint.urls import (  # type: ignore[import-untyped]
        URLFetcher,
        URLFetcherResponse,
    )

    class Buscador(URLFetcher):
        def fetch(self, url: str, headers: Any = None) -> Any:
            if imagens and url in imagens:
                conteudo, tipo = imagens[url]
                return URLFetcherResponse(url, body=conteudo, headers={"Content-Type": tipo})
            if url != URL_DO_LOGO or marca.logo_svg is None:
                raise UrlRecusada(f"URL recusada no PDF do contrato: {url[:80]}")
            return URLFetcherResponse(
                url, body=marca.logo_svg, headers={"Content-Type": "image/svg+xml"}
            )

    return Buscador(fail_on_errors=False)


def documento(corpo: str, marca: Marca, registro: list[tuple[str, str]] | None = None) -> str:
    """O HTML completo: cabeçalho com a marca, o corpo já montado e, se houver, a página de
    registro da assinatura."""
    logo = f'<img src="{URL_DO_LOGO}" alt="">' if marca.logo_svg else ""
    linhas = "".join(
        f"<tr><td>{html.escape(rotulo)}</td><td>{html.escape(valor)}</td></tr>"
        for rotulo, valor in registro or []
    )
    pagina_de_registro = (
        f'<section class="registro"><h2>Registro da assinatura eletrônica</h2>'
        f"<table>{linhas}</table></section>"
        if registro
        else ""
    )
    cor = marca.cor if _cor_valida(marca.cor) else "#1f1f1f"
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        f"<style>{_CSS % {'cor': cor}}</style></head><body>"
        f'<header>{logo}<span class="marca">{html.escape(marca.nome)}</span></header>'
        f"<main>{corpo}</main>{pagina_de_registro}</body></html>"
    )


def _cor_valida(cor: str) -> bool:
    return len(cor) == 7 and cor[0] == "#" and all(c in "0123456789abcdefABCDEF" for c in cor[1:])


def gerar(
    corpo: str,
    marca: Marca,
    registro: list[tuple[str, str]] | None = None,
    imagens: Imagens | None = None,
) -> bytes:
    from weasyprint import HTML  # type: ignore[import-untyped]

    pdf = HTML(
        string=documento(corpo, marca, registro), url_fetcher=buscador(marca, imagens)
    ).write_pdf()
    if not isinstance(pdf, bytes):
        raise TypeError("O WeasyPrint não devolveu o PDF.")
    return pdf


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()
