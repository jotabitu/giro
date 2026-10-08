"""Convites e usuários (USR-01, PLT-08, PLT-09). Único lugar que cria usuário e muda status.

O token do convite nunca vai para a fila do Celery: a tarefa de envio recebe só o id do
convite e gera o token na hora (o link anterior deixa de valer). O comando da equipe da
plataforma gera o token e imprime o link, sem e-mail.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import status

from comum import relogio
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.conexao import schema_atual
from comum.erros import Conflito, ErroDeNegocio, ErroDeValidacao
from comum.estados import transicionar

from .models import Convite, FuncaoPlataforma, Perfil, StatusUsuario, Usuario

VALIDADE_DO_CONVITE = timedelta(days=7)  # USR-01


class ConviteExpirado(ErroDeNegocio):
    status_http = status.HTTP_410_GONE

    def __init__(self) -> None:
        super().__init__("convite_expirado", "Este convite venceu. Peça um novo.")


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _novo_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_do_token(token)


def link_do_convite(host: str, token: str) -> str:
    return f"https://{host}/convite/{token}"


def criar_convite(usuario: Usuario, enviado_por: Usuario | None = None) -> tuple[Convite, str]:
    """Convite novo de 7 dias. Devolve o token em claro uma vez; o banco guarda o hash."""
    token, token_hash = _novo_token()
    convite = Convite.objects.create(
        usuario=usuario,
        token_hash=token_hash,
        expira_em=relogio.agora() + VALIDADE_DO_CONVITE,
        enviado_por=enviado_por,
    )
    return convite, token


def renovar_token(convite: Convite) -> str:
    """Token novo para o mesmo convite (usado no envio do e-mail)."""
    token, token_hash = _novo_token()
    convite.token_hash = token_hash
    convite.save(update_fields=["token_hash", "atualizado_em"])
    return token


def convite_pelo_token(token: str) -> Convite:
    """404 se não existe ou já foi usado; 410 se venceu (USR-01)."""
    convite = (
        Convite.objects.select_related("usuario")
        .filter(token_hash=hash_do_token(token), aceito_em__isnull=True)
        .first()
    )
    if convite is None or convite.usuario.status != StatusUsuario.CONVITE_PENDENTE:
        raise Http404
    if convite.expira_em <= relogio.agora():
        raise ConviteExpirado
    return convite


# --- Administrador da empresa nova (PLT-01, USR-01) ---


def convidar_administrador(nome: str, email: str, celular: str = "") -> Convite:
    """No schema da empresa: administrador `convite_pendente` e convite enviado após o commit."""
    from apps.plataforma.services import atualizar_uso

    with transaction.atomic():
        usuario = Usuario(
            email=email.strip().lower(),
            nome=nome.strip(),
            celular=celular,
            perfil=Perfil.ADMINISTRADOR,
            status=StatusUsuario.CONVITE_PENDENTE,
        )
        usuario.set_unusable_password()
        usuario.full_clean(exclude=["password"])
        usuario.save()
        registrar_evento(
            "usuario.convidar",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois=retrato(usuario),
            regra="USR-01",
        )
        convite, _ = criar_convite(usuario)
        atualizar_uso("usuarios", 1)  # convite pendente conta no limite (USR-01)
        _enviar_depois_do_commit(convite)
    return convite


def _enviar_depois_do_commit(convite: Convite) -> None:
    from .tasks import contas_enviar_convite

    schema = schema_atual()
    transaction.on_commit(lambda: contas_enviar_convite.delay(schema, convite.pk))


# --- Equipe da plataforma (PLT-08, PLT-09) ---


def host_da_plataforma() -> str:
    return f"{settings.SUBDOMINIO_PLATAFORMA}.{settings.DOMINIO_BASE}"


def convidar_equipe_plataforma(email: str, funcao: str, nome: str) -> tuple[Usuario, str]:
    """No public. Devolve a pessoa e o link do convite (o comando imprime)."""
    if funcao not in FuncaoPlataforma.values:
        raise ErroDeValidacao({"funcao": [f"Use uma destas: {', '.join(FuncaoPlataforma.values)}"]})
    email = email.strip().lower()
    with transaction.atomic():
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = Usuario(
                email=email,
                nome=nome.strip() or email,
                funcao_plataforma=funcao,
                status=StatusUsuario.CONVITE_PENDENTE,
            )
            usuario.set_unusable_password()
            usuario.full_clean(exclude=["password"])
            usuario.save()
            registrar_evento(
                "usuario.convidar", Categoria.SEGURANCA, objeto=usuario, depois=retrato(usuario)
            )
        elif usuario.status != StatusUsuario.CONVITE_PENDENTE:
            raise Conflito("transicao_usuario", "Esta pessoa já tem acesso.")
        _, token = criar_convite(usuario)
    return usuario, link_do_convite(host_da_plataforma(), token)


def aceitar_convite(token: str, senha: str) -> Usuario:
    """Cria a senha. A pessoa continua `convite_pendente` até confirmar o 2FA (PLT-08)."""
    with transaction.atomic():
        convite = convite_pelo_token(token)
        usuario = convite.usuario
        try:
            validate_password(senha, usuario)
        except ValidationError as erro:
            raise ErroDeValidacao({"senha": list(erro.messages)}) from erro
        usuario.set_password(senha)
        usuario.save(update_fields=["password", "atualizado_em"])
        convite.aceito_em = relogio.agora()
        convite.save(update_fields=["aceito_em", "atualizado_em"])
        registrar_evento("usuario.aceitar_convite", Categoria.SEGURANCA, objeto=usuario)
    return usuario


def ativar_depois_do_2fa(usuario: Usuario) -> None:
    """Convite aceito e código confirmado: a pessoa passa a `ativo`."""
    if usuario.status == StatusUsuario.CONVITE_PENDENTE:
        transicionar(usuario, StatusUsuario.ATIVO, acao="usuario.ativar")


def convite_aceito(usuario: Usuario) -> bool:
    return Convite.objects.filter(usuario=usuario, aceito_em__isnull=False).exists()
