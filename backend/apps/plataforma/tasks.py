"""Tarefas da plataforma: aviso de 90% do plano (PLT-03), correção noturna do uso, aviso de
entrada do suporte e fim dos acessos vencidos (PLT-07, AUT-15), baixa das faturas da assinatura
pelo webhook da conta principal (PLT-14), as notas que esperavam o endereço (PLT-15) e a virada
dos estados da assinatura (PLT-01, PLT-02, PLT-04)."""

from typing import Any
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django_tenants.utils import get_public_schema_name, schema_context

from comum.erros import ParceiroForaDoAr
from comum.tarefas import para_cada_empresa, tarefa_de_empresa
from integracoes.pagamentos.base import ParceiroIndisponivel

from .models import Empresa, Item

FUSO = "America/Sao_Paulo"


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
            f"Ao chegar a {uso['limite']}, não dá para cadastrar mais {nome_item}, e o que já "
            "está cadastrado continua funcionando. Para aumentar o limite, mude de plano em "
            "Assinatura."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
    return len(destinatarios)


@shared_task(name="plataforma_avisar_entrada_do_suporte")
@tarefa_de_empresa(inclui_suspensas=True)
def plataforma_avisar_entrada_do_suporte(schema_name: str, acesso_suporte_id: int) -> int:
    """PLT-07: os administradores ativos sabem na hora que o suporte entrou, por quê e até
    quando."""
    from .models import AcessoSuporte

    with schema_context(get_public_schema_name()):
        acesso = AcessoSuporte.objects.select_related("usuario", "empresa").get(
            pk=acesso_suporte_id
        )
        nome, marca = acesso.usuario.nome, acesso.empresa.nome_exibicao
    destinatarios = list(
        get_user_model()
        .objects.filter(perfil="administrador", status="ativo")
        .values_list("email", flat=True)
    )
    if not destinatarios:
        return 0
    fim = acesso.fim.astimezone(ZoneInfo(FUSO)).strftime("%H:%M")
    send_mail(
        subject=f"{marca}: o suporte entrou no sistema",
        message=(
            f"{nome}, da equipe de suporte, entrou no sistema da {marca} "
            f'com a permissão "{acesso.get_permissao_display()}" até {fim}.\n'
            f"Motivo: {acesso.motivo}\n"
            "Você pode encerrar ou bloquear o acesso do suporte em Administração."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
    return len(destinatarios)


@shared_task(name="aut_15_encerrar_acessos_de_suporte_vencidos")
def aut_15_encerrar_acessos_de_suporte_vencidos(**_: Any) -> int:
    """AUT-15, a cada minuto: o acesso de suporte vencido vai para `encerrado` (PLT-07)."""
    from .services import encerrar_acessos_vencidos

    return encerrar_acessos_vencidos()


@shared_task(name="plataforma_virar_estados")
def plataforma_virar_estados(**_: Any) -> dict[str, Any]:
    """Às 00:05: faturas vencidas em `atrasada` (D+1), os planos agendados que valem hoje
    (PLT-04) e os estados das empresas (PLT-01, PLT-02; tabela de transições de `assinatura.md`).
    Idempotente no mesmo dia."""
    from .services import virar_estados

    virada = virar_estados()
    return {
        "atrasadas": virada.atrasadas,
        "mudancas_de_plano": virada.mudancas_de_plano,
        "estados": virada.estados,
    }


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


@shared_task(
    name="plataforma_processar_webhook_fatura",
    autoretry_for=(ParceiroIndisponivel,),
    retry_backoff=60,
    retry_backoff_max=60 * 60,
    max_retries=24,
)
def plataforma_processar_webhook_fatura(webhook_id: int) -> str:
    """PLT-14: baixa da fatura da assinatura pelo aviso da conta principal, depois de consultar
    a cobrança no parceiro. Parceiro fora do ar: tenta de novo mais tarde (o aviso fica sem
    `processado_em`)."""
    from .services import processar_webhook_fatura

    return processar_webhook_fatura(webhook_id)


@shared_task(name="plataforma_pedir_notas_pendentes")
def plataforma_pedir_notas_pendentes(empresa_id: int) -> int:
    """PLT-15: quando a empresa passa a ter endereço, pede as notas das faturas pagas que
    esperavam por ele. Só com `GIRO_NFSE_ASSINATURA_ATIVA`; a emissão é da T-197 (bloqueada até
    o cadastro municipal), e até lá esta tarefa só conta as que esperam."""
    from .models import FaturaAssinatura, StatusFatura
    from .services import nfse_ligada

    if not nfse_ligada():
        return 0
    with schema_context(get_public_schema_name()):
        return FaturaAssinatura.objects.filter(
            empresa_id=empresa_id, status=StatusFatura.PAGA, nota_situacao=""
        ).count()


@shared_task(
    name="plataforma_atualizar_pagador",
    autoretry_for=(ParceiroForaDoAr,),
    retry_backoff=60,
    retry_backoff_max=60 * 60,
    max_retries=24,
)
def plataforma_atualizar_pagador(empresa_id: int) -> str:
    """PLT-15: os dados fiscais mudaram; o pagador da empresa na conta principal muda antes da
    próxima cobrança. Parceiro fora do ar: tenta de novo mais tarde."""
    from .services import atualizar_pagador

    with schema_context(get_public_schema_name()):
        empresa = Empresa.objects.get(pk=empresa_id)
        return atualizar_pagador(empresa)
