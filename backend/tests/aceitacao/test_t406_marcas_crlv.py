"""T-406 · Marcas do CRLV-e real no catálogo (VEI-08, achado do E2E da T-375).

Os dois CRLV-e reais do Detran-CE trazem "RE/CLASSIC 350" e "CHEVROLET/CRUZE LT NB". Os PDFs
daqui são fictícios, no leiaute do Detran (`documentos_pdf.CrlvDetran`), só com esses textos; os
reais não entram no repositório.
"""

from dataclasses import replace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.veiculos import catalogo
from apps.veiculos.catalogo import Modelo

from . import documentos_pdf as pdfs
from .test_t012_filiais import MotoRapida

LEITURA = "/api/veiculos/leitura-crlv/"
CLASSIC_350 = Modelo("Royal Enfield", "Classic 350", "moto")


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


def test_vei_08_marca_do_detran_pelo_apelido() -> None:
    # RE é a Royal Enfield; a Classic 350 da lista própria é a única igual.
    assert catalogo.achar_modelo("RE/CLASSIC 350") == CLASSIC_350
    # CHEVROLET e GM valem também como "GM - Chevrolet" (FIPE); VW como "VW - VolksWagen".
    cruze = Modelo("GM - Chevrolet", "CRUZE LTZ 1.4 16V Turbo Flex 4p Aut.", "carro")
    assert catalogo.achar_modelo("CHEVROLET/CRUZE LTZ 1.4 16V TURBO FLEX 4P AUT") == cruze
    assert catalogo.achar_modelo("GM/CRUZE LTZ 1.4 16V TURBO FLEX 4P AUT") == cruze
    assert catalogo.achar_modelo("GM/ONIX") == Modelo("Chevrolet", "Onix", "carro")
    assert catalogo.achar_modelo("VW/GOL") == Modelo("Volkswagen", "Gol", "carro")
    # O "I/" do importado sai antes da marca.
    assert catalogo.achar_modelo("I/RE/CLASSIC 350") == CLASSIC_350
    # Só a marca, mesmo pelo apelido, não basta.
    assert catalogo.achar_modelo("RE/") is None
    assert catalogo.achar_modelo("CHEVROLET") is None


def test_vei_08_carro_com_versoes_continua_na_dica() -> None:
    """CA-247-05: "CRUZE LT" tem as versões 1.4 e 1.8 na FIPE, e o "NB" do Detran não as
    separa. A marca agora vale, mas o modelo não é único."""
    assert catalogo.achar_modelo("CHEVROLET/CRUZE LT NB") is None
    assert catalogo.achar_modelo("CHEVROLET/CRUZE LT") is None


def _ler(moto: MotoRapida, marca_modelo: str, base: pdfs.CrlvDetran) -> dict:  # type: ignore[type-arg]
    conteudo = replace(base, marca_modelo=marca_modelo).pdf()
    arquivo = SimpleUploadedFile("crlv.pdf", conteudo, content_type="application/pdf")
    resposta = moto.api("Mariana").post(LEITURA, {"arquivo": arquivo}, format="multipart")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def test_vei_08_crlv_detran_moto_re_classic_350(moto) -> None:
    corpo = _ler(moto, "RE/CLASSIC 350", pdfs.CRLV_DETRAN_MOTO)
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == (
        "Royal Enfield",
        "Classic 350",
    )
    assert corpo["dicas"] == {"marca_modelo": None}


def test_vei_08_crlv_detran_carro_chevrolet_cruze_lt_nb(moto) -> None:
    corpo = _ler(moto, "CHEVROLET/CRUZE LT NB", pdfs.CRLV_DETRAN_CARRO)
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == (None, None)
    assert corpo["dicas"] == {"marca_modelo": "CHEVROLET/CRUZE LT NB"}
