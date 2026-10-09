"""Views finas de clientes (docs/api/clientes.md).

O cliente é da empresa, compartilhado entre filiais: nada aqui filtra pelo `X-Filial`. Ver a
lista é de todos os perfis, com CPF mascarado (AUD-04); o detalhe completo é só de quem cadastra
e nunca do suporte Giro (AUD-09). Escrever segue a tabela "Quem pode" do contrato.
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from comum.erros import ErroDeValidacao
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil, filiais_permitidas, filial_pedida

from .. import selectors, services
from ..models import Cliente
from .serializers import (
    AnaliseClienteSerializer,
    ClienteDetalheSerializer,
    ClienteEdicaoSerializer,
    ClienteEntradaSerializer,
    ClienteSerializer,
    DocumentoEntradaClienteSerializer,
    ListaDeClientesSerializer,
    MotivoClienteSerializer,
    PedidoAprovacaoCriadoClienteSerializer,
)

CADASTRO: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor")
)
GESTAO: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
DIRETO = frozenset({"administrador", "gerente"})  # desbloqueiam sem pedir (CLI-05)


def _entrada(classe: type[Serializer[Any]], request: Request, **kwargs: Any) -> dict[str, Any]:
    entrada = classe(data=request.data, **kwargs)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _cliente(pk: int) -> Cliente:
    return get_object_or_404(Cliente, pk=pk)


def _representacao(
    cliente: Cliente, request: Request, codigo: int = status.HTTP_200_OK
) -> Response:
    cliente = Cliente.objects.get(pk=cliente.pk)
    dados, completa = selectors.representacao(cliente, request.user)
    classe = ClienteDetalheSerializer if completa else ClienteSerializer
    return Response(classe(dados).data, status=codigo)


class ClientesView(APIView):
    suporte_somente_leitura = True  # o suporte lê, sempre mascarado (PLT-07, AUD-09)

    def get_permissions(self) -> Any:
        if self.request.method == "POST":
            return [permissao() for permissao in CADASTRO]
        return super().get_permissions()

    @extend_schema(
        responses=ListaDeClientesSerializer,
        operation_id="clientes_list",
        parameters=[
            OpenApiParameter("situacao", enum=list(selectors.SITUACOES_DA_LISTA)),
            OpenApiParameter("tipo", enum=["pf", "pj"]),
            OpenApiParameter("busca", str),
            OpenApiParameter("ordem", enum=list(selectors.ORDENS)),
        ],
        summary="Clientes (CLI-06, AUD-04)",
    )
    def get(self, request: Request) -> Response:
        parametros = request.query_params
        todos = Cliente.objects.all()
        if parametros.get("tipo") in ("pf", "pj"):
            todos = todos.filter(tipo=parametros["tipo"])
        contagens = selectors.contagens(todos)
        qs = selectors.filtrar(
            todos,
            situacao=parametros.get("situacao"),
            tipo=None,
            busca=parametros.get("busca"),
        )
        paginacao = PaginacaoPorCursor()
        ordem = selectors.ORDENS.get(parametros.get("ordem", ""), "-criado_em")
        paginacao.ordering = (ordem, "-id" if ordem.startswith("-") else "id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        dados = [selectors.resumida(c) for c in pagina]
        return paginacao.get_paginated_response(
            ClienteSerializer(dados, many=True).data,
            extras={
                "contagens": contagens,
                "indicadores": selectors.indicadores(todos, contagens),
            },
        )

    @extend_schema(
        request=ClienteEntradaSerializer,
        responses={201: ClienteDetalheSerializer},
        summary="Cadastrar cliente (CLI-01, CLI-03, CLI-08)",
    )
    def post(self, request: Request) -> Response:
        cliente = services.cadastrar(_entrada(ClienteEntradaSerializer, request))
        return _representacao(cliente, request, status.HTTP_201_CREATED)


class ClienteView(APIView):
    suporte_somente_leitura = True  # resumida para o suporte (AUD-09)

    def get_permissions(self) -> Any:
        if self.request.method == "PATCH":
            return [permissao() for permissao in CADASTRO]
        return super().get_permissions()

    @extend_schema(
        responses=ClienteDetalheSerializer,
        summary="Cliente: completo para quem cadastra, resumido para os demais (AUD-04)",
    )
    def get(self, request: Request, pk: int) -> Response:
        return _representacao(_cliente(pk), request)

    @extend_schema(
        request=ClienteEdicaoSerializer, responses=ClienteDetalheSerializer, summary="Editar"
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(ClienteEdicaoSerializer, request, partial=True)
        return _representacao(services.editar(_cliente(pk), dados), request)


class DocumentosView(APIView):
    permission_classes = CADASTRO
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": DocumentoEntradaClienteSerializer},
        responses={201: ClienteDetalheSerializer},
        summary="Enviar documento (CLI-03, AUD-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(DocumentoEntradaClienteSerializer, request)
        cliente = _cliente(pk)
        services.enviar_documento(cliente, dados["tipo"], dados["arquivo"])
        return _representacao(cliente, request, status.HTTP_201_CREATED)


class AnaliseView(APIView):
    permission_classes = CADASTRO

    @extend_schema(responses=AnaliseClienteSerializer, summary="Análise do cadastro (CLI-04)")
    def get(self, request: Request, pk: int) -> Response:
        return Response(AnaliseClienteSerializer(selectors.analise(_cliente(pk))).data)


class AnalisarView(APIView):
    permission_classes = CADASTRO

    @extend_schema(
        request=ClienteEntradaSerializer,
        responses=AnaliseClienteSerializer,
        summary="Análise de um cadastro ainda não salvo (CLI-04)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(ClienteEntradaSerializer, request)
        return Response(AnaliseClienteSerializer(selectors.analise_de_dados(dados)).data)


class BloquearView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=MotivoClienteSerializer,
        responses=ClienteDetalheSerializer,
        summary="Bloquear (CLI-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(MotivoClienteSerializer, request)
        return _representacao(services.bloquear(_cliente(pk), dados["motivo"]), request)


def _filial_do_pedido(request: Request) -> int:
    """APR-05: a filial da requisição do vendedor (o cliente é da empresa)."""
    pedida = filial_pedida(request)
    if isinstance(pedida, int):
        return pedida
    filiais = filiais_permitidas(request.user)
    if len(filiais) == 1:
        return next(iter(filiais))
    raise ErroDeValidacao({"filial": ["Escolha a filial no cabeçalho X-Filial."]})


class DesbloquearView(APIView):
    permission_classes = CADASTRO

    @extend_schema(
        request=MotivoClienteSerializer,
        responses={200: ClienteDetalheSerializer, 202: PedidoAprovacaoCriadoClienteSerializer},
        summary="Desbloquear: direto para gerente e administrador; pedido APR-05 do vendedor",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(MotivoClienteSerializer, request)
        cliente = _cliente(pk)
        if getattr(request.user, "perfil", None) in DIRETO:
            return _representacao(services.desbloquear(cliente, dados["motivo"]), request)
        pedido = services.pedir_desbloqueio(
            cliente, dados["motivo"], request.user, _filial_do_pedido(request)
        )
        return Response(
            PedidoAprovacaoCriadoClienteSerializer({"pedido_aprovacao": pedido.como_dict()}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class InativarView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=MotivoClienteSerializer,
        responses=ClienteDetalheSerializer,
        summary="Inativar (CLI-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(MotivoClienteSerializer, request)
        return _representacao(services.inativar(_cliente(pk), dados["motivo"]), request)


class ReativarView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=MotivoClienteSerializer,
        responses=ClienteDetalheSerializer,
        summary="Reativar (CLI-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(MotivoClienteSerializer, request)
        return _representacao(services.reativar(_cliente(pk), dados["motivo"]), request)
