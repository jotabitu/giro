"""T-189 · Revisão de segurança do cartão e da conta principal (ADR 0023, T-184).

Relatório: `docs/seguranca/2026-10-15-t189-cartao-conta-principal.md`. Os testes `xfail` estritos
são os achados ainda abertos: passam a falhar como "XPASS" quando a correção entrar, e aí o `xfail`
sai junto. O M-01 foi corrigido na T-268.
"""

import contextlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from django.db import connection

from comum.models import WebhookRecebido
from integracoes.pagamentos import CABECALHO_DO_TOKEN, conta_principal, hash_do_token, provedor
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.asaas import Asaas
from integracoes.pagamentos.base import (
    CartaoGuardado,
    ContaPagamentoRef,
    Pagador,
    ParceiroIndisponivel,
    PedidoCobranca,
)

from .conftest import HOST_PLATAFORMA
from .conftest import cliente as cliente_http

WEBHOOK = "/api/webhooks/pagamentos/asaas/"
TOKEN_PRINCIPAL = "token-ficticio-da-conta-principal-t189"
TOKEN_DO_CARTAO = "tok-ficticio-do-cartao-t189"
API = Path(__file__).resolve().parents[2] / "apps"


@pytest.fixture
def moto(criar_empresa):
    pagamentos.limpar()
    yield criar_empresa()
    pagamentos.limpar()


def test_adr_0023_aviso_guardado_sem_o_token_do_cartao(
    moto, settings, django_capture_on_commit_callbacks
):
    """O aviso do parceiro traz o `creditCard` da cobrança paga no cartão (como a consulta,
    `gravacoes/asaas.json`). O Giro grava o aviso, mas o token só pode existir cifrado na forma
    de pagamento (ADR 0023, item 2)."""
    settings.GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH = hash_do_token(TOKEN_PRINCIPAL)
    cobranca = provedor().criar_cobranca(
        conta_principal(),
        PedidoCobranca("cartao_link", 44900, date(2026, 10, 22), "f-1", Pagador("x")),
    )
    corpo = pagamentos.simular_pagamento(cobranca.id, evento_id="evt_t189_1")
    corpo["payment"]["creditCard"] = {
        "creditCardNumber": "4242",
        "creditCardBrand": "VISA",
        "creditCardToken": TOKEN_DO_CARTAO,
    }
    with django_capture_on_commit_callbacks(execute=True):
        resposta = cliente_http(HOST_PLATAFORMA).post(
            WEBHOOK, corpo, format="json", headers={CABECALHO_DO_TOKEN: TOKEN_PRINCIPAL}
        )
    connection.set_schema_to_public()
    assert resposta.status_code == 200
    guardado = WebhookRecebido.objects.get(evento_id="evt_t189_1")
    assert TOKEN_DO_CARTAO not in json.dumps(guardado.corpo)


@pytest.mark.xfail(
    strict=True,
    reason="M-02 da T-189: subconta sem chave cai na chave da conta principal",
    raises=AssertionError,
)
def test_adr_0007_subconta_sem_chave_nunca_usa_a_chave_principal():
    """Uma subconta cuja chave volta vazia não pode falar com o parceiro como a conta do Giro:
    a cobrança da locadora iria para a conta principal (e o dinheiro, para o Giro)."""
    chaves: list[str] = []

    def transporte(_metodo: str, _url: str, _dados: Any, cabecalhos: Any) -> tuple[int, bytes]:
        chaves.append(cabecalhos["access_token"])
        return 200, b'{"id": "pay_1", "status": "PENDING", "value": 10.0}'

    asaas = Asaas(chave_principal="chave-da-conta-principal", transporte=transporte)
    subconta_sem_chave = ContaPagamentoRef("acc_subconta", lambda: "")
    with contextlib.suppress(ParceiroIndisponivel):  # recusar é o esperado
        asaas.consultar_cobranca(subconta_sem_chave, "pay_1")
    assert "chave-da-conta-principal" not in chaves


def test_adr_0023_nenhuma_rota_recebe_dado_do_cartao():
    """Nenhum serializer ou view da API aceita número, validade ou código do cartão, nem expõe o
    token (ADR 0023, itens 1 e 2). O cartão só existe na página do parceiro."""
    proibido = re.compile(
        r"\b(numero_(do_)?cartao|cartao_numero|cvv|ccv|cvc|codigo_(de_)?seguranca|"
        r"validade_(do_)?cartao|card_?number|cartao_token\w*)\b",
        re.IGNORECASE,
    )
    achados = [
        f"{arquivo.relative_to(API)}:{n}"
        for arquivo in API.glob("*/api/*.py")
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1)
        if proibido.search(linha)
    ]
    assert not achados, f"Dado do cartão na API: {achados}"


def test_adr_0023_cartao_guardado_sem_token_no_repr():
    cartao = CartaoGuardado(TOKEN_DO_CARTAO, "visa", "4242")
    assert TOKEN_DO_CARTAO not in repr(cartao)


def test_adr_0023_aviso_sem_cartao_e_a_limpeza_dos_ja_gravados(moto):
    """T-268: a regra única (`aviso_sem_cartao`) e a migração que limpa os avisos já gravados,
    no schema da empresa (as subcontas) como no `public`."""
    from importlib import import_module

    from django.apps import apps as registro

    from integracoes.pagamentos.base import aviso_sem_cartao

    bruto = {
        "event": "PAYMENT_CONFIRMED",
        "payment": {"id": "pay_1", "creditCard": {"creditCardToken": TOKEN_DO_CARTAO}},
    }
    assert aviso_sem_cartao(bruto) == {"event": "PAYMENT_CONFIRMED", "payment": {"id": "pay_1"}}
    assert "creditCard" in bruto["payment"]  # o original não muda
    assert aviso_sem_cartao({"event": "X"}) == {"event": "X"}

    antigo = WebhookRecebido.objects.create(
        provedor="asaas",
        evento_id="evt_t268_antigo",
        recebido_em="2026-10-07T10:00:00Z",
        corpo={"evento": {"tipo": "pago"}, "bruto": bruto},
    )
    import_module("comum.migrations.0003_aviso_sem_cartao").limpar(registro, None)
    antigo.refresh_from_db()
    assert TOKEN_DO_CARTAO not in json.dumps(antigo.corpo)
    assert antigo.corpo["bruto"]["payment"] == {"id": "pay_1"}
    assert antigo.corpo["evento"] == {"tipo": "pago"}
