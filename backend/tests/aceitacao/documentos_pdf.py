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


def pdf_de_textos(paginas: list[list[tuple]]) -> bytes:  # type: ignore[type-arg]
    """Um PDF com cada texto em (x, y) ou (x, y, fonte, tamanho); fonte 1 é Helvetica (padrão,
    9 pontos) e 2 é Courier-Bold, as duas em WinAnsi. Sem nada além disso."""
    objetos: list[bytes] = []

    def novo(corpo: bytes) -> int:
        objetos.append(corpo)
        return len(objetos)

    fonte = novo(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    fonte_mono = novo(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>"
    )
    paginas_id = novo(b"")  # preenchido depois
    filhas: list[int] = []
    for textos in paginas:
        fluxo = b"".join(
            b"BT /F%d %.1f Tf %.1f %.1f Td (%s) Tj ET\n"
            % (
                item[3] if len(item) > 3 else 1,
                item[4] if len(item) > 4 else 9,
                item[0],
                item[1],
                _texto_pdf(item[2]),
            )
            for item in textos
        )
        conteudo = novo(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(fluxo), fluxo))
        filhas.append(
            novo(
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R >>"
                % (paginas_id, fonte, fonte_mono, conteudo)
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


@dataclass(frozen=True)
class CrlvDetran(Crlv):
    """O CRLV-e como o Detran emite (T-331, calibração com dois documentos reais do Detran-CE).

    Só o leiaute vem do documento real: as posições de cada texto, rótulos em Helvetica de 5,8
    pontos e valores em monoespaçada de 10. Todo valor é inventado. O que importa para o parser:
    o rótulo do chassi divide a linha com o da placa anterior; o valor do exercício fica à esquerda
    do rótulo; a coluna da direita (seguro DPVAT) tem texto em todas as linhas, e entre o rótulo
    e o valor do chassi, da marca e da cor há linhas com texto só nela.
    """

    def textos(self) -> list[tuple]:  # type: ignore[type-arg]
        def rotulo(x: float, y: float, texto: str) -> tuple:  # type: ignore[type-arg]
            return (x, y, texto, 1, 5.8)

        def valor(x: float, y: float, texto: str) -> tuple:  # type: ignore[type-arg]
            return (x, y, texto, 2, 10)

        return [
            (53.1, 816.9, "REPÚBLICA FEDERATIVA DO BRASIL", 1, 9.5),
            rotulo(53.1, 811.4, "MINISTÉRIO DOS TRANSPORTES"),
            rotulo(53.1, 805.9, "SECRETARIA NACIONAL DE TRÂNSITO - SENATRAN"),
            rotulo(31.0, 784.3, "DETRAN-CE"),
            (31.0, 772.7, "CERTIFICADO DE REGISTRO E LICENCIAMENTO DE VEÍCULO - DIGITAL", 1, 6.4),
            rotulo(316.7, 772.7, "CATEGORIA"),
            rotulo(510.6, 772.7, "CAPACIDADE"),
            valor(316.2, 761.7, "PARTICULAR"),
            rotulo(31.0, 746.7, "CÓDIGO RENAVAM"),
            valor(509.7, 746.9, "*.*"),
            valor(31.1, 733.0, self.renavam),
            rotulo(316.7, 734.4, "POTÊNCIA/CILINDRADA"),
            rotulo(510.3, 734.4, "PESO BRUTO TOTAL"),
            valor(316.2, 720.7, "110CC/0110"),
            valor(509.7, 720.7, "0.1"),
            rotulo(31.0, 720.4, "PLACA"),
            rotulo(144.6, 720.4, "EXERCÍCIO"),
            valor(31.1, 706.8, self.placa),
            valor(102.6, 706.8, self.exercicio),
            rotulo(316.7, 708.2, "MOTOR"),
            rotulo(453.1, 708.2, "CMT"),
            rotulo(490.0, 708.2, "EIXOS"),
            rotulo(528.0, 708.2, "LOTAÇÃO"),
            rotulo(202.9, 698.6, "QRCode"),
            valor(316.2, 694.4, "HA12E1234567"),
            valor(453.5, 694.4, "0.1"),
            valor(504.4, 694.4, "*"),
            valor(538.4, 694.4, "02P"),
            rotulo(31.0, 694.2, "ANO FABRICAÇÃO"),
            rotulo(102.7, 694.2, "ANO MODELO"),
            rotulo(316.7, 681.9, "CARROCERIA"),
            valor(31.1, 680.5, self.ano_fabricacao),
            valor(102.6, 680.5, self.ano_modelo),
            valor(316.2, 668.2, "NÃO APLICAVEL"),
            rotulo(31.0, 668.0, "NÚMERO DO CRV"),
            rotulo(316.7, 655.7, "NOME"),
            valor(31.1, 654.2, "***"),
            valor(316.2, 643.6, PROPRIETARIO),
            rotulo(463.0, 625.9, "CPF / CNPJ"),
            valor(462.9, 611.9, CPF_PROPRIETARIO),
            rotulo(31.0, 599.4, "CÓDIGO DE SEGURANÇA DO CLA"),
            rotulo(161.9, 599.4, "CAT"),
            rotulo(316.7, 599.4, "LOCAL"),
            rotulo(509.7, 599.4, "DATA"),
            valor(31.1, 576.7, "12345678901"),
            valor(162.3, 576.7, "***"),
            valor(316.2, 576.7, "FORTALEZA CE"),
            valor(509.7, 576.7, "07/10/2026"),
            rotulo(31.0, 564.2, "MARCA / MODELO / VERSÃO"),
            rotulo(383.2, 561.2, "ASSINADO DIGITALMENTE PELO DETRAN"),
            rotulo(526.6, 551.2, "*"),
            (315.2, 547.2, "DADOS DO SEGURO DPVAT", 1, 6.5),
            valor(31.1, 541.4, self.marca_modelo),
            rotulo(316.7, 530.6, "CAT. TARIF"),
            rotulo(389.0, 530.6, "DATA DE QUITAÇÃO"),
            rotulo(477.1, 530.6, "PAGAMENTO"),
            rotulo(31.0, 528.9, "ESPÉCIE / TIPO"),
            rotulo(477.1, 519.2, "COTA ÚNICA"),
            rotulo(530.0, 519.2, "PARCELADO"),
            valor(316.2, 512.7, "*"),
            valor(389.0, 512.7, "*"),
            valor(31.1, 506.2, "PASSAGEIRO MOTOCICLETA"),
            rotulo(316.7, 498.8, "REPASSE OBRIGATÓRIO AO"),
            rotulo(422.8, 498.8, "CUSTO DO"),
            rotulo(495.8, 498.8, "CUSTO EFETIVO"),
            rotulo(31.0, 493.7, "PLACA ANTERIOR / UF"),
            rotulo(158.5, 493.7, "CHASSI"),
            rotulo(316.7, 490.6, "FUNDO NACIONAL DE SAÚDE (R$)"),
            rotulo(422.8, 490.6, "BILHETE (R$)"),
            rotulo(495.8, 490.6, "DO SEGURO (R$)"),
            valor(316.2, 475.0, "*"),
            valor(423.5, 475.0, "*"),
            valor(494.3, 475.0, "*"),
            valor(31.1, 470.9, "*******/CE"),
            valor(130.6, 470.9, self.chassi),
            rotulo(316.7, 459.2, "REPASSE OBRIGATÓRIO AO"),
            rotulo(422.8, 459.2, "VALOR DO IOF (R$)"),
            rotulo(495.8, 459.2, "VALOR TOTAL A SER PAGO"),
            rotulo(31.0, 458.4, "COR PREDOMINANTE"),
            rotulo(102.4, 458.4, "COMBUSTÍVEL"),
            rotulo(316.7, 451.0, "DEPARTAMENTO NACIONAL DE"),
            rotulo(495.8, 451.0, "PELO SEGURADO (R$)"),
            rotulo(316.7, 442.8, "TRÂNSITO (R$)"),
            valor(31.1, 435.7, self.cor),
            valor(102.6, 435.7, self.combustivel),
            valor(316.2, 434.3, "*"),
            valor(423.5, 434.3, "*"),
            valor(494.3, 434.3, "*"),
            (
                31.1,
                425.4,
                "Documento emitido por CDT (00000000) em 07/10/2026 às 10:00:00.",
                1,
                4.4,
            ),
            (315.2, 410.0, "INFORMAÇÕES DO SEGURO DPVAT", 1, 6.5),
            (27.6, 409.9, "OBSERVAÇÕES DO VEÍCULO", 1, 6.5),
            valor(28.1, 391.6, "ALIENADO FIDUCIARIAMENTE"),
            (27.6, 157.0, "MENSAGENS SENATRAN", 1, 6.5),
            rotulo(32.2, 136.2, "Você Sabia?"),
            rotulo(
                32.2,
                119.3,
                "Na Carteira Digital de Trânsito - CDT, você tem acesso ao CRLV, à CNH e",
            ),
            rotulo(32.2, 85.2, "Leia o QR Code e baixe agora."),
        ]


# Dois CRLV-e no leiaute do Detran, com valores inventados (a moto do seed e um carro).
CRLV_DETRAN_MOTO = CrlvDetran()
CRLV_DETRAN_CARRO = CrlvDetran(
    placa="XYZ1234",
    chassi="9BD195271K0123456",
    renavam="00123456789",
    marca_modelo="FIAT/MOBI LIKE",
    ano_fabricacao="2019",
    ano_modelo="2019",
    cor="BRANCA",
    combustivel="ALCOOL/GASOLINA",
)


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
