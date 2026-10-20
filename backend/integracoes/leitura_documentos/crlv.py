"""Campos do CRLV-e a partir do texto do PDF (VEI-08, ADR 0026, item 1). Funções puras.

Só a biblioteca padrão: este módulo roda no processo filho, que não importa o Django nem outro
app (ADR 0026, item 4). O proprietário (nome, CPF ou CNPJ) nunca é procurado.

O texto vem da extração com leiaute do `pypdf`: os rótulos ficam numa linha e os valores na de
baixo, na mesma coluna, ou na mesma linha depois do rótulo. Cada campo passa por um validador; o
que não passa não é preenchido, e a leitura segue com os outros.
"""

import re
import unicodedata
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

ANO_MINIMO = 1900
LINHAS_ABAIXO = 3  # até quantas linhas abaixo do rótulo o valor pode estar
# Quantas colunas o valor pode ficar fora da coluna do rótulo: no leiaute do Detran-CE o
# exercício fica 11 colunas à esquerda do rótulo (T-331, T-336).
FOLGA_DA_COLUNA = 12

COMBUSTIVEIS = {
    "GASOLINA": "gasolina",
    "ALCOOL": "etanol",
    "ETANOL": "etanol",
    "ALCOOL GASOLINA": "flex",
    "GASOLINA ALCOOL": "flex",
    "ETANOL GASOLINA": "flex",
    "GASOLINA ETANOL": "flex",
    "FLEX": "flex",
    "DIESEL": "diesel",
    "ELETRICO": "eletrico",
    "ELETRICIDADE": "eletrico",
    "HIBRIDO": "hibrido",
    "GASOLINA ELETRICO": "hibrido",
    "ELETRICO GASOLINA": "hibrido",
}

# Letra proibida no chassi (ISO 3779): I, O e Q.
CHASSI = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")
PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")  # antiga (AAA9999) ou Mercosul (AAA9A99)


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def _chave(texto: str) -> str:
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", sem_acento(texto).upper()).split())


# --- Validadores: devolvem o valor limpo ou None ---


def placa(bruto: str) -> str | None:
    valor = re.sub(r"[^A-Z0-9]", "", sem_acento(bruto).upper())
    return valor if PLACA.match(valor) else None


def chassi(bruto: str) -> str | None:
    valor = re.sub(r"[^A-Z0-9]", "", sem_acento(bruto).upper())
    return valor if CHASSI.match(valor) else None


def renavam(bruto: str) -> str | None:
    """11 dígitos (os de 9, antigos, ganham zeros à esquerda) com o dígito verificador."""
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) == 9:
        digitos = digitos.zfill(11)
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return None
    pesos = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(d) * p for d, p in zip(digitos[:10], pesos, strict=True))
    verificador = (soma * 10) % 11
    verificador = 0 if verificador == 10 else verificador
    return digitos if verificador == int(digitos[10]) else None


def ano(bruto: str) -> int | None:
    achado = re.fullmatch(r"\s*(\d{4})\s*", bruto)
    if not achado:
        return None
    valor = int(achado.group(1))
    return valor if ANO_MINIMO <= valor <= date.today().year + 1 else None


def cor(bruto: str) -> str | None:
    valor = " ".join(sem_acento(bruto).split()).lower()
    if not valor or len(valor) > 30 or not re.fullmatch(r"[a-z ]+", valor):
        return None
    # O texto do cadastro, com o acento da palavra quando houver ("vermelha", "prata").
    return " ".join(bruto.split()).lower()


def combustivel(bruto: str) -> str | None:
    return COMBUSTIVEIS.get(_chave(bruto))


def marca_modelo(bruto: str) -> str | None:
    """O texto lido ("HONDA/POP 110I ES"), sem validar contra o catálogo: isso é com o pai."""
    valor = " ".join(bruto.split())
    if not valor or len(valor) > 80 or "/" not in valor:
        return None
    return valor if re.fullmatch(r"[A-Za-z0-9À-ÿ/.\- ]+", valor) else None


