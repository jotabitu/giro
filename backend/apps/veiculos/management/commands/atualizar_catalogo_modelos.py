"""Regrava o catálogo de marcas e modelos a partir da tabela FIPE baixada pela equipe (T-257).

    python manage.py atualizar_catalogo_modelos <arquivo.csv>

O arquivo é um CSV em UTF-8 com as colunas `marca`, `modelo` e `tipo` (`moto` ou `carro`, no
singular ou no plural; outro tipo fica de fora). O comando não consulta a internet: a
atualização é manual e vai por PR, com o `dados/catalogo_modelos.csv` regravado sem duplicata e
em ordem de marca e modelo.
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


class Command(BaseCommand):
    help = "Regrava o catálogo de marcas e modelos a partir de um CSV da tabela FIPE."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("arquivo", type=Path)

    def handle(self, *args: Any, **opcoes: Any) -> None:
        caminho: Path = opcoes["arquivo"]
        if not caminho.is_file():
            raise CommandError(f"Arquivo não encontrado: {caminho}")
        modelos, ignoradas = ler_tabela(caminho)
        if not modelos:
            raise CommandError("Nenhum modelo válido no arquivo. O catálogo não mudou.")
        gravados = catalogo.gravar_csv(modelos)
        catalogo.modelos.cache_clear()
        self.stdout.write(
            f"Catálogo regravado com {gravados} modelos ({ignoradas} linhas ignoradas)."
        )
