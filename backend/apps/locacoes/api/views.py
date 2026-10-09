"""Views finas de locações e planos especiais (docs/api/locacoes.md).

A locação é da filial: a lista e o detalhe seguem o `X-Filial` (USR-07), e fora do escopo o
detalhe responde 404. O vistoriador não usa a lista (403) e vê o detalhe sem valores.
"""

from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.models import Filial
from apps.filiais.selectors import filtrar_por_filial
from comum.erros import ErroDeValidacao
from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas
from comum.permissoes import com_padrao, exige_perfil, filiais_permitidas, filial_pedida

from .. import selectors, services
from ..models import Locacao, PlanoEspecial
from .serializers import (
    ConfirmarLocacaoSerializer,
    HistoricoLocacaoSerializer,
    ListaDeLocacoesSerializer,
    ListaDePlanosEspeciaisSerializer,
    LocacaoDetalheSerializer,
    LocacaoEntradaSerializer,
    LocacaoSerializer,
    PlanoEspecialEntradaSerializer,
    PlanoEspecialSerializer,
    SimulacaoLocacaoSerializer,
)

CRIAM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente", "vendedor"))
LEEM_A_LISTA: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro")
)
ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))


def _entrada(classe: type[Serializer[Any]], request: Request, **kwargs: Any) -> dict[str, Any]:
    entrada = classe(data=request.data, **kwargs)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _filial_unica(request: Request) -> int | None:
    """A filial do `X-Filial`, ou a única da pessoa. Com "Todas as filiais", nenhuma."""
    pedida = filial_pedida(request)
    if isinstance(pedida, int):
        return pedida
    filiais = filiais_permitidas(request.user)
    if pedida is None and len(filiais) == 1:
        return next(iter(filiais))
    return None


def _filial_da_locacao(request: Request) -> Filial:
    """Locação nova é de uma filial só: com "Todas as filiais", a pessoa escolhe uma."""
    filial_id = _filial_unica(request)
    if filial_id is None:
        raise ErroDeValidacao({"filial": ["Escolha a filial no cabeçalho X-Filial."]})
    return Filial.objects.get(pk=filial_id)


def _locacao(request: Request, pk: int) -> Locacao:
    locacao = filtrar_por_filial(selectors.base(), request).filter(pk=pk).first()
    if locacao is None:
        raise Http404
    return locacao  # type: ignore[no-any-return]


def _detalhe(request: Request, pk: int, codigo: int = status.HTTP_200_OK) -> Response:
    dados = selectors.detalhe(_locacao(request, pk), request.user)
    if getattr(request.user, "perfil", "") == "vistoriador":
        dados = selectors.sem_valores(dados)
    return Response(LocacaoDetalheSerializer(dados).data, status=codigo)


class LocacoesView(APIView):
    def get_permissions(self) -> Any:
        permissoes = CRIAM if self.request.method == "POST" else LEEM_A_LISTA
        return [permissao() for permissao in permissoes]

    @extend_schema(
        responses=ListaDeLocacoesSerializer,
        operation_id="locacoes_list",
        parameters=[
            OpenApiParameter("aba", enum=list(selectors.ABAS)),
            OpenApiParameter("periodicidade", enum=["diaria", "semanal", "mensal"]),
            OpenApiParameter("plano_especial", int),
            OpenApiParameter("veiculo", int),
            OpenApiParameter("cliente", int),
            OpenApiParameter("busca", str),
            OpenApiParameter("ordem", enum=list(selectors.ORDENS)),
        ],
        summary="Locações (LOC-07, LOC-10)",
    )
    def get(self, request: Request) -> Response:
        todas = filtrar_por_filial(selectors.base(), request)
        qs = selectors.filtrar(todas, request.query_params)
        paginacao = PaginacaoPorCursor()
        ordem = selectors.ORDENS.get(request.query_params.get("ordem", ""), "fim_previsto")
        paginacao.ordering = (ordem, "-id" if ordem.startswith("-") else "id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        return paginacao.get_paginated_response(
            LocacaoSerializer([selectors.linha(x) for x in pagina], many=True).data,
            extras={
                "indicadores": selectors.indicadores(todas, _filial_unica(request)),
                "contagens": selectors.contagens(todas),
            },
        )

    @extend_schema(
        request=LocacaoEntradaSerializer,
        responses={201: LocacaoDetalheSerializer},
        summary="Criar rascunho (LOC-01 a LOC-05)",
    )
    def post(self, request: Request) -> Response:
        locacao = services.criar_rascunho(
            _entrada(LocacaoEntradaSerializer, request),
            _filial_da_locacao(request),
            request.user,
        )
        return _detalhe(request, locacao.pk, status.HTTP_201_CREATED)


