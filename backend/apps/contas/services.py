"""Convites, usuários e senha (USR-01, USR-03, USR-04, USR-06, PLT-03, PLT-08, PLT-09). Único
lugar que cria usuário e muda status.

Cada pessoa tem um convite valendo por vez: um convite novo, reenviado ou aceito invalida os
anteriores (P-06 da T-057). O token vai no fragmento do link (`/convite#<token>`) e chega à API
só no corpo (P-09, T-072).

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
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework import status

from comum import relogio
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.conexao import schema_atual
from comum.erros import Conflito, ErroDeNegocio, ErroDeRegra, ErroDeValidacao
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
    """O token no fragmento: não chega ao servidor nem ao proxy (P-09)."""
    return f"https://{host}/convite#{token}"


def host_da_empresa(schema_name: str) -> str:
    """O domínio principal da empresa, o mesmo do link do e-mail."""
    from django_tenants.utils import get_public_schema_name, schema_context

    from apps.plataforma.models import Dominio

    with schema_context(get_public_schema_name()):
        dominio = Dominio.objects.get(tenant__schema_name=schema_name, is_primary=True)
        return str(dominio.domain)


def _invalidar_convites(usuario: Usuario, exceto: int | None = None) -> None:
    """P-06: os outros convites da pessoa vencem agora (o link antigo responde 410)."""
    agora = relogio.agora()
    convites = Convite.objects.filter(usuario=usuario, expira_em__gt=agora)
    if exceto is not None:
        convites = convites.exclude(pk=exceto)
    convites.update(expira_em=agora, atualizado_em=agora)


def criar_convite(usuario: Usuario, enviado_por: Usuario | None = None) -> tuple[Convite, str]:
    """Convite novo de 7 dias, que invalida os anteriores (P-06). Devolve o token em claro uma
    vez; o banco guarda o hash."""
    _invalidar_convites(usuario)
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


# --- Convite da empresa (USR-01, PLT-03) ---

EMAIL_EM_USO = ("email_em_uso", "Já existe um usuário com este e-mail")


def _so_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


def _conferir_celular(celular: str, erros: dict[str, list[str]]) -> str:
    digitos = _so_digitos(celular)
    if celular and len(digitos) not in (10, 11):
        erros["celular"] = ["Informe o celular com DDD."]
    return digitos


def _definir_filiais(usuario: Usuario, filiais: list[int]) -> None:
    """O app `filiais` grava o vínculo na mesma transação (contrato de contas; ADR 0011)."""
    from comum.eventos import publicar

    publicar("contas.filiais_do_usuario_definidas", usuario_id=usuario.pk, filiais_ids=filiais)


def convidar(
    *,
    email: str,
    perfil: str,
    filiais: list[int] | None = None,
    nome: str = "",
    celular: str = "",
    permissoes_extras: list[str] | None = None,
    por: Usuario | None = None,
    marca_equipe: bool = True,
) -> Usuario:
    """Pessoa `convite_pendente` e convite de 7 dias, enviado depois do commit por e-mail e, com
    celular, por WhatsApp (USR-01). Conta no limite do plano (PLT-03). O primeiro convite marca o
    passo `equipe` da implantação, mesmo sem aceite (IMP-07)."""
    from apps.plataforma.services import atualizar_uso, exigir_limite, registrar_passo_implantacao

    email = email.strip().lower()
    filiais = sorted(set(filiais or []))
    erros: dict[str, list[str]] = {}
    if perfil != Perfil.ADMINISTRADOR and not filiais:
        erros["filiais"] = ["Escolha ao menos uma filial."]
    celular = _conferir_celular(celular, erros)
    if erros:
        raise ErroDeValidacao(erros)
    with transaction.atomic():
        if Usuario.objects.filter(email__iexact=email).exists():
            raise Conflito(*EMAIL_EM_USO)
        exigir_limite("usuarios")
        usuario = Usuario(
            email=email,
            nome=nome.strip() or email.split("@")[0],
            celular=celular,
            perfil=perfil,
            permissoes_extras=sorted(set(permissoes_extras or [])),
            status=StatusUsuario.CONVITE_PENDENTE,
        )
        usuario.set_unusable_password()
        usuario.full_clean(exclude=["password"], validate_unique=False, validate_constraints=False)
        try:
            with transaction.atomic():
                usuario.save()
        except IntegrityError as erro:  # o mesmo e-mail, ao mesmo tempo
            raise Conflito(*EMAIL_EM_USO) from erro
        registrar_evento(
            "usuario.convidar",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois=retrato(usuario),
            regra="USR-01",
        )
        if perfil != Perfil.ADMINISTRADOR:
            _definir_filiais(usuario, filiais)
        convite, _ = criar_convite(usuario, enviado_por=por)
        atualizar_uso("usuarios", 1)  # convite pendente conta no limite (USR-01)
        if marca_equipe:
            registrar_passo_implantacao("equipe")
        _enviar_depois_do_commit(convite)
    return usuario


def convidar_administrador(nome: str, email: str, celular: str = "") -> Convite:
    """Administrador da compra (PLT-01), no schema da empresa nova: o mesmo convite, sem quem
    convidou. Ao ficar `ativo`, marca o passo `conta` da implantação; o passo `equipe` não conta
    este convite (IMP-07)."""
    usuario = convidar(
        email=email, nome=nome, celular=celular, perfil=Perfil.ADMINISTRADOR, marca_equipe=False
    )
    return Convite.objects.filter(usuario=usuario).latest("criado_em")


def _enviar_depois_do_commit(convite: Convite) -> None:
    from .tasks import contas_enviar_convite

    schema = schema_atual()
    transaction.on_commit(lambda: contas_enviar_convite.delay(schema, convite.pk))


def _travar(usuario: Usuario) -> Usuario:
    """Relê a pessoa com a linha travada: o status conferido é o que vai mudar."""
    travado: Usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    return travado


def gerar_link_convite(
    usuario: Usuario,
    por: Usuario,
    mensagem: str = "Só dá para copiar o link de um convite pendente.",
) -> tuple[Usuario, Convite, str]:
    """Só `convite_pendente` (vencido ou não): convite novo de 7 dias, que invalida todos os
    anteriores (o do e-mail, o do reenvio e os links copiados), sem mudar o status nem o plano.
    Devolve o token em claro uma vez (USR-01, P-06). Chamar dentro de uma transação."""
    usuario = _travar(usuario)
    if usuario.status != StatusUsuario.CONVITE_PENDENTE:
        raise Conflito("transicao_usuario", mensagem)
    convite, token = criar_convite(usuario, enviado_por=por)
    return usuario, convite, token


def reenviar_convite(usuario: Usuario, por: Usuario) -> Usuario:
    """Só `convite_pendente`: convite novo de 7 dias pelos mesmos canais; o link anterior deixa
    de valer (P-06)."""
    with transaction.atomic():
        usuario, convite, _ = gerar_link_convite(
            usuario, por, "Só um convite pendente pode ser reenviado."
        )
        registrar_evento(
            "usuario.reenviar_convite", Categoria.SEGURANCA, objeto=usuario, regra="USR-01"
        )
        _enviar_depois_do_commit(convite)
    return usuario


def copiar_link_convite(usuario: Usuario, por: Usuario) -> tuple[Usuario, Convite, str]:
    """ "Copiar link do convite" (USR-01, T-250): o link novo sai só na resposta, sem e-mail nem
    WhatsApp. O evento leva o novo vencimento, nunca o link nem o token."""
    with transaction.atomic():
        usuario, convite, token = gerar_link_convite(usuario, por)
        registrar_evento(
            "usuario.copiar_link_convite",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois={"convite_expira_em": convite.expira_em.isoformat()},
            regra="USR-01",
        )
    return usuario, convite, token


def cancelar_convite(usuario: Usuario, por: Usuario) -> Usuario:
    """Só `convite_pendente`: a pessoa vai para `desativado` e sai do plano."""
    from apps.plataforma.services import atualizar_uso

    with transaction.atomic():
        usuario = _travar(usuario)
        if usuario.status != StatusUsuario.CONVITE_PENDENTE:
            raise Conflito("transicao_usuario", "Só um convite pendente pode ser cancelado.")
        transicionar(
            usuario, StatusUsuario.DESATIVADO, acao="usuario.cancelar_convite", regra="USR-01"
        )
        _invalidar_convites(usuario)
        _sessoes().revogar_todas(usuario, MotivoRevogacao.USUARIO_DESATIVADO, por=por)
        atualizar_uso("usuarios", -1)
    return usuario


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


def aceitar_convite(token: str, senha: str, nome: str | None = None) -> Usuario:
    """Cria a senha (e corrige o nome, na empresa). A pessoa continua `convite_pendente` até o
    `pronto`: na hora, sem 2 etapas, ou ao confirmar o código (USR-01, PLT-08). Os outros
    convites dela deixam de valer (P-06)."""
    with transaction.atomic():
        convite = convite_pelo_token(token)
        # Dois aceites ao mesmo tempo: o segundo espera e cai no 404 de convite usado.
        Convite.objects.select_for_update().filter(pk=convite.pk).get()
        convite = convite_pelo_token(token)
        usuario = convite.usuario
        if nome is not None and nome.strip():
            usuario.nome = nome.strip()
        validar_senha(senha, usuario, campo="senha")
        usuario.set_password(senha)
        usuario.save(update_fields=["nome", "password", "atualizado_em"])
        convite.aceito_em = relogio.agora()
        convite.save(update_fields=["aceito_em", "atualizado_em"])
        _invalidar_convites(usuario, exceto=convite.pk)
        registrar_evento(
            "usuario.aceitar_convite", Categoria.SEGURANCA, objeto=usuario, regra="USR-01"
        )
    return usuario


def ativar_depois_do_2fa(usuario: Usuario) -> None:
    """Convite aceito e, se exigido, código confirmado: a pessoa passa a `ativo`.

    O administrador da compra (convite sem quem convidou) marca o passo `conta` da implantação
    (IMP-05).
    """
    if usuario.status != StatusUsuario.CONVITE_PENDENTE:
        return
    transicionar(usuario, StatusUsuario.ATIVO, acao="usuario.ativar", regra="USR-01")
    if usuario.perfil == Perfil.ADMINISTRADOR and _administrador_da_compra(usuario):
        from apps.plataforma.services import registrar_passo_implantacao

        registrar_passo_implantacao("conta")


def _administrador_da_compra(usuario: Usuario) -> bool:
    aceito = (
        Convite.objects.filter(usuario=usuario, aceito_em__isnull=False)
        .order_by("-aceito_em")
        .first()
    )
    return aceito is not None and aceito.enviado_por_id is None


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


# --- Administração de usuários (USR-03, USR-04; tela Admin-Usuarios) ---

ULTIMO_ADMINISTRADOR = (
    "ultimo_administrador",
    "A empresa precisa de ao menos um administrador ativo",
)


def _conferir_outro_administrador(usuario: Usuario) -> None:
    """422 se `usuario` é o último administrador ativo. Trava os administradores: dois
    rebaixamentos ao mesmo tempo não deixam a empresa sem nenhum."""
    administradores = list(
        Usuario.objects.select_for_update()
        .filter(perfil=Perfil.ADMINISTRADOR, status=StatusUsuario.ATIVO)
        .values_list("pk", flat=True)
    )
    if set(administradores) <= {usuario.pk}:
        raise ErroDeRegra(*ULTIMO_ADMINISTRADOR)


def alterar_usuario(
    usuario: Usuario,
    *,
    por: Usuario,
    perfil: str | None = None,
    filiais: list[int] | None = None,
    permissoes_extras: list[str] | None = None,
) -> Usuario:
    """`PATCH /api/usuarios/{id}/`. Cada parte vai para a auditoria (`seguranca`) com antes e
    depois. O perfil novo que exige 2 etapas derruba os tokens sem `otp` (ADR 0013)."""
    with transaction.atomic():
        usuario = _travar(usuario)
        perfil_final = perfil or usuario.perfil
        if perfil is not None and perfil != usuario.perfil:
            if usuario.perfil == Perfil.ADMINISTRADOR and usuario.status == StatusUsuario.ATIVO:
                _conferir_outro_administrador(usuario)
            if (
                usuario.perfil == Perfil.ADMINISTRADOR
                and perfil != Perfil.ADMINISTRADOR
                and not filiais
            ):
                raise ErroDeValidacao({"filiais": ["Escolha ao menos uma filial."]})
            antes = usuario.perfil
            usuario.perfil = perfil
            usuario.save(update_fields=["perfil", "atualizado_em"])
            registrar_evento(
                "usuario.alterar_perfil",
                Categoria.SEGURANCA,
                objeto=usuario,
                antes={"perfil": antes},
                depois={"perfil": perfil},
                regra="USR-03",
            )
        if filiais is not None and perfil_final != Perfil.ADMINISTRADOR:
            if not filiais:
                raise ErroDeValidacao({"filiais": ["Escolha ao menos uma filial."]})
            _definir_filiais(usuario, sorted(set(filiais)))
        if permissoes_extras is not None:
            novas = sorted(set(permissoes_extras))
            antes_extras = sorted(usuario.permissoes_extras)
            if novas != antes_extras:
                usuario.permissoes_extras = novas
                usuario.save(update_fields=["permissoes_extras", "atualizado_em"])
                registrar_evento(
                    "usuario.alterar_permissoes",
                    Categoria.SEGURANCA,
                    objeto=usuario,
                    antes={"permissoes_extras": antes_extras},
                    depois={"permissoes_extras": novas},
                    regra="USR-03",
                )
    return usuario


def desativar_usuario(usuario: Usuario, *, por: Usuario, motivo: str = "") -> Usuario:
    """USR-04: na mesma transação revoga as sessões (a pessoa sai na requisição seguinte) e
    tira do plano. O histórico continua."""
    from apps.plataforma.services import atualizar_uso

    if usuario.pk == por.pk:
        raise ErroDeRegra(
            "desativar_a_si_mesmo", "Peça a outro administrador para desativar seu acesso"
        )
    with transaction.atomic():
        usuario = _travar(usuario)
        if usuario.perfil == Perfil.ADMINISTRADOR and usuario.status == StatusUsuario.ATIVO:
            _conferir_outro_administrador(usuario)
        transicionar(
            usuario,
            StatusUsuario.DESATIVADO,
            acao="usuario.desativar",
            motivo=motivo,
            regra="USR-04",
        )
        _invalidar_convites(usuario)
        _sessoes().revogar_todas(usuario, MotivoRevogacao.USUARIO_DESATIVADO, por=por)
        atualizar_uso("usuarios", -1)
    return usuario


def ja_foi_ativo(usuario: Usuario) -> bool:
    """USR-04: a pessoa já chegou a `ativo`. Quem nunca teve convite foi criada já ativa (seed,
    `createsuperuser`); quem teve convite precisa de uma transição para `ativo` na auditoria
    (`usuario.ativar` ou `usuario.reativar`)."""
    from apps.auditoria.models import EventoAuditoria

    if not Convite.objects.filter(usuario=usuario).exists():
        return True
    return bool(
        EventoAuditoria.objects.filter(
            objeto_tipo=Usuario._meta.model_name,
            objeto_id=usuario.pk,
            depois__status=StatusUsuario.ATIVO,
        ).exists()
    )


def reativar_usuario(usuario: Usuario, *, por: Usuario) -> Usuario:
    """USR-04: quem já foi `ativo` volta `ativo`; quem nunca chegou a `ativo` (convite
    cancelado, mesmo com a senha criada) volta para `convite_pendente`, com convite novo de 7
    dias pelos mesmos canais (USR-01). Nos dois casos volta a contar no plano (422 `PLT-03` no
    limite, sem convite)."""
    from apps.plataforma.services import atualizar_uso, exigir_limite

    with transaction.atomic():
        usuario = _travar(usuario)
        if usuario.status != StatusUsuario.DESATIVADO:
            raise Conflito("transicao_usuario", "Só um usuário desativado pode ser reativado.")
        exigir_limite("usuarios")
        if ja_foi_ativo(usuario):
            transicionar(usuario, StatusUsuario.ATIVO, acao="usuario.reativar", regra="USR-04")
        else:
            transicionar(
                usuario,
                StatusUsuario.CONVITE_PENDENTE,
                acao="usuario.reativar_convite",
                regra="USR-04",
            )
            # O link novo cria a senha: a anterior, se havia, deixa de valer.
            usuario.set_unusable_password()
            usuario.save(update_fields=["password", "atualizado_em"])
            convite, _ = criar_convite(usuario, enviado_por=por)
            _enviar_depois_do_commit(convite)
        atualizar_uso("usuarios", 1)
    return usuario


def redefinir_2fa(usuario: Usuario, *, por: Usuario, motivo: str) -> Usuario:
    """Apaga autenticador e códigos e encerra as sessões; no próximo login a pessoa configura
    de novo, se o perfil exigir (USR-02). Para quem perdeu o celular e os códigos."""
    from .dois_fatores import remover_2fa

    with transaction.atomic():
        usuario = _travar(usuario)
        remover_2fa(usuario)
        registrar_evento(
            "usuario.redefinir_2fa",
            Categoria.SEGURANCA,
            objeto=usuario,
            motivo=motivo,
            regra="USR-02",
        )
        _sessoes().revogar_todas(usuario, MotivoRevogacao.REVOGADA_PELO_ADMINISTRADOR, por=por)
    return usuario


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
