"""Quem fez cada coisa no histórico do seed (AUD-01): o ator do evento é a pessoa do caso, e não
"Sistema". O bloqueio automático do Rafael e as baixas por webhook ficam sem ator."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from comum.auditoria import Ator, TipoAtor, usar_ator


@contextmanager
def como(usuario: Any) -> Iterator[None]:
    with usar_ator(Ator(tipo=TipoAtor.USUARIO, id=usuario.pk, nome=usuario.nome)):
        yield
