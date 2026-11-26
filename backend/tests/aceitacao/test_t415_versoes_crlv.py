"""T-415 · CRLV-e: escolher a versão quando várias batem (VEI-08, ADR 0031).

O CRLV-e real do Chevrolet Cruze (Detran-CE) traz "CHEVROLET/CRUZE LT NB". A FIPE não tem "NB",
e "CRUZE LT" bate com 3 versões. Decisão do dono em 29 out 2026: preencher a marca e mostrar as
versões que batem para a pessoa escolher uma. O PDF daqui é fictício, no leiaute do Detran
(`documentos_pdf.CrlvDetran`); o real não entra no repositório.
"""

from dataclasses import replace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.veiculos import catalogo
from apps.veiculos.catalogo import Modelo

from . import documentos_pdf as pdfs
from .test_t012_filiais import MotoRapida

LEITURA = "/api/veiculos/leitura-crlv/"
MODELOS = "/api/veiculos/modelos/"
CHEVROLET = "GM - Chevrolet"
CRUZE_LT = [
    Modelo(CHEVROLET, "CRUZE LT 1.4 16V Turbo Flex 4p Aut.", "carro"),
    Modelo(CHEVROLET, "CRUZE LT 1.8 16V FlexPower 4p Aut.", "carro"),
    Modelo(CHEVROLET, "CRUZE LT 1.8 16V FlexPower 4p Mec.", "carro"),
]


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


def _ler(moto: MotoRapida, marca_modelo: str) -> dict:  # type: ignore[type-arg]
    conteudo = replace(pdfs.CRLV_DETRAN_CARRO, marca_modelo=marca_modelo).pdf()
    arquivo = SimpleUploadedFile("crlv.pdf", conteudo, content_type="application/pdf")
    resposta = moto.api("Mariana").post(LEITURA, {"arquivo": arquivo}, format="multipart")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def test_vei_08_candidatos_ignoram_sufixo_que_nao_existe_na_fipe() -> None:
    # "NB" não existe em nenhuma versão do Cruze: sai, e "CRUZE LT" acha as 3 versões.
    assert catalogo.candidatos("CHEVROLET/CRUZE LT NB") == CRUZE_LT
    assert catalogo.candidatos("GM/CRUZE LT NB") == CRUZE_LT
    assert catalogo.achar_modelo("CHEVROLET/CRUZE LT NB") is None
    # A palavra que existe nas versões filtra; a que não existe é ignorada.
    assert catalogo.candidatos("CHEVROLET/CRUZE LT AUT NB") == [CRUZE_LT[0], CRUZE_LT[1]]
    assert catalogo.candidatos("CHEVROLET/CRUZE LT 1.4 NB") == [CRUZE_LT[0]]
    # Um candidato só preenche, como antes.
    assert catalogo.achar_modelo("CHEVROLET/CRUZE LT 1.4 NB") == CRUZE_LT[0]
    assert catalogo.candidatos("HONDA/POP 110I ES") == [Modelo("Honda", "Pop 110i ES", "moto")]


def test_vei_08_candidatos_so_a_marca_nao_basta() -> None:
    assert catalogo.candidatos("CHEVROLET") == []
    assert catalogo.candidatos("CHEVROLET/NB") == []
    assert catalogo.candidatos("CHEVROLET/XYZ ABC") == []
    assert catalogo.candidatos("SUZUKI/YES 125") == []


def test_vei_08_ca_521_01_varias_versoes_preenche_a_escolhida_pela_api(moto) -> None:
    """T-521: com várias versões, a mais parecida com o texto preenche marca e modelo, conta nos
    preenchidos e vem em `dicas.escolhido`; as versões vêm da mais parecida à menos parecida."""
    corpo = _ler(moto, "CHEVROLET/CRUZE LT NB")
    escolhido = CRUZE_LT[0]
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == (CHEVROLET, escolhido.modelo)
    assert "marca" in corpo["lidos"] and "modelo" in corpo["lidos"]
    assert corpo["quantidade"] == 16  # mais os 7 do documento (VEI-09, T-421)
    assert corpo["rotulo"] == "CRLV-e lido · 16 campos preenchidos"
    assert corpo["dicas"] == {
        "marca_modelo": "CHEVROLET/CRUZE LT NB",
        "candidatos": [{"marca": m.marca, "modelo": m.modelo, "tipo": m.tipo} for m in CRUZE_LT],
        "escolhido": {"marca": CHEVROLET, "modelo": escolhido.modelo, "tipo": "carro"},
    }
    # A ordem é pela semelhança: a palavra "AUT" põe a 1.8 Aut. na frente.
    ordem = catalogo.por_semelhanca("CHEVROLET/CRUZE LT AUT NB", CRUZE_LT[:2])
    assert ordem == [CRUZE_LT[1], CRUZE_LT[0]]


def test_vei_08_ca_521_02_sem_candidato_preenche_o_texto_lido(moto) -> None:
    """T-521: sem versão no catálogo, marca e modelo saem do texto lido, separados na "/", com o
    nome da marca do catálogo quando ela está nele (pelo nome ou pelo apelido do Detran)."""
    corpo = _ler(moto, "SUZUKI/YES 125")
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == ("Suzuki", "YES 125")
    assert "marca" in corpo["lidos"] and "modelo" in corpo["lidos"]
    assert corpo["dicas"] == {"marca_modelo": "SUZUKI/YES 125", "candidatos": [], "escolhido": None}
    assert catalogo.separar("GM/XYZ ABC") == ("GM - Chevrolet", "XYZ ABC")
    assert catalogo.separar("ACME/ABC 1") == ("ACME", "ABC 1")
    assert catalogo.separar("I/ACME ABC") == ("ACME", "ABC")
    assert catalogo.separar("HONDA/") == ("Honda", None)


def test_vei_08_ca_521_03_uma_versao_preenche_como_antes(moto) -> None:
    corpo = _ler(moto, "CHEVROLET/CRUZE LT 1.4 NB")
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == (CHEVROLET, CRUZE_LT[0].modelo)
    assert corpo["dicas"] == {"marca_modelo": None, "candidatos": [], "escolhido": None}


def test_vei_08_ca_521_01_no_maximo_5_versoes(moto) -> None:
    # "CHEVROLET/CRUZE" bate com as 17 versões do Cruze. T-521 (decisão do dono): vêm as 5 mais
    # parecidas, a escolhida na frente; as outras, a pessoa busca na lista de modelos.
    assert len(catalogo.candidatos("CHEVROLET/CRUZE")) == 17
    corpo = _ler(moto, "CHEVROLET/CRUZE")
    assert corpo["campos"]["marca"] == CHEVROLET
    assert len(corpo["dicas"]["candidatos"]) == 5
    assert corpo["dicas"]["candidatos"][0] == corpo["dicas"]["escolhido"]
    assert corpo["campos"]["modelo"] == corpo["dicas"]["escolhido"]["modelo"]


def test_vei_08_lista_de_modelos_aceita_o_apelido_da_marca(moto) -> None:
    api = moto.api("Mariana")
    resultados = api.get(MODELOS, {"marca": "Chevrolet", "busca": "cruze lt"}).json()["resultados"]
    assert [r["modelo"] for r in resultados if r["modelo"].startswith("CRUZE LT ")] == [
        m.modelo for m in CRUZE_LT
    ]
    # Pela busca também: "chevrolet cruze" acha as versões de "GM - Chevrolet".
    resultados = api.get(MODELOS, {"tipo": "carro", "busca": "chevrolet cruze"}).json()[
        "resultados"
    ]
    assert len(resultados) == 17 and {r["marca"] for r in resultados} == {CHEVROLET}
    # "VW" vale como "VW - VolksWagen" e como "Volkswagen" da lista própria.
    marcas = {m.marca for m in catalogo.listar(marca="VW", busca="gol")}
    assert marcas == {"VW - VolksWagen", "Volkswagen"}
    # A marca da lista continua valendo sozinha.
    assert {m.marca for m in catalogo.listar(marca="GM - Chevrolet")} == {CHEVROLET}
