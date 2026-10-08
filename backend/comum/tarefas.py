"""Tarefas Celery por empresa (ADR 0012).

    @shared_task(name="aut_02_marcar_devolucao_atrasada")
    @tarefa_de_empresa
    def aut_02_marcar_devolucao_atrasada(schema_name: str) -> None: ...

O primeiro argumento de toda tarefa de empresa é `schema_name`. O Beat chama
`para_cada_empresa(aut_02_marcar_devolucao_atrasada)`.

Antes de entrar, `na_empresa` confere no public que a empresa existe, está num status
permitido e que o schema ainda existe no banco. Sem isso, com o search_path
`<schema>, public` do django-tenants, uma tarefa na fila de uma empresa já apagada (AUD-08)
leria e gravaria as tabelas do public (achado T-039).
"""

import functools
import logging
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Protocol, TypedDict

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from comum.auditoria import Ator, TipoAtor, ator_atual, usar_ator
from comum.conexao import schema_atual as schema_atual  # para quem agenda tarefa
from comum.empresa import STATUS_OPERANDO, STATUS_SO_LEITURA

_REGRA_DA_TAREFA = re.compile(r"^aut_(\d+)_")
logger = logging.getLogger(__name__)


class AtorDaFila(TypedDict):
    """Quem pediu a tarefa, sem nome nem outro dado pessoal na fila (ADR 0018, item 3)."""

    tipo: str
    id: int | None
    acesso_suporte_id: int | None


def ator_para_fila() -> AtorDaFila | None:
    """Para passar como `ator=` ao agendar uma tarefa pedida por uma pessoa."""
    ator = ator_atual()
    if ator.tipo == TipoAtor.SISTEMA:
        return None
    return {"tipo": ator.tipo, "id": ator.id, "acesso_suporte_id": ator.acesso_suporte_id}


def _nome_do_usuario(id_usuario: int | None, *, no_public: bool) -> str:
    if id_usuario is None:
        return ""
    consulta = get_user_model().objects.filter(pk=id_usuario).values_list("nome", flat=True)
    if no_public:
        with schema_context(get_public_schema_name()):
            return str(consulta.first() or "")
    return str(consulta.first() or "")


def _montar_ator(ator: AtorDaFila | None, regra: str) -> Ator:
    """Sem `ator`, é o Sistema. Com ele, o nome é buscado ao entrar no schema."""
    if ator is None:
        return Ator(tipo=TipoAtor.SISTEMA, nome="Sistema", regra=regra)
    if ator["tipo"] == TipoAtor.SUPORTE:
        # O atendente é usuário do public (ADR 0013, item 2).
        nome = _nome_do_usuario(ator["id"], no_public=True) or "Suporte Giro"
    elif ator["tipo"] == TipoAtor.USUARIO:
        nome = _nome_do_usuario(ator["id"], no_public=False) or "Usuário removido"
    else:
        raise ValueError(f"Tipo de ator desconhecido: {ator['tipo']}")
    return Ator(
        tipo=ator["tipo"],
        id=ator["id"],
        nome=nome,
        acesso_suporte_id=ator.get("acesso_suporte_id"),
        regra=regra,
    )


class EmpresaIndisponivel(Exception):
    """A empresa não existe, não está num status permitido ou o schema foi apagado."""


class TarefaCelery(Protocol):
    def delay(self, *args: Any, **kwargs: Any) -> Any: ...


def regra_da_tarefa(nome: str) -> str:
    """`aut_02_marcar_devolucao_atrasada` → `AUT-02`."""
    achado = _REGRA_DA_TAREFA.match(nome)
    return f"AUT-{achado.group(1)}" if achado else ""


def _status_permitidos(inclui_suspensas: bool) -> frozenset[str]:
    return STATUS_OPERANDO | STATUS_SO_LEITURA if inclui_suspensas else STATUS_OPERANDO


def conferir_empresa_para_tarefa(schema_name: str, *, inclui_suspensas: bool = False) -> None:
    """Levanta `EmpresaIndisponivel` se não for seguro entrar no schema."""
    if schema_name == get_public_schema_name():
        raise EmpresaIndisponivel("Tarefa de empresa não roda no schema público.")
    with schema_context(get_public_schema_name()):
        status = (
            get_tenant_model()
            .objects.filter(schema_name=schema_name)
            .values_list("status", flat=True)
            .first()
        )
        if status is None:
            raise EmpresaIndisponivel(f"Empresa {schema_name} não existe.")
        if status not in _status_permitidos(inclui_suspensas):
            raise EmpresaIndisponivel(f"Empresa {schema_name} está {status}.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [schema_name])
            if cursor.fetchone() is None:
                raise EmpresaIndisponivel(f"O schema {schema_name} não existe mais.")


@contextmanager
def na_empresa(
    schema_name: str,
    *,
    regra: str = "",
    ator: AtorDaFila | None = None,
    inclui_suspensas: bool = False,
) -> Iterator[None]:
    """Confere a empresa e entra no schema dela.

    O ator da auditoria é o Sistema (com a `regra`) ou, com `ator`, quem pediu a tarefa.
    """
    conferir_empresa_para_tarefa(schema_name, inclui_suspensas=inclui_suspensas)
    with schema_context(schema_name), usar_ator(_montar_ator(ator, regra)):
        yield


def tarefa_de_empresa[**P, R](
    funcao: Callable[P, R] | None = None, *, inclui_suspensas: bool = False
) -> Any:
    """`@tarefa_de_empresa` ou `@tarefa_de_empresa(inclui_suspensas=True)` (leitura e cobrança).

    Empresa indisponível não é erro da tarefa: ela registra um aviso e não faz nada.
    Um argumento nomeado `ator` (de `ator_para_fila()`) é consumido aqui e não chega à função.
    """

    def decorar(alvo: Callable[P, R]) -> Callable[P, R | None]:
        regra = regra_da_tarefa(alvo.__name__)

        @functools.wraps(alvo)
        def executar(*args: P.args, **kwargs: P.kwargs) -> R | None:
            ator: AtorDaFila | None = kwargs.pop("ator", None)  # type: ignore[assignment]
            schema_name = args[0] if args else kwargs.get("schema_name")
            if not isinstance(schema_name, str) or schema_name == get_public_schema_name():
                raise TypeError(f"{alvo.__name__}: o 1º argumento deve ser o schema da empresa.")
            try:
                conferir_empresa_para_tarefa(schema_name, inclui_suspensas=inclui_suspensas)
            except EmpresaIndisponivel as motivo:
                logger.warning("%s ignorada: %s", alvo.__name__, motivo)
                return None
            with na_empresa(schema_name, regra=regra, ator=ator, inclui_suspensas=inclui_suspensas):
                return alvo(*args, **kwargs)

        return executar

    return decorar(funcao) if funcao is not None else decorar


def schemas_das_empresas(*, inclui_suspensas: bool = False) -> list[str]:
    status = _status_permitidos(inclui_suspensas)
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
