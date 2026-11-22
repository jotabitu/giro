"""Tarefas automáticas de `veiculos` (ADR 0012), no fuso `America/Sao_Paulo`."""

from typing import Any

from celery import shared_task

from comum import relogio
from comum.tarefas import para_cada_empresa, tarefa_de_empresa


@shared_task(name="aut_06_vencimento_de_documentos")
@tarefa_de_empresa
def aut_06_vencimento_de_documentos(schema_name: str) -> dict[str, int]:
    """AUT-06 às 07:00: alerta 30 dias antes e aplica VEI-03 no dia. Idempotente."""
    from .services import aplicar_vencimento_de_documentos

    return aplicar_vencimento_de_documentos(relogio.hoje())


@shared_task(name="aut_06_vencimento_de_documentos_de_todas")
def aut_06_vencimento_de_documentos_de_todas(**_: Any) -> int:
    """Chamada pelo Beat: uma tarefa por empresa que opera."""
    return para_cada_empresa(aut_06_vencimento_de_documentos)


@shared_task(name="consolidar_precos_agendados")
@tarefa_de_empresa
def consolidar_precos_agendados(schema_name: str) -> dict[str, int]:
    """VEI-12 (ADR 0041, item 1), às 00:05: o preço agendado vencido vira o vigente, com
    histórico e auditoria do Sistema. Idempotente; a leitura por data já usa o preço certo."""
    from .services import consolidar_precos_agendados as consolidar

    return consolidar(relogio.hoje())


@shared_task(name="consolidar_precos_agendados_de_todas")
def consolidar_precos_agendados_de_todas(**_: Any) -> int:
    """Chamada pelo Beat: uma tarefa por empresa que opera."""
    return para_cada_empresa(consolidar_precos_agendados)
