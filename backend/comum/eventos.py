"""Despachante de eventos de domínio entre apps (ADR 0011, item 3).

Assinantes rodam na mesma transação de quem publica, em ordem de registro; se um falha, tudo
volta. Efeito externo (WhatsApp, e-mail, parceiro de pagamento, PDF) nunca roda no assinante:
ele agenda uma tarefa Celery com `transaction.on_commit`.
"""

import re
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from django.db import transaction

Assinante = Callable[..., None]

_NOME_EVENTO = re.compile(r"^[a-z_]+\.[a-z_]+$")
_assinantes: dict[str, list[Assinante]] = defaultdict(list)


def _validar_nome(evento: str) -> None:
    if not _NOME_EVENTO.match(evento):
        raise ValueError(f"Nome de evento fora do padrão <app>.<fato_no_passado>: {evento!r}")


def assinar(evento: str, assinante: Assinante) -> None:
    """Chame no `AppConfig.ready()` do app assinante."""
    _validar_nome(evento)
    if assinante not in _assinantes[evento]:
        _assinantes[evento].append(assinante)


def assinante(evento: str) -> Callable[[Assinante], Assinante]:
    """Decorador equivalente a `assinar` para funções em `<app>/eventos.py`."""

    def registrar(funcao: Assinante) -> Assinante:
        assinar(evento, funcao)
        return funcao

    return registrar


def publicar(evento: str, **dados: Any) -> None:
    _validar_nome(evento)
    with transaction.atomic():
        for funcao in list(_assinantes.get(evento, ())):
            funcao(**dados)


def remover_assinante(evento: str, funcao: Assinante) -> None:
    """Para testes."""
    if funcao in _assinantes.get(evento, ()):
        _assinantes[evento].remove(funcao)
