"""Configuração comum a todos os ambientes. Valores vêm das variáveis de `.env.example`."""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".localhost", "127.0.0.1", "backend"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
# Sem CORS: frontend e API na mesma origem (ADR 0013, item 5). O proxy (Next em dev, proxy
# reverso em produção) repassa o Host original em X-Forwarded-Host; o django-tenants o usa.
USE_X_FORWARDED_HOST = True

# Domínio: admin.<DOMINIO_BASE> é a plataforma; <subdominio>.<DOMINIO_BASE>, a empresa.
DOMINIO_BASE = env("DOMINIO_BASE", default="localhost")
SUBDOMINIO_PLATAFORMA = env("SUBDOMINIO_PLATAFORMA", default="admin")

# --- Multiempresa (ADR 0002, 0008, 0011) ---
# Apps nos dois schemas aparecem nas duas listas.
APPS_DOS_DOIS_SCHEMAS = [
    "comum",
    "apps.auditoria",
    "apps.contas",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Só o núcleo: o autenticador e os códigos de recuperação são do app contas (P-08).
    "django_otp",
    "rest_framework_simplejwt.token_blacklist",
]

SHARED_APPS = [
    "django_tenants",
    "apps.plataforma",
    *APPS_DOS_DOIS_SCHEMAS,
    # Admin só no public, com 2 etapas (ADR 0013, item 4).
    "django.contrib.admin",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
]

# Ordem da ADR 0011 (de cima para baixo).
TENANT_APPS = [
    *APPS_DOS_DOIS_SCHEMAS,
    "apps.empresas",
    "apps.filiais",
    "apps.notificacoes",
    "apps.clientes",
    "apps.veiculos",
    "apps.contratos",
    "apps.aprovacoes",
    "apps.financeiro",
    "apps.manutencao",
    "apps.locacoes",
    "apps.vistorias",
    "apps.vendas",
    "apps.automacoes",
    "apps.relatorios",
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "plataforma.Empresa"
TENANT_DOMAIN_MODEL = "plataforma.Dominio"
PUBLIC_SCHEMA_NAME = "public"
PUBLIC_SCHEMA_URLCONF = "config.urls_publico"
ROOT_URLCONF = "config.urls"
# Host sem domínio cadastrado responde 404 (não cai no public): SHOW_PUBLIC_IF_NO_TENANT_FOUND
# fica desligado (padrão do django-tenants), e prod.py o fixa em False. Os domínios da
# plataforma são criados pela migração plataforma.0002.

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "comum.middleware.AtorDaRequisicaoMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Usuários (ADR 0008) ---
AUTH_USER_MODEL = "contas.Usuario"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
# 2 etapas (ADR 0013): `contas.Autenticador` e `contas.CodigoRecuperacao`, com o bloqueio do
# Giro (PLT-08, USR-06), sem o atraso progressivo do django-otp.
# Senha (tela Acesso-Senha): textos prontos em `apps/contas/senhas.py`.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "apps.contas.senhas.TamanhoMinimo"},
    {"NAME": "apps.contas.senhas.LetrasENumeros"},
    {"NAME": "apps.contas.senhas.DiferenteDoEmailEDaEmpresa"},
    {"NAME": "apps.contas.senhas.SenhaComum"},
]

# --- Idioma e fuso: UTC no banco, exibição em America/Sao_Paulo ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- API ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["comum.autenticacao.JWTDaEmpresa"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "comum.permissoes.EmpresaOperando",
        "comum.permissoes.EscopoDeFilial",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "comum.erros.tratar_excecao",
    "DEFAULT_PAGINATION_CLASS": "comum.paginacao.PaginacaoPorCursor",
    # Só as rotas públicas de acesso usam (comum.limites; P-03 da T-057).
    "DEFAULT_THROTTLE_RATES": {
        "entrar_ip_minuto": "10/min",
        "entrar_ip_hora": "50/hour",
        "entrar_email_minuto": "10/min",
        "entrar_email_hora": "50/hour",
        "acesso_ip": "30/min",
        "cep_usuario": "30/min",
    },
}

# /api/schema/ e /api/docs/ (config/urls.py e urls_publico.py). Fechados em produção (S-17).
EXPOR_DOCUMENTACAO_DA_API = env.bool("GIRO_EXPOR_DOCUMENTACAO_DA_API", default=True)

