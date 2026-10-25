"""Isolamento entre tarefas no mesmo processo do worker Celery (S-11, ADR 0012).

O worker prefork reaproveita o processo: um schema ou ator que uma tarefa deixou para trás
(sem passar por `na_empresa`) chegaria à próxima. Antes e depois de toda tarefa a conexão
volta ao public e o ator volta ao Sistema.

Tarefa eager (`CELERY_TASK_ALWAYS_EAGER`, testes e seed) roda no processo e na conexão de quem a
chamou. Ela também começa e termina limpa, mas no fim devolve o schema e o ator de quem chamou:
sem isso, o seed ficava no public depois do commit que dispara o convite (T-281).
"""

from typing import Any

from celery.signals import task_postrun, task_prerun

from comum.auditoria import guardar_ator, limpar_ator, restaurar_ator
from comum.conexao import conexao

# Contexto de quem chamou, por tarefa eager em andamento (o id da tarefa é único).
_CHAMADORES: dict[str, tuple[Any, Any]] = {}


def _eager(tarefa: Any) -> bool:
    return bool(getattr(getattr(tarefa, "request", None), "is_eager", False))


def limpar_contexto(**_: Any) -> None:
    conexao().set_schema_to_public()
    limpar_ator()


def antes_da_tarefa(sender: Any = None, task_id: str | None = None, **_: Any) -> None:
    if task_id is not None and _eager(sender):
        _CHAMADORES[task_id] = (conexao().tenant, guardar_ator())
    limpar_contexto()


def depois_da_tarefa(sender: Any = None, task_id: str | None = None, **_: Any) -> None:
    limpar_contexto()
    chamador = _CHAMADORES.pop(task_id, None) if task_id is not None else None
    if chamador is not None:
        tenant, ator = chamador
        if tenant is not None:
            conexao().set_tenant(tenant)
        restaurar_ator(ator)


def conectar() -> None:
    task_prerun.connect(antes_da_tarefa, weak=False, dispatch_uid="giro_limpar_antes")
    task_postrun.connect(depois_da_tarefa, weak=False, dispatch_uid="giro_limpar_depois")
