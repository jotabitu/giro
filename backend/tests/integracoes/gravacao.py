"""Transporte que devolve as respostas gravadas do Asaas (`gravacoes/asaas.json`), sem rede.

Confere cada chamada contra a gravação (método, caminho e chaves da consulta), guarda o corpo
enviado para o teste conferir e falha se sobrar ou faltar chamada.
"""

import json
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from integracoes.pagamentos.asaas import Asaas

GRAVACOES = json.loads(
    (Path(__file__).parent / "gravacoes" / "asaas.json").read_text(encoding="utf-8")
)
URL = "https://asaas.teste/v3"
CHAVE_DA_SUBCONTA = "chave-de-teste-da-subconta"  # nunca uma chave de verdade
CHAVE_PRINCIPAL = "chave-de-teste-da-conta-principal"


class Gravacao:
    def __init__(self, *casos: str) -> None:
        self.esperadas: list[dict[str, Any]] = [i for caso in casos for i in GRAVACOES[caso]]
        self.feitas: list[dict[str, Any]] = []

    def __call__(
        self, metodo: str, url: str, corpo: bytes | None, cabecalhos: Mapping[str, str]
    ) -> tuple[int, bytes]:
        if not self.esperadas:
            raise AssertionError(f"Chamada a mais: {metodo} {url}")
        esperada = self.esperadas.pop(0)
        partes = urlsplit(url)
        caminho = partes.path.removeprefix("/v3")
        consulta = {k: v[0] for k, v in parse_qs(partes.query).items()}
        assert (metodo, caminho) == (esperada["metodo"], esperada["caminho"])
        assert sorted(consulta) == sorted(esperada.get("consulta", []))
        self.feitas.append(
            {
                "metodo": metodo,
                "caminho": caminho,
                "consulta": consulta,
                "corpo": json.loads(corpo, parse_float=Decimal) if corpo else None,
                "chave": cabecalhos.get("access_token"),
                "cabecalhos": dict(cabecalhos),
            }
        )
        resposta = esperada["resposta"]
        return resposta["status"], json.dumps(resposta["corpo"]).encode()

    def corpo(self, metodo: str, caminho: str) -> Any:
        for feita in self.feitas:
            if (feita["metodo"], feita["caminho"]) == (metodo, caminho):
                return feita["corpo"]
        raise AssertionError(f"Sem chamada {metodo} {caminho}")

    def conferir_fim(self) -> None:
        assert not self.esperadas, f"Faltaram chamadas: {self.esperadas}"


def asaas(*casos: str) -> tuple[Asaas, Gravacao]:
    gravacao = Gravacao(*casos)
    return Asaas(url_base=URL, chave_principal=CHAVE_PRINCIPAL, transporte=gravacao), gravacao
