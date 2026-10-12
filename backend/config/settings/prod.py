import base64
import ipaddress

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import (
    CHAVE_DADOS_PESSOAIS_DE_EXEMPLO,
    CHAVE_SEGREDOS_DE_EXEMPLO,
    GIRO_CHAVE_DADOS_PESSOAIS,
    GIRO_CHAVE_SEGREDOS,
    GIRO_PEPPER_HMAC,
    PEPPER_DE_EXEMPLO,
    SECRET_KEY,
    SIMPLE_JWT,
    env,
)

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS com preload (S-18). O preload exige pelo menos 1 ano; em homologação use um valor menor
# em DJANGO_HSTS_SEGUNDOS e DJANGO_HSTS_PRELOAD=0 enquanto o domínio não estiver estável.
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SEGUNDOS", default=60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = env.bool("DJANGO_HSTS_PRELOAD", default=True)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Host sem empresa responde 404, nunca o schema público (S-16).
SHOW_PUBLIC_IF_NO_TENANT_FOUND = False

# Documentação da API fechada, salvo se o ambiente pedir (S-17).
EXPOR_DOCUMENTACAO_DA_API = env.bool("GIRO_EXPOR_DOCUMENTACAO_DA_API", default=False)

# Segredos próprios de produção: falha ao subir se faltarem ou se repetirem.
# Variável ausente ou vazia vale como não definida: base.py cai nos padrões de desenvolvimento,
# e produção não pode subir com eles (T-133).
for _nome in (
    "JWT_SIGNING_KEY",
    "GIRO_CHAVE_DADOS_PESSOAIS",
    "GIRO_CHAVE_SEGREDOS",
    "GIRO_PEPPER_HMAC",
):
    if not env(_nome, default="").strip():
        raise ImproperlyConfigured(f"Defina {_nome}: vazia ou ausente não é aceita em produção.")
if SIMPLE_JWT["SIGNING_KEY"] == SECRET_KEY:
    raise ImproperlyConfigured("Defina JWT_SIGNING_KEY, diferente de DJANGO_SECRET_KEY.")
_redes_proxy = env.list("GIRO_REDES_PROXY", default=[])
if not _redes_proxy:
    raise ImproperlyConfigured("Defina GIRO_REDES_PROXY com a rede do proxy reverso (ADR 0018).")
for _rede in _redes_proxy:
    try:
        _cidr = ipaddress.ip_network(_rede.strip(), strict=False)
    except ValueError as erro:
        raise ImproperlyConfigured(f"GIRO_REDES_PROXY com rede inválida: {_rede!r}.") from erro
    if _cidr.prefixlen == 0:
        raise ImproperlyConfigured("GIRO_REDES_PROXY não pode confiar em todos os endereços.")

# Cifra de dados pessoais (ADR 0014, R-03 da T-050): os valores do .env.example estão no
# repositório e não valem em homologação nem em produção.
_MATERIAL_DE_EXEMPLO = {
    CHAVE_DADOS_PESSOAIS_DE_EXEMPLO.split(":", 1)[1],
    CHAVE_SEGREDOS_DE_EXEMPLO.split(":", 1)[1],
}
_PEPPER_DE_EXEMPLO = PEPPER_DE_EXEMPLO


def _material(valor: str) -> set[str]:
    """Os bytes de cada chave ("<id>:<base64>"), sem o id, para comparar entre variáveis."""
    return {parte.split(":", 1)[-1].strip() for parte in valor.split(",") if parte.strip()}


_dados, _segredos = _material(GIRO_CHAVE_DADOS_PESSOAIS), _material(GIRO_CHAVE_SEGREDOS)
if (_dados | _segredos) & _MATERIAL_DE_EXEMPLO:
    raise ImproperlyConfigured("GIRO_CHAVE_* com valor do .env.example. Gere chaves próprias.")
if _dados & _segredos:
    raise ImproperlyConfigured("GIRO_CHAVE_DADOS_PESSOAIS e GIRO_CHAVE_SEGREDOS repetem uma chave.")
for _nome, _chaves in (("GIRO_CHAVE_DADOS_PESSOAIS", _dados), ("GIRO_CHAVE_SEGREDOS", _segredos)):
    for _chave in _chaves:
        try:
            _tamanho = len(base64.b64decode(_chave, validate=True))
        except ValueError:
            _tamanho = 0
        if _tamanho != 32:
            raise ImproperlyConfigured(f"{_nome} precisa de chaves de 32 bytes em base64.")
if GIRO_PEPPER_HMAC == _PEPPER_DE_EXEMPLO:
    raise ImproperlyConfigured("GIRO_PEPPER_HMAC com valor do .env.example. Gere um próprio.")
if len(GIRO_PEPPER_HMAC.encode()) < 32:
    raise ImproperlyConfigured("GIRO_PEPPER_HMAC precisa de pelo menos 32 bytes.")
if GIRO_PEPPER_HMAC in (SECRET_KEY, SIMPLE_JWT["SIGNING_KEY"]):
    raise ImproperlyConfigured("GIRO_PEPPER_HMAC não pode repetir outro segredo.")
