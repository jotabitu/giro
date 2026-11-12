"""Tarefas de contratos: PDF e envio do link (S-09, S-15), PDF assinado e o aviso do aditivo
sem assinatura (`LOC-08`).

Recebem só ids. O token é criado aqui, na hora do envio, e nunca passa pela fila. O PDF tem
tempo limite de 60 s (S-09); a memória do worker é limitada na infraestrutura.
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db import transaction
from django.utils.text import slugify

from comum import arquivos
from comum.tarefas import para_cada_empresa, tarefa_de_empresa
from integracoes.whatsapp import enviar_whatsapp, whatsapp_ao_cliente_final

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
    # Na fase 1, só por e-mail (ADR 0034); o WhatsApp, só com `GIRO_WHATSAPP_CLIENTE_FINAL`.
    if cliente.celular and whatsapp_ao_cliente_final():
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


def _momento(enfileirado_em: str | None) -> datetime | None:
    return datetime.fromisoformat(enfileirado_em) if enfileirado_em else None


@shared_task(name="contratos_preparar_e_enviar", soft_time_limit=60, time_limit=70)
@tarefa_de_empresa
def contratos_preparar_e_enviar(
    schema_name: str, contrato_id: int, enfileirado_em: str | None = None
) -> None:
    """Idempotente: só age em contrato `gerado`. Não troca um token gerado depois de entrar na
    fila (um link copiado; B-02 da T-411): termina sem enviar e sem erro."""
    with transaction.atomic():
        contrato = _travar(contrato_id)
        if contrato is None or contrato.status != StatusContrato.GERADO:
            return
        if services.token_mais_novo_que(contrato, _momento(enfileirado_em)):
            return
        marca, host = _marca_e_host()
        if not contrato.pdf:
            services.gravar_pdf(contrato, marca)
        _enviar_link(contrato, marca, host)


@shared_task(name="contratos_reenviar")
@tarefa_de_empresa
def contratos_reenviar(
    schema_name: str, contrato_id: int, enfileirado_em: str | None = None
) -> None:
    """Novo link para quem não assinou; o PDF assinado para quem já assinou. O link copiado
    depois de a tarefa entrar na fila continua valendo (B-02 da T-411)."""
    with transaction.atomic():
        contrato = _travar(contrato_id)
        if contrato is None or contrato.status == StatusContrato.CANCELADO:
            return
        marca, host = _marca_e_host()
        if contrato.status != StatusContrato.ASSINADO:
            if services.token_mais_novo_que(contrato, _momento(enfileirado_em)):
                return
            _enviar_link(contrato, marca, host)
            return
        _enviar_assinado(contrato, marca)


def _enviar_assinado(contrato: Contrato, marca: pdf.Marca) -> None:
    """O contrato assinado por e-mail, com o PDF anexo (seção Automações: contrato assinado por
    e-mail na fase 1, ADR 0034). Pelo WhatsApp, com o link de 15 minutos (AUD-05), só com
    `GIRO_WHATSAPP_CLIENTE_FINAL` ligada e celular."""
    cliente = contrato.cliente
    arquivo = contrato.pdf_assinado or contrato.pdf
    if not arquivo:
        return
    titulo = contrato.titulo.lower()
    if cliente.celular and whatsapp_ao_cliente_final():
        url = arquivos.url_assinada(arquivo.name)
        enviar_whatsapp(
            cliente.celular,
            f"{marca.nome}: seu {titulo} assinado da "
            f"{contrato.origem_codigo} está em {url.url} (o link vale 15 minutos).",
        )
    if cliente.email:
        with arquivo.open("rb") as aberto:
            conteudo = aberto.read()
        email = EmailMessage(
            subject=f"{marca.nome}: {titulo} assinado",
            body=(
                f"Olá, {cliente.nome}.\n"
                f"{marca.nome}: seu {titulo} assinado da {contrato.origem_codigo} "
                "segue anexo, em PDF."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[cliente.email],
        )
        email.attach(
            f"{contrato.origem_codigo}-{slugify(contrato.titulo)}-assinado.pdf",
            conteudo,
            "application/pdf",
        )
        email.send()


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
