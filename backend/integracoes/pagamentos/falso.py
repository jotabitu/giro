"""Pagamentos falsos para desenvolvimento e testes: as cobranças ficam na memória.

`simular_pagamento(cobranca_id, valor_centavos=None)` faz o parceiro dizer que a cobrança foi
paga (com outro valor, se pedido) e devolve o corpo do webhook que ele mandaria (CA-017-07).
Subcontas e autorizações recorrentes também ficam na memória (T-029).

Conta principal (T-184): os pagadores ficam em `pagadores`; a cobrança `cartao_link` paga por
`simular_pagamento` devolve um cartão guardado (`CARTAO_DE_TESTE`), e `recusar_cartao(token)` faz
o parceiro recusar as próximas cobranças naquele token. `autorizar_pix(autorizacao_id)` ativa a
autorização do Pix Automático e devolve o corpo do aviso (PLT-13).
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
    Autorizacao,
    CartaoGuardado,
    CartaoRecusado,
    Cobranca,
    ContaPagamentoRef,
    DadosEmpresa,
    EventoWebhook,
    Pagador,
    PedidoCobranca,
    PedidoRecorrencia,
    SituacaoCobranca,
    Subconta,
)


@dataclass
class _Guardada:
    cobranca: Cobranca
    situacao: SituacaoCobranca
    referencia_externa: str


cobrancas: dict[str, _Guardada] = {}
subcontas: dict[str, str] = {}  # conta_externa_id -> status
autorizacoes: dict[str, Autorizacao] = {}
pagadores: dict[str, Pagador] = {}  # id do cliente na conta principal -> o que foi mandado
tokens_recusados: set[str] = set()
# FIN-04 (T-307): com `sem_pix_no_boleto()`, o boleto sai sem o Pix, como a conta sem chave Pix.
_boleto_sem_pix: list[bool] = [False]
_numeros = count(1)

CARTAO_DE_TESTE = ("visa", "4242")


def limpar() -> None:
    cobrancas.clear()
    subcontas.clear()
    autorizacoes.clear()
    pagadores.clear()
    tokens_recusados.clear()
    _boleto_sem_pix[0] = False


def sem_pix_no_boleto() -> None:
    """Simula "Pix não disponível" no boleto (o 400 do `pixQrCode`) até o próximo `limpar()`."""
    _boleto_sem_pix[0] = True


def recusar_cartao(token: str) -> None:
    tokens_recusados.add(token)


class PagamentosFalso:
    def criar_subconta(self, empresa: DadosEmpresa) -> Subconta:
        numero = next(_numeros)
        conta_externa_id = f"acc_falso_{numero:06d}"
        subcontas[conta_externa_id] = "pendente"
        return Subconta(conta_externa_id, f"wal_falso_{numero:06d}", f"chave_falsa_{numero:06d}")

    def consultar_subconta(self, conta: ContaPagamentoRef) -> str:
        return subcontas.get(conta.conta_externa_id, "pendente")

    def criar_autorizacao_recorrente(
        self, conta: ContaPagamentoRef, pedido: PedidoRecorrencia
    ) -> Autorizacao:
        autorizacao = Autorizacao(
            f"aut_falso_{next(_numeros):06d}", "pendente", "00020126falsoautorizacao"
        )
        autorizacoes[autorizacao.id] = autorizacao
        return autorizacao

    def cobrar_com_autorizacao(
        self, conta: ContaPagamentoRef, autorizacao_id: str, pedido: PedidoCobranca
    ) -> Cobranca:
        if autorizacoes[autorizacao_id].status != "ativa":
            raise ValueError("Autorização que não está ativa não cobra.")
        return self.criar_cobranca(conta, pedido)

    def cancelar_autorizacao(self, conta: ContaPagamentoRef, autorizacao_id: str) -> None:
        if autorizacao_id in autorizacoes:
            autorizacoes[autorizacao_id] = replace(autorizacoes[autorizacao_id], status="cancelada")

    def consultar_autorizacao(self, conta: ContaPagamentoRef, autorizacao_id: str) -> Autorizacao:
        return autorizacoes.get(autorizacao_id) or Autorizacao(autorizacao_id, "cancelada")

    def criar_ou_atualizar_pagador(self, conta: ContaPagamentoRef, pagador: Pagador) -> str:
        cliente_id = pagador.id_externo or f"cus_falso_{next(_numeros):06d}"
        pagadores[cliente_id] = pagador
        return cliente_id

    def cobrar_cartao_salvo(
        self, conta: ContaPagamentoRef, token: str, pedido: PedidoCobranca
    ) -> Cobranca:
        if token in tokens_recusados:
            raise CartaoRecusado("O cartão foi recusado.")
        cobranca = self.criar_cobranca(conta, replace(pedido, tipo="cartao"))
        bandeira, final = CARTAO_DE_TESTE
        cobrancas[cobranca.id].situacao = SituacaoCobranca(
            "paga",
            valor_pago_centavos=pedido.valor_centavos,
            pago_em=relogio.agora(),
            forma="cartao",
            cartao=CartaoGuardado(token, bandeira, final),
        )
        return cobranca

    def criar_cobranca(self, conta: ContaPagamentoRef, pedido: PedidoCobranca) -> Cobranca:
        numero = next(_numeros)
        cobranca_id = f"pay_falso_{numero:06d}"
        pix = pedido.tipo == "pix"
        cartao = pedido.tipo in ("cartao_link", "cartao")
        boleto = not pix and not cartao
        cobranca = Cobranca(
            id=cobranca_id,
            tipo=pedido.tipo,
            valor_centavos=pedido.valor_centavos,
            vencimento=pedido.vencimento,
            pix_copia_e_cola=(
                f"00020126falso{cobranca_id}5204000053039865802BR"
                if pix or (boleto and not _boleto_sem_pix[0])
                else ""
            ),
            qr_code_url=f"https://pagamentos.falso/qr/{cobranca_id}.png" if pix else "",
            linha_digitavel=f"23790.00009 {numero:05d}.000000 00000.000000 1" if boleto else "",
            boleto_url=f"https://pagamentos.falso/boleto/{cobranca_id}.pdf" if boleto else "",
            url_pagina=f"https://pagamentos.falso/pagar/{cobranca_id}" if cartao else "",
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
            if "payment" not in dados and "pixAutomaticAuthorization" in dados:
                return EventoWebhook(
                    provedor="asaas",
                    evento_id=str(dados["id"]),
                    tipo=str(dados["event"]),
                    cobranca_id="",
                    referencia_externa="",
                    token=token,
                    autorizacao_id=str(dados["pixAutomaticAuthorization"]["id"]),
                )
            pagamento = dados["payment"]
            return EventoWebhook(
                provedor="asaas",
                evento_id=str(dados["id"]),
                tipo=str(dados["event"]),
                cobranca_id=str(pagamento["id"]),
                referencia_externa=str(pagamento.get("externalReference") or ""),
                token=token,
            )
        except (ValueError, KeyError, TypeError, AttributeError):
            return None


def simular_pagamento(
    cobranca_id: str, valor_centavos: int | None = None, *, evento_id: str | None = None
) -> dict[str, Any]:
    """A cobrança fica paga no parceiro; devolve o corpo do webhook `PAYMENT_RECEIVED`."""
    guardada = cobrancas[cobranca_id]
    pago_em: datetime = relogio.agora()
    cartao = None
    forma = guardada.cobranca.tipo
    if forma in ("cartao_link", "cartao"):
        # Na página do parceiro, o cartão fica guardado para as próximas (ADR 0023).
        bandeira, final = CARTAO_DE_TESTE
        cartao = CartaoGuardado(f"tok_falso_{cobranca_id}", bandeira, final)
        forma = "cartao"
    guardada.situacao = SituacaoCobranca(
        "paga",
        valor_pago_centavos=valor_centavos or guardada.cobranca.valor_centavos,
        pago_em=pago_em,
        forma=forma,
        cartao=cartao,
        recibo_url=f"https://pagamentos.falso/recibo/{cobranca_id}",
    )
    return corpo_do_webhook(cobranca_id, "PAYMENT_RECEIVED", evento_id)


def autorizar_pix(autorizacao_id: str, *, evento_id: str | None = None) -> dict[str, Any]:
    """A autorização fica ativa no banco; devolve o corpo do aviso que o parceiro mandaria."""
    autorizacoes[autorizacao_id] = replace(autorizacoes[autorizacao_id], status="ativa")
    return {
        "id": evento_id or f"evt_{autorizacao_id}_ativada",
        "event": "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED",
        "pixAutomaticAuthorization": {"id": autorizacao_id},
    }


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
