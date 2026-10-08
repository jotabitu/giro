"""Sessões revogáveis (ADR 0014, item 1; USR-04, USR-06) e a rotação do refresh (P-07 da T-057).

- O login completo abre a sessão; access e refresh levam o `sid`.
- A sessão acaba com 12 h sem uso no desktop e 30 dias no celular, contados de `ultimo_uso`,
  que muda no `renovar` e, no máximo a cada 5 minutos, nas requisições.
- A autenticação confere a sessão a cada requisição, com cache de até 30 s por `sid`, apagado
  na revogação: revogar derruba o access na requisição seguinte.
- Cada sessão guarda o `jti` do refresh vigente. Um refresh da sessão que não é o vigente (usado
  de novo, roubado ou duas renovações ao mesmo tempo) revoga a sessão inteira.
"""

import ipaddress
import re
from datetime import datetime, timedelta
from typing import Any

from django.core.cache import cache
from django.db import transaction
from rest_framework.request import Request
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from comum import relogio
from comum.auditoria import Categoria, ator_atual, registrar_evento
from comum.autenticacao import (
    CLAIM_AMR,
    CLAIM_SESSAO,
    emitir_tokens,
    refresh_do_cookie,
    registrar_sessoes,
)
from comum.erros import NaoAutenticado

from .models import DURACAO_DA_SESSAO, MotivoRevogacao, Sessao, TipoSessao, Usuario

CACHE_DA_SESSAO = timedelta(seconds=30)
ATUALIZAR_ULTIMO_USO = timedelta(minutes=5)


def sessao_encerrada() -> NaoAutenticado:
    return NaoAutenticado("sessao_encerrada", "Sua sessão terminou. Entre de novo.")


def _chave_do_cache(sid: int) -> str:
    return f"contas:sessao:{sid}"


# --- Aparelho e IP para a lista de sessões ---

_NAVEGADORES = (
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("Chrome/", "Chrome"),
    ("Firefox/", "Firefox"),
    ("Safari/", "Safari"),
)
_SISTEMAS = (
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Windows", "Windows"),
    ("Mac OS", "Mac"),
    ("Linux", "Linux"),
)


def resumir_aparelho(user_agent: str) -> str:
    """ "Chrome no Windows". Sem reconhecer, os primeiros 60 caracteres."""
    navegador = next((nome for marca, nome in _NAVEGADORES if marca in user_agent), "")
    sistema = next((nome for marca, nome in _SISTEMAS if marca in user_agent), "")
    if navegador and sistema:
        return f"{navegador} no {sistema}"
    return navegador or sistema or re.sub(r"\s+", " ", user_agent)[:60]


def mascarar_ip(ip: str | None) -> str | None:
    """IPv4 pela rede /24 (`177.12.34.0/24`); IPv6 pelo /64."""
    if not ip:
        return None
    endereco = ipaddress.ip_address(ip)
    prefixo = 24 if endereco.version == 4 else 64
    return str(ipaddress.ip_network((endereco, prefixo), strict=False))


# --- Interface registrada em `comum.autenticacao` ---


class SessoesDoGiro:
    def abrir(self, usuario: Any, tipo: str) -> int:
        tipo = tipo if tipo in TipoSessao.values else TipoSessao.DESKTOP
        agora = relogio.agora()
        ator = ator_atual()
        sessao = Sessao.objects.create(
            usuario=usuario,
            tipo=tipo,
            aparelho=resumir_aparelho(ator.aparelho or ""),
            ip=ator.ip,
            ultimo_uso=agora,
            expira_em=agora + DURACAO_DA_SESSAO[tipo],
        )
        return int(sessao.pk)

    def vincular(self, sid: int, jti: str) -> None:
        Sessao.objects.filter(pk=sid).update(refresh_jti=jti)

    def conferir(self, sid: int, usuario_id: Any) -> None:
        agora = relogio.agora()
        valida_ate = cache.get(_chave_do_cache(sid))
        if isinstance(valida_ate, float) and valida_ate > agora.timestamp():
            return
        sessao = Sessao.objects.filter(pk=sid, usuario_id=usuario_id).first()
        if sessao is None or not sessao.ativa_em(agora):
            if sessao is not None:
                _marcar_expirada(sessao, agora)
            raise sessao_encerrada()
        if agora - sessao.ultimo_uso >= ATUALIZAR_ULTIMO_USO:
            _usar(sessao, agora)
        valida = min(agora + CACHE_DA_SESSAO, sessao.expira_em)
        cache.set(_chave_do_cache(sid), valida.timestamp(), CACHE_DA_SESSAO.total_seconds())


def registrar() -> None:
    registrar_sessoes(SessoesDoGiro())


def _usar(sessao: Sessao, agora: datetime) -> None:
    sessao.ultimo_uso = agora
    sessao.expira_em = agora + sessao.duracao
    Sessao.objects.filter(pk=sessao.pk, revogada_em__isnull=True).update(
        ultimo_uso=sessao.ultimo_uso, expira_em=sessao.expira_em
    )


