"""Status e configuração da empresa que o `comum` precisa conhecer sem importar `plataforma`
nem `empresas` (ADR 0011).

Os valores de status são os do enum `plataforma.Empresa.Status`; um teste garante que não
divergem. A configuração vem de uma função que o app `empresas` registra.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from django_tenants.utils import get_public_schema_name

from comum.conexao import conexao

# Operam normalmente (escrevem). "Plataforma e assinatura" nas regras.
STATUS_OPERANDO = frozenset({"em_teste", "ativa", "inadimplente"})
# Só leitura e exportação.
STATUS_SO_LEITURA = frozenset({"suspensa"})
# Só leitura até a volta (PLT-06): escreve só nas rotas de cancelar e voltar da pausa.
STATUS_PAUSADA = "pausada"
# Não entra no sistema (AUD-08): o middleware recusa todo pedido.
STATUS_CANCELADA = "cancelada"

# --- Configuração da empresa lida por quem está acima de `empresas` (ADR 0011) ---

_exige_2fa_todos: Callable[[], bool] | None = None


def registrar_exige_2fa_todos(funcao: Callable[[], bool]) -> None:
    """Chamado pelo `ready()` do app `empresas`: lê `ConfiguracaoEmpresa.exige_2fa_todos`."""
    global _exige_2fa_todos
    _exige_2fa_todos = funcao


def exige_2fa_todos() -> bool:
    """USR-02: o administrador ligou "exigir para todos". Sem a função registrada, `False`."""
    return _exige_2fa_todos() if _exige_2fa_todos is not None else False


_atividade: Callable[[], str] | None = None


def registrar_atividade(funcao: Callable[[], str]) -> None:
    """Chamado pelo `ready()` do app `empresas`: lê `ConfiguracaoEmpresa.atividade`."""
    global _atividade
    _atividade = funcao


def atividade() -> str:
    """PLT-12: `aluga`, `vende` ou `ambos` (ADR 0024, item 2). Sem a função registrada, ou no
    schema `public`, `ambos`."""
    if _atividade is not None and conexao().schema_name != get_public_schema_name():
        return _atividade()
    return "ambos"


# --- Módulos do plano (PLT-12, ADR 0024, item 2) ---

_recursos: Callable[[], frozenset[str] | None] | None = None
_recusa: Callable[[str], Exception] | None = None
# A conta é feita uma vez por pedido (plano e ramo); fora de um pedido, a cada chamada.
_do_pedido: ContextVar[dict[str, frozenset[str]] | None] = ContextVar(
    "recursos_do_pedido", default=None
)


def registrar_recursos(
    recursos: Callable[[], frozenset[str] | None], recusa: Callable[[str], Exception]
) -> None:
    """Chamado pelo `ready()` do app `plataforma`: os recursos ligados na empresa do schema atual
    (`None` sem empresa) e o 403 `PLT-12` de um recurso desligado."""
    global _recursos, _recusa
    _recursos, _recusa = recursos, recusa


def recursos() -> frozenset[str] | None:
    """Os recursos ligados na empresa do schema atual; `None` no `public`, sem empresa ou sem a
    função registrada (tudo ligado)."""
    schema = conexao().schema_name
    if _recursos is None or schema == get_public_schema_name():
        return None
    guardados = _do_pedido.get()
    if guardados is not None and schema in guardados:
        return guardados[schema]
    ligados = _recursos()
    if guardados is not None and ligados is not None:
        guardados[schema] = ligados
    return ligados


def tem_recurso(recurso: str) -> bool:
    """A porta dos apps de cima para a PLT-12, sem importar `plataforma`. No `public`, `True`."""
    ligados = recursos()
    return ligados is None or recurso in ligados


def recusa_do_recurso(recurso: str) -> Exception:
    """O 403 `PLT-12` do recurso desligado (`plataforma.md`, "Módulos por plano")."""
    if _recusa is None:
        raise RuntimeError("O app plataforma não registrou os recursos.")
    return _recusa(recurso)


def esquecer_recursos() -> None:
    """O ramo ou o plano mudaram no meio do pedido: a próxima leitura conta de novo."""
    guardados = _do_pedido.get()
    if guardados is not None:
        guardados.clear()


@contextmanager
def recursos_do_pedido() -> Iterator[None]:
    """Guarda a conta dos recursos durante um pedido (`RecursosDoPedidoMiddleware`)."""
    marca = _do_pedido.set({})
    try:
        yield
    finally:
        _do_pedido.reset(marca)


# --- Marca da empresa (`docs/api/empresas.md`, T-129) ---

_marca: Callable[[], dict[str, Any]] | None = None


def registrar_marca(funcao: Callable[[], dict[str, Any]]) -> None:
    """Chamado pelo `ready()` do app `empresas` com `empresas.selectors.marca`."""
    global _marca
    _marca = funcao


def marca() -> dict[str, Any]:
    """Nome, iniciais, logo e cores da empresa do schema atual. Sem a função registrada, ou no
    schema `public` (aceite de convite da plataforma), só o nome da empresa da conexão."""
    if _marca is not None and conexao().schema_name != get_public_schema_name():
        return _marca()
    return {"nome_exibicao": str(getattr(conexao().tenant, "nome_exibicao", "") or "")}


def nome_da_empresa() -> str:
    """O nome de exibição da marca: e-mails, `issuer` do autenticador e contratos."""
    return str(marca()["nome_exibicao"])
