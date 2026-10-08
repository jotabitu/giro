"""Tarefas da plataforma: aviso de 90% do plano (PLT-03) e correção noturna do uso."""

from typing import Any

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django_tenants.utils import get_public_schema_name, schema_context

from comum.tarefas import para_cada_empresa, tarefa_de_empresa

from .models import Empresa, Item


@shared_task(name="plataforma_avisar_limite_90")
@tarefa_de_empresa
def plataforma_avisar_limite_90(schema_name: str, item: str) -> int:
    """E-mail "limite do plano em 90%" aos administradores ativos, com a marca da locadora."""
    from .selectors import uso_do_plano

    with schema_context(get_public_schema_name()):
        empresa = Empresa.objects.select_related("plano").get(schema_name=schema_name)
        uso = uso_do_plano(empresa)[item]
    destinatarios = list(
        get_user_model()
        .objects.filter(perfil="administrador", status="ativo")
        .values_list("email", flat=True)
    )
    if not destinatarios:
        return 0
    nome_item = Item(item).label
    send_mail(
        subject=f"{empresa.nome_exibicao}: limite do plano em 90%",
        message=(
            f"Sua empresa usa {uso['usado']} de {uso['limite']} {nome_item} do plano. "
            f"Ao chegar a {uso['limite']}, não será possível cadastrar novos {nome_item}. "
            "Para aumentar o limite, mude de plano."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
    return len(destinatarios)


@shared_task(name="plataforma_recalcular_uso")
@tarefa_de_empresa(inclui_suspensas=True)
def plataforma_recalcular_uso(schema_name: str) -> dict[str, int]:
    from .services import recalcular_uso

    with schema_context(get_public_schema_name()):
        empresa = Empresa.objects.get(schema_name=schema_name)
    return recalcular_uso(empresa)


@shared_task(name="plataforma_recalcular_uso_de_todas")
def plataforma_recalcular_uso_de_todas(**_: Any) -> int:
    """Agendada pelo Beat de madrugada; enfileira uma correção por empresa."""
    return para_cada_empresa(plataforma_recalcular_uso, inclui_suspensas=True)
