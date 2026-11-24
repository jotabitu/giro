"""`python manage.py alinhar_veiculos_sem_preco [<schema>]` (VEI-15, ADR 0041, item 3, passo 6).

Roda depois do `migrate_schemas`, no deploy e no `make seed`: leva a `indisponivel` "sem preço" os
veículos `disponivel` sem plano ligado (e volta a `disponivel` os "sem preço" que já têm plano),
pelo serviço de domínio, com histórico de status e auditoria do Sistema. Sem schema, todas as
empresas. Pode rodar de novo: a segunda vez não muda nada.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django_tenants.utils import schema_context

from comum.tarefas import schemas_das_empresas

from ...services import alinhar_veiculos_sem_preco


class Command(BaseCommand):
    help = "Leva a sem preço os veículos disponíveis sem plano ligado (VEI-15)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("schema", nargs="?", default="")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        schemas = [opcoes["schema"]] if opcoes["schema"] else schemas_das_empresas()
        for schema in schemas:
            with schema_context(schema):
                contagem = alinhar_veiculos_sem_preco()
            self.stdout.write(
                f"{schema}: {contagem['sem_preco']} veículo(s) sem preço e "
                f"{contagem['com_preco']} de volta à frota."
            )
