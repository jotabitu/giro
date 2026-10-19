"""O que fica aberto em cada módulo do plano (PLT-12, ADR 0024, item 7).

Os apps donos registram um contador por grupo no `ready()`; `contar()` roda no schema corrente.
Grupo sem contador registrado (app que ainda não existe) vale 0, como os contadores da `FIL-06`.
"""

from collections.abc import Callable, Iterable
from typing import Any

# Na ordem do texto da recusa: grupo, recurso, singular, plural (`assinatura.md`, `empresas.md`).
GRUPOS: tuple[tuple[str, str, str, str], ...] = (
    (
        "despesas_aguardando_aprovacao",
        "manutencao_despesas",
        "despesa aguardando aprovação",
        "despesas aguardando aprovação",
    ),
    ("despesas_a_pagar", "manutencao_despesas", "despesa a pagar", "despesas a pagar"),
    ("ordens_servico", "manutencao_despesas", "OS aberta", "OS abertas"),
    ("vendas", "vendas_comissoes", "venda aberta", "vendas abertas"),
    ("comissoes", "vendas_comissoes", "comissão a pagar", "comissões a pagar"),
    ("locacoes", "locacoes_vistoria", "locação aberta", "locações abertas"),
)
RECURSO_DO_GRUPO = {grupo: recurso for grupo, recurso, _, _ in GRUPOS}

_contadores: dict[str, Callable[[], int]] = {}


def registrar_pendencia(recurso: str, grupo: str, contar: Callable[[], int]) -> None:
    if RECURSO_DO_GRUPO.get(grupo) != recurso:
        raise ValueError(f"Grupo {grupo} não é do recurso {recurso}.")
    _contadores[grupo] = contar


def pendencias(recursos: Iterable[str]) -> list[dict[str, Any]]:
    """`[{grupo, quantidade, texto}]` dos recursos pedidos, só os grupos com quantidade."""
    pedidos = set(recursos)
    abertos = []
    for grupo, recurso, um, varios in GRUPOS:
        contar = _contadores.get(grupo)
        if recurso not in pedidos or contar is None:
            continue
        quantidade = int(contar())
        if quantidade:
            texto = f"{quantidade} {um if quantidade == 1 else varios}"
            abertos.append({"grupo": grupo, "quantidade": quantidade, "texto": texto})
    return abertos
