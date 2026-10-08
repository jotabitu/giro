"""`python manage.py convidar_equipe_plataforma <email> <funcao> --nome "..."` (fase 1).

Convida alguém para a equipe da plataforma (PLT-09) e imprime o link do convite (7 dias).
A pessoa cria a senha pelo link e só vira `ativo` ao confirmar o 2FA (PLT-08).
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django_tenants.utils import get_public_schema_name, schema_context

from comum.erros import ErroDeNegocio

from ...models import FuncaoPlataforma
from ...services import convidar_equipe_plataforma


class Command(BaseCommand):
    help = "Convida uma pessoa para a equipe da plataforma e imprime o link do convite."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email")
        parser.add_argument("funcao", choices=FuncaoPlataforma.values)
        parser.add_argument("--nome", default="")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        with schema_context(get_public_schema_name()):
            try:
                usuario, link = convidar_equipe_plataforma(
                    opcoes["email"], opcoes["funcao"], opcoes["nome"]
                )
            except ErroDeNegocio as erro:
                raise CommandError(erro.mensagem) from erro
        self.stdout.write(f"Convite de {usuario.nome} ({usuario.funcao_plataforma}): {link}")
