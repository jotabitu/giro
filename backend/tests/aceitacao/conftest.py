"""Fixtures dos testes de aceitação: relógio congelado, planos, empresas e equipe da plataforma."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from django.db import connection
from rest_framework.test import APIClient

HOST_PLATAFORMA = "admin.localhost"
CNPJ_MOTO_RAPIDA = "12.345.678/0001-95"  # T-053: o 0001-10 não passava no dígito verificador


@pytest.fixture
def planos(db) -> dict[str, Any]:
    from apps.plataforma.models import Plano

    return {plano.nome: plano for plano in Plano.objects.all()}


@pytest.fixture
def criar_empresa(publico, relogio, planos) -> Callable[..., Any]:
    """Cria pelo serviço (o mesmo do Django Admin), já de volta ao public."""
    from apps.plataforma.services import Administrador
    from apps.plataforma.services import criar_empresa as servico

    def criar(
        subdominio: str = "motorapida",
        cnpj: str = CNPJ_MOTO_RAPIDA,
        plano: str = "Profissional",
        **campos: Any,
    ) -> Any:
        administrador = campos.pop(
            "administrador",
            Administrador(nome="Mariana Costa", email="mariana@motorapida.com.br"),
        )
        dados = {
            "razao_social": "Moto Rápida Locações Ltda",
            "nome_exibicao": "Moto Rápida",
            "cidade": "Fortaleza",
            "uf": "CE",
            **campos,
        }
        empresa = servico(
            cnpj=cnpj,
            subdominio=subdominio,
            plano=planos[plano],
            administrador=administrador,
            **dados,
        )
        connection.set_schema_to_public()
        return empresa

    return criar


@pytest.fixture
def relogio_jwt(relogio, monkeypatch):
    """Os tokens usam o relógio congelado dos testes: o simplejwt (emissão e `exp`) e o PyJWT
    (`iat` e `exp` na leitura)."""
    from comum import relogio as relogio_do_giro

    class Relogio(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Any:
            return relogio_do_giro.agora().astimezone(tz or UTC)

    monkeypatch.setattr(
        "rest_framework_simplejwt.tokens.aware_utcnow",
        lambda: relogio_do_giro.agora().astimezone(UTC),
    )
    monkeypatch.setattr("jwt.api_jwt.datetime", Relogio)
    return relogio


# --- API ---


def cliente(host: str, token: str | None = None) -> APIClient:
    api = APIClient(HTTP_HOST=host, REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="pytest")
    if token:
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


@pytest.fixture(autouse=True)
def _volta_ao_public_depois():
    """Uma requisição de teste deixa a conexão no schema do host; o teste segue no public."""
    yield
    connection.set_schema_to_public()


# --- Equipe da plataforma (PLT-08, PLT-09) ---


SENHA = "senha-forte-giro-2026"
EQUIPE_SEED = {
    "Você": ("dono@girolocadoras.com.br", "dono"),
    "Diego Santos": ("diego@girolocadoras.com.br", "suporte"),
    "Paula Andrade": ("paula@girolocadoras.com.br", "financeiro"),
    "Caio Ribeiro": ("caio@girolocadoras.com.br", "sucesso"),
}


def codigo_atual(dispositivo: Any) -> str:
    """Código do `contas.Autenticador` agora (relógio de verdade, como o do celular)."""
    return f"{dispositivo.totp().token():0{dispositivo.DIGITOS}d}"


def liberar_codigo(dispositivo: Any) -> None:
    """O mesmo código não vale duas vezes no mesmo passo de 30 s (replay)."""
    type(dispositivo).objects.filter(pk=dispositivo.pk).update(ultimo_passo=-1)
    dispositivo.refresh_from_db()


def autenticador_confirmado(usuario: Any) -> Any:
    """Autenticador já confirmado, como se a pessoa tivesse ativado as 2 etapas."""
    from apps.contas.models import Autenticador

    dispositivo = Autenticador(user=usuario, name="autenticador", confirmed=True)
    dispositivo.gerar_chave()
    dispositivo.save()
    return dispositivo


@pytest.fixture
def equipe(publico) -> dict[str, tuple[Any, Any]]:
    """A equipe do seed, ativa e com autenticador confirmado."""
    from apps.contas.models import Usuario

    pessoas = {}
    for nome, (email, funcao) in EQUIPE_SEED.items():
        usuario = Usuario.objects.create_user(email, SENHA, nome=nome, funcao_plataforma=funcao)
        pessoas[nome] = (usuario, autenticador_confirmado(usuario))
    return pessoas


def entrar(usuario: Any, dispositivo: Any) -> str:
    """Access token da plataforma pelo login de verdade."""
    liberar_codigo(dispositivo)
    resposta = cliente(HOST_PLATAFORMA).post(
        "/api/plataforma/auth/entrar/",
        {"email": usuario.email, "senha": SENHA, "codigo": codigo_atual(dispositivo)},
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()
    connection.set_schema_to_public()
    return str(resposta.json()["access"])
