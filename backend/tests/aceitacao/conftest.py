"""Fixtures dos testes de aceitação: relógio congelado, planos, empresas e equipe da plataforma."""

import time
from collections.abc import Callable
from typing import Any

import pytest
from django.db import connection
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
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


def codigo_atual(dispositivo: TOTPDevice) -> str:
    totp = TOTP(dispositivo.bin_key, dispositivo.step, dispositivo.t0, dispositivo.digits)
    totp.time = time.time()
    return f"{totp.token():0{dispositivo.digits}d}"


def liberar_codigo(dispositivo: TOTPDevice) -> None:
    """O django-otp recusa o mesmo código duas vezes no mesmo passo de 30 s (replay)."""
    TOTPDevice.objects.filter(pk=dispositivo.pk).update(last_t=-1)
    dispositivo.refresh_from_db()


@pytest.fixture
def equipe(publico) -> dict[str, tuple[Any, TOTPDevice]]:
    """A equipe do seed, ativa e com autenticador confirmado."""
    from apps.contas.models import Usuario

    pessoas = {}
    for nome, (email, funcao) in EQUIPE_SEED.items():
        usuario = Usuario.objects.create_user(email, SENHA, nome=nome, funcao_plataforma=funcao)
        dispositivo = TOTPDevice.objects.create(user=usuario, name="autenticador", confirmed=True)
        pessoas[nome] = (usuario, dispositivo)
    return pessoas


def entrar(usuario: Any, dispositivo: TOTPDevice) -> str:
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