# --- Leitura por rótulo ---

# (campo, rótulo normalizado, validador). A ordem importa: "ANO MODELO" antes de "MODELO", e o
# "MARCA / MODELO / VERSÃO" tem rótulo próprio.
Validador = Callable[[str], Any]
CAMPOS: list[tuple[str, str, Validador]] = [
    ("placa", "PLACA", placa),
    ("chassi", "CHASSI", chassi),
    ("renavam", "CODIGO RENAVAM", renavam),
    ("marca_modelo", "MARCA MODELO VERSAO", marca_modelo),
    ("ano_fabricacao", "ANO FABRICACAO", ano),
    ("ano_modelo", "ANO MODELO", ano),
    ("cor", "COR PREDOMINANTE", cor),
    ("combustivel", "COMBUSTIVEL", combustivel),
    ("exercicio", "EXERCICIO", ano),
]
# Rótulos que começam com o de outro campo e não podem ser confundidos com ele.
NAO_E_O_ROTULO = {"PLACA": ("PLACA ANTERIOR",)}


def _linhas(texto: str) -> list[str]:
    # Uma letra por posição: a coluna do rótulo vale na linha de baixo.
    return [sem_acento(linha).upper() for linha in texto.splitlines()]


def _onde_esta(linha: str, rotulo: str) -> Iterator[tuple[int, int]]:
    """Início e fim do rótulo na linha, aceitando espaços, barras e pontos entre as palavras."""
    palavras = [re.escape(p) for p in rotulo.split()]
    padrao = r"(?<![A-Z0-9])" + r"[\s/.:\-]*".join(palavras) + r"(?![A-Z0-9])"
    for achado in re.finditer(padrao, linha):
        resto = linha[achado.start() :]
        if any(resto.startswith(outro) for outro in NAO_E_O_ROTULO.get(rotulo, ())):
            continue
        yield achado.start(), achado.end()


def _candidatos(linhas: list[str], originais: list[str], rotulo: str) -> Iterator[str]:
    for i, linha in enumerate(linhas):
        for inicio, fim in _onde_esta(linha, rotulo):
            # Na mesma linha, logo depois do rótulo ("PLACA: TBC5H21"). Três espaços ou mais já
            # separam a coluna do lado, que é outro rótulo.
            mesma_linha = re.match(r" {0,2}:? {0,2}(\S.*)", originais[i][fim:])
            if mesma_linha:
                yield re.split(r" {3,}", mesma_linha.group(1).strip())[0]
            # Abaixo, perto da coluna do rótulo: a primeira linha com um pedaço a até
            # `FOLGA_DA_COLUNA` colunas dela, o mais perto primeiro. Linha só com texto de outra
            # coluna (o bloco do seguro DPVAT, no leiaute do Detran-CE) não encerra a busca.
            for j in range(i + 1, min(i + 1 + LINHAS_ABAIXO, len(linhas))):
                perto = sorted(
                    (max(0, bloco.start() - fim, inicio - bloco.end()), bloco.start(), bloco[0])
                    for bloco in re.finditer(r"\S+(?: {1,2}\S+)*", originais[j])
                    if max(0, bloco.start() - fim, inicio - bloco.end()) <= FOLGA_DA_COLUNA
                )
                if perto:
                    yield from (texto for _, _, texto in perto)
                    break


def extrair(texto: str) -> dict[str, Any]:
    """Os campos achados e válidos; campo que não passa no validador fica de fora."""
    originais = texto.splitlines()
    linhas = _linhas(texto)
    campos: dict[str, Any] = {}
    for campo, rotulo, validador in CAMPOS:
        for candidato in _candidatos(linhas, originais, rotulo):
            valor = validador(candidato)
            if valor is not None:
                campos[campo] = valor
                break
    fabricacao, modelo = campos.get("ano_fabricacao"), campos.get("ano_modelo")
    if fabricacao and modelo and not fabricacao <= modelo <= fabricacao + 1:
        campos.pop("ano_modelo")  # o mesmo critério do cadastro (VEI-01)
    return campos