class SimularLocacaoView(APIView):
    permission_classes = CRIAM

    @extend_schema(
        request=LocacaoEntradaSerializer,
        responses=SimulacaoLocacaoSerializer,
        summary="Simular (não grava nada; LOC-01 a LOC-05, LOC-14, LOC-15)",
    )
    def post(self, request: Request) -> Response:
        dados = selectors.simular(
            _entrada(LocacaoEntradaSerializer, request),
            _filial_da_locacao(request),
            request.user,
        )
        return Response(SimulacaoLocacaoSerializer(dados).data)


class LocacaoView(APIView):
    def get_permissions(self) -> Any:
        if self.request.method == "PATCH":
            return [permissao() for permissao in CRIAM]
        return super().get_permissions()

    @extend_schema(responses=LocacaoDetalheSerializer, summary="Detalhe da locação")
    def get(self, request: Request, pk: int) -> Response:
        return _detalhe(request, pk)

    @extend_schema(
        request=LocacaoEntradaSerializer,
        responses=LocacaoDetalheSerializer,
        summary="Editar rascunho (409 fora de rascunho)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(LocacaoEntradaSerializer, request, partial=True)
        services.editar_rascunho(_locacao(request, pk), dados)
        return _detalhe(request, pk)


class ConfirmarLocacaoView(APIView):
    permission_classes = CRIAM

    @extend_schema(
        request=ConfirmarLocacaoSerializer,
        responses=LocacaoDetalheSerializer,
        summary="Confirmar (LOC-03, LOC-15, IMP-04, FIL-05, APR-01, FIN-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(ConfirmarLocacaoSerializer, request)
        services.confirmar(_locacao(request, pk), request.user, dados.get("primeiro_vencimento"))
        return _detalhe(request, pk)


class HistoricoLocacaoView(APIView):
    @extend_schema(responses=HistoricoLocacaoSerializer, summary="Linha do tempo da locação")
    def get(self, request: Request, pk: int) -> Response:
        itens = selectors.historico(_locacao(request, pk), request.user)
        return Response(HistoricoLocacaoSerializer({"resultados": itens}).data)


# --- Planos especiais ---


class PlanosEspeciaisView(APIView):
    def get_permissions(self) -> Any:
        if self.request.method == "POST":
            return [permissao() for permissao in ADMINISTRADOR]
        return super().get_permissions()

    @extend_schema(
        responses=ListaDePlanosEspeciaisSerializer,
        parameters=[OpenApiParameter("ativo", enum=["true", "false", "todos"])],
        summary="Planos especiais (LOC-01)",
    )
    def get(self, request: Request) -> Response:
        planos = selectors.planos_especiais(request.query_params.get("ativo"))
        dados = [selectors.representacao_plano(p) for p in planos]
        return envelope_sem_paginas(PlanoEspecialSerializer(dados, many=True).data)

    @extend_schema(
        request=PlanoEspecialEntradaSerializer,
        responses={201: PlanoEspecialSerializer},
        summary="Criar plano especial (LOC-01, LOC-15)",
    )
    def post(self, request: Request) -> Response:
        plano = services.criar_plano(_entrada(PlanoEspecialEntradaSerializer, request))
        return Response(
            PlanoEspecialSerializer(selectors.representacao_plano(plano)).data,
            status=status.HTTP_201_CREATED,
        )


def _plano(pk: int) -> PlanoEspecial:
    plano = PlanoEspecial.objects.filter(pk=pk).first()
    if plano is None:
        raise Http404
    return plano


class PlanoEspecialView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(
        request=PlanoEspecialEntradaSerializer,
        responses=PlanoEspecialSerializer,
        summary="Editar plano especial (vale para locações novas, LOC-15)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(PlanoEspecialEntradaSerializer, request, partial=True)
        plano = services.editar_plano(_plano(pk), dados)
        return Response(PlanoEspecialSerializer(selectors.representacao_plano(plano)).data)


class DesativarPlanoEspecialView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(request=None, responses=PlanoEspecialSerializer, summary="Desativar plano")
    def post(self, request: Request, pk: int) -> Response:
        plano = services.desativar_plano(_plano(pk))
        return Response(PlanoEspecialSerializer(selectors.representacao_plano(plano)).data)
