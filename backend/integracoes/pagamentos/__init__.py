"""Pagamentos atrás de uma interface (`base.py`). `provedor()` escolhe a implementação por
`GIRO_PROVEDOR_PAGAMENTOS`: `falso` (padrão em desenvolvimento e testes) ou `asaas` (T-029).

O token do webhook nunca fica guardado em claro: `hash_do_token` é o que vai para
`plataforma.ContaPagamento.webhook_token_hash` (S-14).
"""

import hashlib
from typing import Protocol

from django.conf import settings

from .base import ContaPagamentoRef, ProvedorPagamentos

CABECALHO_DO_TOKEN = "asaas-access-token"  # noqa: S105 - nome do cabeçalho, não o token
CONTA_PRINCIPAL = "principal"


def provedor() -> ProvedorPagamentos:
    nome = getattr(settings, "GIRO_PROVEDOR_PAGAMENTOS", "falso")
    if nome == "asaas":
        from .asaas import Asaas

        return Asaas()
    if nome != "falso":
        raise ValueError(f"Provedor de pagamentos desconhecido: {nome}")
    from .falso import PagamentosFalso

    return PagamentosFalso()


class _ComChave(Protocol):
    conta_externa_id: str

    def chave_api_cifrada_claro(self) -> str: ...


def referencia(conta: _ComChave) -> ContaPagamentoRef:
    """A `plataforma.ContaPagamento` como a interface a vê. A chave segue cifrada: a
    implementação decifra na hora da chamada ao parceiro (S-05)."""
    return ContaPagamentoRef(conta.conta_externa_id, conta.chave_api_cifrada_claro)


def conta_principal() -> ContaPagamentoRef:
    """A conta do Giro no parceiro (faturas da assinatura): sem subconta, com a chave do ambiente
    (`GIRO_ASAAS_CHAVE_API`)."""
    return ContaPagamentoRef(CONTA_PRINCIPAL)


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
