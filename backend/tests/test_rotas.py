"""Rotas por host: Admin só no public (ADR 0013, item 4); host desconhecido responde 404."""

import pytest
from django.conf import settings


@pytest.mark.parametrize("caminho", ["/admin/", "/admin/login/"])
def test_admin_nao_existe_no_host_da_empresa(client, db, caminho):
    resposta = client.get(caminho, HTTP_HOST="empresa-a.localhost")
    assert resposta.status_code == 404


def test_admin_do_public_pede_login_com_2_etapas(client, publico):
    resposta = client.get("/admin/", HTTP_HOST="admin.localhost")
    assert resposta.status_code == 302
    resposta = client.get("/admin/login/", HTTP_HOST="admin.localhost")
    assert resposta.status_code == 200
    assert "otp_token" in resposta.content.decode()


def test_host_sem_empresa_responde_404(client, db):
    resposta = client.get("/api/schema/", HTTP_HOST="nao-existe.localhost")
    assert resposta.status_code == 404


@pytest.mark.parametrize("host", ["empresa-a.localhost", "admin.localhost", "localhost"])
def test_schema_openapi_responde(client, db, host):
    resposta = client.get("/api/schema/", HTTP_HOST=host)
    assert resposta.status_code == 200
    assert b"openapi" in resposta.content


def test_admin_so_nos_apps_do_public():
    assert "django.contrib.admin" in settings.SHARED_APPS
    assert "django.contrib.admin" not in settings.TENANT_APPS


def test_sem_cors():
    # ADR 0013, item 5: frontend e API na mesma origem.
    assert "corsheaders" not in settings.INSTALLED_APPS
