"""Tarefas da plataforma: aviso de 90% do plano (PLT-03), correção noturna do uso, aviso de
entrada do suporte e fim dos acessos vencidos (PLT-07, AUT-15), baixa das faturas da assinatura
pelo webhook da conta principal (PLT-14), as notas que esperavam o endereço (PLT-15), a virada
dos estados da assinatura (PLT-01, PLT-02, PLT-04), a geração, a emissão e a cobrança no cartão
das faturas (PLT-02, PLT-04, PLT-13) e a régua da assinatura (AUT-13)."""

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
# PLT-13, CA-ASS-63: a linha do e-mail do boleto quando o Pix automático ainda não foi autorizado.
PIX_AUTOMATICO_PENDENTE = (
    "Seu Pix automático ainda não foi autorizado. Esta fatura vai por boleto com Pix."
)


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


@shared_task(name="plataforma_gerar_faturas")
def plataforma_gerar_faturas(**_: Any) -> dict[str, Any]:
    """Às 06:00 (PLT-02): faturas do período seguinte 5 dias antes do vencimento, com a
    conferência do downgrade agendado (PLT-04); a emissão no parceiro; e o cartão guardado no
    vencimento, com uma tentativa a mais. Idempotente no mesmo dia."""
    from .services import gerar_faturas

    geracao = gerar_faturas()
    return {
        "faturas": geracao.faturas,
        "emitidas": geracao.emitidas,
        "cartoes": geracao.cartoes,
    }


@shared_task(
    name="plataforma_cobrar_cartao",
    autoretry_for=(ParceiroForaDoAr,),
    retry_backoff=60,
    retry_backoff_max=60 * 60,
    max_retries=24,
)
def plataforma_cobrar_cartao(fatura_id: int) -> str:
    """PLT-04: a diferença do upgrade no cartão guardado, na hora. Parceiro fora do ar: tenta de
    novo mais tarde (a tentativa não conta)."""
    from comum import relogio

    from .services import cobrar_cartao_da_fatura

    return cobrar_cartao_da_fatura(fatura_id, relogio.hoje())


@shared_task(name="plataforma_enviar_boleto")
def plataforma_enviar_boleto(fatura_id: int, pix_pendente: bool = False) -> int:
    """PLT-02: o boleto (com Pix) vai por e-mail no dia em que é criado, 5 dias antes do
    vencimento, para o e-mail de cobrança e os administradores (PLT-15). Marca Giro. Com
    `pix_pendente`, a fatura saiu em boleto porque o Pix automático não foi autorizado (PLT-13)."""
    from comum.dinheiro import formatar_reais

    from .calendario import descricao_da_fatura, dia_e_mes
    from .models import FaturaAssinatura
    from .services import destinatarios_da_cobranca

    with schema_context(get_public_schema_name()):
        fatura = FaturaAssinatura.objects.select_related("empresa", "plano").get(pk=fatura_id)
        if fatura.cobranca_tipo != "boleto" or not fatura.cobranca_boleto_url:
            return 0
        destinatarios = destinatarios_da_cobranca(fatura.empresa)
    if not destinatarios:
        return 0
    descricao = descricao_da_fatura(
        fatura.tipo, fatura.plano.nome, fatura.ciclo, fatura.periodo_inicio, fatura.periodo_fim
    )
    vence = dia_e_mes(fatura.vencimento)
    send_mail(
        subject=f"Giro: boleto da fatura {fatura.codigo}, vence em {vence}",
        message=(
            (f"{PIX_AUTOMATICO_PENDENTE}\n" if pix_pendente else "")
            + f"A fatura {fatura.codigo} da {fatura.empresa.nome_exibicao} ({descricao}), de "
            f"{formatar_reais(int(fatura.valor_centavos))}, vence em {vence}.\n"
            f"Boleto: {fatura.cobranca_boleto_url}\n"
            f"Linha digitável: {fatura.cobranca_linha_digitavel}\n"
            # Sem o Pix do boleto (a conta sem chave Pix), sem a linha vazia (T-305).
            + (
                f"Pix copia e cola: {fatura.cobranca_pix_copia_e_cola}\n"
                if fatura.cobranca_pix_copia_e_cola
                else ""
            )
            + "Você também paga pelo botão Pagar, em Assinatura."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
    return len(destinatarios)


@shared_task(name="plataforma_avisar_downgrade_recusado")
def plataforma_avisar_downgrade_recusado(
    empresa_id: int, plano_id: int, vencimento: str, excede: dict[str, Any]
) -> int:
    """PLT-04 (CA-ASS-40): o downgrade agendado deixou de caber na geração da fatura. O
    administrador e o e-mail de cobrança recebem o motivo, como na recusa."""
    from datetime import date

    from .calendario import dia_e_mes
    from .models import Plano
    from .services import destinatarios_da_cobranca, texto_do_que_excede

    with schema_context(get_public_schema_name()):
        empresa = Empresa.objects.select_related("plano").get(pk=empresa_id)
        agendado = Plano.objects.get(pk=plano_id)
        destinatarios = destinatarios_da_cobranca(empresa)
    if not destinatarios or empresa.plano is None:
        return 0
    dia = dia_e_mes(date.fromisoformat(vencimento))
    send_mail(
        subject=f"Giro: a mudança para o plano {agendado.nome} não aconteceu",
        message=(
            f"A {empresa.nome_exibicao} ia mudar para o plano {agendado.nome} em {dia}, mas o uso "
            f"de hoje não cabe nele: {texto_do_que_excede(excede)}.\n"
            f"Por isso, a fatura de {dia} saiu pelo plano {empresa.plano.nome}, e a empresa "
            "continua nele. Para mudar, ajuste o uso e escolha o plano de novo em Assinatura."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
    return len(destinatarios)


@shared_task(name="aut_13_regua_assinatura")
def aut_13_regua_assinatura(**_: Any) -> dict[str, int]:
    """AUT-13, às 09:00 (PLT-02): D-3 lembrete por e-mail; D0 e D+3 e-mail e WhatsApp; D+7 aviso
    de suspensão e a tarefa de ligação da equipe. Idempotente no mesmo dia."""
    from .services import regua_da_assinatura

    return regua_da_assinatura()


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
