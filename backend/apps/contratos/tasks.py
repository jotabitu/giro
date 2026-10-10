"""Tarefas de contratos: PDF e envio do link (S-09, S-15), PDF assinado e o aviso do aditivo
sem assinatura (`LOC-08`).

Recebem só ids. O token é criado aqui, na hora do envio, e nunca passa pela fila. O PDF tem
tempo limite de 60 s (S-09); a memória do worker é limitada na infraestrutura.
"""

from typing import Any
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from comum.tarefas import para_cada_empresa, tarefa_de_empresa
from integracoes.whatsapp import enviar_whatsapp

from . import pdf, selectors, services
from .models import Contrato, StatusContrato

_marca_e_host = selectors.marca_e_host


def _enviar_link(contrato: Contrato, marca: pdf.Marca, host: str) -> None:
    token = services.novo_token(contrato)
    link = services.link_de_assinatura(host, token)
    cliente = contrato.cliente
    texto = (
        f"{marca.nome}: seu {contrato.titulo.lower()} da {contrato.origem_codigo} está pronto. "
        f"Leia e assine em {link} (vale por 7 dias)."
    )
    if cliente.celular:
        enviar_whatsapp(cliente.celular, texto)
    if cliente.email:
        send_mail(
            subject=f"{marca.nome}: {contrato.titulo.lower()} para assinar",
            message=f"Olá, {cliente.nome}.\n{texto}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cliente.email],
        )
    services.marcar_enviado(contrato)


def _travar(contrato_id: int) -> Contrato | None:
    return (
        Contrato.objects.select_for_update(of=("self",))
        .select_related("cliente")
        .filter(pk=contrato_id)
        .first()
    )


@shared_task(name="contratos_preparar_e_enviar", soft_time_limit=60, time_limit=70)
@tarefa_de_empresa
def contratos_preparar_e_enviar(schema_name: str, contrato_id: int) -> None:
    """Idempotente: só age em contrato `gerado`."""
    with transaction.atomic():
        contrato = _travar(contrato_id)
        if contrato is None or contrato.status != StatusContrato.GERADO:
            return
        marca, host = _marca_e_host()
        if not contrato.pdf:
            services.gravar_pdf(contrato, marca)
        _enviar_link(contrato, marca, host)


@shared_task(name="contratos_reenviar")
@tarefa_de_empresa
def contratos_reenviar(schema_name: str, contrato_id: int) -> None:
    """Novo link para quem não assinou; o PDF assinado para quem já assinou."""
    with transaction.atomic():
        contrato = _travar(contrato_id)
        if contrato is None or contrato.status == StatusContrato.CANCELADO:
            return
        marca, host = _marca_e_host()
        if contrato.status != StatusContrato.ASSINADO:
            _enviar_link(contrato, marca, host)
            return
        url = selectors.url_do_pdf(contrato)
        if url is not None and contrato.cliente.celular:
            enviar_whatsapp(
                contrato.cliente.celular,
                f"{marca.nome}: seu {contrato.titulo.lower()} assinado da "
                f"{contrato.origem_codigo} está em {url.url} (o link vale 15 minutos).",
            )


@shared_task(name="contratos_registrar_assinatura", soft_time_limit=60, time_limit=70)
@tarefa_de_empresa
def contratos_registrar_assinatura(schema_name: str, contrato_id: int) -> None:
    with transaction.atomic():
        contrato = _travar(contrato_id)
        if (
            contrato is None
            or contrato.status != StatusContrato.ASSINADO
            or contrato.pdf_assinado
            or contrato.assinado_em is None
        ):
            return
        marca, _ = _marca_e_host()
        fuso = ZoneInfo(contrato.filial.fuso)
        quando = contrato.assinado_em.astimezone(fuso).strftime("%d/%m/%Y %H:%M:%S")
        services.gravar_pdf_assinado(contrato, marca, f"{quando} ({contrato.filial.fuso})")


@shared_task(name="contratos_avisar_aditivos_sem_assinatura")
@tarefa_de_empresa
def contratos_avisar_aditivos_sem_assinatura(schema_name: str) -> int:
    """`LOC-08`: aditivo sem assinatura em 7 dias vira tarefa para os gerentes da filial."""
    return services.avisar_aditivos_sem_assinatura()


@shared_task(name="contratos_avisar_aditivos_sem_assinatura_de_todas")
def contratos_avisar_aditivos_sem_assinatura_de_todas(**_: Any) -> int:
    """Chamada pelo Beat, uma vez por dia: uma tarefa por empresa que opera."""
    return para_cada_empresa(contratos_avisar_aditivos_sem_assinatura)
