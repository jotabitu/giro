"""Regrava o catálogo de marcas e modelos a partir das listas baixadas pela equipe (T-257, T-374).

    python manage.py atualizar_catalogo_modelos <arquivo.csv> [<arquivo.csv> ...]

A carga completa (ADR 0031) junta a saída de `scripts/baixar_catalogo_parallelum.py` com a lista
própria, que vai por último:

    python manage.py atualizar_catalogo_modelos <saida_parallelum.csv>
        apps/veiculos/dados/catalogo_modelos_proprios.csv  (na mesma linha)

Cada arquivo é um CSV em UTF-8 com as colunas `marca`, `modelo` e `tipo` (`moto` ou `carro`, no
singular ou no plural; outro tipo fica de fora). O arquivo que vem depois vence: na duplicata
(pela chave normalizada e o tipo) e na grafia da marca, que é uma só no CSV inteiro (a do último
arquivo; nele, a dos carros antes da das motos; senão, a que vier). O modelo fica como vem. O
comando não consulta a internet: a atualização é manual e vai por PR, com o
`dados/catalogo_modelos.csv` regravado sem duplicata e em ordem de marca e modelo.
"""

import csv
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.veiculos import catalogo

TIPOS_ACEITOS = {"moto": "moto", "motos": "moto", "carro": "carro", "carros": "carro"}


def ler_tabela(caminho: Path) -> tuple[list[catalogo.Modelo], int]:
    """Os modelos válidos da tabela e quantas linhas ficaram de fora (tipo fora da lista ou
    marca ou modelo vazio)."""
    modelos: list[catalogo.Modelo] = []
    ignoradas = 0
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        colunas = {c.strip().lower() for c in leitor.fieldnames or []}
        if not set(catalogo.CABECALHO) <= colunas:
            raise CommandError("O arquivo precisa das colunas marca, modelo e tipo.")
        for linha in leitor:
            dados = {(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
            tipo = TIPOS_ACEITOS.get(catalogo.normalizar(dados["tipo"]).lower())
            marca, modelo = " ".join(dados["marca"].split()), " ".join(dados["modelo"].split())
            if not (tipo and marca and modelo):
                ignoradas += 1
                continue
            modelos.append(catalogo.Modelo(marca, modelo, tipo))
    return modelos, ignoradas


def juntar(listas: list[list[catalogo.Modelo]]) -> list[catalogo.Modelo]:
    """As listas na ordem dos arquivos, com a última vencendo, e uma grafia por marca."""
    em_ordem: list[catalogo.Modelo] = []
    for lista in reversed(listas):
        em_ordem += sorted(lista, key=lambda m: m.tipo != "carro")  # estável: carros primeiro
    grafias: dict[str, str] = {}
    for modelo in em_ordem:
        grafias.setdefault(modelo.marca_normalizada, modelo.marca)
    return [catalogo.Modelo(grafias[m.marca_normalizada], m.modelo, m.tipo) for m in em_ordem]


class Command(BaseCommand):
    help = "Regrava o catálogo de marcas e modelos a partir de um ou mais CSVs da tabela FIPE."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("arquivos", type=Path, nargs="+")

    def handle(self, *args: Any, **opcoes: Any) -> None:
        caminhos: list[Path] = opcoes["arquivos"]
        for caminho in caminhos:
            if not caminho.is_file():
                raise CommandError(f"Arquivo não encontrado: {caminho}")
        listas, ignoradas = [], 0
        for caminho in caminhos:
            lista, fora = ler_tabela(caminho)
            listas.append(lista)
            ignoradas += fora
        modelos = juntar(listas)
        if not modelos:
            raise CommandError("Nenhum modelo válido no arquivo. O catálogo não mudou.")
        gravados = catalogo.gravar_csv(modelos)
        catalogo.modelos.cache_clear()
        self.stdout.write(
            f"Catálogo regravado com {gravados} modelos ({ignoradas} linhas ignoradas)."
        )
