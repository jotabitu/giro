"""JWT preso à empresa em que foi emitido (ADR 0008, item 5, e ADR 0013, item 1).

O mesmo `user_id` existe em várias empresas. Todo token leva as claims `schema` e `empresa_id`
(PK da empresa, nunca reusada) e só vale no host dessa empresa. `conferir_empresa` é o
único ponto de conferência: a autenticação usa e os serializers de login, refresh, verify e
sair (T-011) também precisam usar, antes de tocar na blacklist. Token de suporte, `pre_2fa`,
claim `amr` e cookie do refresh entram com a T-011 (ADR 0013, itens 2, 3 e 5).
"""

from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken, Token

from comum.conexao import conexao

CLAIM_SCHEMA = "schema"
CLAIM_EMPRESA = "empresa_id"


def _empresa_atual() -> tuple[str, int | None]:
    tenant = getattr(conexao(), "tenant", None)
    return str(conexao().schema_name), getattr(tenant, "pk", None)


def emitir_tokens(usuario: AbstractBaseUser) -> RefreshToken:
    """Refresh (e o access derivado dele) com `schema` e `empresa_id` da empresa atual."""
    schema, empresa_id = _empresa_atual()
    if empresa_id is None:
        raise RuntimeError("Sem empresa na conexão: não é possível emitir token.")
    refresh = RefreshToken.for_user(usuario)
    refresh[CLAIM_SCHEMA] = schema
    refresh[CLAIM_EMPRESA] = empresa_id
    return refresh


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
        return super().get_user(validated_token)
