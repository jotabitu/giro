"""T-374 · Catálogo completo de modelos (VEI-08, ADR 0031).

O catálogo versionado tem a carga da Parallelum mais a lista própria. A leitura do CRLV-e usa os
PDFs fictícios no leiaute do Detran (`documentos_pdf.CrlvDetran`, T-331) e roda na `empresa_a`.
"""

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.veiculos import catalogo
from apps.veiculos.catalogo import Modelo

from . import documentos_pdf as pdfs
from .test_t012_filiais import MotoRapida

LEITURA = "/api/veiculos/leitura-crlv/"


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def catalogo_temporario(tmp_path, monkeypatch) -> Iterator[Path]:
    arquivo = tmp_path / "catalogo_modelos.csv"
    monkeypatch.setattr(catalogo, "ARQUIVO", arquivo)
    catalogo.modelos.cache_clear()
    yield arquivo
    catalogo.modelos.cache_clear()


def test_vei_08_catalogo_completo_com_a_lista_propria() -> None:
    no_arquivo = catalogo.ler_csv(catalogo.ARQUIVO)
    tipos = {tipo: sum(1 for m in no_arquivo if m.tipo == tipo) for tipo in catalogo.TIPOS}
    assert tipos["carro"] > 7000 and tipos["moto"] > 2000  # ADR 0031: 7.386 e 2.038
    # A lista própria inteira está lá, e o arquivo está como o comando grava.
    assert set(catalogo.ler_csv(catalogo.ARQUIVO_PROPRIO)) <= set(no_arquivo)
    assert catalogo.organizar(no_arquivo) == no_arquivo
    # Uma grafia por marca no CSV inteiro.
    grafias: dict[str, set[str]] = defaultdict(set)
    for modelo in no_arquivo:
        grafias[modelo.marca_normalizada].add(modelo.marca)
    assert all(len(nomes) == 1 for nomes in grafias.values())
    assert grafias["HONDA"] == {"Honda"} and grafias["YAMAHA"] == {"Yamaha"}


def test_vei_08_catalogo_chave_calculada_na_leitura() -> None:
    modelo = Modelo("Honda", "Pop 110i ES", "moto")
    assert (modelo.chave, modelo.marca_normalizada) == ("HONDA POP 110I ES", "HONDA")
    assert modelo == Modelo("Honda", "Pop 110i ES", "moto")


def _ler(moto: MotoRapida, conteudo: bytes) -> dict:  # type: ignore[type-arg]
    arquivo = SimpleUploadedFile("crlv.pdf", conteudo, content_type="application/pdf")
    resposta = moto.api("Mariana").post(LEITURA, {"arquivo": arquivo}, format="multipart")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def test_vei_08_catalogo_crlv_detran_moto_acha_um_modelo(moto) -> None:
    corpo = _ler(moto, pdfs.CRLV_DETRAN_MOTO.pdf())
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == ("Honda", "Pop 110i ES")
    assert corpo["dicas"] == {"marca_modelo": None}


def test_vei_08_catalogo_crlv_detran_carro_com_versoes_vai_para_a_dica(moto) -> None:
    """CA-247-05: "FIAT/MOBI LIKE" começa mais de uma versão da FIPE e não preenche."""
    assert catalogo.achar_modelo("FIAT/MOBI LIKE") is None
    corpo = _ler(moto, pdfs.CRLV_DETRAN_CARRO.pdf())
    assert (corpo["campos"]["marca"], corpo["campos"]["modelo"]) == (None, None)
    assert corpo["dicas"] == {"marca_modelo": "FIAT/MOBI LIKE"}


def test_vei_08_catalogo_comando_junta_arquivos(catalogo_temporario, tmp_path) -> None:
    parallelum = tmp_path / "parallelum.csv"
    parallelum.write_text(
        "marca,modelo,tipo\n"
        "Honda,City EX 1.5,carro\n"
        "HONDA,POP 110i ES,moto\n"
        "YAMAHA,FACTOR 150 ED,moto\n",
        encoding="utf-8",
    )
    propria = tmp_path / "propria.csv"
    propria.write_text("marca,modelo,tipo\nHonda,Pop 110i ES,moto\n", encoding="utf-8")
    call_command("atualizar_catalogo_modelos", str(parallelum), str(propria))
    # A lista própria vence a duplicata; "Honda" dos carros vale para as motos; "YAMAHA" fica
    # como veio; o modelo nunca muda de grafia.
    assert catalogo_temporario.read_text(encoding="utf-8") == (
        "marca,modelo,tipo\n"
        "Honda,City EX 1.5,carro\n"
        "Honda,Pop 110i ES,moto\n"
        "YAMAHA,FACTOR 150 ED,moto\n"
    )
