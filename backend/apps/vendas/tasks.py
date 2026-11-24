"""Tarefas automáticas de `vendas` (ADR 0012), no fuso `America/Sao_Paulo`."""

from typing import Any

from celery import shared_task

from comum.tarefas import para_cada_empresa, tarefa_de_empresa

# PLT-12, ADR 0024: a empresa sem o módulo de vendas é pulada.
MODULO = "vendas_comissoes"


@shared_task(name="aut_19_vencer_propostas")
@tarefa_de_empresa(recurso=MODULO)
def aut_19_vencer_propostas(schema_name: str) -> int:
    """AUT-19, às 02:40: a proposta sem resposta há 7 dias corridos vira `perdida` (VEN-13).
    Idempotente: a perdida sai da seleção, e a rodada perdida pega as vencidas na próxima."""
    from .services import vencer_propostas

    return vencer_propostas()


@shared_task(name="aut_19_vencer_propostas_de_todas")
def aut_19_vencer_propostas_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, às 02:40: uma tarefa por empresa que opera."""
    return para_cada_empresa(aut_19_vencer_propostas)


@shared_task(name="vendas_enviar_proposta", soft_time_limit=60, time_limit=70)
@tarefa_de_empresa
def vendas_enviar_proposta(schema_name: str, venda_id: int, momento: str = "") -> None:
    """VEN-15 (T-502, fase 1c): grava o PDF da proposta e manda o e-mail com ele anexo, depois do
    commit do envio. Recebe só ids; o envio mais novo vence (`momento`). PDF com tempo limite de
    60 s, como o do contrato (S-09)."""
    from .envio import enviar

    enviar(venda_id, momento)
