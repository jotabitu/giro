"""Views finas da plataforma (fase 1 de docs/api/plataforma.md).

Método de fase 2 numa rota de fase 1 (ex.: `POST /api/plataforma/planos/`) responde 404,
como rota que ainda não existe, e não 405.
"""

from typing import Any, NoReturn

from django.db.models import Count, DateTimeField, Q, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas

from .. import selectors
from ..models import Plano
from ..permissoes import exige_permissao
from .serializers import (
    AssinaturaSerializer,
    EmpresaDetalheSerializer,
    EmpresaListaSerializer,
    ListaDeEmpresasSerializer,
    ListaDePlanosSerializer,
    PlanoSerializer,
    representar_assinatura,
)

ORDENS = {
    "nome": ("nome_exibicao", "id"),
    "-criado_em": ("-criado_em", "-id"),
    "-ultimo_acesso_em": ("-ultimo_acesso_ordem", "-id"),
}
NUNCA = Value("1970-01-01T00:00:00Z", output_field=DateTimeField())


class SoFase1(APIView):
    def http_method_not_allowed(self, request: Any, *args: Any, **kwargs: Any) -> NoReturn:
        raise NotFound("Não encontrado.")


class PlanosView(SoFase1):
    permission_classes = [IsAuthenticated, exige_permissao("ver_empresas")]

    @extend_schema(
        responses=ListaDePlanosSerializer,
        operation_id="plataforma_planos_list",
        summary="Planos (PLT-03)",
    )
    def get(self, request: Request) -> Response:
        planos = Plano.objects.annotate(
            empresas_no_plano=Count("empresas", filter=~Q(empresas__status="cancelada"))
        ).order_by("ordem", "id")
        return envelope_sem_paginas(PlanoSerializer(planos, many=True).data)


class EmpresasView(SoFase1):
    permission_classes = [IsAuthenticated, exige_permissao("ver_empresas")]

    @extend_schema(
        responses=ListaDeEmpresasSerializer,
        operation_id="plataforma_empresas_list",
        summary="Empresas da plataforma (IMP-05)",
        parameters=[
            OpenApiParameter("situacao", enum=list(selectors.SITUACOES_FILTRAVEIS)),
            OpenApiParameter("plano", int),
            OpenApiParameter("status", str),
            OpenApiParameter("busca", str),
            OpenApiParameter("ordem", enum=list(ORDENS)),
        ],
    )
    def get(self, request: Request) -> Response:
        params = request.query_params
        qs = selectors.filtrar_empresas(
            situacao_aba=params.get("situacao"),
            plano=params.get("plano"),
            status=params.get("status"),
            busca=params.get("busca"),
        ).annotate(ultimo_acesso_ordem=Coalesce("uso__ultimo_acesso_em", NUNCA))
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ORDENS.get(params.get("ordem", ""), ORDENS["nome"])  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        dados = EmpresaListaSerializer([selectors.item_da_lista(e) for e in pagina], many=True)
        return paginacao.get_paginated_response(
            dados.data, extras={"contagens": selectors.contagens_das_empresas()}
        )


class EmpresaDetalheView(SoFase1):
    permission_classes = [IsAuthenticated, exige_permissao("ver_empresas")]

    @extend_schema(responses=EmpresaDetalheSerializer, summary="Detalhe da empresa (PLT-01)")
    def get(self, request: Request, pk: int) -> Response:
        empresa = get_object_or_404(selectors.com_situacao(), pk=pk)
        return Response(EmpresaDetalheSerializer(selectors.detalhe_empresa(empresa)).data)


class AssinaturaView(SoFase1):
    """Do lado da empresa: plano, uso e situação da assinatura (PLT-03). Todos os perfis; os
    blocos do administrador só para ele (assinatura.md)."""

    suporte_somente_leitura = True

    @extend_schema(responses=AssinaturaSerializer, summary="Assinatura e uso do plano (PLT-03)")
    def get(self, request: Request) -> Response:
        return Response(representar_assinatura(selectors.assinatura(usuario=request.user)))
