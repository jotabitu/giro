"""Campos de dinheiro e percentual (ADR 0009). O nome termina em `_centavos` ou `_pct`."""

from typing import Any

from django.db import models


class CentavosField(models.PositiveBigIntegerField):  # type: ignore[type-arg]
    """Valor monetário que nunca é negativo, em centavos."""


class CentavosComSinalField(models.BigIntegerField):  # type: ignore[type-arg]
    """Só para saldos, diferenças e extrato bancário."""


class PercentualField(models.DecimalField):  # type: ignore[type-arg]
    """Percentual com 2 casas (`8.00`)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("max_digits", 5)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)
