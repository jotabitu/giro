"""Configuração comum a todos os ambientes. Valores vêm das variáveis de `.env.example`."""

from datetime import timedelta
from pathlib import Path
from typing import Any

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# Valores de exemplo do .env.example: só valem em desenvolvimento. config.settings.prod os recusa.
CHAVE_DADOS_PESSOAIS_DE_EXEMPLO = "1:O6Era8PkgBlfbOR6Nt6IGvnBlEL9vRRNA3iXRdxDtkg="
CHAVE_SEGREDOS_DE_EXEMPLO = "1:b/jBUdVpQ6mwUQJnFhzjnMkTVZvziqLLZfoEWrBDhs0="
PEPPER_DE_EXEMPLO = "07128db7f37327bc0128ca29852fae5bf3b0f67c758ad430d12af360c0332089"


def env_preenchida(nome: str, padrao: str) -> str:
    """Valor da variável; ausente ou vazia (`NOME=` no .env) cai no padrão de desenvolvimento.

    `env(nome, default=...)` só usa o padrão quando a variável não existe, e o compose entrega
    `NOME=` do .env como string vazia (T-133). Produção confere a variável crua em prod.py.
    """
    return env(nome, default="").strip() or padrao


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
    "apps.importacao",
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
    # O DateTimeField devolve o datetime cru; quem formata é o renderizador (ADR 0020).
    "DATETIME_FORMAT": None,
    "DEFAULT_RENDERER_CLASSES": [
        "comum.renderizacao.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    # Só as rotas públicas de acesso usam (comum.limites; P-03 da T-057).
    "DEFAULT_THROTTLE_RATES": {
        "entrar_ip_minuto": "10/min",
        "entrar_ip_hora": "50/hour",
        "entrar_email_minuto": "10/min",
        "entrar_email_hora": "50/hour",
        "acesso_ip": "30/min",
        "cep_usuario": "30/min",
        # Marca e logo, públicas (docs/api/empresas.md).
        "marca_ip": "120/min",
        # Link de assinatura de contrato (S-15).
        "assinatura_ip": "10/min",
        "assinatura_token": "20/min",
        # Webhook do parceiro de pagamentos (S-14).
        "webhook_ip": "120/min",
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
        "StatusVeiculoEnum": "apps.veiculos.models.StatusVeiculo",
        "TipoDocumentoEnum": "apps.veiculos.models.TipoDocumento",
        "TipoDocumentoClienteEnum": "apps.clientes.models.TipoDocumentoCliente",
        "StatusClienteEnum": "apps.clientes.models.StatusCliente",
        "TipoClienteEnum": "apps.clientes.models.TipoCliente",
        "StatusContratoEnum": "apps.contratos.models.StatusContrato",
        "StatusModeloContratoEnum": ["publicado", "rascunho"],
        # O do cancelamento (LOC-12), sem dinheiro, e o do acerto (DEV-02), com dinheiro pelo caixa.
        "FormaDevolucaoEnum": [("pix", "Pix"), ("estorno_cartao", "Estorno no cartão")],
        "FormaDevolucaoAcertoEnum": "apps.vistorias.models.FormaDevolucao",
        # Nomes que veículos já publicava, antes de clientes ter outro `motivo` e `situacao`.
        "MotivoEnum": ["perda_total", "roubo", "sucata", "outro"],
        "SituacaoEnum": ["em_dia", "vence_em_breve", "vencido"],
        # Painel (T-129).
        "TipoVeiculoEnum": "apps.veiculos.models.TipoVeiculo",
        "TipoValorEnum": ["numero", "centavos", "pct"],
        "TipoParaHojeEnum": ["reembolso", "despesa"],
        "StatusConviteEnum": ["aceito", "pendente"],
        # Importação (T-027).
        "TipoImportacaoEnum": "apps.importacao.models.TipoImportacao",
        "StatusImportacaoEnum": "apps.importacao.models.StatusImportacao",
        "StatusLinhaImportacaoEnum": "apps.importacao.models.StatusLinha",
        # Financeiro (T-017).
        "StatusContaReceberEnum": [
            "aberta",
            "vence_hoje",
            "atrasada",
            "paga",
            "cancelada",
            "renegociada",
        ],
        "StatusCaixaEnum": ["aberto", "aguardando_aprovacao", "fechado", "fechado_sem_conferencia"],
        "StatusDespesaEnum": "apps.financeiro.models.StatusDespesa",
        "StatusReembolsoEnum": "apps.financeiro.models.StatusReembolso",
        "CategoriaDespesaEnum": "apps.financeiro.models.CategoriaDespesa",
        "CategoriaEnum": "apps.clientes.models.CategoriaCnh",  # nome que clientes já publicava
        "FormaDespesaEnum": "apps.financeiro.models.FormaDespesa",
        "TipoMovimentoEnum": "apps.financeiro.models.TipoMovimento",
        "TipoLancamentoEnum": ["multa", "avaria", "outro"],
        "TipoCobrancaPedidaEnum": ["pix", "boleto"],
        "FormaRecebimentoEnum": ["dinheiro", "cartao_debito", "cartao_credito"],
        "OrigemDoLancamentoEnum": ["locacao", "venda", "devolucao"],
        # Auditoria e exportação (T-018), sem renomear os enums que já existiam.
        "CategoriaAuditoriaEnum": "comum.auditoria.Categoria",
        "TipoAtorEnum": "comum.auditoria.TipoAtor",
        "ItemExportacaoEnum": "apps.auditoria.models.ItemExportacao",
        "FormatoExportacaoEnum": "apps.auditoria.models.FormatoExportacao",
        "StatusExportacaoEnum": "apps.auditoria.models.StatusExportacao",
    },
}

