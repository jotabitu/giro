"""Catálogo de marcas e modelos, "Da lista FIPE" da tela Veiculo-Novo (VEI-08, ADR 0026, item 7).

Marcas e modelos da Tabela FIPE, obtidos pela API aberta da Parallelum (provisório, ADR 0031),
mais a lista própria da equipe (`dados/catalogo_modelos_proprios.csv`, nomes genéricos como
"CG 160 Fan", que o seed usa). A carga é feita fora do servidor
(`scripts/baixar_catalogo_parallelum.py`) e entra pelo comando `atualizar_catalogo_modelos`, por
PR, a cada trimestre.

A lista é local: o arquivo versionado `dados/catalogo_modelos.csv` (`marca`, `modelo`, `tipo`),
lido uma vez por processo e guardado em memória, com a chave já normalizada. É igual para todas
as empresas. Nada aqui consulta a internet.
"""

import csv
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

DADOS = Path(__file__).resolve().parent / "dados"
ARQUIVO = DADOS / "catalogo_modelos.csv"
ARQUIVO_PROPRIO = DADOS / "catalogo_modelos_proprios.csv"
CABECALHO = ("marca", "modelo", "tipo")
TIPOS = ("moto", "carro")
LIMITE_DA_LISTA = 50


@dataclass(frozen=True)
class Modelo:
    marca: str
    modelo: str
    tipo: str
    # Calculadas uma vez, na criação (na leitura do CSV), e não a cada pedido.
    chave: str = field(init=False, compare=False, repr=False)
    marca_normalizada: str = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "chave", normalizar(f"{self.marca} {self.modelo}"))
        object.__setattr__(self, "marca_normalizada", normalizar(self.marca))


def normalizar(texto: str) -> str:
    """Sem acento, maiúsculas, sem pontuação e com um espaço só entre as palavras."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", sem_acento.upper()).split())


def _ordem(modelo: Modelo) -> tuple[str, str]:
    return modelo.marca_normalizada, normalizar(modelo.modelo)


def organizar(modelos: Iterable[Modelo]) -> list[Modelo]:
    """Sem duplicata (pela chave normalizada e o tipo, fica a primeira) e em ordem de marca e
    modelo. É o formato que o CSV guarda."""
    vistos: dict[tuple[str, str], Modelo] = {}
    for modelo in modelos:
        vistos.setdefault((modelo.chave, modelo.tipo), modelo)
    return sorted(vistos.values(), key=lambda m: (*_ordem(m), m.tipo))


def ler_csv(caminho: Path) -> list[Modelo]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            Modelo(linha["marca"].strip(), linha["modelo"].strip(), linha["tipo"].strip())
            for linha in csv.DictReader(arquivo)
        ]


def gravar_csv(modelos: Iterable[Modelo], caminho: Path | None = None) -> int:
    organizados = organizar(modelos)
    with (caminho or ARQUIVO).open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, lineterminator="\n")
        escritor.writerow(CABECALHO)
        escritor.writerows((m.marca, m.modelo, m.tipo) for m in organizados)
    return len(organizados)


@cache
def modelos() -> tuple[Modelo, ...]:
    """O catálogo inteiro, lido do arquivo na primeira chamada do processo."""
    return tuple(ler_csv(ARQUIVO))


def listar(
    *, tipo: str | None = None, marca: str | None = None, busca: str | None = None
) -> list[Modelo]:
    """Para `GET /api/veiculos/modelos/`: até 50, em ordem de marca e modelo."""
    marca_normalizada = normalizar(marca or "")
    termos = normalizar(busca or "").split()
    achados = [
        m
        for m in modelos()
        if (not tipo or m.tipo == tipo)
        and (not marca_normalizada or m.marca_normalizada == marca_normalizada)
        and all(termo in m.chave for termo in termos)
    ]
    return achados[:LIMITE_DA_LISTA]


def _comeca_com(texto: str, inicio: str) -> bool:
    return texto == inicio or texto.startswith(f"{inicio} ")


def achar_modelo(texto: str) -> Modelo | None:
    """O modelo do catálogo para o texto lido do CRLV-e ("HONDA/POP 110I ES"), só se for único.

    Vale o `marca + modelo` igual ao texto normalizado; sem igual, o texto como começo de um só
    modelo, ou um só modelo como começo do texto. Mais de um, ou nenhum: `None`, e a leitura
    manda a dica em vez de preencher (ADR 0026, item 7). Só a marca não basta.
    """
    lido = normalizar(texto)
    if not lido:
        return None
    candidatos = [m for m in modelos() if m.chave == lido]
    if not candidatos:
        candidatos = [m for m in modelos() if _comeca_com(m.chave, lido)]
    if not candidatos:
        candidatos = [m for m in modelos() if _comeca_com(lido, m.chave)]
    candidatos = [m for m in candidatos if lido != m.marca_normalizada]
    return candidatos[0] if len(candidatos) == 1 else None
