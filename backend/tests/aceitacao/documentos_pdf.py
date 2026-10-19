"""PDFs fictícios no leiaute do CRLV-e, para a T-265 (docs/qa/criterios/T-247.md).

Gerados aqui, com texto posicionado como no documento do Detran (rótulo em cima, valor embaixo,
na mesma coluna), para nenhum documento real entrar no repositório (ADR 0026, item 1). O
proprietário é fictício e serve para provar que ele nunca é lido.
"""

import io
from dataclasses import dataclass, replace

from pypdf import PdfReader, PdfWriter

PROPRIETARIO = "ANTONIO FICTICIO DE SOUSA"
CPF_PROPRIETARIO = "529.982.247-25"


def _texto_pdf(texto: str) -> bytes:
    bruto = texto.encode("cp1252")
    return bruto.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def pdf_de_textos(paginas: list[list[tuple[float, float, str]]]) -> bytes:
    """Um PDF com Helvetica (WinAnsi) e cada texto em (x, y), sem nada além disso."""
    objetos: list[bytes] = []

    def novo(corpo: bytes) -> int:
        objetos.append(corpo)
        return len(objetos)

    fonte = novo(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    paginas_id = novo(b"")  # preenchido depois
    filhas: list[int] = []
    for textos in paginas:
        fluxo = b"".join(
            b"BT /F1 9 Tf %.1f %.1f Td (%s) Tj ET\n" % (x, y, _texto_pdf(t)) for x, y, t in textos
        )
        conteudo = novo(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(fluxo), fluxo))
        filhas.append(
            novo(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                % (paginas_id, fonte, conteudo)
            )
        )
    kids = b" ".join(b"%d 0 R" % f for f in filhas)
    objetos[paginas_id - 1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(filhas))
    catalogo = novo(b"<< /Type /Catalog /Pages %d 0 R >>" % paginas_id)

    saida = io.BytesIO()
    saida.write(b"%PDF-1.4\n")
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(saida.tell())
        saida.write(b"%d 0 obj\n%s\nendobj\n" % (numero, corpo))
    xref = saida.tell()
    saida.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1))
    for posicao in posicoes:
        saida.write(b"%010d 00000 n \n" % posicao)
    saida.write(
        b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objetos) + 1, catalogo, xref)
    )
    return saida.getvalue()


@dataclass(frozen=True)
class Crlv:
    placa: str = "TBC-5H21"
    chassi: str = "9C2JC7510SR000123"
    renavam: str = "01234567897"
    marca_modelo: str = "HONDA/POP 110I ES"
    ano_fabricacao: str = "2025"
    ano_modelo: str = "2026"
    cor: str = "VERMELHA"
    combustivel: str = "GASOLINA"
    exercicio: str = "2026"

    def textos(self) -> list[tuple[float, float, str]]:
        # Três colunas (x = 40, 220 e 400), rótulo e valor 12 pontos abaixo.
        blocos = [
            (40, 780, "CÓDIGO RENAVAM", self.renavam),
            (220, 780, "PLACA", self.placa),
            (400, 780, "EXERCÍCIO", self.exercicio),
            (40, 740, "ANO FABRICAÇÃO", self.ano_fabricacao),
            (220, 740, "ANO MODELO", self.ano_modelo),
            (400, 740, "NÚMERO DO CRV", "123456789012"),
            (40, 700, "MARCA / MODELO / VERSÃO", self.marca_modelo),
            (40, 660, "ESPÉCIE / TIPO", "PASSAGEIRO MOTOCICLETA"),
            (220, 660, "PLACA ANTERIOR / UF", "*******/CE"),
            (40, 620, "CHASSI", self.chassi),
            (40, 580, "COR PREDOMINANTE", self.cor),
            (220, 580, "COMBUSTÍVEL", self.combustivel),
            (40, 540, "NOME", PROPRIETARIO),
            (40, 500, "CPF / CNPJ", CPF_PROPRIETARIO),
            (40, 460, "LOCAL", "FORTALEZA CE"),
            (220, 460, "DATA", "07/10/2026"),
        ]
        textos = [(40.0, 815.0, "REPÚBLICA FEDERATIVA DO BRASIL · CRLV DIGITAL")]
        for x, y, rotulo, valor in blocos:
            textos += [(float(x), float(y), rotulo), (float(x), float(y - 12), valor)]
        return textos

    def pdf(self) -> bytes:
        return pdf_de_textos([self.textos()])


CRLV_TBC5H21 = Crlv()
CRLV_QXA4B21 = Crlv(
    placa="QXA4B21",
    chassi="9C2KC2210PR004401",
    renavam="00987654322",
    marca_modelo="HONDA/CG 160 FAN",
    ano_fabricacao="2023",
    ano_modelo="2023",
    cor="PRETA",
    combustivel="ALCOOL/GASOLINA",
)
CRLV_FORA_DA_LISTA = replace(CRLV_TBC5H21, marca_modelo="SUZUKI/YES 125")


def nao_e_documento() -> bytes:
    return pdf_de_textos([[(40, 780, "Relatório trimestral"), (40, 760, "Receita 2026")]])


def sem_texto() -> bytes:
    return pdf_de_textos([[]])


def com_paginas(quantidade: int) -> bytes:
    return pdf_de_textos([CRLV_TBC5H21.textos() for _ in range(quantidade)])


def com_senha() -> bytes:
    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(CRLV_TBC5H21.pdf())))
    escritor.encrypt(user_password="", owner_password="dono")
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()


def com_javascript_e_anexo() -> bytes:
    escritor = PdfWriter(clone_from=PdfReader(io.BytesIO(CRLV_TBC5H21.pdf())))
    escritor.add_js("app.alert('oi');")
    escritor.add_attachment("anexo.txt", b"conteudo escondido")
    saida = io.BytesIO()
    escritor.write(saida)
    return saida.getvalue()
