"""`python manage.py anonimizar_titular <schema> <cliente_id> --dono <email> --motivo "..."
--confirmacao "<nome do cliente>"` (AUD-06, T-369).

Anonimiza o cadastro de um cliente para o pedido do titular, até a tela da fase 2. Só o Dono da
plataforma, com o nome do cliente digitado como está. Contratos e registros financeiros ficam.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from comum.erros import ErroDeNegocio

from ...models import Cliente
from ...titular import anonimizar, conferir_pedido, empresa_para_titular, texto_do_erro


class Command(BaseCommand):
    help = "Anonimiza o cadastro de um cliente para o pedido do titular (AUD-06). Só o Dono."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("schema")
        parser.add_argument("cliente_id", type=int)
        parser.add_argument("--dono", required=True, help="E-mail do Dono da plataforma.")
        parser.add_argument("--motivo", required=True, help="De preferência o chamado.")
        parser.add_argument("--confirmacao", required=True, help="O nome do cliente.")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        try:
            pedido = conferir_pedido(opcoes["dono"], opcoes["motivo"])
            empresa = empresa_para_titular(opcoes["schema"])
            apagados = anonimizar(empresa, opcoes["cliente_id"], pedido, opcoes["confirmacao"])
        except ErroDeNegocio as erro:
            raise CommandError(texto_do_erro(erro)) from erro
        except Cliente.DoesNotExist as erro:
            raise CommandError("Cliente não encontrado nesta empresa.") from erro
        self.stdout.write(
            f"Cliente {opcoes['cliente_id']} anonimizado; {apagados} arquivo(s) apagado(s)."
        )
