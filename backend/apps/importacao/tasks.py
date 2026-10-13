"""Tarefas da importação (docs/api/importacao.md). Recebem só ids; as duas primeiras entram
com o ator de quem pediu (`na_empresa(schema, ator=...)`), para a auditoria e os cadastros
ficarem em nome do administrador ou do "Suporte Giro" (AUD-03), nunca do Sistema."""

from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from comum.tarefas import para_cada_empresa, tarefa_de_empresa

from . import services


@shared_task(name="importacao_validar", soft_time_limit=300, time_limit=330)
@tarefa_de_empresa
def importacao_validar(schema_name: str, importacao_id: int) -> None:
    """IMP-02: valida cada linha, sem gravar nos cadastros."""
    services.validar(importacao_id)


@shared_task(name="importacao_importar", soft_time_limit=900, time_limit=960)
@tarefa_de_empresa
def importacao_importar(schema_name: str, importacao_id: int) -> None:
    """IMP-03: grava as linhas prontas até o limite do plano. Passou do tempo, nada fica
    gravado e a importação volta para `validada`."""
    try:
        services.gravar(importacao_id)
    except SoftTimeLimitExceeded:
        services.interromper(importacao_id)


@shared_task(name="importacao_limpar")
@tarefa_de_empresa
def importacao_limpar(schema_name: str) -> int:
    """Arquivo e linhas saem 30 dias depois do envio."""
    return services.limpar_vencidas()


@shared_task(name="importacao_limpar_de_todas")
def importacao_limpar_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, uma vez por dia: uma tarefa por empresa que opera."""
    return para_cada_empresa(importacao_limpar)
