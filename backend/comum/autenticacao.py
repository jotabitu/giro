"""JWT preso à empresa em que foi emitido (ADR 0008, item 5, e ADR 0013, itens 1, 3 e 5).

O mesmo `user_id` existe em várias empresas. Todo token leva as claims `schema` e `empresa_id`
(PK da empresa, nunca reusada) e só vale no host dessa empresa. `conferir_empresa` é o
único ponto de conferência: a autenticação usa, e renovar e sair também, antes de tocar na
blacklist. Tokens finais levam `amr` (`["pwd"]` ou `["pwd", "otp"]`); quem `exige_2fa` sem
`otp` recebe 401 `2fa_obrigatorio`. O token `pre_2fa` (5 min, sem refresh) só vale nas rotas
de 2 etapas. Sessões (`sid`) e o token de suporte entram com a T-011.
"""

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import RefreshToken, Token

from comum.conexao import conexao
from comum.erros import NaoAutenticado

CLAIM_SCHEMA = "schema"
CLAIM_EMPRESA = "empresa_id"
CLAIM_AMR = "amr"
AMR_SENHA = ("pwd",)
AMR_SENHA_E_CODIGO = ("pwd", "otp")

COOKIE_REFRESH = "__Host-giro_refresh"
CABECALHO_DO_FRONTEND = ("HTTP_X_REQUESTED_WITH", "giro")


def _empresa_atual() -> tuple[str, int | None]:
    tenant = getattr(conexao(), "tenant", None)
    return str(conexao().schema_name), getattr(tenant, "pk", None)


def _prender_a_empresa(token: Token) -> None:
    schema, empresa_id = _empresa_atual()
    if empresa_id is None:
        raise RuntimeError("Sem empresa na conexão: não é possível emitir token.")
    token[CLAIM_SCHEMA] = schema
    token[CLAIM_EMPRESA] = empresa_id


def emitir_tokens(usuario: AbstractBaseUser, amr: Iterable[str] = AMR_SENHA) -> RefreshToken:
    """Refresh (e o access derivado dele) com `schema`, `empresa_id` e `amr`."""
    schema, empresa_id = _empresa_atual()
    if empresa_id is None:
        raise RuntimeError("Sem empresa na conexão: não é possível emitir token.")
    refresh = RefreshToken.for_user(usuario)
    refresh[CLAIM_SCHEMA] = schema
    refresh[CLAIM_EMPRESA] = empresa_id
    refresh[CLAIM_AMR] = list(amr)
    return refresh


class TokenPre2FA(Token):
    """Senha certa, falta o código (ADR 0013, item 3). Só em `2fa/configurar` e `2fa/verificar`."""

    token_type = "pre_2fa"  # noqa: S105 - tipo do token, não segredo
    lifetime = timedelta(minutes=5)


def emitir_pre_2fa(usuario: AbstractBaseUser) -> TokenPre2FA:
    token = TokenPre2FA()
    token[api_settings.USER_ID_CLAIM] = getattr(usuario, api_settings.USER_ID_FIELD)
    _prender_a_empresa(token)
    return token


def conferir_empresa(token: Token | dict[str, Any]) -> None:
    """401 se faltar claim ou se o token for de outra empresa."""
    schema, empresa_id = _empresa_atual()
    if (
        token.get(CLAIM_SCHEMA) is None
        or token.get(CLAIM_EMPRESA) is None
        or token.get(CLAIM_SCHEMA) != schema
        or token.get(CLAIM_EMPRESA) != empresa_id
    ):
        raise AuthenticationFailed(
            "Este acesso não vale para esta empresa. Entre de novo.",
            code="nao_autenticado",
        )


class JWTDaEmpresa(JWTAuthentication):
    def get_user(self, validated_token: Token) -> Any:
        conferir_empresa(validated_token)
        # A classe-mãe busca o usuário no schema atual e recusa quem não está ativo (USR-04).
        usuario = super().get_user(validated_token)
        if getattr(usuario, "exige_2fa", False) and "otp" not in validated_token.get(CLAIM_AMR, []):
            raise NaoAutenticado("2fa_obrigatorio", "Confirme o código de verificação.")
        return usuario


class JWTPre2FA(JWTAuthentication):
    """Aceita só o token `pre_2fa`. Convite pendente passa (está configurando o 2FA)."""

    def get_validated_token(self, raw_token: bytes) -> Token:
        try:
            return TokenPre2FA(raw_token)  # type: ignore[arg-type]
        except TokenError as erro:
            raise InvalidToken({"detail": str(erro)}) from erro

    def get_user(self, validated_token: Token) -> Any:
        conferir_empresa(validated_token)
        usuario = (
            get_user_model()
            .objects.filter(pk=validated_token.get(api_settings.USER_ID_CLAIM))
            .exclude(status="desativado")
            .first()
        )
        if usuario is None:
            raise AuthenticationFailed("Entre de novo.", code="nao_autenticado")
        return usuario


# --- Refresh em cookie host-only (ADR 0013, item 5) ---


def gravar_cookie_refresh(resposta: HttpResponse, refresh: RefreshToken) -> None:
    resposta.set_cookie(
        COOKIE_REFRESH,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/",
        secure=True,
        httponly=True,
        samesite="Strict",
    )


def apagar_cookie_refresh(resposta: HttpResponse) -> None:
    resposta.delete_cookie(COOKIE_REFRESH, path="/", samesite="Strict")


def veio_do_frontend(request: Request) -> bool:
    chave, valor = CABECALHO_DO_FRONTEND
    return bool(request.META.get(chave) == valor)


def refresh_do_cookie(request: Request) -> RefreshToken:
    """Assinatura e validade primeiro, depois a empresa e só então a blacklist."""
    bruto = request.COOKIES.get(COOKIE_REFRESH)
    if not bruto:
        raise AuthenticationFailed("Entre de novo.", code="nao_autenticado")
    try:
        conteudo = token_backend.decode(bruto, verify=True)  # type: ignore[arg-type]
    except TokenError as erro:
        raise AuthenticationFailed("Entre de novo.", code="nao_autenticado") from erro
    if conteudo.get(api_settings.TOKEN_TYPE_CLAIM) != RefreshToken.token_type:
        raise AuthenticationFailed("Entre de novo.", code="nao_autenticado")
    conferir_empresa(conteudo)
    try:
        return RefreshToken(bruto)  # type: ignore[arg-type]
    except TokenError as erro:  # vencido ou na blacklist
        raise AuthenticationFailed("Entre de novo.", code="nao_autenticado") from erro
