"""Envio de WhatsApp atrás de uma interface (USR-01: convite também por WhatsApp).

`enviar_whatsapp(celular, texto)` escolhe o provedor por `GIRO_PROVEDOR_WHATSAPP`. Por enquanto só
existe o `falso`, que guarda as mensagens em `caixa_de_saida` (como o `mail.outbox`); o provedor
real entra com a integração de WhatsApp.
"""

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings


@dataclass(frozen=True)
class MensagemWhatsApp:
    celular: str
    texto: str


class ProvedorDeWhatsApp(Protocol):
    def enviar(self, mensagem: MensagemWhatsApp) -> None: ...


def provedor() -> ProvedorDeWhatsApp:
    nome = getattr(settings, "GIRO_PROVEDOR_WHATSAPP", "falso")
    if nome != "falso":
        raise ValueError(f"Provedor de WhatsApp desconhecido: {nome}")
    from .falso import WhatsAppFalso

    return WhatsAppFalso()


def whatsapp_ao_cliente_final() -> bool:
    """`GIRO_WHATSAPP_CLIENTE_FINAL` (ADR 0034, decisão de 11 nov 2026). Desligada, nenhum aviso
    ao cliente final nem à pessoa convidada sai pelo WhatsApp (pontos 1 a 7: convite, contrato,
    contrato assinado, régua de cobrança, recibo do pagamento, recibo da devolução, lembrete da
    devolução); todos vão por e-mail. A régua da assinatura (ponto 8, `AUT-13`) não olha a chave.
    O código do envio ao cliente fica guardado para quando o dono religar."""
    return bool(getattr(settings, "GIRO_WHATSAPP_CLIENTE_FINAL", False))


def enviar_whatsapp(celular: str, texto: str) -> None:
    """`celular` só com dígitos e DDD (10 ou 11)."""
    provedor().enviar(MensagemWhatsApp(celular=celular, texto=texto))
