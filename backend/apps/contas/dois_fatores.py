"""Verificação em 2 etapas e bloqueio por códigos errados (PLT-08; ADR 0013, item 3).

Autenticador: `TOTPDevice` do django-otp. Códigos de recuperação: `StaticDevice` com 8 códigos
de uso único. 3 códigos errados seguidos bloqueiam por 15 minutos e geram evento de
segurança na auditoria do schema (o `public`, para a equipe da plataforma).
"""

import secrets
from datetime import UTC, timedelta

from django.db import transaction
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from comum import relogio
from comum.auditoria import Categoria, registrar_evento
from comum.erros import MuitasTentativas

from .models import Usuario

CODIGOS_ERRADOS_PARA_BLOQUEAR = 3
TEMPO_DE_BLOQUEIO = timedelta(minutes=15)
QUANTOS_CODIGOS_DE_RECUPERACAO = 8
NOME_AUTENTICADOR = "autenticador"
NOME_RECUPERACAO = "recuperacao"


def autenticador_confirmado(usuario: Usuario) -> TOTPDevice | None:
    return TOTPDevice.objects.filter(user=usuario, confirmed=True).first()


def tem_2fa(usuario: Usuario) -> bool:
    return autenticador_confirmado(usuario) is not None


def novo_autenticador(usuario: Usuario) -> TOTPDevice:
    """Troca o segredo do autenticador ainda não confirmado."""
    TOTPDevice.objects.filter(user=usuario, confirmed=False).delete()
    return TOTPDevice.objects.create(user=usuario, name=NOME_AUTENTICADOR, confirmed=False)


def _codigo_de_recuperacao() -> str:
    bruto = secrets.token_hex(4)
    return f"{bruto[:4]}-{bruto[4:]}"


def confirmar_autenticador(dispositivo: TOTPDevice) -> list[str]:
    """Confirma o dispositivo e gera os 8 códigos de recuperação, mostrados uma vez só."""
    with transaction.atomic():
        dispositivo.confirmed = True
        dispositivo.save(update_fields=["confirmed"])
        StaticDevice.objects.filter(user=dispositivo.user).delete()
        recuperacao = StaticDevice.objects.create(
            user=dispositivo.user, name=NOME_RECUPERACAO, confirmed=True
        )
        codigos = [_codigo_de_recuperacao() for _ in range(QUANTOS_CODIGOS_DE_RECUPERACAO)]
        StaticToken.objects.bulk_create(
            [StaticToken(device=recuperacao, token=codigo) for codigo in codigos]
        )
    return codigos


def codigos_restantes(usuario: Usuario) -> int:
    return int(StaticToken.objects.filter(device__user=usuario, device__confirmed=True).count())


def conferir_codigo(
    usuario: Usuario, *, codigo: str = "", codigo_recuperacao: str = "", confirmando: bool = False
) -> TOTPDevice | None:
    """O dispositivo que aceitou o código, ou `None`. `confirmando` usa o ainda não confirmado."""
    if codigo_recuperacao:
        recuperacao = StaticDevice.objects.filter(user=usuario, confirmed=True).first()
        if recuperacao is not None and recuperacao.verify_token(codigo_recuperacao.strip()):
            return autenticador_confirmado(usuario)
        return None
    dispositivo = TOTPDevice.objects.filter(user=usuario, confirmed=not confirmando).first()
    if dispositivo is not None and codigo and dispositivo.verify_token(codigo.strip()):
        return dispositivo
    return None


# --- Bloqueio (PLT-08) ---


def _erro_de_bloqueio(usuario: Usuario) -> MuitasTentativas:
    if usuario.bloqueado_ate is None:
        raise ValueError("Usuário sem bloqueio.")
    return MuitasTentativas(
        "PLT-08",
        "Acesso bloqueado por 15 minutos depois de 3 códigos errados",
        {"tentar_de_novo_em": usuario.bloqueado_ate.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
    )


def conferir_bloqueio(usuario: Usuario) -> None:
    """429 enquanto o bloqueio vale, mesmo com o código certo."""
    if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > relogio.agora():
        raise _erro_de_bloqueio(usuario)


def registrar_codigo_errado(usuario: Usuario) -> None:
    """Conta o erro; no 3º, bloqueia, grava o evento de segurança e levanta 429."""
    agora = relogio.agora()
    with transaction.atomic():
        atual = Usuario.objects.select_for_update().get(pk=usuario.pk)
        if atual.bloqueado_ate is not None and atual.bloqueado_ate <= agora:
            atual.bloqueado_ate = None
            atual.tentativas_erradas = 0
        atual.tentativas_erradas += 1
        bloqueou = atual.tentativas_erradas >= CODIGOS_ERRADOS_PARA_BLOQUEAR
        if bloqueou:
            atual.tentativas_erradas = 0
            atual.bloqueado_ate = agora + TEMPO_DE_BLOQUEIO
        atual.save(update_fields=["tentativas_erradas", "bloqueado_ate", "atualizado_em"])
        if bloqueou:
            registrar_evento(
                "usuario.bloqueado",
                Categoria.SEGURANCA,
                objeto=atual,
                depois={"bloqueado_ate": atual.bloqueado_ate},
                motivo="3 códigos de verificação errados",
                regra="PLT-08",
            )
    if bloqueou:
        raise _erro_de_bloqueio(atual)


def zerar_tentativas(usuario: Usuario) -> None:
    if usuario.tentativas_erradas or usuario.bloqueado_ate:
        usuario.tentativas_erradas = 0
        usuario.bloqueado_ate = None
        usuario.save(update_fields=["tentativas_erradas", "bloqueado_ate", "atualizado_em"])
