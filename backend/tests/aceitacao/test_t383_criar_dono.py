"""T-383 · Comando do primeiro Dono da plataforma (`criar_dono_da_plataforma`; PLT-08, PLT-09,
ADR 0029).

O Dono nasce no `public`, com acesso ao Django Admin e as 2 etapas confirmadas no próprio
comando. A senha vem do terminal (`getpass`), nunca da linha de comando. Dados fictícios.
"""

from collections.abc import Callable
from io import StringIO

import pytest
from django.core.management import call_command, load_command_class
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client

from apps.auditoria.models import EventoAuditoria
from apps.contas.management.commands import criar_dono_da_plataforma as comando
from apps.contas.models import Autenticador, CodigoRecuperacao, Usuario

from .conftest import HOST_PLATAFORMA, SENHA, codigo_atual, liberar_codigo

EMAIL = "dono@giro.exemplo"
NOME = "Helena Prado"


@pytest.fixture
def terminal(monkeypatch) -> Callable[..., None]:
    """O que a pessoa digita: a senha duas vezes (sem eco) e o código do autenticador."""

    def digitar(senha: str = SENHA, de_novo: str | None = None, codigo: str | None = None) -> None:
        senhas = iter([senha, senha if de_novo is None else de_novo])
        monkeypatch.setattr(comando, "getpass", lambda _: next(senhas))

        def o_codigo(_: str) -> str:
            if codigo is not None:
                return codigo
            return codigo_atual(Autenticador.objects.get(user__email=EMAIL, confirmed=False))

        monkeypatch.setattr("builtins.input", o_codigo)

    return digitar


def _criar(*args: str) -> str:
    saida = StringIO()
    call_command("criar_dono_da_plataforma", *(args or (EMAIL, "--nome", NOME)), stdout=saida)
    connection.set_schema_to_public()
    return saida.getvalue()


def _nada_criado() -> None:
    connection.set_schema_to_public()
    assert not Usuario.objects.filter(email=EMAIL).exists()
    assert not Autenticador.objects.filter(user__email=EMAIL).exists()
    assert not EventoAuditoria.objects.filter(acao="usuario.criar_dono").exists()


def test_plt_09_criar_dono_com_2_etapas(db, terminal):
    terminal()
    saida = _criar()
    dono = Usuario.objects.get(email=EMAIL)
    assert (dono.nome, dono.funcao_plataforma, dono.status, dono.perfil) == (
        NOME,
        "dono",
        "ativo",
        "",
    )
    assert dono.is_staff and dono.is_superuser and dono.check_password(SENHA)
    dispositivo = Autenticador.objects.get(user=dono)
    assert dispositivo.confirmed
    assert "otpauth://totp/Giro" in saida and dispositivo.chave_legivel() in saida
    assert SENHA not in saida
    assert CodigoRecuperacao.objects.filter(usuario=dono).count() == 8
    assert len([linha for linha in saida.splitlines() if linha.startswith("  ")]) == 2 + 8
    acoes = list(
        EventoAuditoria.objects.filter(objeto_tipo="usuario", objeto_id=dono.pk)
        .order_by("id")
        .values_list("acao", flat=True)
    )
    assert acoes[0] == "usuario.criar_dono"
    assert "usuario.ativar" in acoes
    criacao = EventoAuditoria.objects.get(acao="usuario.criar_dono")
    assert (criacao.categoria, criacao.regra) == ("seguranca", "PLT-09")
    assert dono.password not in str(criacao.depois)  # a senha é omitida (ADR 0014)

    # Entra no Django Admin com a senha e o código (PLT-08).
    liberar_codigo(dispositivo)
    navegador = Client(HTTP_HOST=HOST_PLATAFORMA, REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="pytest")
    resposta = navegador.post(
        "/admin/login/",
        {
            "username": EMAIL,
            "password": SENHA,
            "otp_token": codigo_atual(dispositivo),
            "next": "/admin/",
        },
    )
    connection.set_schema_to_public()
    assert resposta.status_code == 302, resposta.content


def test_plt_08_codigo_errado_nao_cria_nada(db, terminal):
    terminal(codigo="000000")
    with pytest.raises(CommandError, match="Código incorreto"):
        _criar()
    _nada_criado()


def test_plt_09_senhas_diferentes_ou_fraca_nao_criam(db, terminal):
    terminal(de_novo="outra-senha-giro-2026")
    with pytest.raises(CommandError, match="As senhas não conferem"):
        _criar()
    terminal(senha="123")
    with pytest.raises(CommandError):
        _criar()
    _nada_criado()


def test_plt_09_so_o_primeiro_dono(db, terminal):
    terminal()
    _criar()
    with pytest.raises(CommandError, match="já tem um Dono"):
        _criar("outro@giro.exemplo")
    assert Usuario.objects.filter(funcao_plataforma="dono").count() == 1


def test_plt_09_email_em_uso(db, terminal):
    Usuario.objects.create_user(EMAIL, SENHA, nome="Ana Suporte", funcao_plataforma="suporte")
    terminal()
    with pytest.raises(CommandError, match="Este e-mail já tem conta"):
        _criar()
    assert not Usuario.objects.filter(funcao_plataforma="dono").exists()


def test_plt_08_senha_nunca_na_linha_de_comando(db):
    parser = load_command_class("apps.contas", "criar_dono_da_plataforma").create_parser(
        "manage.py", "criar_dono_da_plataforma"
    )
    opcoes = {o for acao in parser._actions for o in acao.option_strings}
    assert not {o for o in opcoes if "senha" in o or "pass" in o}
    with pytest.raises(CommandError):
        call_command("criar_dono_da_plataforma", EMAIL, "--senha", SENHA)
