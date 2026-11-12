"""Views finas das vendas (`docs/api/vendas.md`). Na T-420: a lista e o detalhe (recurso
`vendas_comissoes`) e "Transferência feita", sob a locação (recurso `locacoes_vistoria`, ADR 0037,
item 6)."""

from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.filiais.selectors import filtrar_por_filial
from apps.locacoes import selectors as locacoes_selectors
from apps.locacoes.api.serializers import LocacaoDetalheSerializer
from apps.locacoes.models import Locacao
from apps.plataforma.models import Recurso
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..models import OrigemVenda
from .serializers import ListaDeVendasSerializer, TransferenciaEntradaSerializer, VendaSerializer

# O vistoriador não vê vendas (`vendas.md`, "Quem pode").
LEEM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro")
)
REGISTRAM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))


class ViewDeVendas(APIView):
    # PLT-12: as rotas /api/vendas/ só abrem com o recurso de vendas (ADR 0024, item 4).
    recurso_do_plano = Recurso.VENDAS_COMISSOES
    permission_classes = LEEM


class VendasView(ViewDeVendas):
    @extend_schema(
        responses=ListaDeVendasSerializer,
        operation_id="vendas_list",
        parameters=[
            OpenApiParameter("origem", enum=[o.value for o in OrigemVenda]),
            OpenApiParameter("transferencia_pendente", enum=["true"]),
            OpenApiParameter("veiculo", int),
            OpenApiParameter("cliente", int),
        ],
        summary="Vendas (na T-420, só as da quitação, VEN-11)",
    )
    def get(self, request: Request) -> Response:
        qs = selectors.filtrar(request.user, request.query_params)
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("-id",)  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        dados = VendaSerializer(
            [selectors.representacao(v, request.user) for v in pagina], many=True
        )
        return paginacao.get_paginated_response(dados.data)


class VendaView(ViewDeVendas):
    @extend_schema(responses=VendaSerializer, summary="Detalhe da venda")
    def get(self, request: Request, pk: int) -> Response:
        venda = selectors.visiveis(request.user).filter(pk=pk).first()
        if venda is None:
            raise Http404
        return Response(VendaSerializer(selectors.representacao(venda, request.user)).data)


def _locacao(request: Request, pk: int) -> Locacao:
    locacao = filtrar_por_filial(locacoes_selectors.base(), request).filter(pk=pk).first()
    if locacao is None:
        raise Http404
    return locacao  # type: ignore[no-any-return]


class TransferenciaView(APIView):
    # `vendas.md`: sob a locação, para abrir em qualquer plano que aluga (ADR 0037, item 6).

    recurso_do_plano = Recurso.LOCACOES_VISTORIA
    permission_classes = REGISTRAM

    @extend_schema(
        request=TransferenciaEntradaSerializer,
        responses=LocacaoDetalheSerializer,
        summary="Transferência feita no Detran (LOC-16, VEN-11): fecha a tarefa da quitação",
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = TransferenciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        locacao = _locacao(request, pk)
        venda = selectors.venda_da_quitacao(locacao.pk)
        if venda is None:
            raise Http404
        services.registrar_transferencia(venda, entrada.validated_data["feita_em"], request.user)
        dados: dict[str, Any] = locacoes_selectors.detalhe(locacao, request.user)
        return Response(LocacaoDetalheSerializer(dados).data)
