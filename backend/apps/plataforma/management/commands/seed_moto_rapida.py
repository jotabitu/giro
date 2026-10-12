"""`python manage.py seed_moto_rapida` (T-127): empresa de exemplo para conferir as telas.

Idempotente: rodar de novo não duplica nada. `--codigo <e-mail>` mostra o código de 2 etapas de
agora das contas do seed (administrador e financeiro), só em desenvolvimento.
"""

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from comum.erros import ErroDeNegocio
from seed import moto_rapida


class Command(BaseCommand):
    help = "Carrega a empresa Moto Rápida (parcial: sem o financeiro da T-017)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--codigo", metavar="EMAIL", help="mostra o código de 2 etapas")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        if os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".prod"):
            raise CommandError("O seed da Moto Rápida não roda em produção.")
        if opcoes["codigo"]:
            self.stdout.write(moto_rapida.codigo_de_2fa(opcoes["codigo"]))
            return
        try:
            resultado = moto_rapida.semear()
        except ErroDeNegocio as erro:
            raise CommandError(erro.mensagem) from erro
        criado = ", ".join(resultado.criado) or "nada novo"
        self.stdout.write(f"Criado: {criado}.")
        if resultado.existente:
            self.stdout.write(f"Já existia: {', '.join(resultado.existente)}.")
        self.stdout.write(f"Acesso: http://{moto_rapida.SUBDOMINIO}.localhost:3000/entrar")
        _, email = moto_rapida.DONO_DA_PLATAFORMA
        self.stdout.write(f"  plataforma    {email}  {moto_rapida.SENHA_DEV}  (2 etapas: --codigo)")
        for email, perfil in moto_rapida.PESSOAS.values():
            dois = "  (2 etapas: --codigo)" if perfil in moto_rapida.PERFIS_COM_2FA else ""
            self.stdout.write(f"  {perfil:<13} {email}  {moto_rapida.SENHA_DEV}{dois}")
