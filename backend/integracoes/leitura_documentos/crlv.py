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


# Tabela de cores do Denatran (M-01 da T-328): fora dela o campo fica vazio, para o texto de
# outro rótulo (o nome do proprietário) nunca virar cor. Comparada sem acento.
CORES_DO_DENATRAN = (
    "amarela", "azul", "bege", "branca", "cinza", "dourada", "grená", "laranja",
    "marrom", "prata", "preta", "rosa", "roxa", "verde", "vermelha", "fantasia",
)  # fmt: skip
_CORES = {sem_acento(c): c for c in CORES_DO_DENATRAN}


def cor(bruto: str) -> str | None:
    """A cor da lista, com o acento dela ("grená"); qualquer outro texto, nada."""
    return _CORES.get(" ".join(sem_acento(bruto).split()).lower())


def combustivel(bruto: str) -> str | None:
    return COMBUSTIVEIS.get(_chave(bruto))


def marca_modelo(bruto: str) -> str | None:
    """O texto lido ("HONDA/POP 110I ES"), sem validar contra o catálogo: isso é com o pai."""
    valor = " ".join(bruto.split())
    if not valor or len(valor) > 80 or "/" not in valor:
        return None
    return valor if re.fullmatch(r"[A-Za-z0-9À-ÿ/.\- ]+", valor) else None


# --- Campos da VEI-09 (T-421, docs/api/veiculos.md, "Do texto do CRLV-e ao campo") ---

# O rótulo foi achado e o documento traz o campo vazio ("NÃO APLICAVEL", asteriscos, peso 0):
# a busca para ali, e o campo fica de fora, sem tentar o texto de outra coluna.
VAZIO = ""

ESPECIES = {
    "PASSAGEIRO": "passageiro",
    "CARGA": "carga",
    "MISTO": "misto",
    "COMPETICAO": "competicao",
    "TRACAO": "tracao",
    "ESPECIAL": "especial",
    "COLECAO": "colecao",
}
# Tipos do CTB (art. 96) com o acento; fora da tabela, o texto lido com só a 1ª maiúscula.
TIPOS_DO_CTB = (
    "Bicicleta", "Ciclomotor", "Motoneta", "Motocicleta", "Triciclo", "Quadriciclo",
    "Automóvel", "Micro-ônibus", "Ônibus", "Bonde", "Reboque", "Semirreboque", "Charrete",
    "Camioneta", "Caminhão", "Caminhão-trator", "Trator de rodas", "Trator de esteiras",
    "Trator misto", "Caminhonete", "Utilitário", "Motor-casa", "Side-car",
)  # fmt: skip
_TIPOS = {_chave(t): t for t in TIPOS_DO_CTB}
MAXIMO_DO_TEXTO = 30
MAXIMO_DAS_OBSERVACOES = 500


def _so_asteriscos(texto: str) -> bool:
    return not texto.replace("*", "").strip()


def _na_faixa(valor: int, minimo: int, maximo: int) -> int | None:
    return valor if minimo <= valor <= maximo else None


def potencia_cilindrada(bruto: str) -> dict[str, int | None] | None:
    """ "15CV/0162" → 15 cv e 162 cc. Potência 0 e cilindrada 0 (elétrico), ou fora da faixa,
    ficam de fora."""
    achado = re.fullmatch(
        r"\s*(\d{1,4})\s*(?:CV|CC)?\s*/\s*(\d{1,5})\s*(?:CC)?\s*", sem_acento(bruto).upper()
    )
    if not achado:
        return None
    return {
        "potencia_cv": _na_faixa(int(achado.group(1)), 1, 999),
        "cilindrada_cc": _na_faixa(int(achado.group(2)), 1, 9999),
    }


def especie_tipo(bruto: str) -> dict[str, str | None] | None:
    """ "PASSAGEIRO MOTOCICLETA" → espécie `passageiro` e tipo "Motocicleta". Espécie fora da
    lista do CTB: nenhum dos dois."""
    palavras = bruto.split()
    if not palavras or ESPECIES.get(_chave(palavras[0])) is None:
        return None
    resto = " ".join(palavras[1:])
    tipo = _TIPOS.get(_chave(resto)) or resto.capitalize()
    return {
        "especie": ESPECIES[_chave(palavras[0])],
        "tipo": tipo if tipo and len(tipo) <= MAXIMO_DO_TEXTO else None,
    }


def carroceria(bruto: str) -> str | None:
    valor = " ".join(bruto.split())
    if _so_asteriscos(valor) or _chave(valor) == "NAO APLICAVEL":
        return VAZIO
    return valor if len(valor) <= MAXIMO_DO_TEXTO else None


