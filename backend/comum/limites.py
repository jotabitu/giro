"""Limite de requisições nas rotas públicas de acesso (P-03 da T-057; S-17 no proxy), no link
de assinatura de contrato (S-15) e na busca de CEP (F-05 da T-064).

Contam no cache (Redis, com a chave por schema de `make_key`). Por IP do cliente
(`comum.rede`, que só confia no `X-Forwarded-For` do proxy; IPv6 pelo /64; sem IP, não conta)
e, em `entrar`, também pelo e-mail informado (em hash), exista ele ou não. CEP, por usuário.
Estourar responde 429 `muitas_requisicoes` (`comum.erros`). As taxas ficam em
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
"""

import hashlib
import ipaddress
import logging
from typing import Any

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

from .rede import ip_do_cliente

logger = logging.getLogger(__name__)
PREFIXO_IPV6 = 64  # quem tem um /64 troca de endereço à vontade (F-04 da T-064)


def chave_do_ip(ip: str | None) -> str | None:
    """IPv4 inteiro; IPv6 pelo prefixo /64. Sem IP, `None`: o limite por IP não se aplica."""
    if not ip:
        return None
    endereco = ipaddress.ip_address(ip)
    if endereco.version == 6:
        return str(ipaddress.ip_network((endereco, PREFIXO_IPV6), strict=False))
    return str(endereco)


class _PorIP(SimpleRateThrottle):
    def get_cache_key(self, request: Request, view: Any) -> str | None:
        ident = chave_do_ip(ip_do_cliente(request))
        if ident is None:
            # Nunca juntar todo mundo numa chave vazia: o proxy está mal configurado (ADR 0018).
            logger.warning(
                "Requisição sem IP do cliente: limite por IP não aplicado (%s)", self.scope
            )
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class _PorUsuario(SimpleRateThrottle):
    def get_cache_key(self, request: Request, view: Any) -> str | None:
        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated:
            return None
        # O suporte não tem usuário na empresa: conta pelo acesso (PLT-07).
        ident = usuario.pk if usuario.pk is not None else f"suporte-{usuario.acesso_suporte_id}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


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


class _PorToken(SimpleRateThrottle):
    """Pelo token do corpo, em hash: o mesmo link não é testado à vontade de IPs diferentes."""

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        token = request.data.get("token") if hasattr(request.data, "get") else None
        if not isinstance(token, str) or not token:
            return None
        ident = hashlib.sha256(token.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AcessoPorIP(_PorIP):
    """Convite (ver e aceitar), renovar e a etapa de 2 etapas."""

    scope = "acesso_ip"


class MarcaPorIP(_PorIP):
    """Marca e logo da empresa, públicas e lidas em toda abertura do login (`empresas.md`)."""

    scope = "marca_ip"


class CepPorUsuario(_PorUsuario):
    """Busca de CEP: cada CEP novo é uma chamada ao ViaCEP (F-05 da T-064)."""

    scope = "cep_usuario"


class AssinaturaPorIP(_PorIP):
    """Link de assinatura de contrato: 10 por minuto por IP (S-15)."""

    scope = "assinatura_ip"


class AssinaturaPorToken(_PorToken):
    """Link de assinatura de contrato: 20 por minuto por token (S-15)."""

    scope = "assinatura_token"


LIMITES_DE_ASSINATURA = [AssinaturaPorIP, AssinaturaPorToken]
LIMITES_DE_ENTRAR = [EntrarPorIPMinuto, EntrarPorIPHora, EntrarPorEmailMinuto, EntrarPorEmailHora]
