"""T-331 · Calibração da leitura do CRLV-e com documentos reais (VEI-08, ADR 0026).

Dois CRLV-e reais do Detran-CE (um de carro, um de moto) foram lidos na máquina do qa, fora do
repositório (dado pessoal). Os PDFs daqui são fictícios, com o leiaute dos reais e valores
inventados (`documentos_pdf.CrlvDetran`). Os cinco campos que o parser errava
nos reais (vazios) eram `xfail` estritos até a correção da T-336; agora todos são testes comuns.
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
        # VEI-09 (T-421): carroceria "NÃO APLICAVEL" e observações em asteriscos ficam de fora.
        "potencia_cv": 8,
        "cilindrada_cc": 109,
        "especie": "passageiro",
        "tipo": "Motocicleta",
        "lotacao": 2,
        "peso_bruto_kg": 240,
        "numero_motor": "JC75E1S123456",
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
        "potencia_cv": 75,
        "cilindrada_cc": 999,
        "especie": "passageiro",
        "tipo": "Automóvel",
        "lotacao": 5,
        "peso_bruto_kg": 1400,
        "numero_motor": "552440012345",
    },
}
# Campos que o parser errou (vieram vazios) nos dois CRLV-e reais e que a T-336 corrigiu: o
# valor fica até 3 linhas abaixo do rótulo, depois de linhas só com o bloco do seguro, ou fora da
# coluna dele (o exercício).
ERRADOS = ("chassi", "marca_modelo", "cor", "combustivel", "exercicio")
CORRETOS = ("placa", "renavam", "ano_fabricacao", "ano_modelo")
# T-421: no leiaute do Detran, a potência e o peso ficam na linha do Renavam, e a lotação divide
# a linha com o CMT e os eixos.
DA_VEI_09 = (
    "potencia_cv",
    "cilindrada_cc",
    "especie",
    "tipo",
    "lotacao",
    "peso_bruto_kg",
    "numero_motor",
)


def _texto(formato: str) -> str:
    conteudo = FORMATOS[formato].pdf()
    return PdfReader(io.BytesIO(conteudo)).pages[0].extract_text(extraction_mode="layout")


def _casos(campos: tuple[str, ...]) -> list:  # type: ignore[type-arg]
    return [
        pytest.param(formato, campo, id=f"{formato}-{campo}")
        for formato in FORMATOS
        for campo in campos
    ]


@pytest.mark.parametrize(("formato", "campo"), _casos(CORRETOS))
def test_vei_08_detran_campo_lido_certo(formato: str, campo: str) -> None:
    assert crlv.extrair(_texto(formato)).get(campo) == ESPERADO[formato][campo]


@pytest.mark.parametrize(("formato", "campo"), _casos(ERRADOS))
def test_vei_08_detran_campo_errado_nos_reais(formato: str, campo: str) -> None:
    assert crlv.extrair(_texto(formato)).get(campo) == ESPERADO[formato][campo]


@pytest.mark.parametrize(("formato", "campo"), _casos(DA_VEI_09))
def test_vei_09_detran_campo_do_documento(formato: str, campo: str) -> None:
    assert crlv.extrair(_texto(formato)).get(campo) == ESPERADO[formato][campo]


@pytest.mark.parametrize("formato", list(FORMATOS))
def test_vei_08_detran_nunca_le_o_proprietario(formato: str) -> None:
    campos = crlv.extrair(_texto(formato))
    assert pdfs.PROPRIETARIO not in str(campos)
    assert pdfs.CPF_PROPRIETARIO not in str(campos)


@pytest.mark.parametrize("formato", list(FORMATOS))
def test_vei_08_detran_pelo_processo_filho_traz_os_campos(formato: str) -> None:
    resposta = leitura_documentos.executar("crlv", FORMATOS[formato].pdf())
    assert resposta["ok"] is True
    assert resposta["campos"] == ESPERADO[formato]
