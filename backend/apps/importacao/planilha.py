"""Leitura da planilha e o modelo para baixar (docs/api/importacao.md, "Planilha" e "Dados
temporários e segurança").

A planilha nunca é executada: só valores de célula, sem fórmulas, macros nem links externos. O
tipo é conferido pelo conteúdo, não pela extensão. O `.xlsx` passa por limites de zip antes de
abrir e é lido em streaming pelo `openpyxl`, com o `defusedxml` instalado.
"""

import csv
import io
import unicodedata
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from rest_framework import status

from comum.erros import ErroDeNegocio, ErroDeValidacao

MAX_BYTES = 5 * 1024 * 1024
MAX_LINHAS = 5000
MAX_CELULA = 1000
MAX_DESCOMPACTADO = 50 * 1024 * 1024
MAX_ENTRADAS_ZIP = 200
EXTENSOES = ("xlsx", "csv")


@dataclass(frozen=True)
class Coluna:
    nome: str
    rotulo: str
    obrigatoria: bool = False  # no cabeçalho (em negrito no modelo)
    exemplo: str = ""


COLUNAS: dict[str, tuple[Coluna, ...]] = {
    "veiculos": (
        Coluna("placa", "Placa", True, "QXA4B21"),
        Coluna("chassi", "Chassi", True, "9C2KC2210PR004417"),
        Coluna("renavam", "Renavam", exemplo="01234567890"),
        Coluna("marca", "Marca", True, "Honda"),
        Coluna("modelo", "Modelo", True, "CG 160 Fan"),
        Coluna("ano_fabricacao", "Ano de fabricação", True, "2023"),
        Coluna("ano_modelo", "Ano do modelo", True, "2023"),
        Coluna("cor", "Cor", True, "Preta"),  # T-164: obrigatória, como no cadastro
        Coluna("km", "Km", True, "18250"),
        Coluna("categoria", "Categoria", True, "Street 150–160"),
        Coluna("filial", "Filial", exemplo="Filial Centro"),
        Coluna("capacidade_tanque_litros", "Capacidade do tanque", exemplo="14"),
        Coluna("valor_compra", "Valor de compra", exemplo="13.900,00"),
        Coluna("data_compra", "Data de compra", exemplo="10/01/2025"),
    ),
    "clientes": (
        # `tipo` vazio é deduzido pelo documento; a coluna pode faltar.
        Coluna("tipo", "Tipo", exemplo="pf"),
        Coluna("nome", "Nome", True, "Juliana Alves"),
        Coluna("documento", "Documento", True, "052.218.330-18"),
        Coluna("celular", "Celular", True, "(85) 99812-3344"),
        Coluna("email", "E-mail", exemplo="juliana@email.com"),
        Coluna("nascimento", "Nascimento", exemplo="14/03/1998"),
        Coluna("profissao", "Profissão", exemplo="Entregadora"),
        Coluna("cnh_numero", "Número da CNH", exemplo="04512345678"),
        Coluna("cnh_categoria", "Categoria da CNH", exemplo="A"),
        Coluna("cnh_validade", "Validade da CNH", exemplo="20/08/2029"),
        Coluna("cnh_primeira_habilitacao", "Primeira habilitação", exemplo="05/02/2017"),
        Coluna("cep", "CEP", exemplo="60150-160"),
        Coluna("logradouro", "Logradouro", exemplo="Rua Padre Mororó"),
        Coluna("numero", "Número", exemplo="410"),
        Coluna("complemento", "Complemento", exemplo="apto 202"),
        Coluna("bairro", "Bairro", exemplo="Centro"),
        Coluna("cidade", "Cidade", exemplo="Fortaleza"),
        Coluna("uf", "UF", exemplo="CE"),
        Coluna("referencia_nome", "Nome da referência", exemplo="Marta Alves"),
        Coluna("referencia_parentesco", "Parentesco", exemplo="mãe"),
        Coluna("referencia_telefone", "Telefone da referência", exemplo="(85) 98877-6655"),
        Coluna("responsavel_nome", "Nome do responsável"),
        Coluna("responsavel_cpf", "CPF do responsável"),
    ),
}

