"""Tarefas da auditoria (ADR 0012)."""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from comum import auditoria
from comum.empresa import nome_da_empresa
from comum.tarefas import tarefa_de_empresa

from . import services


@shared_task(name="auditoria_exportar")
@tarefa_de_empresa(inclui_suspensas=True)  # empresa suspensa ainda exporta (AUD-08)
def auditoria_exportar(schema_name: str, exportacao_id: int, link: str) -> None:
    """Gera o arquivo (AUD-07) e avisa quem pediu, por e-mail, com o link de 7 dias."""
    exportacao = services.gerar(exportacao_id)
    if exportacao is None or exportacao.solicitada_por_id is None:
        return
    emails = auditoria.consultar("emails_de_usuarios", {exportacao.solicitada_por_id})
    email = emails.get(exportacao.solicitada_por_id)
    if not email:
        return
    send_mail(
        subject=f"{nome_da_empresa()}: sua exportação está pronta",
        message=(
            f"O arquivo que você pediu ({services.conteudo_rotulo(exportacao)}) está pronto.\n"
            f"Baixe em {link}\n"
            "O link vale 7 dias e pede que você entre no sistema."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
