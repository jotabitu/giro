"""Origem dos links que o sistema manda ou copia (recibo, convite, assinar, senha, suporte).

Um lugar só para o esquema e a porta (T-467): `GIRO_LINKS_ESQUEMA` (padrão `https`) e
`GIRO_LINKS_PORTA` (padrão vazio, sem porta). Homologação e produção ficam no padrão; o
desenvolvimento no compose usa `http` e a porta do Next (`config.settings.dev`), para o link
abrir como está. O webhook de pagamentos não passa por aqui: o parceiro chama sempre por HTTPS.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ESQUEMAS = ("http", "https")


def origem(host: str) -> str:
    """ "https://motorapida.giro.ceo" ou, no desenvolvimento,
    "http://motorapida.localhost:3000"."""
    esquema = str(getattr(settings, "GIRO_LINKS_ESQUEMA", "https") or "https").strip().lower()
    porta = str(getattr(settings, "GIRO_LINKS_PORTA", "") or "").strip()
    if esquema not in ESQUEMAS:
        raise ImproperlyConfigured(f"GIRO_LINKS_ESQUEMA deve ser http ou https: {esquema!r}.")
    if porta and not porta.isdigit():
        raise ImproperlyConfigured(f"GIRO_LINKS_PORTA deve ser um número: {porta!r}.")
    return f"{esquema}://{host}{f':{porta}' if porta else ''}"


def link(host: str, caminho: str) -> str:
    """A origem mais o caminho, que começa com "/" ("/recibo#<token>")."""
    return f"{origem(host)}{caminho}"