SIMPLE_JWT: dict[str, Any] = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    # Teto do refresh, acima da sessão mais longa: quem decide é a sessão (12 h ou 30 dias, USR-06).
    "REFRESH_TOKEN_LIFETIME": timedelta(days=31),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # Chave própria dos tokens: vazar uma não compromete a outra. Em prod.py é obrigatória e
    # diferente de SECRET_KEY; em dev e testes cai em SECRET_KEY.
    "SIGNING_KEY": env_preenchida("JWT_SIGNING_KEY", SECRET_KEY),
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
    # AUT-06: vencimento de documentos de veículos (VEI-03), às 07:00.
    "aut_06_vencimento_de_documentos": {
        "task": "aut_06_vencimento_de_documentos_de_todas",
        "schedule": crontab(hour=7, minute=0),
    },
    # AUT-02: marca a devolução atrasada (LOC-10, LOC-11), de hora em hora.
    "aut_02_marcar_devolucao_atrasada": {
        "task": "aut_02_marcar_devolucao_atrasada_de_todas",
        "schedule": crontab(minute=0),
    },
    # Rascunho de locação com 24 h sem uso vai para `cancelada` (seção "Locação" das regras).
    "locacoes_cancelar_rascunhos_sem_uso": {
        "task": "locacoes_cancelar_rascunhos_sem_uso_de_todas",
        "schedule": crontab(minute=15),
    },
    # LOC-08: aditivo sem assinatura em 7 dias vira tarefa para os gerentes da filial.
    "contratos_avisar_aditivos_sem_assinatura": {
        "task": "contratos_avisar_aditivos_sem_assinatura_de_todas",
        "schedule": crontab(hour=8, minute=0),
    },
    # AUT-03: régua de cobrança (WhatsApp e atraso para o bloqueio, CLI-05), às 09:00.
    "aut_03_regua_de_cobranca": {
        "task": "aut_03_regua_de_cobranca_de_todas",
        "schedule": crontab(hour=9, minute=0),
    },
    # AUT-08: caixa não fechado fecha sozinho sem conferência (FIN-08), às 23:59.
    "aut_08_fechamento_automatico_do_caixa": {
        "task": "aut_08_fechamento_automatico_do_caixa_de_todas",
        "schedule": crontab(hour=23, minute=59),
    },
    # Planilhas e linhas da importação saem 30 dias depois do envio (docs/api/importacao.md).
    "importacao_limpar": {
        "task": "importacao_limpar_de_todas",
        "schedule": crontab(hour=4, minute=0),
    },
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
# Vazias (ou ausentes) caem nos valores de exemplo; em prod.py são obrigatórias e próprias.
GIRO_CHAVE_DADOS_PESSOAIS = env_preenchida(
    "GIRO_CHAVE_DADOS_PESSOAIS", CHAVE_DADOS_PESSOAIS_DE_EXEMPLO
)
GIRO_CHAVE_SEGREDOS = env_preenchida("GIRO_CHAVE_SEGREDOS", CHAVE_SEGREDOS_DE_EXEMPLO)
GIRO_PEPPER_HMAC = env_preenchida("GIRO_PEPPER_HMAC", PEPPER_DE_EXEMPLO)

# --- Integrações (backend/integracoes/) ---
# CEP: "falso" (CEPs do seed) em dev e testes; "viacep" em homologação e produção.
# Módulos (apps) já entregues: o menu do `eu` esconde os outros, para nunca levar a uma tela
# que não existe (USR-05, T-047). Cada entrega acrescenta o seu.
GIRO_MODULOS_ATIVOS = env.list(
    "GIRO_MODULOS_ATIVOS",
    default=[
        "aprovacoes",
        "clientes",
        "contas",
        "contratos",
        "filiais",
        "financeiro",
        "locacoes",
        "plataforma",
        "veiculos",
        "vistorias",
    ],
)
GIRO_PROVEDOR_CEP = env("GIRO_PROVEDOR_CEP", default="falso")
# Arquivos privados (ADR 0009, AUD-05): "falso" (na memória) em dev e testes; "s3" com um bucket
# privado compatível com S3 em homologação e produção.
GIRO_ARMAZENAMENTO = env("GIRO_ARMAZENAMENTO", default="falso")
S3_BUCKET = env("S3_BUCKET", default="")
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
S3_REGIAO = env("S3_REGIAO", default="")
S3_CHAVE_DE_ACESSO = env("S3_CHAVE_DE_ACESSO", default="")
S3_CHAVE_SECRETA = env("S3_CHAVE_SECRETA", default="")
# WhatsApp: só o "falso" (mensagens na memória) até a integração real.
GIRO_PROVEDOR_WHATSAPP = env("GIRO_PROVEDOR_WHATSAPP", default="falso")
# Pagamentos (Pix, boleto, webhook): só o "falso" (cobranças na memória) até a T-029 (Asaas).
GIRO_PROVEDOR_PAGAMENTOS = env("GIRO_PROVEDOR_PAGAMENTOS", default="falso")

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
