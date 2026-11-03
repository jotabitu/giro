"""`python manage.py acertar_reservas_t410 [<schema>]` (T-410, CA-410-23, ADR 0035).

Acerta as locações `aguardando_retirada` criadas antes da T-410: as contas em aberto passam a
esperar a retirada (nada vence antes dela, LOC-05) e o veículo `disponivel` vai para
`reservado`. Sem schema, todas as empresas. Pode rodar de novo: a segunda vez não muda nada.
As que já passaram do último dia para retirar caem na próxima execução da `AUT-17`.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django_tenants.utils import schema_context

from comum.tarefas import schemas_das_empresas

from ...services import acertar_reservas_t410


class Command(BaseCommand):
    help = "Acerta reservas e contas das locações aguardando retirada (T-410)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("schema", nargs="?", default="")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        schemas = [opcoes["schema"]] if opcoes["schema"] else schemas_das_empresas()
        for schema in schemas:
            with schema_context(schema):
                contas, veiculos = acertar_reservas_t410()
            self.stdout.write(f"{schema}: {contas} conta(s) e {veiculos} veículo(s) acertados.")
