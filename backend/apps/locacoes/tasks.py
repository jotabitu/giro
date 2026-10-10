"""Tarefas automáticas de `locacoes` (ADR 0012), no fuso `America/Sao_Paulo`."""

from typing import Any

from celery import shared_task

from comum.tarefas import para_cada_empresa, tarefa_de_empresa


@shared_task(name="aut_02_marcar_devolucao_atrasada")
@tarefa_de_empresa
def aut_02_marcar_devolucao_atrasada(schema_name: str) -> int:
    """AUT-02, de hora em hora: aplica LOC-10 e LOC-11 (`devolucao_atrasada` no dia seguinte ao
    fim previsto). Idempotente."""
    from .services import marcar_devolucoes_atrasadas

    return marcar_devolucoes_atrasadas()


@shared_task(name="aut_02_marcar_devolucao_atrasada_de_todas")
def aut_02_marcar_devolucao_atrasada_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, de hora em hora: uma tarefa por empresa que opera."""
    return para_cada_empresa(aut_02_marcar_devolucao_atrasada)


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
