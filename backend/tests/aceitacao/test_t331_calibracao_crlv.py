"""T-331 · Calibração da leitura do CRLV-e com documentos reais (VEI-08, ADR 0026).

Dois CRLV-e reais do Detran-CE (um de carro, um de moto) foram lidos na máquina do qa, fora do
repositório (dado pessoal). Os PDFs daqui são fictícios, com o leiaute dos reais e valores
inventados (`documentos_pdf.CrlvDetran`). Cada campo errado pelo parser nos reais é um teste
`xfail` estrito: quando o backend corrigir (tarefa descrita no handoff T-331-qa), o teste passa,
o `xfail` estrito avisa e a marca sai.

Os campos que o parser já lê certo nos reais ficam como teste comum, para a correção não os quebrar.
"""

import io

import pytest
from pypdf import PdfReader

from integracoes import leitura_documentos
from integracoes.leitura_documentos import crlv

from . import documentos_pdf as pdfs

FORMATOS = {"moto": pdfs.CRLV_DETRAN_MOTO, "carro": pdfs.CRLV_DETRAN_CARRO}
ESPERADO = {
    "moto": {
        "placa": "TBC5H21",
        "chassi": "9C2JC7510SR000123",
        "renavam": "01234567897",
        "marca_modelo": "HONDA/POP 110I ES",
        "ano_fabricacao": 2025,
        "ano_modelo": 2026,
        "cor": "vermelha",
        "combustivel": "gasolina",
        "exercicio": 2026,
    },
    "carro": {
        "placa": "XYZ1234",
        "chassi": "9BD195271K0123456",
        "renavam": "00123456789",
        "marca_modelo": "FIAT/MOBI LIKE",
        "ano_fabricacao": 2019,
        "ano_modelo": 2019,
        "cor": "branca",
        "combustivel": "flex",
        "exercicio": 2026,
    },
}
# Campos que o parser errou (vieram vazios) nos dois CRLV-e reais. O valor lido certo não muda o
# motivo: o rótulo é achado, e o valor não é pego (ver a causa no handoff).
ERRADOS = ("chassi", "marca_modelo", "cor", "combustivel", "exercicio")
CORRETOS = ("placa", "renavam", "ano_fabricacao", "ano_modelo")
CAUSA = {
    "chassi": "linha abaixo do rótulo só com texto do seguro (coluna da direita)",
    "marca_modelo": "linha abaixo do rótulo só com texto do seguro (coluna da direita)",
    "cor": "duas linhas abaixo do rótulo só com texto do seguro (coluna da direita)",
    "combustivel": "duas linhas abaixo do rótulo só com texto do seguro (coluna da direita)",
    "exercicio": "valor à esquerda do rótulo, fora da coluna dele",
}


def _texto(formato: str) -> str:
    conteudo = FORMATOS[formato].pdf()
    return PdfReader(io.BytesIO(conteudo)).pages[0].extract_text(extraction_mode="layout")


def _casos(campos: tuple[str, ...], marcar: bool) -> list:  # type: ignore[type-arg]
    casos = []
    for formato in FORMATOS:
        for campo in campos:
            marcas = (
                [pytest.mark.xfail(strict=True, reason=f"T-331: {CAUSA[campo]}")] if marcar else []
            )
            casos.append(pytest.param(formato, campo, id=f"{formato}-{campo}", marks=marcas))
    return casos


@pytest.mark.parametrize(("formato", "campo"), _casos(CORRETOS, marcar=False))
def test_vei_08_detran_campo_lido_certo(formato: str, campo: str) -> None:
    assert crlv.extrair(_texto(formato)).get(campo) == ESPERADO[formato][campo]


@pytest.mark.parametrize(("formato", "campo"), _casos(ERRADOS, marcar=True))
def test_vei_08_detran_campo_errado_nos_reais(formato: str, campo: str) -> None:
    assert crlv.extrair(_texto(formato)).get(campo) == ESPERADO[formato][campo]


@pytest.mark.parametrize("formato", list(FORMATOS))
def test_vei_08_detran_nunca_le_o_proprietario(formato: str) -> None:
    campos = crlv.extrair(_texto(formato))
    assert pdfs.PROPRIETARIO not in str(campos)
    assert pdfs.CPF_PROPRIETARIO not in str(campos)


@pytest.mark.xfail(strict=True, reason="T-331: cinco campos de cada CRLV-e do Detran vêm vazios")
@pytest.mark.parametrize("formato", list(FORMATOS))
def test_vei_08_detran_pelo_processo_filho_traz_os_nove_campos(formato: str) -> None:
    resposta = leitura_documentos.executar("crlv", FORMATOS[formato].pdf())
    assert resposta["ok"] is True
    assert resposta["campos"] == ESPERADO[formato]
