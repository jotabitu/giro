"""Um app só importa de apps acima dele na ordem da ADR 0011; `comum` não importa nenhum."""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

NIVEL = {
    "auditoria": 2,
    "plataforma": 3,
    "empresas": 4,
    "contas": 4,
    "filiais": 5,
    "notificacoes": 5,
    "clientes": 6,
    "veiculos": 6,
    "contratos": 7,
    "aprovacoes": 7,
    "financeiro": 8,
    "manutencao": 9,
    "locacoes": 10,
    "vistorias": 11,
    "vendas": 12,
    "automacoes": 13,
    "relatorios": 13,
    "importacao": 13,  # ADR 0017
}


def _apps_importados(arquivo: Path) -> set[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    modulos: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            modulos += [alias.name for alias in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            modulos.append(no.module)
    return {m.split(".")[1] for m in modulos if m.startswith("apps.") and m.count(".") >= 1}


def test_todos_os_apps_estao_na_ordem():
    pastas = {p.name for p in (RAIZ / "apps").iterdir() if (p / "apps.py").exists()}
    assert pastas == set(NIVEL)


def test_nenhum_app_importa_de_baixo_para_cima():
    violacoes = []
    for app, nivel in NIVEL.items():
        for arquivo in (RAIZ / "apps" / app).rglob("*.py"):
            if "tests" in arquivo.parts:
                continue
            for outro in _apps_importados(arquivo):
                if outro != app and NIVEL.get(outro, 99) >= nivel:
                    violacoes.append(f"{arquivo.relative_to(RAIZ)} importa apps.{outro}")
    assert not violacoes, "\n".join(violacoes)


def test_comum_nao_importa_apps_de_dominio():
    violacoes = [
        str(arquivo.relative_to(RAIZ))
        for arquivo in (RAIZ / "comum").rglob("*.py")
        if "tests" not in arquivo.parts and _apps_importados(arquivo)
    ]
    assert not violacoes


# ADR 0019: os apps de origem abrem pedidos só por `comum.aprovacoes`, nunca importando
# `aprovacoes`; o assinante em `<app>/eventos.py` recebe o evento sem importar nada.
ORIGENS_DE_PEDIDOS = ("clientes", "veiculos", "financeiro", "manutencao", "locacoes", "vendas")


def test_origens_de_pedidos_nao_importam_aprovacoes():
    violacoes = [
        str(arquivo.relative_to(RAIZ))
        for app in ORIGENS_DE_PEDIDOS
        for arquivo in (RAIZ / "apps" / app).rglob("*.py")
        if "tests" not in arquivo.parts
        and arquivo.name != "eventos.py"
        and "aprovacoes" in _apps_importados(arquivo)
    ]
    assert not violacoes, "\n".join(violacoes)
