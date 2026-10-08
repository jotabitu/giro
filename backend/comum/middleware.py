"""Preenche o ator da auditoria a partir da requisição (ADR 0010, item 5).

O usuário é lido na hora em que o evento é gravado, porque a autenticação JWT do DRF só roda
dentro da view (e o DRF repassa `user` e `auth` para o `HttpRequest`).
"""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from comum.auditoria import ATOR_SISTEMA, Ator, TipoAtor, usar_ator
from comum.rede import ip_do_cliente

TAMANHO_APARELHO = 200


def ator_da_requisicao(request: HttpRequest) -> Ator:
    ip = ip_do_cliente(request)
    aparelho = request.META.get("HTTP_USER_AGENT", "")[:TAMANHO_APARELHO]
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return Ator(tipo=ATOR_SISTEMA.tipo, nome=ATOR_SISTEMA.nome, ip=ip, aparelho=aparelho)
    if getattr(usuario, "e_suporte", False):
        # Suporte da plataforma (PLT-07, AUD-03): sem usuário da empresa, com o acesso.
        return Ator(
            tipo=TipoAtor.SUPORTE,
            nome=usuario.nome,
            ip=ip,
            aparelho=aparelho,
            acesso_suporte_id=usuario.acesso_suporte_id,
        )
    return Ator(
        tipo=TipoAtor.USUARIO,
        id=usuario.pk,
        nome=getattr(usuario, "nome", "") or str(usuario),
        ip=ip,
        aparelho=aparelho,
    )


class AtorDaRequisicaoMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        with usar_ator(lambda: ator_da_requisicao(request)):
            return self.get_response(request)
