"""`python manage.py carregar_demo_moto_rapida --confirmar motorapida` (T-476).

Carrega os dados de negócio da Moto Rápida numa empresa que já existe, inclusive em produção, sem
criar conta nenhuma (ver `seed/demo.py`). Idempotente: na segunda rodada não faz nada. Recusa
empresa com mais de um usuário ou com dados que não vieram da demonstração.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from comum.erros import ErroDeNegocio
from seed import demo


class Command(BaseCommand):
    help = "Carrega os dados de demonstração da Moto Rápida numa empresa existente, sem contas."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--subdominio", default="motorapida", help="empresa alvo")
        parser.add_argument(
            "--confirmar", metavar="SUBDOMINIO", required=True, help="repita o subdomínio alvo"
        )

    def handle(self, *args: Any, **opcoes: Any) -> None:
        try:
            resultado = demo.carregar(opcoes["subdominio"], opcoes["confirmar"])
        except ErroDeNegocio as erro:
            raise CommandError(erro.mensagem) from erro
        if resultado.ja_carregada:
            self.stdout.write("A demonstração já estava carregada: nada novo.")
            return
        self.stdout.write(f"Criado: {', '.join(resultado.criado)}.")
        self.stdout.write(f"Datas andaram {resultado.dias} dias (07 out 2026 vira hoje).")
