"""Data de referência no desenvolvimento (ADR 0021): a rota de ambiente, o cabeçalho
`X-Giro-Data-Simulada`, o aviso `giro.W001` do `check` e o `WARNING` ao subir."""

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from django.core.checks import CheckMessage
from django.core.checks import Warning as AvisoDoCheck
from django.http import HttpRequest, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum import relogio
from comum.limites import AmbientePorIP
from comum.permissoes import EmpresaOperando, EscopoDeFilial

logger = logging.getLogger("giro.relogio")
CABECALHO = "X-Giro-Data-Simulada"


def mensagem(data: date) -> str:
    return f"Data de referência ligada: {data.isoformat()}"


def avisar_ao_subir() -> None:
    """Chamado no `ready()`: backend, worker e beat registram o aviso ao subir."""
    data = relogio.data_de_referencia()
    if data is not None:
        logger.warning("%s. Ambiente de desenvolvimento.", mensagem(data))


def conferir_data_de_referencia(app_configs: Any = None, **_: Any) -> list[CheckMessage]:
    """`manage.py check`: aviso `giro.W001` com a data ligada."""
    data = relogio.data_de_referencia()
    if data is None:
        return []
    return [AvisoDoCheck(mensagem(data), id="giro.W001")]


class DataSimuladaMiddleware:
    """Com a data ligada, toda resposta leva `X-Giro-Data-Simulada: AAAA-MM-DD`."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        resposta = self.get_response(request)
        data = relogio.data_de_referencia()
        if data is not None:
            resposta[CABECALHO] = data.isoformat()
        return resposta


class AmbienteSerializer(serializers.Serializer[Any]):
    hoje = serializers.DateField(help_text="O dia do relógio do domínio em America/Sao_Paulo.")
    data_simulada = serializers.BooleanField(
        help_text="`true` só no desenvolvimento com GIRO_DATA_REFERENCIA ligada."
    )


class AmbienteView(APIView):
    """Pública, sem login: com ou sem token (inclusive o do suporte), a resposta é a mesma."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny, EmpresaOperando, EscopoDeFilial]
    throttle_classes = [AmbientePorIP]

    @extend_schema(
        auth=[], responses=AmbienteSerializer, summary="Hoje e se a data é simulada (ADR 0021)"
    )
    def get(self, request: Request) -> Response:
        dados = {
            "hoje": relogio.hoje(),
            "data_simulada": relogio.data_de_referencia() is not None,
        }
        return Response(AmbienteSerializer(dados).data, headers={"Cache-Control": "no-store"})
