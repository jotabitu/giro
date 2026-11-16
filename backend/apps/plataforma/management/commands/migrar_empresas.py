"""O `migrate_schemas` do deploy só nas empresas prontas (ADR 0040, item 7; B-1 da revisão do
PR #600).

O `migrate_schemas --tenant` do django-tenants percorre todas as `Empresa`: uma reserva sem
schema cairia no `public` pelo `search_path` ou derrubaria o deploy, e uma reserva no meio da
criação seria migrada junto com a tarefa. Aqui só `Empresa.objects.prontas()`; as reservas vão
ao log, puladas (a tarefa de criação migra o schema dela).
"""

import logging
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.plataforma.models import Empresa

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migra os schemas das empresas prontas (as reservas ficam para a tarefa de criação)."

    def handle(self, *args: Any, **opcoes: Any) -> None:
        publico = get_public_schema_name()
        with schema_context(publico):
            prontas = list(
                Empresa.objects.prontas()
                .exclude(schema_name=publico)
                .order_by("pk")
                .values_list("schema_name", flat=True)
            )
            reservas = list(
                Empresa.objects.filter(schema_pronto_em__isnull=True)  # inclui-reserva
                .exclude(schema_name=publico)
                .values_list("pk", "schema_name")
            )
        for pk, schema in reservas:
            logger.warning(
                "ADR 0040: reserva pulada no migrate (empresa_id=%s, schema=%s).", pk, schema
            )
        for schema in prontas:
            call_command(
                "migrate_schemas",
                schema_name=schema,
                interactive=False,
                verbosity=opcoes["verbosity"],
            )
        self.stdout.write(
            f"{len(prontas)} empresa(s) migrada(s); {len(reservas)} reserva(s) pulada(s)."
        )
