"""Envio de avisos. Por enquanto só o sino; push, e-mail e WhatsApp entram com o contrato de
notificações."""

from collections.abc import Iterable

from django.db import transaction

from .models import Notificacao


def avisar(
    destinatarios: Iterable[int],
    *,
    tipo: str,
    titulo: str,
    link: str = "",
    urgente: bool = False,
    chave: str = "",
) -> int:
    """Um aviso no sino de cada destinatário. Com `chave`, quem já recebeu não recebe de novo
    (tarefas automáticas que rodam mais de uma vez no dia). Devolve quantos foram criados."""
    criados = 0
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
    return criados
