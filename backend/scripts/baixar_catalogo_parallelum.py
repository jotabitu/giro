"""Baixa as marcas e os modelos da API aberta da Parallelum para um CSV (VEI-08, ADR 0031).

    python backend/scripts/baixar_catalogo_parallelum.py <saida.csv>

Roda fora do servidor, na máquina de alguém da equipe, só com a biblioteca padrão. Lê
`/{tipo}/brands` e `/{tipo}/brands/{code}/models` de `cars` (carro) e `motorcycles` (moto), sem
`trucks`, com um pedido por segundo. Sem token, a API permite 500 pedidos por dia, e uma carga
usa cerca de 213. No 429, para com a mensagem e não grava nada. A saída é um CSV
`marca,modelo,tipo`, que vai para o comando `atualizar_catalogo_modelos` junto com a lista
própria da equipe. Não é importado pelo Django.
"""

import csv
import http.client
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

BASE = "https://parallelum.com.br/fipe/api/v2"
TIPOS = {"cars": "carro", "motorcycles": "moto"}
INTERVALO = 1.0  # segundos entre pedidos
TENTATIVAS = 3  # para a conexão que cai no meio, não para o 429
ESPERA_ANTES_DE_TENTAR_DE_NOVO = 5.0
CABECALHO = ("marca", "modelo", "tipo")


class LimiteAtingido(Exception):
    """A API respondeu 429: o limite do dia acabou."""


def buscar(url: str, esperar: Callable[[float], None] = time.sleep) -> Any:
    """Uma resposta da API. Falha passageira de rede tenta de novo (até `TENTATIVAS`); o 429 não."""
    if not url.startswith(f"{BASE}/"):
        raise ValueError(f"Fora da API da Parallelum: {url}")
    # A URL é sempre a `BASE` em https, conferida acima.
    pedido = urllib.request.Request(url, headers={"User-Agent": "giro-catalogo"})  # noqa: S310
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=30) as resposta:  # noqa: S310
                return json.load(resposta)
        except urllib.error.HTTPError as erro:
            if erro.code == 429:
                raise LimiteAtingido from erro
            if erro.code < 500 or tentativa == TENTATIVAS:
                raise
        except (urllib.error.URLError, http.client.HTTPException, OSError):
            if tentativa == TENTATIVAS:
                raise
        esperar(ESPERA_ANTES_DE_TENTAR_DE_NOVO * tentativa)
    raise AssertionError("inalcançável")


def baixar(
    buscar: Callable[[str], Any] = buscar,
    esperar: Callable[[float], None] = time.sleep,
) -> list[tuple[str, str, str]]:
    """Todas as linhas `(marca, modelo, tipo)`, um pedido por segundo. O 429 sobe como
    `LimiteAtingido`, antes de qualquer gravação."""
    linhas: list[tuple[str, str, str]] = []
    primeiro = True

    def pedir(caminho: str) -> Any:
        nonlocal primeiro
        if not primeiro:
            esperar(INTERVALO)
        primeiro = False
        return buscar(f"{BASE}/{caminho}")

    for tipo_api, tipo in TIPOS.items():
        for marca in pedir(f"{tipo_api}/brands"):
            for modelo in pedir(f"{tipo_api}/brands/{marca['code']}/models"):
                linhas.append((" ".join(marca["name"].split()), modelo["name"].strip(), tipo))
    return linhas


def gravar(linhas: list[tuple[str, str, str]], saida: Path) -> None:
    with saida.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(CABECALHO)
        escritor.writerows(linhas)


def main(
    argumentos: list[str],
    buscar: Callable[[str], Any] = buscar,
    esperar: Callable[[float], None] = time.sleep,
) -> int:
    if len(argumentos) != 1:
        print("Uso: baixar_catalogo_parallelum.py <saida.csv>", file=sys.stderr)
        return 2
    try:
        linhas = baixar(buscar, esperar)
    except LimiteAtingido:
        print(
            "A API da Parallelum respondeu 429: o limite de pedidos do dia acabou. "
            "Nada foi gravado. Tente de novo amanhã.",
            file=sys.stderr,
        )
        return 1
    gravar(linhas, Path(argumentos[0]))
    print(f"{len(linhas)} modelos gravados em {argumentos[0]}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
