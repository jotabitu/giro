"""Envio de avisos: o sino e, quando pedido, o e-mail (AUT-17, ADR 0035, item 6). Push e
WhatsApp entram com o contrato de notificações."""

from collections.abc import Iterable
from email.headerregistry import Address
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction

from comum.empresa import nome_da_empresa

from .models import Notificacao


def remetente() -> str:
    """O endereço de `DEFAULT_FROM_EMAIL` com o nome da locadora, como na régua (AUT-03)."""
    _, endereco = parseaddr(settings.DEFAULT_FROM_EMAIL)
    return str(Address(display_name=nome_da_empresa(), addr_spec=endereco))


def _mandar_emails(destinatarios: list[int], titulo: str) -> None:
    enderecos = (
        get_user_model()
        .objects.filter(pk__in=destinatarios)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    de = remetente()
    for endereco in enderecos:
        send_mail(subject=titulo, message=titulo, from_email=de, recipient_list=[endereco])


def avisar(
    destinatarios: Iterable[int],
    *,
    tipo: str,
    titulo: str,
    link: str = "",
    urgente: bool = False,
    chave: str = "",
    por_email: bool = False,
) -> int:
    """Um aviso no sino de cada destinatário. Com `chave`, quem já recebeu não recebe de novo
    (tarefas automáticas que rodam mais de uma vez no dia). Com `por_email`, depois do commit,
    o mesmo título por e-mail só para quem recebeu o aviso agora, com o remetente da locadora.
    Devolve quantos foram criados."""
    criados = 0
    novos: list[int] = []
    with transaction.atomic():
        for destinatario_id in set(destinatarios):
            if chave:
                _, novo = Notificacao.objects.get_or_create(
                    destinatario_id=destinatario_id,
                    chave=chave,
                    defaults={"tipo": tipo, "titulo": titulo, "link": link, "urgente": urgente},
                )
            else:
                Notificacao.objects.create(
                    destinatario_id=destinatario_id,
                    tipo=tipo,
                    titulo=titulo,
                    link=link,
                    urgente=urgente,
                )
                novo = True
            criados += int(novo)
            if novo:
                novos.append(destinatario_id)
        if por_email and novos:
            transaction.on_commit(lambda: _mandar_emails(novos, titulo))
    return criados
