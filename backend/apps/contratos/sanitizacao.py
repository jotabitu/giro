"""HTML do modelo de contrato com lista branca (S-09, `docs/api/contratos.md`).

O texto é limpo no servidor ao salvar. Ficam só as tags da lista, sem atributos, menos
`colspan` e `rowspan` com número. `script` e `style` saem com o conteúdo; o resto (`img`, `a`,
`iframe`, `link`, atributos `style` e `on*`) sai e deixa só o texto. O logo da locadora entra
pelo cabeçalho fixo do PDF, nunca pelo texto.
"""

import nh3

TAGS = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "strong",
        "em",
        "u",
        "ol",
        "ul",
        "li",
        "br",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
    }
)
_ATRIBUTOS = {"td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}
_SAEM_COM_O_CONTEUDO = {"script", "style", "iframe", "object", "embed", "template"}
TAMANHO_MAXIMO = 200_000  # caracteres; o PDF tem tempo e memória limitados


def _so_numero(tag: str, atributo: str, valor: str) -> str | None:
    return valor if valor.isdigit() and 0 < int(valor) <= 50 else None


def limpar(texto: str) -> str:
    return nh3.clean(
        texto,
        tags=set(TAGS),
        clean_content_tags=_SAEM_COM_O_CONTEUDO,
        attributes=_ATRIBUTOS,
        attribute_filter=_so_numero,
        url_schemes=set(),
        link_rel=None,
        strip_comments=True,
    )
