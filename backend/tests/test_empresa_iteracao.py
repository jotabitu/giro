"""ADR 0040, item 7: quem itera ou resolve empresa parte de `Empresa.objects.prontas()`.

A reserva (`schema_pronto_em` nulo) é inalcançável. `Empresa.objects.<consulta>` direto só vale em
`plataforma.banco`, no Django Admin e nas linhas marcadas `# inclui-reserva` (a criação, que
precisa ver a reserva para não repetir o endereço ou o CNPJ, e o alarme das reservas presas). As
migrações ficam fora (a de dados do item 5 usa o model histórico).
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTAS = ("apps", "comum")
EXCECOES = {"apps/plataforma/banco.py", "apps/plataforma/admin.py"}
MARCA = "# inclui-reserva"
# `Empresa.objects.x(` ou `get_tenant_model().objects.x(`, também quebrado em linhas; nunca
# dentro de crase (texto de docstring).
CONSULTA = re.compile(
    r"(?<!`)\b(?:Empresa|get_tenant_model\(\))\s*\.\s*objects\s*\.\s*(?!prontas\(\))(\w+)\s*\("
)


def _ofensas() -> list[str]:
    achadas = []
    for pasta in PASTAS:
        for arquivo in sorted((RAIZ / pasta).rglob("*.py")):
            relativo = arquivo.relative_to(RAIZ).as_posix()
            if "/tests/" in relativo or "/migrations/" in relativo or relativo in EXCECOES:
                continue
            texto = arquivo.read_text(encoding="utf-8")
            linhas = texto.splitlines()
            for achado in CONSULTA.finditer(texto):
                inicio = texto.count("\n", 0, achado.start())
                fim = texto.count("\n", 0, achado.end())
                trecho = linhas[inicio : fim + 2]
                if any(MARCA in linha for linha in trecho):
                    continue
                achadas.append(f"{relativo}:{inicio + 1}: {achado.group(0)}")
    return achadas


def test_empresa_iteracao_usa_prontas():
    assert _ofensas() == []


def test_empresa_iteracao_usa_prontas_acha_o_que_falta(tmp_path):
    """O próprio teste pega a consulta direta, inclusive quebrada em linhas."""
    pasta = tmp_path / "apps" / "x"
    pasta.mkdir(parents=True)
    (tmp_path / "comum").mkdir()
    (pasta / "m.py").write_text(
        "a = Empresa.objects.filter(pk=1)\n"
        "b = (\n    get_tenant_model()\n    .objects.exclude(x=1)\n)\n"
        "c = Empresa.objects.prontas().get(pk=1)\n"
        "d = Empresa.objects.get(pk=1)  # inclui-reserva\n",
        encoding="utf-8",
    )
    globals()["RAIZ"] = tmp_path
    try:
        ofensas = _ofensas()
    finally:
        globals()["RAIZ"] = Path(__file__).resolve().parent.parent
    assert [o.split(":")[1] for o in ofensas] == ["1", "3"]
