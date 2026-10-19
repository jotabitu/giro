"""T-257 · Catálogo de marcas e modelos (VEI-08, ADR 0026, item 7).

O catálogo é o `apps/veiculos/dados/catalogo_modelos.csv`, igual para todas as empresas. A rota
roda na `empresa_a` com as pessoas do seed.
"""

from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.veiculos import catalogo
from apps.veiculos.catalogo import Modelo

from .test_t012_filiais import MotoRapida

POP_ES = Modelo("Honda", "Pop 110i ES", "moto")


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def catalogo_temporario(tmp_path, monkeypatch) -> Path:
    arquivo = tmp_path / "catalogo_modelos.csv"
    monkeypatch.setattr(catalogo, "ARQUIVO", arquivo)
    catalogo.modelos.cache_clear()
    yield arquivo
    catalogo.modelos.cache_clear()


def test_vei_08_catalogo_acha_modelo_unico() -> None:
    # O "HONDA/POP 110I ES" do crlv-tbc5h21.pdf (docs/qa/criterios/T-247.md).
    assert catalogo.achar_modelo("HONDA/POP 110I ES") == POP_ES
    assert catalogo.achar_modelo("honda / pop 110i es") == POP_ES
    assert catalogo.achar_modelo("HONDA/POP 110I") == Modelo("Honda", "Pop 110i", "moto")
    assert catalogo.achar_modelo("HONDA/CG 160 FAN") == Modelo("Honda", "CG 160 Fan", "moto")
    assert catalogo.achar_modelo("YAMAHA/NMAX 160") == Modelo("Yamaha", "NMax 160", "moto")
    # Começo único: o texto lido é o início de um modelo só, ou um modelo só é o início dele.
    assert catalogo.achar_modelo("RENAULT/KWI") is None  # palavra cortada não vale
    assert catalogo.achar_modelo("HONDA/XRE 300") == Modelo("Honda", "XRE 300 Sahara", "moto")
    assert catalogo.achar_modelo("RENAULT/KWID ZEN 1.0") == Modelo("Renault", "Kwid", "carro")


def test_vei_08_catalogo_ambiguo_nao_preenche() -> None:
    assert catalogo.achar_modelo("HONDA/POP") is None  # Pop 110i e Pop 110i ES
    assert catalogo.achar_modelo("HONDA/CG 160") is None  # Cargo, Fan, Start e Titan
    assert catalogo.achar_modelo("RENAULT") is None  # só a marca não basta
    assert catalogo.achar_modelo("SUZUKI/YES 125") is None  # fora da lista
    assert catalogo.achar_modelo("  /  ") is None


def test_vei_08_catalogo_tem_os_modelos_do_seed_sem_duplicata() -> None:
    do_seed = {
        ("Honda", "Pop 110i"),
        ("Honda", "Biz 125"),
        ("Honda", "CG 160 Fan"),
        ("Yamaha", "Factor 150"),
        ("Yamaha", "NMax 160"),
        ("Renault", "Kwid"),
        ("Fiat", "Mobi"),
        ("Honda", "Pop 110i ES"),
    }
    no_arquivo = catalogo.ler_csv(catalogo.ARQUIVO)
    assert do_seed <= {(m.marca, m.modelo) for m in no_arquivo}
    # O arquivo está como o comando grava: sem duplicata e em ordem.
    assert catalogo.organizar(no_arquivo) == no_arquivo
    assert {m.tipo for m in no_arquivo} <= set(catalogo.TIPOS)


def test_vei_08_lista_de_modelos_filtra(moto) -> None:
    for nome in ("Mariana", "Bruna", "João", "Lúcia"):  # todos veem veículos
        assert moto.api(nome).get("/api/veiculos/modelos/").status_code == 200, nome
    api = moto.api("Bruna")

    carros = api.get("/api/veiculos/modelos/", {"tipo": "carro"}).json()["resultados"]
    assert carros and {m["tipo"] for m in carros} == {"carro"}
    assert {"marca": "Renault", "modelo": "Kwid", "tipo": "carro"} in carros

    pops = api.get("/api/veiculos/modelos/", {"marca": "honda", "busca": "pop"}).json()
    assert pops["resultados"] == [
        {"marca": "Honda", "modelo": "Pop 110i", "tipo": "moto"},
        {"marca": "Honda", "modelo": "Pop 110i ES", "tipo": "moto"},
    ]
    busca = api.get("/api/veiculos/modelos/", {"busca": "yamaha nmax"}).json()["resultados"]
    assert [m["modelo"] for m in busca] == ["NMax 160"]
    assert api.get("/api/veiculos/modelos/", {"tipo": "moto", "marca": "Fiat"}).json() == {
        "resultados": []
    }

    todos = api.get("/api/veiculos/modelos/").json()["resultados"]
    ordem = [(catalogo.normalizar(m["marca"]), catalogo.normalizar(m["modelo"])) for m in todos]
    assert ordem == sorted(ordem)

    invalido = api.get("/api/veiculos/modelos/", {"tipo": "caminhao"})
    assert invalido.status_code == 400
    assert "tipo" in invalido.json()["campos"]


def test_vei_08_lista_de_modelos_ate_50(moto, monkeypatch) -> None:
    muitos = tuple(Modelo("Honda", f"Modelo {n:03d}", "moto") for n in range(60))
    monkeypatch.setattr(catalogo, "modelos", lambda: muitos)
    resultados = moto.api().get("/api/veiculos/modelos/").json()["resultados"]
    assert len(resultados) == 50
    assert resultados[0]["modelo"] == "Modelo 000"


def test_vei_08_comando_regrava_o_catalogo(catalogo_temporario, tmp_path) -> None:
    fipe = tmp_path / "fipe.csv"
    fipe.write_text(
        "Marca,Modelo,Tipo\n"
        "Yamaha,  NMax   160 ,Motos\n"
        "Honda,Pop 110i ES,moto\n"
        "HONDA,POP 110I ES,moto\n"  # duplicata pela chave normalizada: fica a primeira
        "Fiat,Mobi,Carros\n"
        "Scania,R 450,caminhoes\n"  # tipo fora da lista
        "Honda,,moto\n",
        encoding="utf-8",
    )
    call_command("atualizar_catalogo_modelos", str(fipe))
    assert catalogo_temporario.read_text(encoding="utf-8") == (
        "marca,modelo,tipo\nFiat,Mobi,carro\nHonda,Pop 110i ES,moto\nYamaha,NMax 160,moto\n"
    )
    assert catalogo.achar_modelo("YAMAHA/NMAX 160") == Modelo("Yamaha", "NMax 160", "moto")


def test_vei_08_comando_recusa_arquivo_sem_colunas(catalogo_temporario, tmp_path) -> None:
    errado = tmp_path / "errado.csv"
    errado.write_text("fabricante,nome\nHonda,Pop\n", encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("atualizar_catalogo_modelos", str(errado))
    assert not catalogo_temporario.exists()
