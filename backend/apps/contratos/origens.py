"""Valores dos marcadores por origem, registrados pelo app de cima (ADR 0011, como a 0015).

`locacoes` registra no `ready()` a função que monta os valores de uma locação. A prévia do
modelo com dados reais (`POST /api/contratos/modelos/{id}/previa/`) usa o registro sem
importar `locacoes`.
"""

from collections.abc import Callable

Montador = Callable[[int], dict[str, str] | None]

_montadores: dict[str, Montador] = {}


def registrar(origem_tipo: str, montar: Montador) -> None:
    _montadores[origem_tipo] = montar


def valores(origem_tipo: str, origem_id: int) -> dict[str, str] | None:
    """Os valores da origem, ou `None` se ela não existe (ou não há quem monte)."""
    montar = _montadores.get(origem_tipo)
    return montar(origem_id) if montar else None
