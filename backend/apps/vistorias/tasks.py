"""Tarefas de vistorias: o recibo da devolução em PDF e o envio por e-mail, com o PDF anexo
(DEV-02, DEV-06). Na fase 1, nada vai ao cliente pelo WhatsApp (ADR 0034): só com
`GIRO_WHATSAPP_CLIENTE_FINAL` ligada.

Recebem só ids. Idempotente: o PDF é gerado uma vez, e o envio só se repete no `reenviar`.
O PDF tem tempo limite de 60 s, como o do contrato (S-09).
"""

from celery import shared_task
from django.core.mail import EmailMessage
from django.db import transaction

from apps.contratos import selectors as contratos_selectors
from apps.financeiro.services import remetente
from comum import arquivos
from comum.tarefas import tarefa_de_empresa
from integracoes.whatsapp import enviar_whatsapp, whatsapp_ao_cliente_final

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
        marca, _ = contratos_selectors.marca_e_host()
        codigo = devolucao.locacao.codigo
        saldo = services.texto_do_saldo(devolucao)
        if cliente.celular and whatsapp_ao_cliente_final():
            url = arquivos.url_assinada(devolucao.recibo.name)
            enviar_whatsapp(
                cliente.celular,
                f"{marca.nome}: recibo da devolução da {codigo}. "
                f"{saldo} Veja o recibo em {url.url} (o link vale 15 minutos).",
            )
        if cliente.email:
            with devolucao.recibo.open("rb") as aberto:
                conteudo = aberto.read()
            email = EmailMessage(
                subject=f"{marca.nome}: recibo da devolução da {codigo}",
                body=(
                    f"Olá, {cliente.nome}.\n"
                    f"{marca.nome}: recibo da devolução da {codigo}. {saldo} "
                    "O recibo segue anexo, em PDF."
                ),
                from_email=remetente(),
                to=[cliente.email],
            )
            email.attach(f"recibo-devolucao-{codigo}.pdf", conteudo, "application/pdf")
            email.send()
        services.marcar_recibo_enviado(devolucao)
