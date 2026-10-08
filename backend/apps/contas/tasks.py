"""Envio do convite (USR-01). Recebe só ids; o token é gerado aqui, na hora do envio."""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django_tenants.utils import get_public_schema_name, schema_context

from comum.tarefas import tarefa_de_empresa

from .models import Convite
from .services import link_do_convite, renovar_token


@shared_task(name="contas_enviar_convite")
@tarefa_de_empresa
def contas_enviar_convite(schema_name: str, convite_id: int) -> None:
    from apps.plataforma.models import Dominio

    convite = Convite.objects.select_related("usuario").filter(pk=convite_id).first()
    if convite is None or convite.aceito_em is not None:
        return
    with schema_context(get_public_schema_name()):
        dominio = Dominio.objects.select_related("tenant").get(
            tenant__schema_name=schema_name, is_primary=True
        )
        marca = dominio.tenant.nome_exibicao
        host = str(dominio.domain)
    token = renovar_token(convite)
    usuario = convite.usuario
    send_mail(
        subject=f"{marca}: seu convite de acesso",
        message=(
            f"Olá, {usuario.nome}. A {marca} convidou você para acessar o sistema.\n"
            f"Crie sua senha em: {link_do_convite(host, token)}\n"
            "O link vale por 7 dias."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )
