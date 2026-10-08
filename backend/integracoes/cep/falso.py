"""CEPs do seed Moto Rápida, para desenvolvimento e testes. Qualquer outro não existe."""

from . import Endereco

CEPS = {
    "60325000": Endereco("60325000", "Av. Bezerra de Menezes", "São Gerardo", "Fortaleza", "CE"),
    "61600000": Endereco("61600000", "Rua Coronel Correia", "Centro", "Caucaia", "CE"),
    "60840280": Endereco("60840280", "Av. Washington Soares", "Messejana", "Fortaleza", "CE"),
}


class CepFalso:
    def buscar(self, cep: str) -> Endereco | None:
        return CEPS.get(cep)