def _marcar_expirada(sessao: Sessao, agora: datetime) -> None:
    """Sessão vencida por falta de uso fica registrada como `expirou` (sem evento: ninguém agiu)."""
    if sessao.revogada_em is None and sessao.expira_em <= agora:
        Sessao.objects.filter(pk=sessao.pk, revogada_em__isnull=True).update(
            revogada_em=agora, motivo_revogacao=MotivoRevogacao.EXPIROU
        )


# --- Revogar ---


def _bloquear_refresh(jti: str) -> None:
    token = OutstandingToken.objects.filter(jti=jti).first()
    if token is not None:
        BlacklistedToken.objects.get_or_create(token=token)


def revogar(sessao: Sessao, motivo: str, por: Usuario | None = None) -> None:
    """Revoga a sessão, bloqueia o refresh vigente e grava o evento de segurança."""
    if sessao.revogada_em is not None:
        return
    with transaction.atomic():
        sessao.revogada_em = relogio.agora()
        sessao.motivo_revogacao = motivo
        sessao.revogada_por = por
        sessao.save(
            update_fields=["revogada_em", "motivo_revogacao", "revogada_por", "atualizado_em"]
        )
        if sessao.refresh_jti:
            _bloquear_refresh(sessao.refresh_jti)
        registrar_evento(
            "sessao.encerrar",
            Categoria.SEGURANCA,
            objeto=sessao,
            depois={"motivo_revogacao": motivo},
            motivo=MotivoRevogacao(motivo).label,
            regra="USR-04" if motivo == MotivoRevogacao.USUARIO_DESATIVADO else "USR-06",
        )
    transaction.on_commit(lambda: cache.delete(_chave_do_cache(int(sessao.pk))))
    cache.delete(_chave_do_cache(int(sessao.pk)))


def ativas(usuario: Usuario) -> Any:
    return Sessao.objects.filter(
        usuario=usuario, revogada_em__isnull=True, expira_em__gt=relogio.agora()
    ).order_by("-ultimo_uso")


def revogar_todas(
    usuario: Usuario, motivo: str, *, por: Usuario | None = None, exceto: int | None = None
) -> int:
    """Revoga as sessões ativas da pessoa (menos `exceto`). Devolve quantas."""
    quantas = 0
    with transaction.atomic():
        for sessao in ativas(usuario).exclude(pk=exceto).select_for_update():
            revogar(sessao, motivo, por)
            quantas += 1
    return quantas


# --- Renovar e sair ---


def renovar(request: Request) -> tuple[Usuario, RefreshToken]:
    """Rotação do refresh do cookie, com a sessão travada (P-07).

    Devolve a pessoa e o refresh novo. O refresh que não é o vigente da sessão revoga a sessão.
    """
    conteudo = refresh_do_cookie(request)
    sid = int(conteudo[CLAIM_SESSAO])
    jti = str(conteudo.get(api_settings.JTI_CLAIM, ""))
    usuario_id = int(conteudo.get(api_settings.USER_ID_CLAIM) or 0)
    agora = relogio.agora()
    reuso = False
    with transaction.atomic():
        sessao = (
            Sessao.objects.select_for_update()
            .select_related("usuario")
            .filter(pk=sid, usuario_id=usuario_id)
            .first()
        )
        if sessao is None:
            raise NaoAutenticado("nao_autenticado", "Entre de novo.")
        if not sessao.ativa_em(agora):
            _marcar_expirada(sessao, agora)
            raise sessao_encerrada()
        if not jti or jti != sessao.refresh_jti:
            revogar(sessao, MotivoRevogacao.REFRESH_REUSADO)
            reuso = True
        else:
            usuario = sessao.usuario
            if not usuario.is_active:
                raise NaoAutenticado("nao_autenticado", "Entre de novo.")
            _bloquear_refresh(jti)
            _usar(sessao, agora)
            novo = emitir_tokens(usuario, conteudo.get(CLAIM_AMR, []), sid=sessao.pk)
    if reuso:  # a revogação fica gravada; só depois responde 401
        raise sessao_encerrada()
    return usuario, novo


def sair(request: Request) -> None:
    """Revoga a sessão do cookie (`saiu`). Cookie inválido ou de outra empresa: nada a fazer."""
    try:
        conteudo = refresh_do_cookie(request)
    except NaoAutenticado:
        return
    sessao = Sessao.objects.filter(
        pk=conteudo[CLAIM_SESSAO], usuario_id=int(conteudo.get(api_settings.USER_ID_CLAIM) or 0)
    ).first()
    if sessao is not None:
        revogar(sessao, MotivoRevogacao.SAIU)


def sid_da_requisicao(request: Request) -> int | None:
    token = getattr(request, "auth", None)
    sid = token.get(CLAIM_SESSAO) if token is not None else None
    return sid if isinstance(sid, int) else None
