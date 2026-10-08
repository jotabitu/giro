"""Views finas das filiais (docs/api/filiais.md). Administrar é só do administrador."""

from typing import Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.plataforma.selectors import empresa_atual, uso_do_plano
from comum import relogio
from comum.erros import NaoEncontrado
from comum.limites import CepPorUsuario
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import (
    com_padrao,
    exige_perfil,
    filiais_permitidas,
    pode,
    pode_escolher_todas,
)
from integracoes.cep import buscar_cep

from .. import selectors, services
from ..calendario import feriados_nacionais
from ..models import FeriadoFilial, Filial
from .serializers import (
    CepSerializer,
    FeriadosEntradaSerializer,
    FilialEntradaSerializer,
    FilialSerializer,
    ListaDeFeriadosSerializer,
    ListaDeFiliaisSerializer,
    ListaDeSugestoesSerializer,
    MinhasFiliaisSerializer,
    MotivoSerializer,
)

SO_ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))


def _representacao(filial: Filial, codigo: int = status.HTTP_200_OK) -> Response:
    return Response(FilialSerializer(selectors.representacao(filial)).data, status=codigo)


def _ano(request: Request) -> int:
    valor = request.query_params.get("ano", "")
    return int(valor) if valor.isdigit() else relogio.hoje().year


class MinhasView(APIView):
    @extend_schema(responses=MinhasFiliaisSerializer, summary="Seletor de filial (USR-07)")
    def get(self, request: Request) -> Response:
        filiais = selectors.minhas_filiais(request.user)
        return Response(
            {
                "pode_escolher_todas": pode_escolher_todas(request.user),
                "resultados": [
                    {"id": f.pk, "nome": f.nome, "matriz": f.matriz, "cidade": f.cidade, "uf": f.uf}
                    for f in filiais
                ],
            }
        )


class FiliaisView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        responses=ListaDeFiliaisSerializer,
        operation_id="filiais_list",
        parameters=[
            OpenApiParameter("ativo", enum=["true", "false"]),
            OpenApiParameter("busca", str),
        ],
        summary="Filiais da empresa (FIL-01, PLT-03)",
    )
    def get(self, request: Request) -> Response:
        qs = selectors.lista(request.query_params.get("ativo"), request.query_params.get("busca"))
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = "nome"
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        empresa = empresa_atual()
        plano = {
            **uso_do_plano(empresa)["filiais"],
            "nome_plano": empresa.plano.nome if empresa.plano else "",
        }
        return paginacao.get_paginated_response(
            [selectors.item_da_lista(f) for f in pagina], extras={"plano": plano}
        )

    @extend_schema(
        request=FilialEntradaSerializer, responses={201: FilialSerializer}, summary="Nova filial"
    )
    def post(self, request: Request) -> Response:
        entrada = FilialEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        filial = services.criar_filial(dict(entrada.validated_data), criada_por=request.user)
        return _representacao(filial, status.HTTP_201_CREATED)


class FilialView(APIView):
    """GET para quem tem a filial no escopo (fora dele, 404); PATCH só do administrador."""

    def get_permissions(self) -> Any:
        if self.request.method == "PATCH":
            return [permissao() for permissao in SO_ADMINISTRADOR]
        return super().get_permissions()

    @extend_schema(responses=FilialSerializer, summary="Filial")
    def get(self, request: Request, pk: int) -> Response:
        # Filial desativada (fora do escopo) só o administrador abre.
        if not pode(request.user, "administracao") and pk not in filiais_permitidas(request.user):
            raise Http404
        return _representacao(get_object_or_404(Filial, pk=pk))

    @extend_schema(
        request=FilialEntradaSerializer, responses=FilialSerializer, summary="Editar filial"
    )
    def patch(self, request: Request, pk: int) -> Response:
        filial = get_object_or_404(Filial, pk=pk)
        entrada = FilialEntradaSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        return _representacao(services.editar_filial(filial, dict(entrada.validated_data)))


class TornarMatrizView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=FilialSerializer, summary="Tornar matriz (FIL-01)")
    def post(self, request: Request, pk: int) -> Response:
        return _representacao(services.tornar_matriz(get_object_or_404(Filial, pk=pk)))


class DesativarView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=MotivoSerializer, responses=FilialSerializer, summary="Desativar (FIL-06)"
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = MotivoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        filial = get_object_or_404(Filial, pk=pk)
        return _representacao(services.desativar(filial, entrada.validated_data["motivo"]))


class ReativarView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=MotivoSerializer, responses=FilialSerializer, summary="Reativar (PLT-03)"
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = MotivoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        filial = get_object_or_404(Filial, pk=pk)
        return _representacao(services.reativar(filial, entrada.validated_data["motivo"]))


def _feriados_do_ano(filial: Filial, ano: int) -> Response:
    return Response(
        {
            "resultados": [
                {"id": f.pk, "data": f.data, "nome": f.nome, "origem": f.origem}
                for f in selectors.feriados_do_ano(filial, ano)
            ]
        }
    )


class FeriadosView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        responses=ListaDeFeriadosSerializer,
        parameters=[OpenApiParameter("ano", int)],
        summary="Feriados da filial (FIL-03)",
    )
    def get(self, request: Request, pk: int) -> Response:
        return _feriados_do_ano(get_object_or_404(Filial, pk=pk), _ano(request))

    @extend_schema(
        request=FeriadosEntradaSerializer,
        responses={201: ListaDeFeriadosSerializer},
        summary="Confirmar feriados (FIL-03)",
    )
    def post(self, request: Request, pk: int) -> Response:
        filial = get_object_or_404(Filial, pk=pk)
        entrada = FeriadosEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        feriados = entrada.validated_data["feriados"]
        services.confirmar_feriados(filial, feriados)
        ano = feriados[0]["data"].year if feriados else _ano(request)
        resposta = _feriados_do_ano(filial, ano)
        resposta.status_code = status.HTTP_201_CREATED
        return resposta


class SugestoesView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        responses=ListaDeSugestoesSerializer,
        parameters=[OpenApiParameter("ano", int)],
        summary="Feriados nacionais sugeridos (FIL-03)",
    )
    def get(self, request: Request, pk: int) -> Response:
        filial = get_object_or_404(Filial, pk=pk)
        ano = _ano(request)
        cadastrados = set(selectors.feriados_do_ano(filial, ano).values_list("data", flat=True))
        return Response(
            {
                "resultados": [
                    {"data": data, "nome": nome, "ja_cadastrado": data in cadastrados}
                    for data, nome in feriados_nacionais(ano)
                ]
            }
        )


class RemoverFeriadoView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=ListaDeFeriadosSerializer, summary="Remover feriado")
    def post(self, request: Request, pk: int, feriado_id: int) -> Response:
        feriado = get_object_or_404(FeriadoFilial, pk=feriado_id, filial_id=pk, ativo=True)
        services.remover_feriado(feriado)
        return _feriados_do_ano(feriado.filial, feriado.data.year)


class CepView(APIView):
    throttle_classes = [CepPorUsuario]

    @extend_schema(responses=CepSerializer, summary="Busca de CEP")
    def get(self, request: Request, cep: str) -> Response:
        endereco = buscar_cep(cep) if len(cep) == 8 and cep.isdigit() else None
        if endereco is None:
            raise NaoEncontrado(
                "cep_nao_encontrado", "Não achamos esse CEP. Preencha o endereço à mão."
            )
        return Response(CepSerializer(endereco.__dict__).data)
