"""Registro dos itens de exportação montados por outros apps (AUD-07, docs/api/auditoria.md).

`auditoria` (nível 2 da ADR 0011) não importa os apps de cima. Quem tem os dados registra o item
no `AppConfig.ready()` (o de baixo registra, o de cima chama, como na ADR 0015): `financeiro`
registra `despesas` (T-178). A auditoria em CSV continua em `services`.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import Exportacao


@dataclass(frozen=True)
class ItemRegistrado:
    rotulo: str
    colunas: tuple[str, ...]
    # Confere o corpo do pedido e devolve os `parametros` da exportação (400 se não vale).
    validar: Callable[[dict[str, Any]], dict[str, Any]]
    linhas: Callable[[Exportacao], list[list[Any]]]
    # O texto de "Exportações recentes": "Despesas · Filial Centro · 01/10/2026 a 31/10/2026".
    conteudo: Callable[[Exportacao], str]


_ITENS: dict[str, ItemRegistrado] = {}


def registrar_item(
    item: str,
    *,
    rotulo: str,
    colunas: tuple[str, ...],
    validar: Callable[[dict[str, Any]], dict[str, Any]],
    linhas: Callable[[Exportacao], list[list[Any]]],
    conteudo: Callable[[Exportacao], str],
) -> None:
    _ITENS[item] = ItemRegistrado(rotulo, colunas, validar, linhas, conteudo)


def item_registrado(item: str) -> ItemRegistrado | None:
    return _ITENS.get(item)
