"""Leituras compostas entre apps por registro (ADR 0015).

O app de baixo registra, no `AppConfig.ready()`, o que sabe sobre um objeto do app de cima;
o app de cima consulta o registro sem importar o de baixo (ADR 0011).

- Anotação: `registrar_anotacao(alvo, bloco, anotar=..., montar=...)`, com alvo `"filiais.Filial"`.
  `aplicar(alvo, qs)` acrescenta as anotações (uma query para a lista toda) e `blocos(alvo, obj)`
  junta o que cada fornecedor montou para cada bloco. Bloco sem fornecedor não aparece.
- Filtro: `registrar_filtro(alvo, nome, filtrar)` (ex.: `com_locacao` e `em_aberto` da lista de
  clientes, registrados por `locacoes` e `financeiro`). `filtro(alvo, nome)` devolve `None` quando
  o fornecedor ainda não existe, e quem consulta decide o que mostrar (contagem `null`).
- Contador: `registrar_contador(alvo="filiais.Filial", nome="veiculos", contar=lambda id: ...)`.
  `contar(alvo, id, nomes)` devolve todos os pedidos; contador não registrado vale 0
  (ex.: operação que impede desativar a filial, FIL-06).
- Total: `registrar_total(alvo, nome, somar)`, uma soma sobre uma lista do app de cima (ex.:
  `em_aberto_centavos` dos clientes, de `financeiro`). `total(alvo, nome, qs)` devolve `None`
  quando o fornecedor ainda não existe.

Módulos do plano (PLT-12, ADR 0024, item 5): anotação, contador e total aceitam `recurso=`. Com o
recurso desligado na empresa, o bloco não vem (`None`), o contador vale 0 e o total `None`, sem
rodar a query.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from django.db.models import QuerySet

from comum.empresa import tem_recurso


@dataclass(frozen=True)
class Anotacao:
    bloco: str
    anotar: Callable[[QuerySet[Any]], QuerySet[Any]]
    montar: Callable[[Any], dict[str, Any] | None]
    recurso: str | None = None

    def ligada(self) -> bool:
        return self.recurso is None or tem_recurso(self.recurso)


_anotacoes: dict[str, list[Anotacao]] = defaultdict(list)
_contadores: dict[str, dict[str, Callable[[int], int]]] = defaultdict(dict)
# Filtro: `filtrar(queryset, *argumentos)`; o `filial` da lista de clientes recebe o id (CLI-10).
_filtros: dict[str, dict[str, Callable[..., QuerySet[Any]]]] = defaultdict(dict)


def registrar_anotacao(
    alvo: str,
    bloco: str,
    anotar: Callable[[QuerySet[Any]], QuerySet[Any]],
    montar: Callable[[Any], dict[str, Any] | None],
    *,
    recurso: str | None = None,
) -> None:
    anotacao = Anotacao(bloco, anotar, montar, recurso)
    if anotacao not in _anotacoes[alvo]:
        _anotacoes[alvo].append(anotacao)


def aplicar(alvo: str, queryset: QuerySet[Any]) -> QuerySet[Any]:
    for anotacao in _anotacoes.get(alvo, ()):
        if anotacao.ligada():
            queryset = anotacao.anotar(queryset)
    return queryset


def blocos(alvo: str, objeto: Any) -> dict[str, dict[str, Any]]:
    """`{bloco: {...}}` com os campos de todos os fornecedores do bloco."""
    resultado: dict[str, dict[str, Any]] = {}
    for anotacao in _anotacoes.get(alvo, ()):
        if not anotacao.ligada():
            continue
        parte = anotacao.montar(objeto)
        if parte is not None:
            resultado.setdefault(anotacao.bloco, {}).update(parte)
    return resultado


def bloco(alvo: str, nome: str, objeto: Any) -> dict[str, Any] | None:
    """Só o bloco `nome`; `None` quando ele não tem fornecedor. O objeto pode ser `None` (ex.: a
    análise antes do cadastro), e o fornecedor do bloco decide o que devolver."""
    fornecedores = [a for a in _anotacoes.get(alvo, ()) if a.bloco == nome and a.ligada()]
    if not fornecedores:
        return None
    resultado: dict[str, Any] = {}
    for anotacao in fornecedores:
        resultado.update(anotacao.montar(objeto) or {})
    return resultado


_recurso_do: dict[tuple[str, str, str], str] = {}


def _desligado(tipo: str, alvo: str, nome: str) -> bool:
    recurso = _recurso_do.get((tipo, alvo, nome))
    return recurso is not None and not tem_recurso(recurso)


def registrar_contador(
    alvo: str, nome: str, contar: Callable[[int], int], *, recurso: str | None = None
) -> None:
    _contadores[alvo][nome] = contar
    if recurso is not None:
        _recurso_do[("contador", alvo, nome)] = recurso


def remover_contador(alvo: str, nome: str) -> None:
    """Para testes."""
    _contadores.get(alvo, {}).pop(nome, None)


def contar(alvo: str, objeto_id: int, nomes: Iterable[str]) -> dict[str, int]:
    registrados = _contadores.get(alvo, {})
    return {
        nome: int(registrados[nome](objeto_id))
        if nome in registrados and not _desligado("contador", alvo, nome)
        else 0
        for nome in nomes
    }


def registrar_filtro(alvo: str, nome: str, filtrar: Callable[..., QuerySet[Any]]) -> None:
    _filtros[alvo][nome] = filtrar


def remover_filtro(alvo: str, nome: str) -> None:
    """Para testes."""
    _filtros.get(alvo, {}).pop(nome, None)


def filtro(alvo: str, nome: str) -> Callable[..., QuerySet[Any]] | None:
    return _filtros.get(alvo, {}).get(nome)


_totais: dict[str, dict[str, Callable[[QuerySet[Any]], int]]] = defaultdict(dict)


def registrar_total(
    alvo: str, nome: str, somar: Callable[[QuerySet[Any]], int], *, recurso: str | None = None
) -> None:
    _totais[alvo][nome] = somar
    if recurso is not None:
        _recurso_do[("total", alvo, nome)] = recurso


def total(alvo: str, nome: str, queryset: QuerySet[Any]) -> int | None:
    somar = _totais.get(alvo, {}).get(nome)
    if somar is not None and _desligado("total", alvo, nome):
        return None
    return int(somar(queryset)) if somar is not None else None
