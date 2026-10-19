"""Views finas das movimentações (docs/api/movimentacoes.md). Quem pode fica nos serviços
(`gere`, `registra_chegada`), que respondem 403 `permissao`; o vistoriador recebe tudo sem os
campos `_centavos` (USR-09)."""

from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.models import Filial
from comum.erros import ErroDeValidacao
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..models import LocalApoio, Movimentacao
from .serializers import (
    CancelarSerializer,
    ChegadaEntradaSerializer,
    EdicaoSerializer,
    FotoEntradaSerializer,
    FotoSerializer,
    LinhaSerializer,
    ListaDeLocaisSerializer,
    ListaSerializer,
    LocalSerializer,
    MovimentacaoSerializer,
    NovaMovimentacaoSerializer,
    NovoLocalSerializer,
    PessoasSerializer,
    QuadroSerializer,
    SaidaDaParadaSerializer,
)

GESTAO: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
SO_ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def sem_valores(dados: Any) -> Any:
    if isinstance(dados, dict):
        return {
            chave: sem_valores(valor)
            for chave, valor in dados.items()
            if not chave.endswith("_centavos")
        }
    if isinstance(dados, list):
        return [sem_valores(item) for item in dados]
    return dados


def _para(request: Request, dados: Any) -> Any:
    """O vistoriador não recebe valores (USR-09)."""
    return sem_valores(dados) if getattr(request.user, "perfil", "") == "vistoriador" else dados


def _visivel(request: Request, pk: int) -> Movimentacao:
    movimentacao = selectors.visiveis(request.user).filter(pk=pk).first()
    if movimentacao is None:
        raise Http404
    return movimentacao


def _existente(pk: int) -> Movimentacao:
    """Para as ações: quem não pode recebe 403 do serviço, não 404."""
    movimentacao = selectors.base().filter(pk=pk).first()
    if movimentacao is None:
        raise Http404
    return movimentacao


def _resposta(
    movimentacao: Movimentacao, request: Request, codigo: int = status.HTTP_200_OK
) -> Response:
    atual = selectors.base().get(pk=movimentacao.pk)
    dados = MovimentacaoSerializer(selectors.representacao(atual, request.user)).data
    return Response(_para(request, dados), status=codigo)


# O suporte só lê as movimentações, mesmo em "ver e editar": toda escrita dá 403 PLT-07 (MOV-02,
# decisão do dono de 16 out 2026, T-319). Ele não leva nem recebe veículo.
ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class QuadroView(APIView):
    suporte_somente_leitura = True

    @extend_schema(
        responses=QuadroSerializer,
        parameters=[
            OpenApiParameter("filial", int),
            OpenApiParameter("levando", enum=["eu"]),
            OpenApiParameter("busca", str, description="código ou placa"),
        ],
        summary="Quadro das movimentações (MOV-01 a MOV-06)",
    )
    def get(self, request: Request) -> Response:
        dados = selectors.quadro(
            request.user, request.query_params.get("filial"), request.query_params
        )
        return Response(_para(request, QuadroSerializer(dados).data))


class MovimentacoesView(APIView):
    suporte_somente_leitura = True
    suporte_proibido = ESCRITA

    @extend_schema(
        responses=ListaSerializer,
        operation_id="movimentacoes_list",
        parameters=[
            OpenApiParameter("status", str, description="vários, separados por vírgula"),
            OpenApiParameter("veiculo", int),
            OpenApiParameter("filial", int),
            OpenApiParameter("levando", enum=["eu"]),
            OpenApiParameter("periodo_inicio", str, description="2026-10-01"),
            OpenApiParameter("periodo_fim", str, description="2026-10-31"),
            OpenApiParameter("busca", str, description="código ou placa"),
        ],
        summary="Movimentações",
    )
    def get(self, request: Request) -> Response:
        qs = selectors.filtrar(request.user, request.query_params)
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("-id",)  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        dados = LinhaSerializer([selectors.linha(m, request.user) for m in pagina], many=True)
        return paginacao.get_paginated_response(_para(request, dados.data))

    @extend_schema(
        request=NovaMovimentacaoSerializer,
        responses={201: MovimentacaoSerializer},
        summary="Nova movimentação (MOV-01 a MOV-03, MOV-06, VEI-04)",
    )
    def post(self, request: Request) -> Response:
        movimentacao = services.criar(_entrada(NovaMovimentacaoSerializer, request), request.user)
        return _resposta(movimentacao, request, status.HTTP_201_CREATED)


