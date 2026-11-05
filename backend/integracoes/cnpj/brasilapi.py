"""BrasilAPI (brasilapi.com.br/api/cnpj/v1): pública, sem chave e sem custo, com os dados
abertos da Receita. Só a biblioteca padrão, como o ViaCEP (ADR 0039)."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import CnpjIndisponivel, DadosDoCnpj

logger = logging.getLogger(__name__)
TEMPO_LIMITE_SEGUNDOS = 5
URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"


def _texto(dados: dict[str, object], campo: str, tamanho: int) -> str:
    valor = dados.get(campo)
    return str(valor).strip()[:tamanho] if isinstance(valor, str) else ""


class BrasilApi:
    def consultar(self, cnpj: str) -> DadosDoCnpj | None:
        if not (len(cnpj) == 14 and cnpj.isdigit()):
            return None
        # URL fixa em https, só com os 14 dígitos: nada de esquema vindo de fora.
        pedido = Request(URL.format(cnpj=cnpj), headers={"User-Agent": "Giro"})  # noqa: S310
        try:
            with urlopen(pedido, timeout=TEMPO_LIMITE_SEGUNDOS) as resposta:  # noqa: S310
                dados = json.load(resposta)
        except HTTPError as erro:
            if erro.code in (400, 404):
                return None
            logger.warning("BrasilAPI indisponível: HTTP %s", erro.code)
            raise CnpjIndisponivel from erro
        except (URLError, TimeoutError, ValueError) as erro:
            logger.warning("BrasilAPI indisponível: %s", type(erro).__name__)
            raise CnpjIndisponivel from erro
        if not isinstance(dados, dict):
            raise CnpjIndisponivel
        uf = _texto(dados, "uf", 2).upper()
        return DadosDoCnpj(
            razao_social=_texto(dados, "razao_social", 150),
            nome_fantasia=_texto(dados, "nome_fantasia", 80),
            cidade=_texto(dados, "municipio", 80).title(),
            uf=uf,
            ativo=_texto(dados, "descricao_situacao_cadastral", 30).upper() == "ATIVA",
        )
