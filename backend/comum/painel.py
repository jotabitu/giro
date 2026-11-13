"""Geração do cache do painel por empresa (`docs/api/painel.md`, "Cache no backend").

A chave do início e dos contadores leva a geração da empresa. Quem muda um número que precisa
aparecer na hora (a transferência no Detran da quitação, `LOC-16`, T-420) chama `renovar()`:
a geração sobe e todo cache do painel daquela empresa deixa de valer, de todas as pessoas, sem
procurar chave por chave. O cache do Django já separa por schema (`django_tenants.cache`).
"""

from django.core.cache import cache
from django.db import transaction
from django_tenants.utils import schema_context

from comum.conexao import schema_atual

CHAVE = "painel:geracao"


def geracao() -> int:
    return int(cache.get(CHAVE) or 0)


def _subir() -> None:
    try:
        cache.incr(CHAVE)
    except ValueError:  # ainda não existe
        cache.set(CHAVE, 1, None)


def renovar() -> None:
    """Depois do commit, na empresa de agora: antes dele, outra leitura podia guardar o número
    velho de novo. Sem transação aberta, roda na hora."""
    schema = schema_atual()

    def _depois() -> None:
        with schema_context(schema):
            _subir()

    transaction.on_commit(_depois)
