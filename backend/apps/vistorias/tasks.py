"""Tarefas de vistorias: o recibo da devolução em PDF e o envio por WhatsApp (DEV-06).

Recebem só ids. Idempotente: o PDF é gerado uma vez, e o envio só se repete no `reenviar`.
O PDF tem tempo limite de 60 s, como o do contrato (S-09).
"""

from celery import shared_task
from django.db import transaction

from apps.contratos import selectors as contratos_selectors
from comum import arquivos
from comum.tarefas import tarefa_de_empresa
from integracoes.whatsapp import enviar_whatsapp

from . import services
from .models import Devolucao, StatusDevolucao


@shared_task(name="vistorias_enviar_recibo", soft_time_limit=60, time_limit=70)
@tarefa_de_empresa
def vistorias_enviar_recibo(schema_name: str, devolucao_id: int, reenviar: bool = False) -> None:
    with transaction.atomic():
        devolucao = (
            Devolucao.objects.select_for_update(of=("self",))
            .select_related("locacao", "locacao__cliente", "locacao__filial")
            .filter(pk=devolucao_id)
            .first()
        )
        if devolucao is None or devolucao.status != StatusDevolucao.CONCLUIDA:
            return
        if devolucao.recibo_enviado_em is not None and not reenviar:
            return
        if not devolucao.recibo:
            services.gravar_recibo(devolucao)
        cliente = devolucao.locacao.cliente
        if cliente.celular:
            marca, _ = contratos_selectors.marca_e_host()
            url = arquivos.url_assinada(devolucao.recibo.name)
            enviar_whatsapp(
                cliente.celular,
                f"{marca.nome}: recibo da devolução da {devolucao.locacao.codigo}. "
                f"{services.texto_do_saldo(devolucao)} Veja o recibo em {url.url} "
                "(o link vale 15 minutos).",
            )
        services.marcar_recibo_enviado(devolucao)
