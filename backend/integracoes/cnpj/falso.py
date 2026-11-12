"""CNPJs fictícios do seed Moto Rápida, para desenvolvimento e testes.

Qualquer outro não é achado."""

from . import DadosDoCnpj

CNPJS = {
    "12345678000195": DadosDoCnpj(
        "Moto Rápida Locações Ltda", "Moto Rápida", "Fortaleza", "CE", ativo=True
    ),
}


class CnpjFalso:
    def consultar(self, cnpj: str) -> DadosDoCnpj | None:
        return CNPJS.get(cnpj)
