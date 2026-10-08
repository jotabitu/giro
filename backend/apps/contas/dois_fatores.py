"""Verificação em 2 etapas e bloqueio por códigos errados (PLT-08; ADR 0013, item 3).

Autenticador: `TOTPDevice` do django-otp. Códigos de recuperação: `StaticDevice` com 8 códigos
de uso único. 3 códigos ou 5 senhas errados seguidos bloqueiam por 15 minutos e geram evento
de segurança na auditoria do schema (o `public`, para a equipe da plataforma). A API e o
Django Admin entram pelos mesmos `tentar_entrar` e `verificar_codigo`.
"""

import secrets
from dataclasses import dataclass, replace
from datetime import UTC, timedelta
from enum import StrEnum

from django.db import transaction
from django.http import HttpRequest
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from comum import relogio
from comum.auditoria import Categoria, TipoAtor, registrar_evento, usar_ator
from comum.erros import MuitasTentativas
from comum.middleware import ator_da_requisicao

from .models import Usuario

CODIGOS_ERRADOS_PARA_BLOQUEAR = 3
SENHAS_ERRADAS_PARA_BLOQUEAR = 5  # decisão de 08/10 (P-03 da T-057), como no USR-06
TEMPO_DE_BLOQUEIO = timedelta(minutes=15)
QUANTOS_CODIGOS_DE_RECUPERACAO = 8
NOME_AUTENTICADOR = "autenticador"
NOME_RECUPERACAO = "recuperacao"


def auditar_entrada(
    request: HttpRequest, acao: str, usuario: Usuario | None, motivo: str = ""
) -> None:
    """`usuario.entrar` e `usuario.entrar_falhou`, com IP e aparelho (API e Django Admin)."""
    ator = ator_da_requisicao(request)
    if usuario is not None and acao == "usuario.entrar":
        ator = replace(ator, tipo=TipoAtor.USUARIO, id=usuario.pk, nome=usuario.nome)
    with usar_ator(ator):
        registrar_evento(acao, Categoria.SEGURANCA, objeto=usuario, motivo=motivo, regra="PLT-08")


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
#
# Bloqueio, verificação e contagem rodam numa transação só, que começa travando a linha do
# usuário (P-02 da T-057): tentativas simultâneas da mesma conta passam uma de cada vez, e
# nenhuma verifica senha ou código depois de o limite ser atingido.


class Falha(StrEnum):
    SENHA = "senha"
    CODIGO = "codigo"


@dataclass
class Tentativa:
    """Resultado de uma tentativa. Sem `falha`, a pessoa passou (com `dispositivo`, se tem 2FA)."""

    usuario: Usuario
    dispositivo: TOTPDevice | None = None
    falha: Falha | None = None
    bloqueio: MuitasTentativas | None = None


def _bloqueado_por_senha(usuario: Usuario) -> bool:
    return usuario.senhas_erradas >= SENHAS_ERRADAS_PARA_BLOQUEAR


def _erro_de_bloqueio(usuario: Usuario) -> MuitasTentativas:
    if usuario.bloqueado_ate is None:
        raise ValueError("Usuário sem bloqueio.")
    motivo = "5 senhas erradas" if _bloqueado_por_senha(usuario) else "3 códigos errados"
    return MuitasTentativas(
        "PLT-08",
        f"Acesso bloqueado por 15 minutos depois de {motivo}",
        {"tentar_de_novo_em": usuario.bloqueado_ate.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")},
    )


def conferir_bloqueio(usuario: Usuario) -> None:
    """429 enquanto o bloqueio vale, mesmo com o código certo. Use sobre a linha travada."""
    if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > relogio.agora():
        raise _erro_de_bloqueio(usuario)


def _travar(usuario: Usuario) -> Usuario:
    """A linha do usuário travada até o fim da transação; bloqueio vencido volta a zero."""
    atual: Usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if atual.bloqueado_ate is not None and atual.bloqueado_ate <= relogio.agora():
        atual.bloqueado_ate = None
        atual.tentativas_erradas = 0
        atual.senhas_erradas = 0
    conferir_bloqueio(atual)
    return atual


def _contar(atual: Usuario, falha: Falha | None) -> MuitasTentativas | None:
    """Grava a contagem na linha travada. No limite, bloqueia e grava o evento de segurança."""
    if falha is None:
        atual.tentativas_erradas = 0
        atual.senhas_erradas = 0
        atual.bloqueado_ate = None
    elif falha == Falha.SENHA:
        atual.senhas_erradas += 1
    else:
        atual.tentativas_erradas += 1
    bloqueou = (
        atual.senhas_erradas >= SENHAS_ERRADAS_PARA_BLOQUEAR
        or atual.tentativas_erradas >= CODIGOS_ERRADOS_PARA_BLOQUEAR
    )
    if bloqueou:
        atual.bloqueado_ate = relogio.agora() + TEMPO_DE_BLOQUEIO
    atual.save(
        update_fields=["tentativas_erradas", "senhas_erradas", "bloqueado_ate", "atualizado_em"]
    )
    if not bloqueou:
        return None
    registrar_evento(
        "usuario.bloqueado",
        Categoria.SEGURANCA,
        objeto=atual,
        depois={"bloqueado_ate": atual.bloqueado_ate},
        motivo=(
            "5 senhas erradas"
            if _bloqueado_por_senha(atual)
            else "3 códigos de verificação errados"
        ),
        regra="PLT-08",
    )
    return _erro_de_bloqueio(atual)


def tentar_entrar(
    usuario: Usuario, *, senha: str, codigo: str = "", codigo_recuperacao: str = ""
) -> Tentativa:
    """Senha e, para quem tem autenticador, código, com a linha do usuário travada.

    Bloqueado: levanta 429 antes de olhar a senha. Quem tem autenticador e não mandou código
    falha como senha errada, para a resposta não dizer que a senha estava certa (P-03).
    """
    with transaction.atomic():
        atual = _travar(usuario)
        dispositivo = None
        if not atual.check_password(senha):
            falha: Falha | None = Falha.SENHA
        elif not tem_2fa(atual):
            falha = None
        elif not codigo and not codigo_recuperacao:
            falha = Falha.SENHA
        else:
            dispositivo = conferir_codigo(
                atual, codigo=codigo, codigo_recuperacao=codigo_recuperacao
            )
            falha = None if dispositivo is not None else Falha.CODIGO
        bloqueio = _contar(atual, falha)
    return Tentativa(atual, dispositivo, falha, bloqueio)


def verificar_codigo(usuario: Usuario, *, codigo: str, confirmando: bool = False) -> Tentativa:
    """Só o código (etapa `pre_2fa`), com a mesma trava e a mesma contagem."""
    with transaction.atomic():
        atual = _travar(usuario)
        dispositivo = conferir_codigo(atual, codigo=codigo, confirmando=confirmando)
        falha = None if dispositivo is not None else Falha.CODIGO
        bloqueio = _contar(atual, falha)
    return Tentativa(atual, dispositivo, falha, bloqueio)
