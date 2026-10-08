from typing import Any

from django.apps import AppConfig
from django.db import connections
from django.db.models.signals import post_migrate


def _permissoes_depois_de_migrar(sender: AppConfig, using: str = "default", **kwargs: Any) -> None:
    from apps.auditoria.banco import aplicar_permissoes

    conexao: Any = connections[using]
    with conexao.cursor() as cursor:
        aplicar_permissoes(cursor, conexao.schema_name)


class AuditoriaConfig(AppConfig):
    name = "apps.auditoria"
    label = "auditoria"

    def ready(self) -> None:
        # Uma vez por schema migrado (o django-tenants roda o migrate em cada um).
        post_migrate.connect(_permissoes_depois_de_migrar, sender=self)
