"""Tarefas Celery por empresa (ADR 0012).

    @shared_task(name="aut_02_marcar_devolucao_atrasada")
    @tarefa_de_empresa
    def aut_02_marcar_devolucao_atrasada(schema_name: str) -> None: ...

O primeiro argumento de toda tarefa de empresa é `schema_name`. O Beat chama
`para_cada_empresa(aut_02_marcar_devolucao_atrasada)`.
"""

import functools
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Protocol

from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from comum.auditoria import Ator, TipoAtor, usar_ator
from comum.conexao import schema_atual as schema_atual  # para quem agenda tarefa
from comum.empresa import STATUS_OPERANDO, STATUS_SO_LEITURA

_REGRA_DA_TAREFA = re.compile(r"^aut_(\d+)_")


class TarefaCelery(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any: ...


def regra_da_tarefa(nome: str) -> str:
    """`aut_02_marcar_devolucao_atrasada` → `AUT-02`."""
    achado = _REGRA_DA_TAREFA.match(nome)
    return f"AUT-{achado.group(1)}" if achado else ""


@contextmanager
def na_empresa(schema_name: str, *, regra: str = "") -> Iterator[None]:
    """Entra no schema da empresa com o ator Sistema da auditoria."""
    ator = Ator(tipo=TipoAtor.SISTEMA, nome="Sistema", regra=regra)
    with schema_context(schema_name), usar_ator(ator):
        yield


def tarefa_de_empresa[**P, R](funcao: Callable[P, R]) -> Callable[P, R]:
    regra = regra_da_tarefa(funcao.__name__)

    @functools.wraps(funcao)
    def executar(*args: P.args, **kwargs: P.kwargs) -> R:
        schema_name = args[0] if args else kwargs.get("schema_name")
        if not isinstance(schema_name, str) or schema_name == get_public_schema_name():
            raise TypeError(f"{funcao.__name__}: o 1º argumento deve ser o schema da empresa.")
        with na_empresa(schema_name, regra=regra):
            return funcao(*args, **kwargs)

    return executar


def schemas_das_empresas(*, inclui_suspensas: bool = False) -> list[str]:
    status = STATUS_OPERANDO | STATUS_SO_LEITURA if inclui_suspensas else STATUS_OPERANDO
    with schema_context(get_public_schema_name()):
        return list(
            get_tenant_model()
            .objects.exclude(schema_name=get_public_schema_name())
            .filter(status__in=status)
            .order_by("schema_name")
            .values_list("schema_name", flat=True)
        )


def para_cada_empresa(
    tarefa: TarefaCelery, *args: Any, inclui_suspensas: bool = False, **kwargs: Any
) -> int:
    """Enfileira uma tarefa por empresa que opera. `inclui_suspensas` só para leitura/cobrança."""
    schemas = schemas_das_empresas(inclui_suspensas=inclui_suspensas)
    for schema_name in schemas:
        tarefa.delay(schema_name, *args, **kwargs)
    return len(schemas)
