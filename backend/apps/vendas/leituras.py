"""O que `vendas` fornece aos apps de baixo (ADR 0015, ADR 0037), no `ready()`.

- `locacoes.Locacao`: bloco `compra_venda` (o `compra.venda` do detalhe da locação quitada, sem
  as `acoes`, que `locacoes` monta).
- `veiculos.Veiculo:ficha`: bloco `vendas` (`{ "itens": [...] }`), as vendas do veículo com a
  transferência no Detran (CA-420-16).
"""

from typing import Any

from django.db.models import QuerySet

from comum import leituras

from . import selectors

LOCACAO = "locacoes.Locacao"
FICHA = "veiculos.Veiculo:ficha"


def _sem_anotar(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset


def montar_compra_venda(locacao: Any) -> dict[str, Any] | None:
    return selectors.venda_da_locacao(locacao.pk)


def montar_vendas(veiculo: Any) -> dict[str, Any] | None:
    itens = selectors.vendas_do_veiculo(veiculo.pk)
    return {"itens": itens} if itens else None


def registrar() -> None:
    leituras.registrar_anotacao(LOCACAO, "compra_venda", _sem_anotar, montar_compra_venda)
    leituras.registrar_anotacao(FICHA, "vendas", _sem_anotar, montar_vendas)
