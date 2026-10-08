"""Status e configuração da empresa que o `comum` precisa conhecer sem importar `plataforma`
nem `empresas` (ADR 0011).

Os valores de status são os do enum `plataforma.Empresa.Status`; um teste garante que não
divergem. A configuração vem de uma função que o app `empresas` registra.
"""

from collections.abc import Callable

# Operam normalmente (escrevem). "Plataforma e assinatura" nas regras.
STATUS_OPERANDO = frozenset({"em_teste", "ativa", "inadimplente"})
# Só leitura e exportação.
STATUS_SO_LEITURA = frozenset({"suspensa"})

# --- Configuração da empresa lida por quem está acima de `empresas` (ADR 0011) ---

_exige_2fa_todos: Callable[[], bool] | None = None


def registrar_exige_2fa_todos(funcao: Callable[[], bool]) -> None:
    """Chamado pelo `ready()` do app `empresas`: lê `ConfiguracaoEmpresa.exige_2fa_todos`."""
    global _exige_2fa_todos
    _exige_2fa_todos = funcao


def exige_2fa_todos() -> bool:
    """USR-02: o administrador ligou "exigir para todos". Sem a função registrada, `False`."""
    return _exige_2fa_todos() if _exige_2fa_todos is not None else False
