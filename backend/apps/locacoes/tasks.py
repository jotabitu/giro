"""Tarefas automáticas de `locacoes` (ADR 0012), no fuso `America/Sao_Paulo`."""

from typing import Any

from celery import shared_task

from comum.tarefas import para_cada_empresa, tarefa_de_empresa

# PLT-12: a empresa sem o módulo (ramo que só vende) é pulada.
MODULO = "locacoes_vistoria"


@shared_task(name="aut_01_lembrete_de_devolucao")
@tarefa_de_empresa(recurso=MODULO)
def aut_01_lembrete_de_devolucao(schema_name: str) -> int:
    """AUT-01, às 08:00: lembra o cliente da devolução do dia, com o horário e o endereço da
    filial. Idempotente: uma vez por locação."""
    from .services import lembrar_devolucoes

    return lembrar_devolucoes()


@shared_task(name="aut_01_lembrete_de_devolucao_de_todas")
def aut_01_lembrete_de_devolucao_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, às 08:00: uma tarefa por empresa que opera."""
    return para_cada_empresa(aut_01_lembrete_de_devolucao)


@shared_task(name="aut_02_marcar_devolucao_atrasada")
@tarefa_de_empresa(recurso=MODULO)
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
@tarefa_de_empresa(recurso=MODULO)
def locacoes_cancelar_rascunhos_sem_uso(schema_name: str) -> int:
    """Rascunho com 24 h sem uso vai para `cancelada`. Idempotente."""
    from .services import cancelar_rascunhos_sem_uso

    return cancelar_rascunhos_sem_uso()


@shared_task(name="locacoes_cancelar_rascunhos_sem_uso_de_todas")
def locacoes_cancelar_rascunhos_sem_uso_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, de hora em hora: uma tarefa por empresa que opera."""
    return para_cada_empresa(locacoes_cancelar_rascunhos_sem_uso)
