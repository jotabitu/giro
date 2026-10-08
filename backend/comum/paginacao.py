"""Envelope de lista de docs/api/README.md: `resultados`, `proximo`, `anterior` (cursor).

Contadores de abas (`contagens`) e indicadores da tela vão no mesmo corpo, como extras
(ponto 6 da T-045): `self.paginator.get_paginated_response(dados, extras={"contagens": ...})`.
"""

from typing import Any

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

CHAVES_DO_ENVELOPE = frozenset({"resultados", "proximo", "anterior"})


def _conferir_extras(extras: dict[str, Any]) -> None:
    repetidas = CHAVES_DO_ENVELOPE & extras.keys()
    if repetidas:
        raise ValueError(f"Extras não podem trocar o envelope: {sorted(repetidas)}")


def envelope_sem_paginas(resultados: Any, extras: dict[str, Any] | None = None) -> Response:
    """O mesmo envelope para listas curtas, sem paginação (ex.: planos)."""
    extras = extras or {}
    _conferir_extras(extras)
    return Response({**extras, "resultados": resultados, "proximo": None, "anterior": None})


class PaginacaoPorCursor(CursorPagination):
    page_size = 25
    page_size_query_param = "tamanho"
    max_page_size = 100
    cursor_query_param = "cursor"
    ordering = "-id"

    def get_paginated_response(self, data: Any, extras: dict[str, Any] | None = None) -> Response:
        extras = extras or {}
        _conferir_extras(extras)
        return Response(
            {
                **extras,
                "resultados": data,
                "proximo": self.get_next_link(),
                "anterior": self.get_previous_link(),
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["resultados", "proximo", "anterior"],
            "properties": {
                "resultados": schema,
                "proximo": {"type": "string", "nullable": True, "format": "uri"},
                "anterior": {"type": "string", "nullable": True, "format": "uri"},
            },
        }
