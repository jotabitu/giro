"""`python manage.py exportar_titular <schema> <cliente_id> --dono <email> --motivo "..."
--saida <arquivo.zip>` (AUD-06, T-369).

Gera o ZIP com os dados do cliente para o pedido do titular, até a tela da fase 2. Só o Dono da
plataforma: o arquivo traz CPF e CNH completos (AUD-09). O arquivo nasce só para o dono do
processo (0600) e nunca sobrescreve outro; entregue-o ao administrador da empresa e apague-o.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from comum.erros import ErroDeNegocio

from ...models import Cliente
from ...titular import conferir_pedido, empresa_para_titular, exportar, texto_do_erro


class Command(BaseCommand):
    help = "Exporta os dados de um cliente para o pedido do titular (AUD-06). Só o Dono."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("schema")
        parser.add_argument("cliente_id", type=int)
        parser.add_argument("--dono", required=True, help="E-mail do Dono da plataforma.")
        parser.add_argument("--motivo", required=True, help="De preferência o chamado.")
        parser.add_argument("--saida", required=True, help="Arquivo .zip novo.")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        try:
            pedido = conferir_pedido(opcoes["dono"], opcoes["motivo"])
            empresa = empresa_para_titular(opcoes["schema"])
            conteudo = exportar(empresa, opcoes["cliente_id"], pedido)
        except ErroDeNegocio as erro:
            raise CommandError(texto_do_erro(erro)) from erro
        except Cliente.DoesNotExist as erro:
            raise CommandError("Cliente não encontrado nesta empresa.") from erro
        try:
            arquivo = os.open(opcoes["saida"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as erro:
            raise CommandError("O arquivo de saída já existe.") from erro
        with os.fdopen(arquivo, "wb") as saida:
            saida.write(conteudo)
        self.stdout.write(f"Dados do cliente {opcoes['cliente_id']} em {opcoes['saida']}.")
