"""T-270: o Sentry não recebe segredo nem dado pessoal (B-01 da T-189, M-03 da T-247).

Usa um transporte de mentira: o SDK monta o evento de verdade (integração do Django, escopo,
`before_send`, `EventScrubber`) e o evento fica na memória, sem rede.
"""

import json
from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from comum.sentry import limpar_evento, opcoes_do_sentry
from integracoes.pagamentos import CABECALHO_DO_TOKEN

from .conftest import HOST_PLATAFORMA
from .conftest import cliente as cliente_http

DSN = "http://chave@localhost/1"
TOKEN_DO_WEBHOOK = "token-do-webhook-que-nao-pode-sair-t270"
TOKEN_DO_CARTAO = "token-do-cartao-que-nao-pode-sair-t270"
CPF_LIDO = "529.982.247-25"
NOME_LIDO = "Maria Exemplo da Silva"


class TransporteDeMentira(Transport):
    def __init__(self, eventos: list[dict[str, Any]]) -> None:
        super().__init__()
        self.eventos = eventos

    def capture_envelope(self, envelope: Any) -> None:
        for item in envelope.items:
            if item.type == "event":
                self.eventos.append(item.payload.json)


@pytest.fixture
def eventos() -> Iterator[list[dict[str, Any]]]:
    """Liga o Sentry com as opções do Giro; devolve a lista dos eventos que sairiam."""
    capturados: list[dict[str, Any]] = []
    sentry_sdk.init(
        **{**opcoes_do_sentry(DSN, "teste"), "transport": TransporteDeMentira(capturados)}
    )
    yield capturados
    sentry_sdk.init()  # sem DSN: volta a desligado


def _texto(eventos: list[dict[str, Any]]) -> str:
    return json.dumps(eventos, ensure_ascii=False)


def test_b01_t189_erro_no_webhook_sem_token_nem_corpo(
    publico: None, eventos: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def quebra() -> None:
        raise RuntimeError("falha provocada pelo teste T-270")

    monkeypatch.setattr("apps.financeiro.api.views.provedor_de_pagamentos", quebra)
    api = cliente_http(HOST_PLATAFORMA)
    api.raise_request_exception = False
    resposta = api.post(
        "/api/webhooks/pagamentos/asaas/",
        {"event": "PAYMENT_RECEIVED", "creditCardToken": TOKEN_DO_CARTAO},
        format="json",
        headers={CABECALHO_DO_TOKEN: TOKEN_DO_WEBHOOK},
    )
    assert resposta.status_code == 500
    assert eventos, "o erro devia ter virado um evento"
    texto = _texto(eventos)
    assert "falha provocada pelo teste T-270" in texto  # o evento existe e tem a exceção
    assert TOKEN_DO_WEBHOOK not in texto
    assert TOKEN_DO_CARTAO not in texto
    assert "PAYMENT_RECEIVED" not in texto  # nem o corpo do aviso
    assert "headers" not in eventos[0]["request"]  # rota de webhook: sem cabeçalho nenhum


def test_m03_t247_variaveis_locais_fora_do_evento(eventos: list[dict[str, Any]]) -> None:
    def le_documento() -> None:
        leitura = {"cpf": CPF_LIDO, "nome": NOME_LIDO}
        raise ValueError(f"falha depois de ler {len(leitura)} campos")

    with pytest.raises(ValueError):
        try:
            le_documento()
        except ValueError:
            sentry_sdk.capture_exception()
            raise
    texto = _texto(eventos)
    assert "falha depois de ler 2 campos" in texto and "le_documento" in texto  # rastro fica
    assert CPF_LIDO not in texto and NOME_LIDO not in texto


def test_m03_t247_sem_a_opcao_o_cpf_sairia(eventos: list[dict[str, Any]]) -> None:
    """Controle: com o padrão do SDK, a variável local vai no evento (o teste acima prova algo)."""
    capturados: list[dict[str, Any]] = []
    padrao = {
        k: v
        for k, v in opcoes_do_sentry(DSN, "teste").items()
        if k not in {"include_local_variables"}
    }
    sentry_sdk.init(**{**padrao, "transport": TransporteDeMentira(capturados)})

    def le_documento() -> None:
        leitura = {"cpf": CPF_LIDO}
        raise ValueError(f"erro {len(leitura)}")

    try:
        le_documento()
    except ValueError:
        sentry_sdk.capture_exception()
    assert CPF_LIDO in _texto(capturados)


def test_b01_t189_scrubber_pega_token_do_cartao_em_qualquer_nivel(
    eventos: list[dict[str, Any]],
) -> None:
    sentry_sdk.set_extra("aviso", {"payment": {"creditCardToken": TOKEN_DO_CARTAO}})
    sentry_sdk.capture_message("aviso de teste T-270")
    assert eventos and TOKEN_DO_CARTAO not in _texto(eventos)


def test_t270_limpar_evento_cabecalhos_celery_e_corpo() -> None:
    evento: dict[str, Any] = {
        "request": {
            "url": "https://motorapida.localhost/api/clientes/",
            "data": {"cpf": CPF_LIDO},
            "cookies": {"sessao": "x"},
            "headers": {"Asaas-Access-Token": "t", "Accept": "application/json", "Cookie": "c"},
        },
        "extra": {"celery-job": {"task_name": "tarefa", "args": [CPF_LIDO], "kwargs": {"a": 1}}},
    }
    saida = limpar_evento(evento, {})
    assert "data" not in saida["request"] and "cookies" not in saida["request"]
    assert saida["request"]["headers"] == {
        "Asaas-Access-Token": "[Filtrado]",
        "Accept": "application/json",
        "Cookie": "[Filtrado]",
    }
    assert saida["extra"]["celery-job"] == {"task_name": "tarefa"}
    assert CPF_LIDO not in json.dumps(saida)
