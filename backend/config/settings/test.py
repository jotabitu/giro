"""Testes: rodam dentro do container (make backend-check) contra o Postgres do Compose."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "chave-so-para-testes")
os.environ.setdefault("DATABASE_URL", "postgres://giro:giro-dev-trocar@db:5432/giro")
# Chaves fixas só para testes (32 bytes em base64), para não depender do .env.
os.environ.setdefault("GIRO_CHAVE_DADOS_PESSOAIS", "1:" + "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE=")
os.environ.setdefault("GIRO_CHAVE_SEGREDOS", "1:" + "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjI=")
os.environ.setdefault("GIRO_PEPPER_HMAC", "pepper-so-para-testes")

from config.settings.base import *  # noqa: F403
from config.settings.base import SHARED_APPS, TENANT_APPS

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# App só de teste com um model que usa ModeloComCodigo e MaquinaDeEstados.
TENANT_APPS = [*TENANT_APPS, "tests.app_exemplo"]
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
