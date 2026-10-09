"""Momentos da API em UTC com `Z`, sem fração de segundo, por um ponto só (ADR 0020).

Com `DATETIME_FORMAT = None` no DRF, o `DateTimeField` devolve o `datetime` cru e quem formata
é o encoder daqui, também para valores soltos na resposta (`detalhes.tentar_de_novo_em`).
Quem usar `serializer.data` fora de uma `Response` passa o resultado por `EncoderDoGiro`.
"""

from datetime import UTC, datetime
from typing import Any

from django.utils import timezone
from rest_framework import renderers
from rest_framework.utils import encoders


class EncoderDoGiro(encoders.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            if timezone.is_naive(obj):
                raise TypeError("Momento sem fuso na resposta da API (ADR 0020)")
            return obj.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return super().default(obj)


class JSONRenderer(renderers.JSONRenderer):
    encoder_class = EncoderDoGiro
