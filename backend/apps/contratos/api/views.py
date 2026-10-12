"""Views finas de contratos (docs/api/contratos.md).

Os modelos são do administrador. O link de assinatura é público (S-15): sem login, com limite
por IP e por token, e mostra só o contrato daquele token.
"""

from typing import Any

from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from comum.empresa import nome_da_empresa
from comum.limites import LIMITES_DE_ASSINATURA
from comum.paginacao import envelope_sem_paginas
from comum.permissoes import EmpresaOperando, com_padrao, exige_perfil
from comum.rede import ip_do_cliente

from .. import marcadores, origens, prontos, selectors, services
from ..models import ModeloContrato
from .serializers import (
    AssinarSerializer,
    AssinaturaFeitaSerializer,
    ConsultaDaAssinaturaSerializer,
    ListaDeMarcadoresSerializer,
    ListaDeModelosProntosSerializer,
    ListaDeModelosSerializer,
    ModeloDetalheSerializer,
    ModeloEdicaoSerializer,
    ModeloEntradaSerializer,
    ModeloResumoSerializer,
    PreviaEntradaSerializer,
    PreviaSerializer,
    TokenDeAssinaturaSerializer,
)

ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _modelo(pk: int) -> ModeloContrato:
    modelo = ModeloContrato.objects.filter(pk=pk).first()
    if modelo is None:
        raise Http404
    return modelo


def _detalhe(modelo: ModeloContrato, codigo: int = status.HTTP_200_OK) -> Response:
    dados = selectors.detalhe_do_modelo(modelo)
    return Response(ModeloDetalheSerializer(dados).data, status=codigo)


# --- Modelos ---


class ModelosView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(
        responses=ListaDeModelosSerializer,
        summary="Modelos de contrato",
        operation_id="contratos_modelos_list",
    )
    def get(self, request: Request) -> Response:
        arquivados = request.query_params.get("arquivados") == "true"
        dados = selectors.modelos(arquivados=arquivados)
        return envelope_sem_paginas(ModeloResumoSerializer(dados, many=True).data)

    @extend_schema(
        request=ModeloEntradaSerializer,
        responses={201: ModeloDetalheSerializer},
        summary="Novo modelo, em rascunho (S-09)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(ModeloEntradaSerializer, request)
        if "a_partir_de" in dados:
            modelo = services.criar_de_pronto(dados.get("nome"), dados["a_partir_de"])
        else:
            modelo = services.criar_modelo(dados["nome"], dados["finalidade"], dados["texto"])
        return _detalhe(modelo, status.HTTP_201_CREATED)


class ModeloView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(responses=ModeloDetalheSerializer, summary="Modelo, com texto e versões")
    def get(self, request: Request, pk: int) -> Response:
        return _detalhe(_modelo(pk))

    @extend_schema(
        request=ModeloEdicaoSerializer,
        responses=ModeloDetalheSerializer,
        summary="Editar (publicado vira rascunho da versão seguinte, LOC-15)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(ModeloEdicaoSerializer, request)
        modelo = services.editar_modelo(_modelo(pk), dados.get("nome"), dados.get("texto"))
        return _detalhe(modelo)


class PreviaModeloView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(
        request=PreviaEntradaSerializer,
        responses=PreviaSerializer,
        summary="Ver com dados reais, sem gerar PDF nem gravar",
    )
    def post(self, request: Request, pk: int) -> Response:
        modelo = _modelo(pk)
        locacao_id = _entrada(PreviaEntradaSerializer, request).get("locacao_id")
        valores = None
        if locacao_id is not None:
            valores = origens.valores("locacao", locacao_id)
            if valores is None:
                raise Http404
        return Response({"html": services.previa(modelo, valores)})


class PublicarModeloView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(
        request=None, responses=ModeloDetalheSerializer, summary="Publicar (S-09, IMP-04)"
    )
    def post(self, request: Request, pk: int) -> Response:
        return _detalhe(services.publicar_modelo(_modelo(pk)))


class ArquivarModeloView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(request=None, responses=ModeloDetalheSerializer, summary="Arquivar (IMP-04)")
    def post(self, request: Request, pk: int) -> Response:
        return _detalhe(services.arquivar_modelo(_modelo(pk)))


class MarcadoresView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(responses=ListaDeMarcadoresSerializer, summary="Campos automáticos (S-09)")
    def get(self, request: Request) -> Response:
        dados = [
            {"chave": m.chave, "rotulo": m.rotulo, "exemplo": m.exemplo}
            for m in marcadores.MARCADORES
        ]
        return envelope_sem_paginas(dados)


class ModelosProntosView(APIView):
    permission_classes = ADMINISTRADOR

    @extend_schema(responses=ListaDeModelosProntosSerializer, summary="Modelos prontos")
    def get(self, request: Request) -> Response:
        dados = [{"chave": p.chave, "nome": p.nome, "texto": p.texto} for p in prontos.PRONTOS]
        return envelope_sem_paginas(dados)


# --- Link público de assinatura (S-15) ---


class Publica(APIView):
    """Sem login e sem filial; a empresa precisa estar operando para receber a assinatura."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny, EmpresaOperando]
    throttle_classes = LIMITES_DE_ASSINATURA


def _empresa_da_assinatura() -> dict[str, Any]:
    return {
        "nome_exibicao": nome_da_empresa(),
        "logo_url": None,  # a marca (logo e cor) entra com a tela Config
        "cor_marca": None,
    }


class ConsultarAssinaturaView(Publica):
    @extend_schema(
        request=TokenDeAssinaturaSerializer,
        responses=ConsultaDaAssinaturaSerializer,
        summary="Ler o contrato do link (S-15)",
    )
    def post(self, request: Request) -> Response:
        contrato = services.consultar(_entrada(TokenDeAssinaturaSerializer, request)["token"])
        url = selectors.url_do_pdf(contrato)
        return Response(
            {
                "empresa": _empresa_da_assinatura(),
                "contrato": {
                    "codigo": contrato.origem_codigo,
                    "titulo": contrato.titulo,
                    "cliente_nome": contrato.cliente.nome,
                    "pdf_url": url.url if url else None,
                    "pdf_url_expira_em": url.expira_em if url else None,
                    "status": contrato.status,
                },
            }
        )


class AssinarView(Publica):
    @extend_schema(
        request=AssinarSerializer,
        responses=AssinaturaFeitaSerializer,
        summary="Assinar pelo link (S-15)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(AssinarSerializer, request)
        contrato = services.assinar(
            dados["token"],
            dados["nome_completo"],
            ip_do_cliente(request),
            request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response({"status": contrato.status, "assinado_em": contrato.assinado_em})


VIEWS_DE_ASSINATURA = (ConsultarAssinaturaView, AssinarView)
