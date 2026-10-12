"""Pagamentos falsos para desenvolvimento e testes: as cobranças ficam na memória.

`simular_pagamento(cobranca_id, valor_centavos=None)` faz o parceiro dizer que a cobrança foi
paga (com outro valor, se pedido) e devolve o corpo do webhook que ele mandaria (CA-017-07).
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from itertools import count
from typing import Any

from comum import relogio

from . import CABECALHO_DO_TOKEN
from .base import (
    Cobranca,
    ContaPagamentoRef,
    EventoWebhook,
    PedidoCobranca,
    SituacaoCobranca,
)


@dataclass
class _Guardada:
    cobranca: Cobranca
    situacao: SituacaoCobranca
    referencia_externa: str


cobrancas: dict[str, _Guardada] = {}
_numeros = count(1)


def limpar() -> None:
    cobrancas.clear()


class PagamentosFalso:
    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca:
        numero = next(_numeros)
        cobranca_id = f"pay_falso_{numero:06d}"
        pix = pedido.tipo == "pix"
        cobranca = Cobranca(
            id=cobranca_id,
            tipo=pedido.tipo,
            valor_centavos=pedido.valor_centavos,
            vencimento=pedido.vencimento,
            pix_copia_e_cola=f"00020126falso{cobranca_id}5204000053039865802BR" if pix else "",
            qr_code_url=f"https://pagamentos.falso/qr/{cobranca_id}.png" if pix else "",
            linha_digitavel="" if pix else f"23790.00009 {numero:05d}.000000 00000.000000 1",
            boleto_url="" if pix else f"https://pagamentos.falso/boleto/{cobranca_id}.pdf",
        )
        cobrancas[cobranca_id] = _Guardada(
            cobranca, SituacaoCobranca("aguardando"), pedido.referencia_externa
        )
        return cobranca

    def cancelar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> None:
        guardada = cobrancas.get(cobranca_id)
        if guardada is not None and guardada.situacao.status == "aguardando":
            guardada.situacao = replace(guardada.situacao, status="cancelada")

    def consultar_cobranca(self, conta: ContaPagamentoRef, cobranca_id: str) -> SituacaoCobranca:
        guardada = cobrancas.get(cobranca_id)
        return guardada.situacao if guardada is not None else SituacaoCobranca("cancelada")

    def validar_webhook(self, cabecalhos: Mapping[str, str], corpo: bytes) -> EventoWebhook | None:
        token = cabecalhos.get(CABECALHO_DO_TOKEN, "")
        try:
            dados = json.loads(corpo)
            pagamento = dados["payment"]
            return EventoWebhook(
                provedor="asaas",
                evento_id=str(dados["id"]),
                tipo=str(dados["event"]),
                cobranca_id=str(pagamento["id"]),
                referencia_externa=str(pagamento.get("externalReference") or ""),
                token=token,
            )
        except (ValueError, KeyError, TypeError):
            return None


def simular_pagamento(
    cobranca_id: str, valor_centavos: int | None = None, *, evento_id: str | None = None
) -> dict[str, Any]:
    """A cobrança fica paga no parceiro; devolve o corpo do webhook `PAYMENT_RECEIVED`."""
    guardada = cobrancas[cobranca_id]
    pago_em: datetime = relogio.agora()
    guardada.situacao = SituacaoCobranca(
        "paga",
        valor_pago_centavos=valor_centavos or guardada.cobranca.valor_centavos,
        pago_em=pago_em,
        forma=guardada.cobranca.tipo,
    )
    return corpo_do_webhook(cobranca_id, "PAYMENT_RECEIVED", evento_id)


def simular_estorno(cobranca_id: str, *, evento_id: str | None = None) -> dict[str, Any]:
    guardada = cobrancas[cobranca_id]
    guardada.situacao = replace(guardada.situacao, status="estornada")
    return corpo_do_webhook(cobranca_id, "PAYMENT_REFUNDED", evento_id)


def corpo_do_webhook(cobranca_id: str, evento: str, evento_id: str | None = None) -> dict[str, Any]:
    guardada = cobrancas[cobranca_id]
    return {
        "id": evento_id or f"evt_{cobranca_id}_{evento.lower()}",
        "event": evento,
        "payment": {
            "id": cobranca_id,
            "externalReference": guardada.referencia_externa,
            # O valor do corpo não vale: a baixa consulta o parceiro (S-14).
            "value": guardada.cobranca.valor_centavos / 100,
        },
    }
