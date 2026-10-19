import base64
import ipaddress
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CHAVE_DADOS_PESSOAIS_DE_EXEMPLO,
    CHAVE_SEGREDOS_DE_EXEMPLO,
    DATABASES,
    EMAIL_BACKEND,
    EMAIL_HOST,
    GIRO_ARMAZENAMENTO,
    GIRO_ASAAS_CHAVE_API,
    GIRO_CHAVE_DADOS_PESSOAIS,
    GIRO_CHAVE_SEGREDOS,
    GIRO_PEPPER_HMAC,
    GIRO_PROVEDOR_PAGAMENTOS,
    PEPPER_DE_EXEMPLO,
    REDIS_URL,
    S3_BUCKET,
    S3_CHAVE_DE_ACESSO,
    S3_CHAVE_SECRETA,
    SECRET_KEY,
    SIMPLE_JWT,
    env,
)

DEBUG = False
# O proxy reverso sobrescreve X-Forwarded-Host (infra/proxy, T-158).
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Só o Django Admin usa a sessão (a API usa tokens): curta e presa ao navegador (ADR 0029).
# Sem SESSION_COOKIE_DOMAIN, o cookie fica no host da plataforma.
SESSION_COOKIE_AGE = 4 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

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

# Data simulada só no desenvolvimento (ADR 0021): um .env de desenvolvimento copiado para o
# servidor não sobe.
if env("GIRO_DATA_REFERENCIA", default="").strip():
    raise ImproperlyConfigured("GIRO_DATA_REFERENCIA só vale no desenvolvimento.")
GIRO_DATA_REFERENCIA = None

# Integrações de desenvolvimento não sobem (T-157). Os e-mails de senha, convite e assinatura
# levam o token: no console, na memória ou em arquivo ele iria para o log ou para o disco, e o
# "dummy" descarta sem avisar. Arquivos e cobranças falsos ficam na memória do processo.
_EMAIL_DE_DESENVOLVIMENTO = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}
if EMAIL_BACKEND.strip() in _EMAIL_DE_DESENVOLVIMENTO:
    raise ImproperlyConfigured(f"EMAIL_BACKEND {EMAIL_BACKEND} só vale no desenvolvimento.")
if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not EMAIL_HOST.strip():
    raise ImproperlyConfigured("Defina EMAIL_HOST para enviar e-mail por SMTP.")
if GIRO_ARMAZENAMENTO != "s3":
    raise ImproperlyConfigured("Defina GIRO_ARMAZENAMENTO=s3: o armazenamento falso não sobe.")
# Bucket e chaves em branco só apareceriam na primeira foto de vistoria (T-266, pedido do devops
# na T-258). O endpoint e a região podem ficar vazios: a AWS usa os padrões do boto3.
for _nome, _valor in (
    ("S3_BUCKET", S3_BUCKET),
    ("S3_CHAVE_DE_ACESSO", S3_CHAVE_DE_ACESSO),
    ("S3_CHAVE_SECRETA", S3_CHAVE_SECRETA),
):
    if not _valor.strip():
        raise ImproperlyConfigured(f"Defina {_nome}: vazia ou ausente não é aceita em produção.")
if GIRO_PROVEDOR_PAGAMENTOS != "asaas":
    raise ImproperlyConfigured("Defina GIRO_PROVEDOR_PAGAMENTOS=asaas: o falso não sobe.")
if not GIRO_ASAAS_CHAVE_API.strip():
    raise ImproperlyConfigured("Defina GIRO_ASAAS_CHAVE_API: vazia não é aceita em produção.")
# Banco e Redis só com senha (T-274, condição da segurança na T-247): a URL sem senha subiria
# contra um serviço aberto na rede interna. Redis: `redis://:senha@host:6379/0`.
if not DATABASES["default"].get("PASSWORD"):
    raise ImproperlyConfigured("DATABASE_URL sem senha: produção só sobe com senha no Postgres.")
for _nome, _url in (
    ("CELERY_BROKER_URL", CELERY_BROKER_URL),
    ("CELERY_RESULT_BACKEND", CELERY_RESULT_BACKEND),
    ("REDIS_URL", REDIS_URL),
):
    if not urlsplit(_url).password:
        raise ImproperlyConfigured(f"{_nome} sem senha: produção só sobe com senha no Redis.")
# WhatsApp: só existe o falso (mensagens na memória); entra nesta trava com a integração real.

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
