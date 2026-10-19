"""Envios de `contas`: convite por e-mail e WhatsApp (USR-01), link de nova senha e aviso de
bloqueio (USR-06).

Recebem só ids; tokens são gerados aqui, na hora do envio, e nunca passam pela fila.
"""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from comum import relogio
from comum.empresa import nome_da_empresa
from comum.tarefas import tarefa_de_empresa
from integracoes.whatsapp import enviar_whatsapp

from .models import Convite, RedefinicaoSenha, Usuario
from .services import host_da_empresa, link_do_convite, renovar_token, renovar_token_de_senha


def _marca_e_host(schema_name: str) -> tuple[str, str]:
    return nome_da_empresa(), host_da_empresa(schema_name)


@shared_task(name="contas_enviar_convite")
@tarefa_de_empresa
def contas_enviar_convite(schema_name: str, convite_id: int) -> None:
    convite = Convite.objects.select_related("usuario").filter(pk=convite_id).first()
    # P-06: o convite que outro (o link copiado, um reenvio) já invalidou, ou que venceu, não sai:
    # o link do e-mail estaria morto (B-01 da T-252).
    if convite is None or convite.aceito_em is not None or convite.expira_em <= relogio.agora():
        return
    marca, host = _marca_e_host(schema_name)
    token = renovar_token(convite)
    usuario = convite.usuario
    link = link_do_convite(host, token)
    send_mail(
        subject=f"{marca}: seu convite de acesso",
        message=(
            f"Olá, {usuario.nome}. A {marca} convidou você para acessar o sistema.\n"
            f"Crie sua senha em: {link}\n"
            "O link vale por 7 dias."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
    )
    # USR-01: com celular, o mesmo link também por WhatsApp, com a marca da locadora.
    if usuario.celular:
        enviar_whatsapp(
            usuario.celular,
            f"{marca}: você foi convidado para acessar o sistema. "
            f"Crie sua senha em {link} (vale por 7 dias).",
        )
        Convite.objects.filter(pk=convite.pk).update(enviado_whatsapp=True)


@shared_task(name="contas_enviar_redefinicao_senha")
@tarefa_de_empresa
def contas_enviar_redefinicao_senha(schema_name: str, pedido_id: int) -> None:
    """Link de 1 hora. O token vai no fragmento da URL, que não chega a servidor nem proxy."""
    pedido = RedefinicaoSenha.objects.select_related("usuario").filter(pk=pedido_id).first()
    if pedido is None or pedido.usado_em is not None:
        return
    marca, host = _marca_e_host(schema_name)
    token = renovar_token_de_senha(pedido)
    send_mail(
        subject=f"{marca}: crie uma senha nova",
        message=(
            f"Olá, {pedido.usuario.nome}. Recebemos um pedido para criar uma senha nova.\n"
            f"Crie em: https://{host}/entrar/redefinir#{token}\n"
            "O link vale por 1 hora e serve uma vez só. Se não foi você, ignore este e-mail."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pedido.usuario.email],
    )


@shared_task(name="contas_avisar_bloqueio")
@tarefa_de_empresa
def contas_avisar_bloqueio(schema_name: str, usuario_id: int) -> None:
    """USR-06: os administradores ativos sabem que um acesso foi bloqueado por 15 minutos."""
    from .selectors import administradores

    usuario = Usuario.objects.filter(pk=usuario_id).first()
    destinatarios = list(administradores().values_list("email", flat=True))
    if usuario is None or not destinatarios:
        return
    marca, _ = _marca_e_host(schema_name)
    send_mail(
        subject=f"{marca}: acesso bloqueado por tentativas erradas",
        message=(
            f"O acesso de {usuario.nome} ({usuario.email}) foi bloqueado por 15 minutos "
            "depois de 5 tentativas erradas.\n"
            "Se não foi a pessoa, confira as sessões dela em Administração, Usuários."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinatarios,
    )
