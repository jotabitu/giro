"""Status e configuração da empresa que o `comum` precisa conhecer sem importar `plataforma`
nem `empresas` (ADR 0011).

Os valores de status são os do enum `plataforma.Empresa.Status`; um teste garante que não
divergem. A configuração vem de uma função que o app `empresas` registra.
"""

from collections.abc import Callable
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
