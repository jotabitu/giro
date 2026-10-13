"""Views finas da importação por planilha (docs/api/importacao.md).

Só o administrador (é parte da Administração e do assistente de implantação). O suporte Giro
entra com o alcance de um administrador: lê nos dois modos e importa com "ver e editar"
(PLT-07); as linhas de clientes saem resumidas para ele (AUD-09).
"""

from typing import Any

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from comum.erros import ErroDeValidacao
from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas
from comum.permissoes import com_padrao, exige_perfil

from .. import planilha, selectors, services
from ..models import Importacao, TipoImportacao
from .serializers import (
    CorrecaoSerializer,
    EnvioSerializer,
    ImportacaoSerializer,
    LinhaSerializer,
    ListaDeImportacoesSerializer,
    ListaDeLinhasSerializer,
)

ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _importacao(pk: int) -> Importacao:
    importacao: Importacao = get_object_or_404(
        Importacao.objects.select_related("filial_padrao"), pk=pk
    )
    return importacao


def _representacao(importacao: Importacao, codigo: int = status.HTTP_200_OK) -> Response:
    importacao = _importacao(importacao.pk)
    dados = selectors.representacao(importacao)
    return Response(ImportacaoSerializer(dados).data, status=codigo)


def _linha(request: Request, importacao: Importacao, linha: Any) -> Response:
    dados = selectors.linha(linha, importacao.tipo, request.user)
    return Response(LinhaSerializer(dados).data)


class Administrador(APIView):
    permission_classes = ADMINISTRADOR


class Leitura(Administrador):
    suporte_somente_leitura = True  # o suporte lê nos dois modos


class ImportacoesView(Leitura):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        responses=ListaDeImportacoesSerializer,
        operation_id="importacoes_list",
        summary="Importações dos últimos 30 dias",
    )
    def get(self, request: Request) -> Response:
        dados = [selectors.representacao(i) for i in selectors.recentes().order_by("-enviada_em")]
        return envelope_sem_paginas(ImportacaoSerializer(dados, many=True).data)

    @extend_schema(
        request={"multipart/form-data": EnvioSerializer},
        responses={202: ImportacaoSerializer},
        summary="Enviar planilha (IMP-02): valida as linhas em segundo plano",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(EnvioSerializer, request)
        importacao = services.enviar(dados["tipo"], dados["arquivo"], dados.get("filial_id"))
        return _representacao(importacao, status.HTTP_202_ACCEPTED)


class ModeloView(Leitura):
    @extend_schema(
        parameters=[OpenApiParameter("tipo", enum=list(TipoImportacao.values), required=True)],
        responses={(200, XLSX): OpenApiTypes.BINARY},
        summary="Planilha modelo, com uma linha de exemplo e a aba Instruções",
    )
    def get(self, request: Request) -> HttpResponse:
        tipo = request.query_params.get("tipo", "")
        if tipo not in TipoImportacao.values:
            raise ErroDeValidacao({"tipo": ["Use veiculos ou clientes."]})
        resposta = HttpResponse(planilha.modelo(tipo), content_type=XLSX)
        resposta["Content-Disposition"] = f'attachment; filename="modelo-{tipo}.xlsx"'
        resposta["X-Content-Type-Options"] = "nosniff"
        return resposta


class ImportacaoView(Leitura):
    @extend_schema(responses=ImportacaoSerializer, summary="Importação")
    def get(self, request: Request, pk: int) -> Response:
        return _representacao(_importacao(pk))


class LinhasView(Leitura):
    @extend_schema(
        responses=ListaDeLinhasSerializer,
        parameters=[OpenApiParameter("status", enum=list(selectors.FILTROS_DE_LINHA))],
        summary="Linhas da planilha, na ordem da planilha",
    )
    def get(self, request: Request, pk: int) -> Response:
        importacao = _importacao(pk)
        linhas = importacao.itens.all()
        filtro = request.query_params.get("status")
        if filtro in selectors.FILTROS_DE_LINHA:
            linhas = linhas.filter(status=filtro)
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("numero",)  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(linhas, request, view=self) or []
        dados = [selectors.linha(item, importacao.tipo, request.user) for item in pagina]
        return paginacao.get_paginated_response(LinhaSerializer(dados, many=True).data)


class LinhaView(Administrador):
    @extend_schema(
        request=CorrecaoSerializer,
        responses=LinhaSerializer,
        summary='"Corrigir aqui": revalida a linha na hora (IMP-02)',
    )
    def patch(self, request: Request, pk: int, numero: int) -> Response:
        dados = _entrada(CorrecaoSerializer, request)
        importacao = _importacao(pk)
        linha = services.corrigir(importacao, numero, dados["dados"])
        return _linha(request, importacao, linha)


class IgnorarLinhaView(Administrador):
    @extend_schema(request=None, responses=LinhaSerializer, summary="Tirar a linha da importação")
    def post(self, request: Request, pk: int, numero: int) -> Response:
        importacao = _importacao(pk)
        return _linha(request, importacao, services.ignorar(importacao, numero))


class ImportarView(Administrador):
    @extend_schema(
        request=None,
        responses={202: ImportacaoSerializer},
        summary="Importar as linhas prontas, até o limite do plano (IMP-03)",
    )
    def post(self, request: Request, pk: int) -> Response:
        importacao = services.importar(_importacao(pk))
        return _representacao(importacao, status.HTTP_202_ACCEPTED)


class CancelarView(Administrador):
    @extend_schema(request=None, responses=ImportacaoSerializer, summary="Cancelar")
    def post(self, request: Request, pk: int) -> Response:
        return _representacao(services.cancelar(_importacao(pk)))