INSTRUCOES = {
    "veiculos": (
        "Uma linha por veículo. Não mude os nomes das colunas.",
        "Obrigatórias (em negrito): placa, chassi, marca, modelo, ano_fabricacao, ano_modelo, "
        "km e categoria.",
        "Placa no padrão antigo (ABC1234) ou Mercosul (ABC1D23). Chassi com 17 letras e números.",
        "Categoria: o nome, como na tabela de preços. Filial: o nome; vazia usa a filial "
        "escolhida no envio.",
        "Valores em reais: 13900, 13.900,00 ou 13900.00. Datas: dd/mm/aaaa ou aaaa-mm-dd.",
        "Veículo já cadastrado (mesma placa ou chassi) não é importado de novo.",
        "Até 5.000 linhas e 5 MB.",
    ),
    "clientes": (
        "Uma linha por cliente. Não mude os nomes das colunas.",
        "Obrigatórias (em negrito): nome, documento e celular.",
        "Tipo: pf ou pj. Vazio, deduzimos pelo documento (CPF ou CNPJ).",
        "Datas: dd/mm/aaaa ou aaaa-mm-dd. Categoria da CNH: A, B, C, D, E, AB, AC, AD ou AE.",
        "O cliente entra com o cadastro incompleto: as fotos dos documentos e o consentimento "
        "você completa depois, na ficha.",
        "Cliente já cadastrado (mesmo documento) não é importado de novo.",
        "Até 5.000 linhas e 5 MB.",
    ),
}


class CabecalhoIncompleto(ErroDeNegocio):
    """Coluna obrigatória faltando no cabeçalho: 400 `validacao` com `colunas_faltando`."""

    status_http = status.HTTP_400_BAD_REQUEST


@dataclass
class Linha:
    numero: int  # a linha na planilha; o cabeçalho é a 1
    valores: dict[str, str]
    longas: list[str] = field(default_factory=list)  # colunas com mais de 1.000 caracteres


@dataclass
class Leitura:
    colunas: list[str]
    linhas: list[Linha]


def normalizar_nome(texto: str) -> str:
    """Sem acento, minúsculo, espaços e traços viram `_`: "Ano Fabricação" → "ano_fabricacao";
    "Street 150–160" e "street 150-160" dão o mesmo nome."""
    tracos = "".join(" " if unicodedata.category(c) == "Pd" else c for c in texto)
    sem_acento = unicodedata.normalize("NFKD", tracos).encode("ascii", "ignore").decode()
    return "_".join(sem_acento.lower().split())


def _arquivo_invalido(mensagem: str) -> ErroDeValidacao:
    return ErroDeValidacao({"arquivo": [mensagem]})


