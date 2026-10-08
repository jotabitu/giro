"""WhatsApp falso para desenvolvimento e testes: guarda as mensagens na memória."""

from . import MensagemWhatsApp

caixa_de_saida: list[MensagemWhatsApp] = []


class WhatsAppFalso:
    def enviar(self, mensagem: MensagemWhatsApp) -> None:
        caixa_de_saida.append(mensagem)
