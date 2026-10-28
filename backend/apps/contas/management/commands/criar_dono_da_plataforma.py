"""`python manage.py criar_dono_da_plataforma <email> --nome "..."` (T-383).

Cria o primeiro Dono da plataforma (PLT-09) no `public`, pela mesma porta do `createsuperuser`
(`Usuario.objects.create_superuser`, a única que dá acesso ao Django Admin, ADR 0029). A senha é
digitada duas vezes no terminal, sem eco, e nunca vai na linha de comando. As 2 etapas são
obrigatórias (PLT-08): o comando mostra o endereço `otpauth://` e a chave, pede o código do
autenticador e só termina com ele certo. Até lá a pessoa fica `convite_pendente`. Imprime os 8
códigos de recuperação uma vez. Qualquer erro desfaz tudo: nada fica criado pela metade.
"""

from getpass import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_context

from comum.auditoria import Categoria, registrar_evento, retrato
from comum.erros import ErroDeValidacao

from ... import dois_fatores
from ...api.plataforma import EMISSOR_DA_PLATAFORMA
from ...models import FuncaoPlataforma, StatusUsuario, Usuario
from ...services import ativar_depois_do_2fa, validar_senha

SENHAS_DIFERENTES = "As senhas não conferem."
JA_TEM_DONO = "A plataforma já tem um Dono. Convide a equipe com o convidar_equipe_plataforma."
EMAIL_EM_USO = "Este e-mail já tem conta."
CODIGO_ERRADO = "Código incorreto. Nada foi criado; rode o comando de novo."


class Command(BaseCommand):
    help = "Cria o primeiro Dono da plataforma, com senha e 2 etapas digitadas no terminal."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email")
        parser.add_argument("--nome", default="")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        email = opcoes["email"].strip().lower()
        nome = opcoes["nome"].strip() or email
        with schema_context(get_public_schema_name()):
            if Usuario.objects.filter(funcao_plataforma=FuncaoPlataforma.DONO).exists():
                raise CommandError(JA_TEM_DONO)
            if Usuario.objects.filter(email=email).exists():
                raise CommandError(EMAIL_EM_USO)
            senha = getpass("Senha: ")
            if getpass("Senha de novo: ") != senha:
                raise CommandError(SENHAS_DIFERENTES)
            try:
                validar_senha(senha, Usuario(email=email, nome=nome), campo="senha")
            except ErroDeValidacao as erro:
                raise CommandError(" ".join(erro.campos["senha"])) from erro
            with transaction.atomic():
                codigos = self._criar(email, nome, senha)
        self.stdout.write("Dono criado. Guarde os códigos de recuperação (aparecem só agora):")
        for codigo in codigos:
            self.stdout.write(f"  {codigo}")

    def _criar(self, email: str, nome: str, senha: str) -> list[str]:
        usuario: Usuario = Usuario.objects.create_superuser(
            email, senha, nome=nome, status=StatusUsuario.CONVITE_PENDENTE
        )
        registrar_evento(
            "usuario.criar_dono",
            Categoria.SEGURANCA,
            objeto=usuario,
            depois=retrato(usuario),
            regra="PLT-09",
        )
        dispositivo = dois_fatores.novo_autenticador(usuario)
        self.stdout.write("Leia no autenticador o endereço abaixo, ou digite a chave:")
        self.stdout.write(f"  {dispositivo.config_url_para(EMISSOR_DA_PLATAFORMA)}")
        self.stdout.write(f"  Chave: {dispositivo.chave_legivel()}")
        codigo = input("Código de 6 dígitos do autenticador: ")
        if dois_fatores.conferir_codigo(usuario, codigo=codigo, confirmando=True) is None:
            raise CommandError(CODIGO_ERRADO)
        codigos = dois_fatores.confirmar_autenticador(dispositivo)
        ativar_depois_do_2fa(usuario)
        return codigos