def texto(valor: Any) -> str:
    """Só o valor da célula, como texto."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def extensao(nome: str) -> str:
    return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""


def conferir_arquivo(nome: str, conteudo: bytes) -> str:
    """Extensão, tamanho, vazio e o conteúdo bater com a extensão. Devolve a extensão."""
    ext = extensao(nome)
    if ext not in EXTENSOES:
        raise _arquivo_invalido("Envie a planilha em .xlsx ou .csv.")
    if not conteudo:
        raise _arquivo_invalido("O arquivo está vazio.")
    if len(conteudo) > MAX_BYTES:
        raise _arquivo_invalido("O arquivo passa de 5 MB.")
    if ext == "xlsx":
        _conferir_zip(conteudo)
    return ext


def _conferir_zip(conteudo: bytes) -> None:
    """Antes de abrir: precisa ser um zip com `[Content_Types].xml`, com no máximo 200 entradas
    e 50 MB descompactado (somando o que cada entrada declara)."""
    try:
        with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
            entradas = pacote.infolist()
    except (zipfile.BadZipFile, ValueError) as erro:
        raise _arquivo_invalido("O arquivo não é uma planilha .xlsx.") from erro
    if not any(e.filename == "[Content_Types].xml" for e in entradas):
        raise _arquivo_invalido("O arquivo não é uma planilha .xlsx.")
    if len(entradas) > MAX_ENTRADAS_ZIP or sum(e.file_size for e in entradas) > MAX_DESCOMPACTADO:
        raise _arquivo_invalido("A planilha é grande demais para importar.")


def _linhas_xlsx(conteudo: bytes) -> Iterator[list[Any]]:
    livro = load_workbook(
        io.BytesIO(conteudo), read_only=True, data_only=True, keep_links=False, keep_vba=False
    )
    try:
        folha = livro.worksheets[0]
        for valores in folha.iter_rows(values_only=True):
            yield list(valores)
    finally:
        livro.close()


def _linhas_csv(conteudo: bytes) -> Iterator[list[Any]]:
    try:
        texto = conteudo.decode("utf-8-sig")  # o BOM sai aqui
    except UnicodeDecodeError as erro:
        raise _arquivo_invalido("Salve o .csv em UTF-8 e envie de novo.") from erro
    primeira = texto.split("\n", 1)[0]
    separador = ";" if primeira.count(";") >= primeira.count(",") else ","
    # T-164: o limite de leitura é o do arquivo (5 MB), para nenhuma célula interromper a leitura.
    # Os 1.000 caracteres são da validação da linha (`_montar`), como no .xlsx.
    anterior = csv.field_size_limit(MAX_BYTES)
    try:
        leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=separador)
        inicio = 1
        for valores in leitor:
            if any(len(v) > MAX_CELULA and ("\n" in v or "\r" in v) for v in valores):
                # Célula longa com quebra de linha é aspas sem fechar: o resto do arquivo
                # viraria uma célula só, e as linhas seguintes sumiriam sem aviso.
                raise _arquivo_invalido(
                    f"A linha {inicio} tem aspas sem fechar. Confira o arquivo e envie de novo."
                )
            yield valores
            inicio = leitor.line_num + 1
    finally:
        csv.field_size_limit(anterior)


def ler(nome: str, conteudo: bytes, tipo: str) -> Leitura:
    """Lê o cabeçalho e as linhas (sem as vazias), contando no streaming até 5.001.

    400 `validacao` no arquivo ilegível, grande demais ou com coluna obrigatória faltando.
    Colunas não reconhecidas são descartadas aqui.
    """
    ext = conferir_arquivo(nome, conteudo)
    conhecidas = {coluna.nome for coluna in COLUNAS[tipo]}
    try:
        brutas = _linhas_xlsx(conteudo) if ext == "xlsx" else _linhas_csv(conteudo)
        return _montar(brutas, conhecidas, tipo)
    except ErroDeNegocio:
        raise
    except Exception as erro:  # qualquer falha do leitor: entidade XML, zip corrompido...
        raise _arquivo_invalido("Não conseguimos ler a planilha. Confira o arquivo.") from erro


def _montar(brutas: Iterator[list[Any]], conhecidas: set[str], tipo: str) -> Leitura:
    cabecalho: list[str] | None = None
    linhas: list[Linha] = []
    for numero, valores in enumerate(brutas, start=1):
        if cabecalho is None:
            cabecalho = [normalizar_nome(texto(v)) for v in valores]
            faltando = [c.nome for c in COLUNAS[tipo] if c.obrigatoria and c.nome not in cabecalho]
            if faltando:
                raise CabecalhoIncompleto(
                    "validacao",
                    "Faltam colunas obrigatórias na planilha.",
                    {"colunas_faltando": faltando},
                )
            continue
        textos = [texto(v) for v in valores]
        if not any(textos):
            continue
        if len(linhas) >= MAX_LINHAS:
            raise _arquivo_invalido("A planilha passa de 5.000 linhas.")
        linha = Linha(numero=numero, valores={})
        for coluna, valor in zip(cabecalho, textos, strict=False):
            if coluna not in conhecidas or coluna in linha.valores:
                continue
            if len(valor) > MAX_CELULA:
                linha.longas.append(coluna)
                valor = valor[:MAX_CELULA]
            linha.valores[coluna] = valor
        linhas.append(linha)
    if cabecalho is None:
        raise _arquivo_invalido("O arquivo está vazio.")
    if not linhas:
        raise _arquivo_invalido("A planilha não tem nenhuma linha preenchida.")
    return Leitura(colunas=[c for c in cabecalho if c in conhecidas], linhas=linhas)


def modelo(tipo: str) -> bytes:
    """O `.xlsx` para baixar: as colunas (obrigatórias em negrito), uma linha de exemplo e a
    aba "Instruções"."""
    livro = Workbook()
    folha = livro.worksheets[0]
    folha.title = "Veículos" if tipo == "veiculos" else "Clientes"
    colunas = COLUNAS[tipo]
    folha.append([c.nome for c in colunas])
    folha.append([c.exemplo for c in colunas])
    for celula, coluna in zip(folha[1], colunas, strict=True):
        celula.font = Font(bold=coluna.obrigatoria)
    instrucoes = livro.create_sheet("Instruções")
    for texto in INSTRUCOES[tipo]:
        instrucoes.append([texto])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()
