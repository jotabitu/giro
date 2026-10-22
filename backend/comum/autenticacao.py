"""JWT preso à empresa em que foi emitido (ADR 0008, item 5, e ADR 0013, itens 1, 3 e 5).

O mesmo `user_id` existe em várias empresas. Todo token leva as claims `schema` e `empresa_id`
(PK da empresa, nunca reusada) e só vale no host dessa empresa. `conferir_empresa` é o
único ponto de conferência: a autenticação usa, e renovar e sair também, antes de tocar na
blacklist. Tokens finais levam `amr` (`["pwd"]` ou `["pwd", "otp"]`); quem `exige_2fa` sem
`otp` recebe 401 `2fa_obrigatorio`. O token `pre_2fa` (5 min, sem refresh) só vale nas rotas
de 2 etapas.

Sessões (ADR 0014, item 1): access e refresh levam `sid`. A sessão é do app `contas`, que fica
acima de `comum` (ADR 0011); ele registra `abrir`, `vincular` e `conferir` com
`registrar_sessoes` no `ready()`. Token sem `sid` não vale.

Suporte (ADR 0013, item 2; T-070): o token `suporte` não tem usuário nem refresh. A autenticação
monta um `AtorSuporte` em memória, confere o acesso no `public` (função registrada pelo app
`plataforma`) e aplica as regras de rota da view: "só ver" é uma lista de views marcadas.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpResponse
from django_tenants.utils import get_public_schema_name
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.tokens import RefreshToken, Token

from comum import relogio
from comum.conexao import conexao
from comum.erros import NaoAutenticado, SemPermissao

CLAIM_SCHEMA = "schema"
CLAIM_EMPRESA = "empresa_id"
CLAIM_AMR = "amr"
CLAIM_SESSAO = "sid"
CLAIM_APARELHO = "aparelho"
# Quando as 2 etapas foram confirmadas (segundos UTC). Só no login completo, nunca na rotação:
# ações sensíveis pedem a confirmação recente (backup completo, S-15; cancelar, T-199).
CLAIM_AUTH_TIME = "auth_time"
AMR_SENHA = ("pwd",)
AMR_SENHA_E_CODIGO = ("pwd", "otp")
DOIS_FATORES_RECENTE = timedelta(minutes=15)

COOKIE_REFRESH = "__Host-giro_refresh"
CABECALHO_DO_FRONTEND = ("HTTP_X_REQUESTED_WITH", "giro")


def token_da_requisicao(request: Request) -> dict[str, Any]:
    """As claims do token da requisição (vazio sem token)."""
    return dict(getattr(request.auth, "payload", None) or {})


def dois_fatores_recente(payload: dict[str, Any]) -> bool:
    """Token com `otp` no `amr` e `auth_time` de no máximo 15 minutos atrás. Quem pede: o backup
    completo (S-15) e o cancelamento da assinatura (T-199, M-01); sem ela, 403 `2fa_recente`."""
    if "otp" not in (payload.get(CLAIM_AMR) or []):
        return False
    momento = payload.get(CLAIM_AUTH_TIME)
    if not isinstance(momento, int | float):
        return False
    return relogio.agora().timestamp() - momento <= DOIS_FATORES_RECENTE.total_seconds()


def _empresa_atual() -> tuple[str, int | None]:
    tenant = getattr(conexao(), "tenant", None)
    return str(conexao().schema_name), getattr(tenant, "pk", None)


def _prender_a_empresa(token: Token) -> None:
    schema, empresa_id = _empresa_atual()
    if empresa_id is None:
        raise RuntimeError("Sem empresa na conexão: não é possível emitir token.")
    token[CLAIM_SCHEMA] = schema
    token[CLAIM_EMPRESA] = empresa_id


class Sessoes(Protocol):
    def abrir(self, usuario: Any, tipo: str) -> int:
        """Cria a sessão de um login completo e devolve o `sid`."""
        ...

    def vincular(self, sid: int, jti: str) -> None:
        """Guarda o `jti` do refresh vigente da sessão (P-07)."""
        ...

    def conferir(self, sid: int, usuario_id: Any) -> None:
        """401 `sessao_encerrada` se a sessão foi revogada ou expirou."""
        ...


_sessoes: Sessoes | None = None


def registrar_sessoes(sessoes: Sessoes) -> None:
    global _sessoes
    _sessoes = sessoes


def sessoes() -> Sessoes:
    if _sessoes is None:
        raise RuntimeError("O app contas não registrou as sessões.")
    return _sessoes


def emitir_tokens(
    usuario: AbstractBaseUser,
    amr: Iterable[str] = AMR_SENHA,
    *,
    tipo: str = "desktop",
    sid: int | None = None,
) -> RefreshToken:
    """Refresh (e o access derivado dele) com `schema`, `empresa_id`, `amr` e `sid`.

    Sem `sid`, abre uma sessão nova do `tipo` (login completo); com ele, é a rotação do refresh
    daquela sessão.
    """
    schema, empresa_id = _empresa_atual()
    if empresa_id is None:
        raise RuntimeError("Sem empresa na conexão: não é possível emitir token.")
    amr = list(amr)
    login_completo = sid is None
    if sid is None:
        sid = sessoes().abrir(usuario, tipo)
    refresh = RefreshToken.for_user(usuario)
    refresh[CLAIM_SCHEMA] = schema
    refresh[CLAIM_EMPRESA] = empresa_id
    refresh[CLAIM_AMR] = list(amr)
    if login_completo and "otp" in amr:
        refresh[CLAIM_AUTH_TIME] = int(relogio.agora().timestamp())
    refresh[CLAIM_SESSAO] = sid
    sessoes().vincular(sid, str(refresh[api_settings.JTI_CLAIM]))
    return refresh


class TokenPre2FA(Token):
    """Senha certa, falta o código (ADR 0013, item 3). Só em `2fa/configurar` e `2fa/verificar`.

    Leva o `aparelho` do login (`desktop` ou `celular`) para a sessão que nasce no fim.
    """

    token_type = "pre_2fa"  # noqa: S105 - tipo do token, não segredo
    lifetime = timedelta(minutes=5)


def emitir_pre_2fa(usuario: AbstractBaseUser, aparelho: str = "desktop") -> TokenPre2FA:
    token = TokenPre2FA()
    token[api_settings.USER_ID_CLAIM] = getattr(usuario, api_settings.USER_ID_FIELD)
    token[CLAIM_APARELHO] = aparelho
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


# --- Token de suporte (ADR 0013, item 2; PLT-07) ---


class TokenSuporte(Token):
    """Sem refresh e sem `user_id`: `exp` é o `fim` do `AcessoSuporte`, conferido no `public` a
    cada requisição pela função que o app `plataforma` registra."""

    token_type = "suporte"  # noqa: S105 - tipo do token, não segredo
    lifetime = timedelta(hours=1)  # trocado pelo `fim` do acesso em `emitir_token_suporte`


CLAIM_ACESSO_SUPORTE = "acesso_suporte_id"
CLAIM_PERMISSAO = "permissao"
SUPORTE_SO_VER = "ver"
SUPORTE_TERMINOU = ("PLT-07", "O acesso de suporte terminou")
SUPORTE_SO_LEITURA = ("PLT-07", "No modo só ver você não pode fazer isto")
SUPORTE_PROIBIDO = ("PLT-07", "O suporte não pode usar esta ação")


@dataclass(frozen=True)
class AtorSuporte:
    """Quem entrou como suporte: objeto em memória, nunca um `contas.Usuario` da empresa.

    Age com o alcance de um administrador em todas as filiais (ADR 0013, item 2).
    """

    acesso_suporte_id: int
    nome: str
    permissao: str
    fim: datetime
    motivo: str
    perfil: str = "administrador"
    permissoes_extras: tuple[str, ...] = ()
    status: str = "ativo"
    e_suporte: bool = True
    is_authenticated: bool = True
    is_anonymous: bool = False
    pk: None = None
    id: None = None


class ConferenciaDeSuporte(Protocol):
    def __call__(self, acesso_suporte_id: int, empresa_id: int) -> AtorSuporte:
        """`AcessoSuporte` ativo, no prazo, da empresa e sem bloqueio; senão 401 `PLT-07`."""
        ...


_conferir_suporte: ConferenciaDeSuporte | None = None


def registrar_suporte(funcao: ConferenciaDeSuporte) -> None:
    """Chamado pelo `ready()` do app `plataforma`."""
    global _conferir_suporte
    _conferir_suporte = funcao


def emitir_token_suporte(
    *, acesso_suporte_id: int, permissao: str, fim: datetime, schema: str, empresa_id: int
) -> TokenSuporte:
    """Emitido no `public` para a empresa do acesso: o token vence no `fim`."""
    token = TokenSuporte()
    token.set_exp(lifetime=fim - token.current_time)
    token[CLAIM_SCHEMA] = schema
    token[CLAIM_EMPRESA] = empresa_id
    token[CLAIM_ACESSO_SUPORTE] = acesso_suporte_id
    token[CLAIM_PERMISSAO] = permissao
    return token


def _tipo_do_token(request: Request) -> str | None:
    """O tipo do Bearer, sem conferir nada: só para escolher o caminho da autenticação."""
    cabecalho = request.META.get(api_settings.AUTH_HEADER_NAME, "")
    partes = str(cabecalho).split()
    if len(partes) != 2 or partes[0] not in api_settings.AUTH_HEADER_TYPES:
        return None
    try:
        conteudo = token_backend.decode(partes[1], verify=False)  # type: ignore[arg-type]
    except (TokenError, TokenBackendError):
        return None
    tipo = conteudo.get(api_settings.TOKEN_TYPE_CLAIM)
    return str(tipo) if tipo else None


def recusar_token_de_suporte(request: Request) -> None:
    """Rotas de autenticação e públicas (entrar, renovar, sair, convite): 403 `PLT-07`."""
    if _tipo_do_token(request) == TokenSuporte.token_type:
        raise SemPermissao(*SUPORTE_PROIBIDO)


def conferir_rota_do_suporte(request: Request, ator: AtorSuporte) -> None:
    """A view decide (ADR 0013, item 2):

    - `suporte_proibido = True` (ou o conjunto de métodos proibidos): 403 `PLT-07` sempre, com a
      mensagem de `mensagem_suporte_proibido` quando a view tem a dela (assinatura, CA-ASS-19);
    - "só ver": só métodos de leitura em views com `suporte_somente_leitura = True`;
    - `so_suporte = True`: rota do próprio suporte (`auth/suporte/sair/`), vale nos dois modos.
    """
    view = (getattr(request, "parser_context", None) or {}).get("view")
    if getattr(view, "so_suporte", False):
        return
    proibido = getattr(view, "suporte_proibido", False)
    if proibido is True or (isinstance(proibido, frozenset) and request.method in proibido):
        raise SemPermissao(*getattr(view, "mensagem_suporte_proibido", SUPORTE_PROIBIDO))
    if ator.permissao == SUPORTE_SO_VER and (
        request.method not in SAFE_METHODS or not getattr(view, "suporte_somente_leitura", False)
    ):
        raise SemPermissao(*SUPORTE_SO_LEITURA)


def _autenticar_suporte(request: Request, bruto: bytes) -> tuple[AtorSuporte, Token]:
    if conexao().schema_name == get_public_schema_name():
        raise SemPermissao(*SUPORTE_PROIBIDO)  # nenhuma rota da plataforma aceita
    try:
        token = TokenSuporte(bruto)  # type: ignore[arg-type]
    except TokenError as erro:
        raise NaoAutenticado(*SUPORTE_TERMINOU) from erro
    try:
        conferir_empresa(token)
    except AuthenticationFailed as erro:
        raise NaoAutenticado(*SUPORTE_TERMINOU) from erro
    acesso_id = token.get(CLAIM_ACESSO_SUPORTE)
    if _conferir_suporte is None or not isinstance(acesso_id, int):
        raise NaoAutenticado(*SUPORTE_TERMINOU)
    ator = _conferir_suporte(acesso_id, int(token[CLAIM_EMPRESA]))
    conferir_rota_do_suporte(request, ator)
    return ator, token


class JWTDaEmpresa(JWTAuthentication):
    def authenticate(self, request: Request) -> Any:
        if _tipo_do_token(request) == TokenSuporte.token_type:
            cabecalho = self.get_header(request)
            bruto = self.get_raw_token(cabecalho) if cabecalho is not None else None
            if bruto is not None:
                return _autenticar_suporte(request, bruto)
        return super().authenticate(request)

    def get_user(self, validated_token: Token) -> Any:
        conferir_empresa(validated_token)
        sid = validated_token.get(CLAIM_SESSAO)
        if not isinstance(sid, int):
            raise NaoAutenticado("nao_autenticado", "Entre de novo.")
        # Sessão revogada ou expirada derruba o access na requisição seguinte (ADR 0014).
        sessoes().conferir(sid, validated_token.get(api_settings.USER_ID_CLAIM))
        # A classe-mãe busca o usuário no schema atual e recusa quem não está ativo (USR-04).
        usuario = super().get_user(validated_token)
        if "otp" not in validated_token.get(CLAIM_AMR, []) and getattr(usuario, "exige_2fa", False):
            raise NaoAutenticado("2fa_obrigatorio", "Confirme o código de verificação.")
        return usuario


class JWTPre2FA(JWTAuthentication):
    """Aceita só o token `pre_2fa`. Convite pendente passa (está configurando o 2FA)."""

    def authenticate(self, request: Request) -> Any:
        recusar_token_de_suporte(request)
        return super().authenticate(request)

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
    """A sessão decide até quando o refresh vale (12 h ou 30 dias sem uso, USR-06)."""
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


def refresh_do_cookie(request: Request) -> dict[str, Any]:
    """O conteúdo do refresh do cookie, com assinatura, validade, tipo, empresa e `sid` conferidos.

    A sessão e a blacklist ficam com quem chama (`contas.sessoes`), depois desta conferência:
    nada é lido nem gravado no schema com token de outra empresa (ADR 0013, item 1).
    Erros são `NaoAutenticado` (401): sem autenticador na view, o DRF trocaria
    `AuthenticationFailed` por 403.
    """
    bruto = request.COOKIES.get(COOKIE_REFRESH)
    if not bruto:
        raise NaoAutenticado("nao_autenticado", "Entre de novo.")
    try:
        conteudo: dict[str, Any] = token_backend.decode(bruto, verify=True)  # type: ignore[arg-type]
    except (TokenError, TokenBackendError) as erro:  # o backend levanta TokenBackendError
        raise NaoAutenticado("nao_autenticado", "Entre de novo.") from erro
    if conteudo.get(api_settings.TOKEN_TYPE_CLAIM) != RefreshToken.token_type:
        raise NaoAutenticado("nao_autenticado", "Entre de novo.")
    try:
        conferir_empresa(conteudo)
    except AuthenticationFailed as erro:
        raise NaoAutenticado("nao_autenticado", "Entre de novo.") from erro
    if not isinstance(conteudo.get(CLAIM_SESSAO), int):
        raise NaoAutenticado("nao_autenticado", "Entre de novo.")
    return conteudo


class JWTPre2FAOuAcesso(JWTAuthentication):
    """`2fa/configurar`: o `pre_2fa` (1º acesso) ou o access de quem ativa por conta própria."""

    def authenticate(self, request: Request) -> Any:
        cabecalho = self.get_header(request)
        bruto = self.get_raw_token(cabecalho) if cabecalho is not None else None
        if bruto is None:
            return None
        try:
            conteudo = token_backend.decode(bruto, verify=True)  # type: ignore[arg-type]
            tipo = conteudo.get(api_settings.TOKEN_TYPE_CLAIM)
        except (TokenError, TokenBackendError) as erro:
            raise InvalidToken({"detail": str(erro)}) from erro
        classe = JWTPre2FA if tipo == TokenPre2FA.token_type else JWTDaEmpresa
        return classe().authenticate(request)
