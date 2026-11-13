"""Textos prontos da auditoria para as ações de `vendas` (`VEN-11`, T-420; A5 da conferência
de 13 nov 2026). Registrados no `ready()` por `comum.auditoria.registrar_formatador`.
"""

from datetime import date
from typing import Any

from comum.auditoria import Texto

from .models import Venda


def _codigo(evento: Any) -> str:
    return f" {evento.objeto_codigo}" if evento.objeto_codigo else ""


def criar_da_quitacao(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Criou a venda VEN-0003 da quitação", "Quitação da LOC-2877" (a descrição da venda)."""
    depois = evento.depois or {}
    descricao = depois.get("descricao") if isinstance(depois.get("descricao"), str) else ""
    if not descricao and evento.objeto_id is not None:
        achada = Venda.objects.filter(pk=evento.objeto_id).values_list("descricao", flat=True)
        descricao = achada.first() or ""
    return Texto(f"Criou a venda{_codigo(evento)} da quitação", str(descricao or evento.motivo))


def registrar_transferencia(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Registrou a transferência no Detran da VEN-0003", "Feita em 13/11/2026"."""
    feita = (evento.depois or {}).get("transferencia_feita_em")
    detalhe = ""
    if isinstance(feita, str):
        try:
            detalhe = f"Feita em {date.fromisoformat(feita[:10]):%d/%m/%Y}"
        except ValueError:
            detalhe = ""
    return Texto(f"Registrou a transferência no Detran da{_codigo(evento) or ' venda'}", detalhe)
