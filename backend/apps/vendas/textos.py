"""Textos prontos da auditoria para as ações de `vendas` (`VEN-11`, T-420; A5 da conferência
de 13 nov 2026). Registrados no `ready()` por `comum.auditoria.registrar_formatador`.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
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


# --- Fluxo da venda de balcão (VEN-13, T-502) ---

ROTULOS = {
    "interessado": "Interessado",
    "proposta": "Proposta enviada",
    "negociacao": "Em negociação",
    "aguardando_aprovacao": "Aguardando gerente",
}


def _da(evento: Any) -> str:
    return f"da{_codigo(evento) or ' venda'}"


def _pct(evento: Any) -> str:
    pct = (evento.depois or {}).get("desconto_pct")
    if pct in (None, ""):
        return ""
    try:
        return f"{Decimal(str(pct)):.2f}%".replace(".", ",")
    except (InvalidOperation, ValueError):
        return ""


def criar(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Criou a venda VEN-0177", "Aguardando gerente"."""
    status = (evento.depois or {}).get("status")
    return Texto(f"Criou a venda{_codigo(evento)}", ROTULOS.get(str(status), ""))


def editar(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Editou a proposta {_da(evento)}", evento.motivo)


def enviar_proposta(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Enviou a proposta {_da(evento)}", evento.motivo)


def reenviar_proposta(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Reenviou a proposta {_da(evento)}", evento.motivo)


def registrar_resposta(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Registrou a resposta do cliente {_da(evento)}", evento.motivo)


def pedir_desconto(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Pediu desconto de 8,00% na VEN-0177", com o motivo do pedido."""
    pct = _pct(evento)
    de = f" de {pct}" if pct else ""
    return Texto(f"Pediu desconto{de} na{_codigo(evento) or ' venda'}", evento.motivo)


def aprovar_desconto(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Desconto {_da(evento)} aprovado", evento.motivo)


def recusar_desconto(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Desconto {_da(evento)} recusado", evento.motivo)


def cancelar_desconto(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Pedido de desconto {_da(evento)} cancelado", evento.motivo)


def perder(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Marcou como perdida a venda{_codigo(evento)}", evento.motivo)


def vencer_proposta(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Proposta {_da(evento)} vencida", "7 dias sem resposta do cliente")


def perdida_pela_outra(evento: Any, _: dict[str, Any]) -> Texto:
    """`VEN-10`: o interessado perdido porque o veículo foi vendido em outra venda."""
    return Texto(f"Venda{_codigo(evento)} perdida", evento.motivo)


# --- Fase 1b: assinatura e conclusão (VEN-15, VEN-06, T-502) ---


def preparar_assinatura(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(
        f"Preparou a assinatura {_da(evento)}", "Contrato gerado e entrada em Contas a receber"
    )


def cancelar_assinatura(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(
        f"Cancelou a assinatura {_da(evento)}", "Contrato e cobrança da entrada cancelados"
    )


def registrar_assinatura(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Cliente assinou o contrato {_da(evento)}", evento.motivo)


def registrar_entrada(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Entrada {_da(evento)} paga", evento.motivo)


def concluir(evento: Any, _: dict[str, Any]) -> Texto:
    return Texto(f"Venda{_codigo(evento)} concluída", "Contrato assinado e entrada paga")


DO_FLUXO: dict[str, Callable[[Any, dict[str, Any]], Texto]] = {
    "venda.criar": criar,
    "venda.editar": editar,
    "venda.enviar_proposta": enviar_proposta,
    "venda.reenviar_proposta": reenviar_proposta,
    "venda.registrar_resposta": registrar_resposta,
    "venda.pedir_desconto": pedir_desconto,
    "venda.aprovar_desconto": aprovar_desconto,
    "venda.recusar_desconto": recusar_desconto,
    "venda.cancelar_desconto": cancelar_desconto,
    "venda.perder": perder,
    "venda.vencer_proposta": vencer_proposta,
    "venda.perdida": perdida_pela_outra,
    "venda.preparar_assinatura": preparar_assinatura,
    "venda.cancelar_assinatura": cancelar_assinatura,
    "venda.registrar_assinatura": registrar_assinatura,
    "venda.registrar_entrada": registrar_entrada,
    "venda.concluir": concluir,
}
