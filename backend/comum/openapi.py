"""Autenticações do Giro no OpenAPI (drf-spectacular): Bearer JWT, como o simplejwt."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class JWTDaEmpresaScheme(SimpleJWTScheme):  # type: ignore[no-untyped-call]
    target_class = "comum.autenticacao.JWTDaEmpresa"


class JWTPre2FAScheme(SimpleJWTScheme):  # type: ignore[no-untyped-call]
    target_class = "comum.autenticacao.JWTPre2FA"
    name = "jwtPre2fa"
