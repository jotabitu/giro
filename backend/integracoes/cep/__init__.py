"""Consulta de CEP atrás de uma interface (contrato de filiais; CLI-01 também usa).

`buscar_cep(cep)` escolhe o provedor por `GIRO_PROVEDOR_CEP` (`falso` em dev e testes,
`viacep` em homologação e produção) e guarda a resposta em cache por 30 dias.
"""

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Protocol

from django.conf import settings
from django.core.cache import cache

CACHE_DO_CEP = int(timedelta(days=30).total_seconds())


@dataclass(frozen=True)
class Endereco:
    cep: str
    logradouro: str
    bairro: str
    cidade: str
    uf: str


class CepIndisponivel(Exception):
    """O provedor não respondeu: não guarda em cache, para tentar de novo depois."""


class ProvedorDeCep(Protocol):
    def buscar(self, cep: str) -> Endereco | None: ...


def provedor() -> ProvedorDeCep:
    nome = getattr(settings, "GIRO_PROVEDOR_CEP", "falso")
    if nome == "viacep":
        from .viacep import ViaCep

        return ViaCep()
    from .falso import CepFalso

    return CepFalso()


def buscar_cep(cep: str) -> Endereco | None:
    """`None` se o CEP não existe. Só dígitos na entrada (8)."""
    chave = f"cep:{cep}"
    guardado = cache.get(chave)
    if guardado is not None:
        return Endereco(**guardado) if guardado else None
    try:
        endereco = provedor().buscar(cep)
    except CepIndisponivel:
        return None
    cache.set(chave, asdict(endereco) if endereco else {}, CACHE_DO_CEP)
    return endereco
