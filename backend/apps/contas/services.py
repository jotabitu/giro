"""Convites, usuários e senha (USR-01, USR-06, PLT-08, PLT-09). Único lugar que cria usuário e
muda status.

O token do convite nunca vai para a fila do Celery: a tarefa de envio recebe só o id do
convite e gera o token na hora (o link anterior deixa de valer). O comando da equipe da
plataforma gera o token e imprime o link, sem e-mail.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import Any

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

from .models import (
    VALIDADE_DO_LINK_DE_SENHA,
    Convite,
    FuncaoPlataforma,
    MotivoRevogacao,
    Perfil,
    RedefinicaoSenha,
    StatusUsuario,
    Usuario,
)

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
        validar_senha(senha, usuario, campo="senha")
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


def convite_em_validade(usuario: Usuario) -> bool:
    """Convite aceito e ainda no prazo de 7 dias (P-05 da T-057).

    Só nesse prazo quem aceitou e ainda não confirmou o código cadastra o primeiro
    autenticador com a senha; depois, precisa de um convite novo.
    """
    return bool(
        Convite.objects.filter(
            usuario=usuario, aceito_em__isnull=False, expira_em__gt=relogio.agora()
        ).exists()
    )


def pode_configurar_2fa(usuario: Usuario) -> bool:
    """Ativo (2 etapas que passaram a ser exigidas) ou convite aceito dentro do prazo (P-05)."""
    if usuario.status == StatusUsuario.ATIVO:
        return True
    return usuario.status == StatusUsuario.CONVITE_PENDENTE and convite_em_validade(usuario)


# --- Senha (tela Acesso-Senha, "Esqueci a senha") ---

PEDIDOS_DE_SENHA_POR_HORA = 3
CONVITE_VENCIDO = "Este convite venceu. Peça um novo ao administrador."


def validar_senha(senha: str, usuario: Usuario, *, campo: str) -> None:
    """400 `validacao` com os textos prontos de `apps/contas/senhas.py`."""
    try:
        validate_password(senha, usuario)
    except ValidationError as erro:
        raise ErroDeValidacao({campo: list(erro.messages)}) from erro


def _sessoes() -> Any:
    from . import sessoes

    return sessoes


def trocar_senha(usuario: Usuario, senha_nova: str, *, sessao_atual: int | None) -> None:
    """A senha atual já foi conferida. As outras sessões da pessoa são encerradas."""
    validar_senha(senha_nova, usuario, campo="senha_nova")
    with transaction.atomic():
        usuario.set_password(senha_nova)
        usuario.save(update_fields=["password", "atualizado_em"])
        registrar_evento(
            "usuario.trocar_senha",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois={"password": "alterada"},
            regra="USR-06",
        )
        _sessoes().revogar_todas(usuario, MotivoRevogacao.SENHA_ALTERADA, exceto=sessao_atual)


def pedir_redefinicao(email: str) -> None:
    """Esqueci a senha: sempre em silêncio para quem chama (não revela quem tem conta).

    Só para conta ativa, no máximo 3 pedidos por e-mail por hora. O link sai depois do commit;
    a tarefa recebe só o id e gera o token na hora.
    """
    usuario = Usuario.objects.filter(
        email=email.strip().lower(), status=StatusUsuario.ATIVO
    ).first()
    if usuario is None:
        return
    agora = relogio.agora()
    with transaction.atomic():
        Usuario.objects.select_for_update().filter(pk=usuario.pk).first()
        recentes = RedefinicaoSenha.objects.filter(
            usuario=usuario, pedido_em__gt=agora - timedelta(hours=1)
        ).count()
        if recentes >= PEDIDOS_DE_SENHA_POR_HORA:
            return
        # Os links anteriores deixam de valer: só o mais novo serve.
        RedefinicaoSenha.objects.filter(usuario=usuario, usado_em__isnull=True).update(
            expira_em=agora
        )
        pedido = RedefinicaoSenha.objects.create(
            usuario=usuario,
            token_hash=_novo_token()[1],  # trocado pelo token do envio
            pedido_em=agora,
            expira_em=agora + VALIDADE_DO_LINK_DE_SENHA,
        )
        registrar_evento(
            "usuario.pedir_redefinicao_senha",
            Categoria.SEGURANCA,
            objeto=usuario,
            regra="USR-06",
        )
        from .tasks import contas_enviar_redefinicao_senha

        schema = schema_atual()
        transaction.on_commit(lambda: contas_enviar_redefinicao_senha.delay(schema, pedido.pk))


class LinkExpirado(ErroDeNegocio):
    status_http = status.HTTP_410_GONE

    def __init__(self) -> None:
        super().__init__("link_expirado", "Este link venceu. Peça outro.")


def renovar_token_de_senha(pedido: RedefinicaoSenha) -> str:
    token, token_hash = _novo_token()
    pedido.token_hash = token_hash
    pedido.save(update_fields=["token_hash", "atualizado_em"])
    return token


def redefinir_senha(token: str, senha_nova: str) -> Usuario:
    """Link de 1 hora e uso único. Encerra todas as sessões; as 2 etapas continuam valendo."""
    with transaction.atomic():
        pedido = (
            RedefinicaoSenha.objects.select_for_update()
            .select_related("usuario")
            .filter(token_hash=hash_do_token(token))
            .first()
        )
        if pedido is None:
            raise Http404
        if pedido.usado_em is not None or pedido.expira_em <= relogio.agora():
            raise LinkExpirado
        usuario = pedido.usuario
        if usuario.status != StatusUsuario.ATIVO:
            raise LinkExpirado
        validar_senha(senha_nova, usuario, campo="senha_nova")
        usuario.set_password(senha_nova)
        usuario.save(update_fields=["password", "atualizado_em"])
        pedido.usado_em = relogio.agora()
        pedido.save(update_fields=["usado_em", "atualizado_em"])
        registrar_evento(
            "usuario.redefinir_senha",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois={"password": "alterada"},
            regra="USR-06",
        )
        _sessoes().revogar_todas(usuario, MotivoRevogacao.SENHA_ALTERADA)
    return usuario


# --- Meus dados ---


def editar_meus_dados(usuario: Usuario, *, nome: str | None, celular: str | None) -> Usuario:
    """`PATCH /api/auth/eu/`: só nome e celular; e-mail e perfil não mudam por aqui."""
    from comum.auditoria import auditar

    campos: dict[str, list[str]] = {}
    if nome is not None and not nome.strip():
        campos["nome"] = ["Informe o nome."]
    digitos = "".join(c for c in (celular or "") if c.isdigit())
    if celular and len(digitos) not in (10, 11):
        campos["celular"] = ["Informe o celular com DDD."]
    if campos:
        raise ErroDeValidacao(campos)
    with auditar(usuario, "usuario.editar_meus_dados", Categoria.SEGURANCA):
        if nome is not None:
            usuario.nome = nome.strip()
        if celular is not None:
            usuario.celular = digitos
        usuario.save(update_fields=["nome", "celular", "atualizado_em"])
    return usuario
