"""Assinantes de eventos de outros apps (ADR 0011). Registrados ao importar, no `ready()`."""

from typing import Any

from comum.eventos import assinante

from . import services


@assinante("locacoes.locacao_cancelada")
def descartar_saida_da_cancelada(
    *, locacao_id: int, antes_da_retirada: bool, motivo: str, **_: Any
) -> None:
    """ADR 0035, item 5: a locação cancelada antes da retirada, pedida ou pela `AUT-17`, não
    deixa a vistoria de saída em rascunho aberta (LOC-12). A concluída fica no histórico."""
    if antes_da_retirada:
        services.descartar_saidas_em_rascunho(locacao_id, motivo)
