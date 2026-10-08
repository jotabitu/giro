"""Isolamento entre tarefas no mesmo processo do worker Celery (S-11, ADR 0012).

O worker prefork reaproveita o processo: um schema ou ator que uma tarefa deixou para trás
(sem passar por `na_empresa`) chegaria à próxima. Antes e depois de toda tarefa a conexão
volta ao public e o ator volta ao Sistema.
"""

from typing import Any

from celery.signals import task_postrun, task_prerun

from comum.auditoria import limpar_ator
from comum.conexao import conexao


def limpar_contexto(**_: Any) -> None:
    conexao().set_schema_to_public()
    limpar_ator()


def conectar() -> None:
    task_prerun.connect(limpar_contexto, weak=False, dispatch_uid="giro_limpar_antes")
    task_postrun.connect(limpar_contexto, weak=False, dispatch_uid="giro_limpar_depois")
