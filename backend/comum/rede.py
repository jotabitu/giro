"""IP do cliente atrás do proxy (ADR 0018, item 4; achado C-03 da T-039).

Uma função só para a auditoria (AUD-01), os bloqueios de login e os limites por IP.
`X-Forwarded-For` só vale quando a conexão vem de um proxy confiável (`REMOTE_ADDR` numa rede
de `GIRO_REDES_PROXY`). Aí o cliente é `xff[-N]`, com N = `GIRO_PROXIES_CONFIAVEIS`: o proxy
acrescenta à direita o IP de quem falou com ele, e o começo da lista o cliente pode forjar.
Qualquer coisa fora disso (sem cabeçalho, cabeçalho curto, valor que não é IP) vale o
`REMOTE_ADDR`.
"""

import ipaddress
from functools import cache

from django.conf import settings
from django.http import HttpRequest

type Rede = ipaddress.IPv4Network | ipaddress.IPv6Network


@cache
def _redes(configuradas: tuple[str, ...]) -> tuple[Rede, ...]:
    return tuple(ipaddress.ip_network(rede.strip(), strict=False) for rede in configuradas)


def _ip_valido(valor: str) -> str | None:
    try:
        return str(ipaddress.ip_address(valor.strip()))
    except ValueError:
        return None


def _de_proxy_confiavel(ip: str | None) -> bool:
    if ip is None:
        return False
    endereco = ipaddress.ip_address(ip)
    redes = _redes(tuple(settings.GIRO_REDES_PROXY))
    return any(endereco.version == rede.version and endereco in rede for rede in redes)


def ip_do_cliente(request: HttpRequest) -> str | None:
    remoto = _ip_valido(request.META.get("REMOTE_ADDR", ""))
    if not _de_proxy_confiavel(remoto):
        return remoto
    cabecalho = request.META.get("HTTP_X_FORWARDED_FOR", "")
    entradas = [parte.strip() for parte in cabecalho.split(",") if parte.strip()]
    saltos = int(settings.GIRO_PROXIES_CONFIAVEIS)
    if saltos < 1 or len(entradas) < saltos:
        return remoto
    return _ip_valido(entradas[-saltos]) or remoto
