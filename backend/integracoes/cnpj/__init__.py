"""Consulta pública de CNPJ atrás de uma interface (compra pública, ADR 0039).

`consultar_cnpj(cnpj)` escolhe o provedor por `GIRO_PROVEDOR_CNPJ` (`falso` em dev e testes,
`brasilapi` em homologação e produção) e guarda a resposta em cache por 7 dias. A consulta só
**preenche** razão social, nome, cidade e UF no checkout: a pessoa confere e edita, e a compra
nunca depende dela. Provedor fora do ar ou CNPJ não achado: a pessoa digita.
"""

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Protocol

from django.conf import settings
from django.core.cache import cache

CACHE_DO_CNPJ = int(timedelta(days=7).total_seconds())


@dataclass(frozen=True)
class DadosDoCnpj:
    razao_social: str
    nome_fantasia: str
    cidade: str
    uf: str
    ativo: bool  # situação cadastral "ATIVA" na Receita


class CnpjIndisponivel(Exception):
    """O provedor não respondeu: não guarda em cache, para tentar de novo depois."""


class ProvedorDeCnpj(Protocol):
    def consultar(self, cnpj: str) -> DadosDoCnpj | None: ...


def provedor() -> ProvedorDeCnpj:
    nome = getattr(settings, "GIRO_PROVEDOR_CNPJ", "falso")
    if nome == "brasilapi":
        from .brasilapi import BrasilApi

        return BrasilApi()
    from .falso import CnpjFalso

    return CnpjFalso()


def consultar_cnpj(cnpj: str) -> DadosDoCnpj | None:
    """`None` se o CNPJ não foi achado ou o provedor está fora. Só dígitos na entrada (14)."""
    chave = f"cnpj:{cnpj}"
    guardado = cache.get(chave)
    if guardado is not None:
        return DadosDoCnpj(**guardado) if guardado else None
    try:
        dados = provedor().consultar(cnpj)
    except CnpjIndisponivel:
        return None
    cache.set(chave, asdict(dados) if dados else {}, CACHE_DO_CNPJ)
    return dados
