"""T-374 · Script que baixa o catálogo da Parallelum (VEI-08, ADR 0031), com respostas falsas.

O script fica fora do Django (`scripts/`) e é carregado aqui pelo caminho. Nada vai à rede.
"""

import importlib.util
import sys
import urllib.error
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

CAMINHO = Path(__file__).resolve().parents[1] / "scripts" / "baixar_catalogo_parallelum.py"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("baixar_catalogo_parallelum", CAMINHO)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


BASE = "https://parallelum.com.br/fipe/api/v2"
RESPOSTAS: dict[str, Any] = {
    f"{BASE}/cars/brands": [{"code": "21", "name": "Fiat"}, {"code": "25", "name": "Honda"}],
    f"{BASE}/cars/brands/21/models": [{"code": "1", "name": "MOBI LIKE 1.0 Fire Flex 5p."}],
    f"{BASE}/cars/brands/25/models": [{"code": "2", "name": "City Sedan EX 1.5 Flex 16V Aut."}],
    f"{BASE}/motorcycles/brands": [{"code": "80", "name": "HONDA"}],
    f"{BASE}/motorcycles/brands/80/models": [
        {"code": "3", "name": "POP 110i ES"},
        {"code": "4", "name": " CG 160 FAN Flex "},
    ],
}


class Api:
    """A API falsa: guarda os pedidos e as esperas, e responde 429 a partir do pedido `limite`."""

    def __init__(self, limite: int | None = None) -> None:
        self.pedidos: list[str] = []
        self.esperas: list[float] = []
        self.limite = limite

    def buscar(self, url: str) -> Any:
        self.pedidos.append(url)
        if self.limite is not None and len(self.pedidos) >= self.limite:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)  # type: ignore[arg-type]
        return RESPOSTAS[url]

    def esperar(self, segundos: float) -> None:
        self.esperas.append(segundos)


def _rodar(script: ModuleType, api: Api, saida: Path) -> int:
    def buscar(url: str) -> Any:
        try:
            return api.buscar(url)
        except urllib.error.HTTPError as erro:
            if erro.code == 429:
                raise script.LimiteAtingido from erro
            raise

    return int(script.main([str(saida)], buscar=buscar, esperar=api.esperar))


def test_vei_08_parallelum_tipos_e_csv(script, tmp_path, capsys) -> None:
    api = Api()
    saida = tmp_path / "parallelum.csv"
    assert _rodar(script, api, saida) == 0
    # Carros e motos, sem `trucks`; um pedido por segundo (a espera vem antes de cada pedido
    # depois do primeiro).
    assert api.pedidos == list(RESPOSTAS)
    assert not any("trucks" in url for url in api.pedidos)
    assert api.esperas == [1.0] * (len(api.pedidos) - 1)
    assert saida.read_text(encoding="utf-8") == (
        "marca,modelo,tipo\n"
        "Fiat,MOBI LIKE 1.0 Fire Flex 5p.,carro\n"
        "Honda,City Sedan EX 1.5 Flex 16V Aut.,carro\n"
        "HONDA,POP 110i ES,moto\n"
        "HONDA,CG 160 FAN Flex,moto\n"
    )
    assert "4 modelos gravados" in capsys.readouterr().out


def test_vei_08_parallelum_para_no_429_sem_gravar(script, tmp_path, capsys) -> None:
    api = Api(limite=4)  # o 429 chega no meio das motos
    saida = tmp_path / "parallelum.csv"
    assert _rodar(script, api, saida) == 1
    assert len(api.pedidos) == 4  # parou ali, sem tentar de novo
    assert not saida.exists()  # nada de meia lista
    assert "429" in capsys.readouterr().err


def test_vei_08_parallelum_tenta_de_novo_so_na_falha_de_rede(script, monkeypatch) -> None:
    respostas: list[Any] = [ConnectionResetError("caiu"), b"[]"]
    esperas: list[float] = []

    class Resposta:
        def __init__(self, corpo: bytes) -> None:
            self.corpo = corpo

        def __enter__(self) -> "Resposta":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return self.corpo

    def abrir(*_: Any, **__: Any) -> Resposta:
        proxima = respostas.pop(0)
        if isinstance(proxima, Exception):
            raise proxima
        return Resposta(proxima)

    monkeypatch.setattr(script.urllib.request, "urlopen", abrir)
    assert script.buscar(f"{BASE}/cars/brands", esperar=esperas.append) == []
    assert esperas == [5.0]

    def limite(*_: Any, **__: Any) -> None:
        raise urllib.error.HTTPError("x", 429, "Too Many Requests", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(script.urllib.request, "urlopen", limite)
    with pytest.raises(script.LimiteAtingido):
        script.buscar(f"{BASE}/cars/brands", esperar=esperas.append)
    assert esperas == [5.0]  # o 429 não espera nem tenta de novo


def test_vei_08_parallelum_fora_do_django() -> None:
    """Só biblioteca padrão, e nenhum código do Django importa o script."""
    texto = CAMINHO.read_text(encoding="utf-8")
    for linha in texto.splitlines():
        if linha.startswith(("import ", "from ")):
            modulo = linha.split()[1].split(".")[0]
            assert modulo in sys.stdlib_module_names, linha
    raiz = CAMINHO.parents[1]
    for arquivo in (raiz / "apps").rglob("*.py"):
        assert "baixar_catalogo_parallelum" not in arquivo.read_text(encoding="utf-8"), arquivo
