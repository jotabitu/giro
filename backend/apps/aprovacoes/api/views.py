"""Views finas das aprovações (docs/api/aprovacoes.md).

Todos os perfis leem a lista: quem decide vê os pedidos que decide (tabela "Quem decide", nas
suas filiais, sem os que fez, salvo o administrador, APR-09) e todos veem os próprios com
`?minhas=true`. Decidir fora do escopo responde 404; decidir o próprio pedido, 403 `APR-09` para
quem não é administrador (no serviço).
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.selectors import filtrar_por_filial
from comum.paginacao import PaginacaoPorCursor

from .. import selectors, services
from ..models import PedidoAprovacao, TipoPedido
from .serializers import (
    AprovarSerializer,
    ListaDePedidosSerializer,
    PedidoSerializer,
    RecusarSerializer,
)


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _representacao(pedido: PedidoAprovacao, quem: selectors.Decisor) -> Response:
    pedido = PedidoAprovacao.objects.select_related("filial", "solicitante", "aprovador").get(
        pk=pedido.pk
    )
    return Response(PedidoSerializer(selectors.representacao(pedido, quem)).data)


class AprovacoesView(APIView):
    @extend_schema(
        responses=ListaDePedidosSerializer,
        operation_id="aprovacoes_list",
        parameters=[
            OpenApiParameter("status", enum=list(PedidoAprovacao.Status.values)),
            OpenApiParameter("tipo", enum=list(TipoPedido.values)),
            OpenApiParameter("minhas", enum=["true", "false"]),
        ],
        summary="Pedidos de aprovação (APR-01 a APR-09)",
    )
    def get(self, request: Request) -> Response:
        parametros = request.query_params
        quem = selectors.decisor(request.user)
        minhas = parametros.get("minhas") == "true"
        decide = filtrar_por_filial(selectors.que_decide(quem), request)
        meus = filtrar_por_filial(
            PedidoAprovacao.objects.filter(solicitante_id=quem.usuario_id), request
        )
        qs = selectors.filtrar(
            meus if minhas else decide,
            status=parametros.get("status"),
            tipo=parametros.get("tipo"),
            minhas=minhas,
        )
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("ordem_da_aba", "id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(
            qs.select_related("filial", "solicitante", "aprovador"), request, view=self
        )
        dados = [selectors.representacao(p, quem) for p in pagina or []]
        indicadores, contagens = selectors.indicadores_e_contagens(decide, meus)
        return paginacao.get_paginated_response(
            PedidoSerializer(dados, many=True).data,
            extras={"indicadores": indicadores, "contagens": contagens},
        )


def _pedido(request: Request, pk: int) -> tuple[PedidoAprovacao, selectors.Decisor]:
    quem = selectors.decisor(request.user)
    return get_object_or_404(selectors.visiveis(quem), pk=pk), quem


class AprovarView(APIView):
    @extend_schema(
        request=AprovarSerializer, responses=PedidoSerializer, summary="Aprovar (APR-09, APR-10)"
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(AprovarSerializer, request)
        pedido, quem = _pedido(request, pk)
        services.aprovar(pedido, request.user, dados.get("motivo", ""))
        return _representacao(pedido, quem)


class RecusarView(APIView):
    @extend_schema(
        request=RecusarSerializer,
        responses=PedidoSerializer,
        summary="Recusar com motivo (APR-07, APR-09, APR-10)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(RecusarSerializer, request)
        pedido, quem = _pedido(request, pk)
        services.recusar(pedido, request.user, dados["motivo"])
        return _representacao(pedido, quem)


class CancelarView(APIView):
    @extend_schema(request=None, responses=PedidoSerializer, summary="Quem pediu desiste")
    def post(self, request: Request, pk: int) -> Response:
        pedido, quem = _pedido(request, pk)
        services.cancelar(pedido, request.user)
        return _representacao(pedido, quem)
