"""Pagamentos atrás de uma interface (`base.py`). `provedor()` escolhe a implementação por
`GIRO_PROVEDOR_PAGAMENTOS`: só o `falso` até a T-029 trazer o Asaas.

O token do webhook nunca fica guardado em claro: `hash_do_token` é o que vai para
`plataforma.ContaPagamento.webhook_token_hash` (S-14).
"""

import hashlib

from django.conf import settings

from .base import ProvedorPagamentos

CABECALHO_DO_TOKEN = "asaas-access-token"  # noqa: S105 - nome do cabeçalho, não o token


def provedor() -> ProvedorPagamentos:
    nome = getattr(settings, "GIRO_PROVEDOR_PAGAMENTOS", "falso")
    if nome != "falso":
        raise ValueError(f"Provedor de pagamentos desconhecido: {nome}")
    from .falso import PagamentosFalso

    return PagamentosFalso()


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
