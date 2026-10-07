"""App Celery do Giro. Tarefas por empresa seguem a ADR 0012 (comum.tarefas)."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("giro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
