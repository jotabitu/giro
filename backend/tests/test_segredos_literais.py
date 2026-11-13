"""Segredos lidos literalmente, sem a expansão de `$` do django-environ (T-475)."""

import importlib
from collections.abc import Iterator

import pytest

import config.settings.base as base


@pytest.fixture
def recarregar_base(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield
    monkeypatch.undo()  # recarrega com o ambiente original, não com o do teste
    importlib.reload(base)


def test_t475_chave_asaas_com_cifrao(
    monkeypatch: pytest.MonkeyPatch, recarregar_base: None
) -> None:
    monkeypatch.setenv("GIRO_ASAAS_CHAVE_API", "$aact_hmlg_exemplo")
    importlib.reload(base)
    assert base.GIRO_ASAAS_CHAVE_API == "$aact_hmlg_exemplo"


def test_t475_segredos_com_cifrao(monkeypatch: pytest.MonkeyPatch, recarregar_base: None) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "$segredo-de-exemplo")
    monkeypatch.setenv("GIRO_PEPPER_HMAC", "$pepper-de-exemplo")
    importlib.reload(base)
    assert base.SECRET_KEY == "$segredo-de-exemplo"
    assert base.GIRO_PEPPER_HMAC == "$pepper-de-exemplo"


def test_t475_valor_sem_cifrao_continua_igual(
    monkeypatch: pytest.MonkeyPatch, recarregar_base: None
) -> None:
    monkeypatch.setenv("EMAIL_HOST_PASSWORD", "senha-de-exemplo")
    monkeypatch.delenv("S3_CHAVE_SECRETA", raising=False)
    importlib.reload(base)
    assert base.EMAIL_HOST_PASSWORD == "senha-de-exemplo"
    assert base.S3_CHAVE_SECRETA == ""
