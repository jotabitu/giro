"""`python manage.py conferir_privilegios [--schema X]` (ADR 0040, itens 2 e 11).

Falha (saída diferente de zero) se, em algum schema de empresa, o `giro_app` tiver privilégio a
menos (sem `USAGE`, sem DML numa tabela ou sequência) ou a mais (`UPDATE`, `DELETE` ou `TRUNCATE`
na auditoria, `CREATE` em schema), se sobrar `CREATE` do `giro_expurgo`, privilégio de `PUBLIC`,
`EXECUTE` da `auditoria_expurgar` para outro papel, ou tabela cujo dono não seja o
`giro_migracao`. Lista também as empresas reservadas sem schema pronto há mais de 1 hora.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.plataforma.privilegios import problemas, problemas_gerais, schemas_de_empresa
from apps.plataforma.selectors import reservas_presas


class Command(BaseCommand):
    help = "Confere os privilégios dos papéis de banco nos schemas de empresa (ADR 0040)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--schema", help="Só o schema desta empresa.")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        schema = opcoes.get("schema")
        schemas = schemas_de_empresa(schema)
        if schema and not schemas:
            raise CommandError(f"Schema {schema!r} não é de uma empresa pronta.")
        erros = [] if schema else problemas_gerais()
        for nome in schemas:
            do_schema = problemas(nome)
            erros.extend(do_schema)
            self.stdout.write(f"{nome}: {'com problemas' if do_schema else 'nada a mudar'}")
        for reserva in reservas_presas():
            self.stderr.write(
                f"Empresa {reserva['empresa_id']} ({reserva['schema']}) sem schema pronto desde "
                f"{reserva['desde']:%d/%m/%Y %H:%M}."
            )
        if erros:
            for erro in erros:
                self.stderr.write(erro)
            raise CommandError(f"{len(erros)} problema(s) de privilégio.")
        self.stdout.write("Privilégios conferidos: nada a mudar.")
