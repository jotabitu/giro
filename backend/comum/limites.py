"""Limite de requisições nas rotas públicas de acesso (P-03 da T-057; S-17 no proxy).

Contam no cache (Redis, com a chave por schema de `make_key`). Por IP do cliente
(`comum.rede`, que só confia no `X-Forwarded-For` do proxy) e, em `entrar`, também pelo
e-mail informado (em hash), exista ele ou não. Estourar responde 429 `muitas_requisicoes`
(`comum.erros`). As taxas ficam em `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
"""

import hashlib
from typing import Any

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

from .rede import ip_do_cliente


class _PorIP(SimpleRateThrottle):
    def get_cache_key(self, request: Request, view: Any) -> str | None:
        return self.cache_format % {"scope": self.scope, "ident": ip_do_cliente(request) or ""}


class _PorEmail(SimpleRateThrottle):
    def get_cache_key(self, request: Request, view: Any) -> str | None:
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        # Hash para o e-mail não ficar em claro nas chaves do Redis.
        ident = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class EntrarPorIPMinuto(_PorIP):
    scope = "entrar_ip_minuto"


class EntrarPorIPHora(_PorIP):
    scope = "entrar_ip_hora"


class EntrarPorEmailMinuto(_PorEmail):
    scope = "entrar_email_minuto"


class EntrarPorEmailHora(_PorEmail):
    scope = "entrar_email_hora"


class AcessoPorIP(_PorIP):
    """Convite (ver e aceitar), renovar e a etapa de 2 etapas."""

    scope = "acesso_ip"


LIMITES_DE_ENTRAR = [EntrarPorIPMinuto, EntrarPorIPHora, EntrarPorEmailMinuto, EntrarPorEmailHora]