def lotacao(bruto: str) -> int | None:
    """ "02P" → 2 pessoas, com o motorista."""
    achado = re.fullmatch(r"\s*(\d{1,3})\s*P?\s*", sem_acento(bruto).upper())
    return _na_faixa(int(achado.group(1)), 1, 99) if achado else None


def peso_bruto_kg(bruto: str) -> int | str | None:
    """Toneladas com vírgula ou ponto ("0,29") → kg inteiros (290). Zero fica de fora."""
    achado = re.fullmatch(r"\s*(\d{1,2})(?:[.,](\d{1,3}))?\s*", bruto)
    if not achado:
        return None
    quilos = int(achado.group(1)) * 1000 + int((achado.group(2) or "0").ljust(3, "0"))
    return _na_faixa(quilos, 1, 99999) if quilos else VAZIO


def numero_motor(bruto: str) -> str | None:
    valor = re.sub(r"[\s*]", "", sem_acento(bruto).upper())
    if not valor:
        return VAZIO
    return valor if re.fullmatch(r"[A-Z0-9]{1,21}", valor) else None


# --- Leitura por rótulo ---

# (campo, rótulo normalizado, validador). A ordem importa: "ANO MODELO" antes de "MODELO", e o
# "MARCA / MODELO / VERSÃO" tem rótulo próprio. O validador que devolve um dicionário preenche
# mais de um campo com o mesmo rótulo ("POTÊNCIA/CILINDRADA", "ESPÉCIE / TIPO").
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
    ("potencia_cilindrada", "POTENCIA CILINDRADA", potencia_cilindrada),
    ("especie_tipo", "ESPECIE TIPO", especie_tipo),
    ("carroceria", "CARROCERIA", carroceria),
    ("lotacao", "LOTACAO", lotacao),
    ("peso_bruto_kg", "PESO BRUTO TOTAL", peso_bruto_kg),
    ("numero_motor", "MOTOR", numero_motor),
]
ROTULO_DAS_OBSERVACOES = "OBSERVACOES DO VEICULO"
# O bloco das observações termina no próximo rótulo, em linhas em branco seguidas ou no limite.
FIM_DAS_OBSERVACOES = ("MENSAGENS SENATRAN",)
LINHAS_DAS_OBSERVACOES = 12
BRANCAS_NO_FIM = 3
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


def observacoes(linhas: list[str], originais: list[str]) -> str | None:
    """As linhas do bloco "OBSERVAÇÕES DO VEÍCULO", na coluna do rótulo, com as quebras.

    A coluna vai até o rótulo seguinte na mesma linha (o "INFORMAÇÕES DO SEGURO DPVAT" do
    Detran-CE). O bloco acaba no próximo rótulo de seção, depois de `BRANCAS_NO_FIM` linhas sem
    texto na coluna ou em `LINHAS_DAS_OBSERVACOES` linhas. Só asteriscos: vazio."""
    for i, linha in enumerate(linhas):
        for inicio, fim in _onde_esta(linha, ROTULO_DAS_OBSERVACOES):
            do_lado = re.search(r"\S", linha[fim:])
            limite = fim + do_lado.start() if do_lado else None
            achadas: list[str] = []
            brancas = 0
            for j in range(i + 1, min(i + 1 + LINHAS_DAS_OBSERVACOES, len(linhas))):
                if any(rotulo in linhas[j] for rotulo in FIM_DAS_OBSERVACOES):
                    break
                trecho = originais[j][max(0, inicio - FOLGA_DA_COLUNA) : limite].strip()
                if not trecho:
                    brancas += 1
                    if achadas and brancas >= BRANCAS_NO_FIM:
                        break
                    continue
                brancas = 0
                achadas.append(" ".join(trecho.split()))
            valor = "\n".join(achadas)
            if _so_asteriscos(valor):
                return VAZIO
            return valor if len(valor) <= MAXIMO_DAS_OBSERVACOES else None
    return None


def extrair(texto: str) -> dict[str, Any]:
    """Os campos achados e válidos; campo que não passa no validador fica de fora."""
    originais = texto.splitlines()
    linhas = _linhas(texto)
    campos: dict[str, Any] = {}
    for campo, rotulo, validador in CAMPOS:
        for candidato in _candidatos(linhas, originais, rotulo):
            valor = validador(candidato)
            if valor is None:
                continue
            if isinstance(valor, dict):
                campos.update({nome: v for nome, v in valor.items() if v is not None})
            elif valor != VAZIO:
                campos[campo] = valor
            break
    nota = observacoes(linhas, originais)
    if nota:
        campos["observacoes"] = nota
    fabricacao, modelo = campos.get("ano_fabricacao"), campos.get("ano_modelo")
    if fabricacao and modelo and not fabricacao <= modelo <= fabricacao + 1:
        campos.pop("ano_modelo")  # o mesmo critério do cadastro (VEI-01)
    return campos
