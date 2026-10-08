from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import SECRET_KEY, SIMPLE_JWT, env

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
if SIMPLE_JWT["SIGNING_KEY"] == SECRET_KEY:
    raise ImproperlyConfigured("Defina JWT_SIGNING_KEY, diferente de DJANGO_SECRET_KEY.")
if not env.list("GIRO_REDES_PROXY", default=[]):
    raise ImproperlyConfigured("Defina GIRO_REDES_PROXY com a rede do proxy reverso (ADR 0018).")
