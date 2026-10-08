"""ViaCEP (viacep.com.br): público, sem chave e sem custo. Só a biblioteca padrão."""

import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

from . import CepIndisponivel, Endereco

logger = logging.getLogger(__name__)
TEMPO_LIMITE_SEGUNDOS = 5


class ViaCep:
    def buscar(self, cep: str) -> Endereco | None:
        if not (len(cep) == 8 and cep.isdigit()):
            return None
        url = f"https://viacep.com.br/ws/{cep}/json/"
        try:
            with urlopen(url, timeout=TEMPO_LIMITE_SEGUNDOS) as resposta:
                dados = json.load(resposta)
        except (URLError, TimeoutError, ValueError) as erro:
            logger.warning("ViaCEP indisponível: %s", erro)
            raise CepIndisponivel from erro
        if dados.get("erro"):
            return None
        return Endereco(
            cep=cep,
            logradouro=dados.get("logradouro", ""),
            bairro=dados.get("bairro", ""),
            cidade=dados.get("localidade", ""),
            uf=dados.get("uf", ""),
        )
