"""`python manage.py conceder_privilegios [--schema X | --todos]` (ADR 0040, itens 2 e 5).

Aplica, pelo alias de migração, as concessões de `auditoria.banco.aplicar_permissoes` nos schemas
de empresa. Idempotente: o deploy roda depois do `migrate_schemas`, e serve para regularizar. Diz,
por schema, se algo mudou ("nada a mudar" quando as ACLs ficaram iguais).
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.plataforma.privilegios import conceder, schemas_de_empresa


class Command(BaseCommand):
    help = "Concede ao giro_app os privilégios nos schemas de empresa (ADR 0040)."

    def add_arguments(self, parser: CommandParser) -> None:
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument("--schema", help="Schema de uma empresa pronta.")
        grupo.add_argument("--todos", action="store_true", help="Todas as empresas prontas.")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        schemas = schemas_de_empresa(opcoes.get("schema"))
        if opcoes.get("schema") and not schemas:
            raise CommandError(f"Schema {opcoes['schema']!r} não é de uma empresa pronta.")
        mudou = False
        for schema in schemas:
            if conceder(schema):
                mudou = True
                self.stdout.write(f"{schema}: privilégios ajustados")
            else:
                self.stdout.write(f"{schema}: nada a mudar")
        self.stdout.write("Privilégios concedidos." if mudou else "Nada a mudar.")
