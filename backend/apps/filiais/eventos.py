"""Assinantes de `filiais` (ADR 0011, item 3) e o contador de filiais do plano (PLT-03)."""

from collections.abc import Iterable
from typing import Any

from comum.eventos import assinante

from .models import Filial


@assinante("contas.filiais_do_usuario_definidas")
def gravar_filiais_do_usuario(*, usuario_id: int, filiais_ids: Iterable[int], **_: Any) -> None:
    """Convite e edição de usuário (contrato de contas, T-011): `contas` não chama `filiais`."""
    from .services import definir_filiais_do_usuario

    definir_filiais_do_usuario(usuario_id, filiais_ids)


def contar_filiais_ativas() -> int:
    return int(Filial.ativos.count())