class MovimentacaoView(APIView):
    # Sem "só ver" do suporte: traz as fotos da chegada com URL assinada (ADR 0013, item 2).
    suporte_proibido = ESCRITA

    @extend_schema(responses=MovimentacaoSerializer, summary="Movimentação")
    def get(self, request: Request, pk: int) -> Response:
        return _resposta(_visivel(request, pk), request)

    @extend_schema(
        request=EdicaoSerializer,
        responses=MovimentacaoSerializer,
        summary="Reagendar ou mudar a agendada (CA-246-05)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(EdicaoSerializer, request)
        return _resposta(services.editar(_existente(pk), dados, request.user), request)


class IniciarView(APIView):
    suporte_proibido = True

    @extend_schema(request=None, responses=MovimentacaoSerializer, summary="Iniciar (MOV-03)")
    def post(self, request: Request, pk: int) -> Response:
        return _resposta(services.iniciar(_existente(pk), request.user), request)


class CancelarView(APIView):
    suporte_proibido = True

    @extend_schema(
        request=CancelarSerializer, responses=MovimentacaoSerializer, summary="Cancelar a agendada"
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(CancelarSerializer, request)
        return _resposta(services.cancelar(_existente(pk), dados["motivo"], request.user), request)


class ChegadaNaParadaView(APIView):
    suporte_proibido = True

    @extend_schema(
        request=None, responses=MovimentacaoSerializer, summary="Cheguei na parada (MOV-04)"
    )
    def post(self, request: Request, pk: int, parada_id: int) -> Response:
        movimentacao = services.chegar_parada(_existente(pk), parada_id, request.user)
        return _resposta(movimentacao, request)


class SaidaDaParadaView(APIView):
    suporte_proibido = True
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request={"multipart/form-data": SaidaDaParadaSerializer},
        responses=MovimentacaoSerializer,
        summary="Saída da parada, com o valor pago (MOV-04, FIN-05)",
    )
    def post(self, request: Request, pk: int, parada_id: int) -> Response:
        dados = _entrada(SaidaDaParadaSerializer, request)
        movimentacao = services.sair_parada(
            _existente(pk), parada_id, dados["valor_pago_centavos"], dados.get("nota"), request.user
        )
        return _resposta(movimentacao, request)


class FotoDaChegadaView(APIView):
    suporte_proibido = True
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": FotoEntradaSerializer},
        responses={201: FotoSerializer},
        summary="Foto da vistoria rápida (MOV-05, AUD-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(FotoEntradaSerializer, request)
        foto = services.enviar_foto(
            _existente(pk), dados["posicao"], dados["arquivo"], request.user
        )
        return Response(FotoSerializer(selectors.foto(foto)).data, status=status.HTTP_201_CREATED)


class ChegadaView(APIView):
    suporte_proibido = True

    @extend_schema(
        request=ChegadaEntradaSerializer,
        responses=MovimentacaoSerializer,
        summary="Confirmar chegada no destino (MOV-05, MOV-06, VEI-01 a VEI-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(ChegadaEntradaSerializer, request)
        return _resposta(services.concluir(_existente(pk), dados, request.user), request)


class PessoasView(APIView):
    """Quem pode levar (MOV-02, T-300): administrador e gerente da filial."""

    permission_classes = GESTAO
    suporte_somente_leitura = True

    @extend_schema(
        responses=PessoasSerializer,
        parameters=[OpenApiParameter("filial", int, required=True)],
        summary="Quem pode levar (MOV-02)",
    )
    def get(self, request: Request) -> Response:
        texto = request.query_params.get("filial") or ""
        filial = Filial.ativos.filter(pk=int(texto)).first() if texto.isdigit() else None
        if filial is None:
            raise ErroDeValidacao({"filial": ["Escolha uma filial."]})
        services.exigir_gestao(request.user, filial.pk)
        return Response(PessoasSerializer(selectors.pessoas(filial.pk, request.user)).data)


class RecebedoresView(APIView):
    """Quem pode receber na chegada (MOV-06, T-300): da filial de destino, sem o financeiro."""

    suporte_somente_leitura = True

    @extend_schema(responses=PessoasSerializer, summary="Quem pode receber (MOV-06)")
    def get(self, request: Request, pk: int) -> Response:
        movimentacao = _existente(pk)
        services.exigir_chegada(movimentacao, request.user)
        return Response(PessoasSerializer(selectors.recebedores(movimentacao, request.user)).data)


class LocaisView(APIView):
    permission_classes = GESTAO
    suporte_somente_leitura = True
    suporte_proibido = ESCRITA

    @extend_schema(
        responses=ListaDeLocaisSerializer,
        parameters=[
            OpenApiParameter("ativo", bool),
            OpenApiParameter("tipo", str),
            OpenApiParameter("busca", str),
        ],
        summary="Locais de apoio (MOV-01)",
    )
    def get(self, request: Request) -> Response:
        locais = [selectors.representacao_local(x) for x in selectors.locais(request.query_params)]
        return Response(ListaDeLocaisSerializer({"resultados": locais}).data)

    @extend_schema(
        request=NovoLocalSerializer,
        responses={201: LocalSerializer},
        summary="Novo local de apoio (MOV-01, CA-246-15)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(NovoLocalSerializer, request)
        local = services.criar_local(dados["nome"], dados["tipo"])
        return Response(
            LocalSerializer(selectors.representacao_local(local)).data,
            status=status.HTTP_201_CREATED,
        )


def _local(pk: int) -> LocalApoio:
    local = LocalApoio.objects.filter(pk=pk).first()
    if local is None:
        raise Http404
    return local


class InativarLocalView(APIView):
    suporte_proibido = True
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=LocalSerializer, summary="Inativar local de apoio")
    def post(self, request: Request, pk: int) -> Response:
        local = services.ativar_local(_local(pk), False)
        return Response(LocalSerializer(selectors.representacao_local(local)).data)


class ReativarLocalView(APIView):
    suporte_proibido = True
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=LocalSerializer, summary="Reativar local de apoio")
    def post(self, request: Request, pk: int) -> Response:
        local = services.ativar_local(_local(pk), True)
        return Response(LocalSerializer(selectors.representacao_local(local)).data)
