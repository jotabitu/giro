"""Envelope de lista de docs/api/README.md: `resultados`, `proximo`, `anterior` (cursor)."""

from typing import Any

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class PaginacaoPorCursor(CursorPagination):
    page_size = 25
    page_size_query_param = "tamanho"
    max_page_size = 100
    cursor_query_param = "cursor"
    ordering = "-id"

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
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
