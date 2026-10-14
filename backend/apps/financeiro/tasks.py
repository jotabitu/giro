"""Tarefas automáticas do financeiro (ADR 0012), no fuso `America/Sao_Paulo`. Idempotentes."""

from typing import Any

from celery import shared_task

from comum.tarefas import para_cada_empresa, tarefa_de_empresa
from integracoes.pagamentos.base import ParceiroIndisponivel


@shared_task(name="aut_03_regua_de_cobranca")
@tarefa_de_empresa
def aut_03_regua_de_cobranca(schema_name: str) -> int:
    """AUT-03, às 09:00: cobranças pelo WhatsApp e `financeiro.parcela_atrasou` (LOC-07,
    CLI-05)."""
    from .services import regua_de_cobranca

    return regua_de_cobranca()


@shared_task(name="aut_03_regua_de_cobranca_de_todas")
def aut_03_regua_de_cobranca_de_todas(**_: Any) -> int:
    return para_cada_empresa(aut_03_regua_de_cobranca)


@shared_task(
    name="aut_05_processar_webhook",
    autoretry_for=(ParceiroIndisponivel,),
    retry_backoff=60,
    retry_backoff_max=60 * 60,
    max_retries=24,
)
@tarefa_de_empresa
def aut_05_processar_webhook(schema_name: str, webhook_id: int) -> str:
    """AUT-05: baixa pelo aviso do parceiro, depois de consultar a cobrança nele (S-14). Com o
    parceiro fora do ar, tenta de novo mais tarde: o aviso fica sem `processado_em` (CA-029-16)."""
    from .services import processar_webhook

    return processar_webhook(webhook_id)


@shared_task(name="aut_08_fechamento_automatico_do_caixa")
@tarefa_de_empresa
def aut_08_fechamento_automatico_do_caixa(schema_name: str) -> int:
    """AUT-08, às 23:59: aplica a FIN-08."""
    from .services import fechar_caixas_sem_conferencia

    return fechar_caixas_sem_conferencia()


@shared_task(name="aut_08_fechamento_automatico_do_caixa_de_todas")
def aut_08_fechamento_automatico_do_caixa_de_todas(**_: Any) -> int:
    return para_cada_empresa(aut_08_fechamento_automatico_do_caixa)