SPECTACULAR_SETTINGS = {
    "TITLE": "API do Giro",
    "DESCRIPTION": "Contrato da API do Giro. Gerado pelo backend (make api-schema).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "EtapaEnum": ["configurar_2fa"],  # nome que o login da plataforma já publicava
        "NivelDeAprovacaoEnum": "apps.contas.api.acesso.NIVEL_DE_APROVACAO",
        "TipoSessaoEnum": "apps.contas.models.TipoSessao",
        "PermissaoExtraEnum": "apps.contas.models.PermissaoExtra",
        "PermissaoSuporteEnum": "apps.plataforma.models.PermissaoSuporte",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    # Teto do refresh, acima da sessão mais longa: quem decide é a sessão (12 h ou 30 dias, USR-06).
    "REFRESH_TOKEN_LIFETIME": timedelta(days=31),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # Chave própria dos tokens: vazar uma não compromete a outra. Em prod.py é obrigatória e
    # diferente de SECRET_KEY; em dev e testes cai em SECRET_KEY.
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
}

# --- Celery (ADR 0012) ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
# S-11: o resultado guardaria o retorno em texto no Redis; quem precisar liga na tarefa.
CELERY_TASK_IGNORE_RESULT = True
CELERY_BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    # Corrige o resumo de uso do plano (PLT-03) contando em cada schema.
    "plataforma_recalcular_uso_de_todas": {
        "task": "plataforma_recalcular_uso_de_todas",
        "schedule": crontab(hour=3, minute=30),
    },
    # AUT-15: encerra os acessos de suporte vencidos (PLT-07).
    "aut_15_encerrar_acessos_de_suporte_vencidos": {
        "task": "aut_15_encerrar_acessos_de_suporte_vencidos",
        "schedule": crontab(minute="*"),
    },
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")

# Toda chave de cache leva o schema da empresa (S-11): nada é compartilhado entre empresas.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_FUNCTION": "django_tenants.cache.make_key",
        "REVERSE_KEY_FUNCTION": "django_tenants.cache.reverse_key",
    }
}

# --- IP do cliente atrás do proxy (ADR 0018, item 4; comum.rede) ---
# X-Forwarded-For só vale quando REMOTE_ADDR está numa destas redes (CIDR). Vazio: nunca.
GIRO_REDES_PROXY = env.list("GIRO_REDES_PROXY", default=[])
GIRO_PROXIES_CONFIAVEIS = env.int("GIRO_PROXIES_CONFIAVEIS", default=1)

# --- Cifra de dados pessoais e segredos (ADR 0014). Nenhuma delas é a SECRET_KEY. ---
# Chaves: "<id>:<base64 de 32 bytes>[,<id>:<chave>...]"; a de maior id cifra.
GIRO_CHAVE_DADOS_PESSOAIS = env("GIRO_CHAVE_DADOS_PESSOAIS")
GIRO_CHAVE_SEGREDOS = env("GIRO_CHAVE_SEGREDOS")
GIRO_PEPPER_HMAC = env("GIRO_PEPPER_HMAC")

# --- Integrações (backend/integracoes/) ---
# CEP: "falso" (CEPs do seed) em dev e testes; "viacep" em homologação e produção.
# Módulos (apps) já entregues: o menu do `eu` esconde os outros, para nunca levar a uma tela
# que não existe (USR-05, T-047). Cada entrega acrescenta o seu.
GIRO_MODULOS_ATIVOS = env.list("GIRO_MODULOS_ATIVOS", default=["contas", "filiais", "plataforma"])
GIRO_PROVEDOR_CEP = env("GIRO_PROVEDOR_CEP", default="falso")
# WhatsApp: só o "falso" (mensagens na memória) até a integração real.
GIRO_PROVEDOR_WHATSAPP = env("GIRO_PROVEDOR_WHATSAPP", default="falso")

# --- E-mail ---
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("EMAIL_FROM", default="Giro <nao-responda@girolocadoras.com.br>")

# --- Sentry (vazio desliga) ---
SENTRY_DSN_BACKEND = env("SENTRY_DSN_BACKEND", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="dev")
if SENTRY_DSN_BACKEND:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN_BACKEND,
        environment=SENTRY_ENVIRONMENT,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
