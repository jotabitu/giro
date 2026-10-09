"""Tarefas automáticas de `locacoes` (ADR 0012), no fuso `America/Sao_Paulo`."""

from typing import Any

from celery import shared_task

from comum.tarefas import para_cada_empresa, tarefa_de_empresa


@shared_task(name="locacoes_cancelar_rascunhos_sem_uso")
@tarefa_de_empresa
def locacoes_cancelar_rascunhos_sem_uso(schema_name: str) -> int:
    """Rascunho com 24 h sem uso vai para `cancelada`. Idempotente."""
    from .services import cancelar_rascunhos_sem_uso

    return cancelar_rascunhos_sem_uso()


@shared_task(name="locacoes_cancelar_rascunhos_sem_uso_de_todas")
def locacoes_cancelar_rascunhos_sem_uso_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, de hora em hora: uma tarefa por empresa que opera."""
    return para_cada_empresa(locacoes_cancelar_rascunhos_sem_uso)
