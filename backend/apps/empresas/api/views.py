"""Marca da locadora, pública (`docs/api/empresas.md`; ADR 0002 e 0004; S-12).

Sem login: o login, o convite, o primeiro acesso e o "esqueci a senha" leem a marca antes de
haver sessão, e a casca do app lê a mesma rota depois. A empresa é a do subdomínio. O logo sai
pela própria API (o storage continua privado), com os cabeçalhos que impedem um SVG de rodar
script mesmo aberto direto na barra de endereço (2ª barreira da S-12; a 1ª é a sanitização no
upload, da tarefa da edição da marca).
"""

from typing import Any

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.erros import NaoEncontrado
from comum.limites import MarcaPorIP
from comum.permissoes import EmpresaOperando, EscopoDeFilial

from .. import selectors
from .serializers import MarcaSerializer

CACHE_DA_MARCA = "public, max-age=300"
CACHE_DO_LOGO_ATUAL = "public, max-age=31536000, immutable"
CACHE_DO_LOGO_ANTIGO = "public, max-age=300"
CSP_DO_LOGO = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


class Publica(APIView):
    """Sem autenticação: com ou sem token (inclusive o do suporte), a resposta é a mesma."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny, EmpresaOperando, EscopoDeFilial]
    throttle_classes = [MarcaPorIP]


def _etag(versao: str) -> str:
    return f'"{versao}"'


def _pede_a_mesma(request: Request, versao: str) -> bool:
    pedidas = str(request.META.get("HTTP_IF_NONE_MATCH", ""))
    return any(
        parte.strip().removeprefix("W/") in (_etag(versao), "*") for parte in pedidas.split(",")
    )


class MarcaView(Publica):
    @extend_schema(
        responses={200: MarcaSerializer, 304: OpenApiResponse(description="Sem mudança")},
        summary="Marca da empresa do subdomínio (nome, logo e cores)",
    )
    def get(self, request: Request) -> Response:
        dados = selectors.marca()
        cabecalhos = {"ETag": _etag(dados["versao"]), "Cache-Control": CACHE_DA_MARCA}
        if _pede_a_mesma(request, dados["versao"]):
            return Response(status=304, headers=cabecalhos)
        return Response(MarcaSerializer(dados).data, headers=cabecalhos)


class LogoView(Publica):
    @extend_schema(
        parameters=[OpenApiParameter("v", str, description="Versão da marca (`versao`).")],
        responses={
            (200, "image/svg+xml"): OpenApiTypes.BINARY,
            (200, "image/png"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="Sem logo (`nao_encontrado`)"),
        },
        summary="Arquivo do logo da empresa (S-12)",
    )
    def get(self, request: Request) -> HttpResponse:
        arquivo = selectors.logo()
        if arquivo is None:
            raise NaoEncontrado("nao_encontrado", "Esta empresa não tem logo.")
        conteudo, tipo, extensao = arquivo
        atual = request.query_params.get("v") == selectors.marca()["versao"]
        resposta = HttpResponse(conteudo, content_type=tipo)
        resposta["Cache-Control"] = CACHE_DO_LOGO_ATUAL if atual else CACHE_DO_LOGO_ANTIGO
        resposta["X-Content-Type-Options"] = "nosniff"
        resposta["Content-Security-Policy"] = CSP_DO_LOGO
        resposta["Content-Disposition"] = f'inline; filename="logo.{extensao}"'
        return resposta
