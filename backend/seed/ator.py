"""Quem fez cada coisa no histórico do seed (AUD-01): o ator do evento é a pessoa do caso, e não
"Sistema". O bloqueio automático do Rafael e as baixas por webhook ficam sem ator."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from comum.auditoria import Ator, TipoAtor, usar_ator


@contextmanager
def como(usuario: Any) -> Iterator[None]:
    with usar_ator(Ator(tipo=TipoAtor.USUARIO, id=usuario.pk, nome=usuario.nome)):
        yield


# Na demonstração (T-476) a empresa só tem o administrador convidado, com o e-mail dele: quem o
# seed buscaria pelo e-mail da Mariana passa a ser esse usuário.
_administrador_unico: ContextVar[Any] = ContextVar("administrador_unico", default=None)
EMAIL_DA_ADMINISTRADORA = "mariana@motorapida.com.br"


@contextmanager
def administrador_unico(usuario: Any) -> Iterator[None]:
    token = _administrador_unico.set(usuario)
    try:
        yield
    finally:
        _administrador_unico.reset(token)


def administradora() -> Any:
    """A Mariana no seed do desenvolvimento; o administrador existente na demonstração."""
    unico = _administrador_unico.get()
    if unico is not None:
        return unico
    from apps.contas.models import Usuario

    return Usuario.objects.get(email=EMAIL_DA_ADMINISTRADORA)
