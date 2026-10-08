"""Números sequenciais por empresa, sem buracos (ADR 0009)."""

from django.db import transaction

from comum.models import Sequencia

# Largura mínima do número por prefixo. Passou da largura, o número cresce (LOC-10000).
LARGURAS = {"LOC": 4, "VEN": 4, "OS": 3, "FAT": 4}
LARGURA_PADRAO = 4


def formatar_codigo(prefixo: str, numero: int) -> str:
    largura = LARGURAS.get(prefixo, LARGURA_PADRAO)
    return f"{prefixo}-{numero:0{largura}d}"


def proximo_numero(chave: str) -> int:
    """Reserva o próximo número da chave no schema atual.

    Usa `SELECT ... FOR UPDATE`: duas transações concorrentes esperam uma pela outra, e um
    rollback devolve o número. Precisa rodar dentro da transação que grava o registro.
    """
    with transaction.atomic():
        Sequencia.objects.get_or_create(chave=chave)
        sequencia = Sequencia.objects.select_for_update().get(chave=chave)
        sequencia.ultimo_numero += 1
        sequencia.save(update_fields=["ultimo_numero"])
        return sequencia.ultimo_numero


def ajustar_sequencia(chave: str, ultimo_numero: int) -> None:
    """Para o seed: faz o próximo código sair depois dos números de referência."""
    Sequencia.objects.update_or_create(chave=chave, defaults={"ultimo_numero": ultimo_numero})
