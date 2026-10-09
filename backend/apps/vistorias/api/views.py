"""Views finas de vistorias (docs/api/vistorias.md).

A vistoria é da filial da locação: fora do escopo (USR-07), 404. Fazem vistoria administrador,
gerente, vendedor e vistoriador; o financeiro não (403). Corrigir é de administrador e gerente
(VIS-04). O vistoriador nunca recebe valores.
"""

from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.models import Filial
from apps.filiais.selectors import filtrar_por_filial
from apps.locacoes import selectors as locacoes_selectors
from apps.locacoes.models import Locacao
from comum.erros import ErroDeValidacao
from comum.permissoes import com_padrao, exige_perfil, filiais_permitidas, filial_pedida

from .. import selectors, services
from ..models import Vistoria
from .serializers import (
    AgendaSerializer,
    AvariaEntradaSerializer,
    AvariaSerializer,
    CorrigirVistoriaSerializer,
    CriarVistoriaSerializer,
    EditarVistoriaSerializer,
    FotoEntradaSerializer,
    FotoSerializer,
    ListaDeAvariasSerializer,
    VistoriaSerializer,
)

FAZEM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "vistoriador")
)
CORRIGEM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
DIAS = ("hoje", "amanha", "semana")


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _locacao(request: Request, pk: int) -> Locacao:
    locacao = filtrar_por_filial(locacoes_selectors.base(), request).filter(pk=pk).first()
    if locacao is None:
        raise Http404
    return locacao  # type: ignore[no-any-return]


def _vistoria(request: Request, pk: int) -> Vistoria:
    vistoria = (
        filtrar_por_filial(selectors.base(), request, "locacao__filial").filter(pk=pk).first()
    )
    if vistoria is None:
        raise Http404
    return vistoria  # type: ignore[no-any-return]


def _para(request: Request, dados: Any) -> Any:
    """O vistoriador nunca recebe valores (CA-016-07)."""
    if getattr(request.user, "perfil", "") == "vistoriador":
        return selectors.sem_valores(dados)
    return dados


def _resposta(request: Request, vistoria: Vistoria, codigo: int = status.HTTP_200_OK) -> Response:
    dados = selectors.representacao(selectors.base().get(pk=vistoria.pk))
    return Response(_para(request, VistoriaSerializer(dados).data), status=codigo)


class VistoriasDaLocacaoView(APIView):
    permission_classes = FAZEM

    @extend_schema(
        request=CriarVistoriaSerializer,
        responses={200: VistoriaSerializer, 201: VistoriaSerializer},
        summary="Abrir a vistoria de saída (VIS-01, VIS-02); o rascunho existente volta com 200",
    )
    def post(self, request: Request, pk: int) -> Response:
        _entrada(CriarVistoriaSerializer, request)
        vistoria, criada = services.iniciar_saida(_locacao(request, pk), request.user)
        codigo = status.HTTP_201_CREATED if criada else status.HTTP_200_OK
        return _resposta(request, vistoria, codigo)


class VistoriaView(APIView):
    permission_classes = FAZEM

    @extend_schema(responses=VistoriaSerializer, summary="Vistoria (fotos com URL de 15 min)")
    def get(self, request: Request, pk: int) -> Response:
        return _resposta(request, _vistoria(request, pk))

    @extend_schema(
        request=EditarVistoriaSerializer,
        responses=VistoriaSerializer,
        summary="Preencher o rascunho (DEV-05, VIS-04)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = _entrada(EditarVistoriaSerializer, request)
        vistoria = services.editar(_vistoria(request, pk), dados, request.user)
        return _resposta(request, vistoria)


class FotosDaVistoriaView(APIView):
    permission_classes = FAZEM
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": FotoEntradaSerializer},
        responses={201: FotoSerializer},
        summary="Enviar foto (VIS-01, AUD-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(FotoEntradaSerializer, request)
        foto = services.enviar_foto(
            _vistoria(request, pk), dados["posicao"], dados["arquivo"], request.user
        )
        return Response(
            FotoSerializer(selectors.representacao_foto(foto)).data, status=status.HTTP_201_CREATED
        )


class AvariasDaVistoriaView(APIView):
    permission_classes = FAZEM

    @extend_schema(
        request=AvariaEntradaSerializer,
        responses={201: AvariaSerializer},
        summary="Marcar avaria (VIS-01, DEV-01, DEV-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(AvariaEntradaSerializer, request)
        avaria = services.registrar_avaria(_vistoria(request, pk), dados, request.user)
        dados = AvariaSerializer(selectors.representacao_avaria(avaria)).data
        return Response(_para(request, dados), status=status.HTTP_201_CREATED)


class AvariaDaVistoriaView(APIView):
    permission_classes = FAZEM

    @extend_schema(responses={204: None}, summary="Remover avaria nova do rascunho")
    def delete(self, request: Request, pk: int, avaria_id: int) -> Response:
        services.remover_avaria(_vistoria(request, pk), avaria_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConcluirVistoriaView(APIView):
    permission_classes = FAZEM

    @extend_schema(
        request=None,
        responses=VistoriaSerializer,
        summary="Concluir (VIS-01 a VIS-04, VEI-01 a VEI-03, CLI-02, CLI-03, CLI-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        vistoria = services.concluir(_vistoria(request, pk), request.user)
        return _resposta(request, vistoria)


class CorrigirVistoriaView(APIView):
    permission_classes = CORRIGEM

    @extend_schema(
        request=CorrigirVistoriaSerializer,
        responses={200: VistoriaSerializer, 201: VistoriaSerializer},
        summary="Corrigir vistoria concluída (VIS-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(CorrigirVistoriaSerializer, request)
        nova, criada = services.corrigir(_vistoria(request, pk), dados["motivo"], request.user)
        codigo = status.HTTP_201_CREATED if criada else status.HTTP_200_OK
        return _resposta(request, nova, codigo)


class AvariasAbertasView(APIView):
    permission_classes = FAZEM

    @extend_schema(
        responses=ListaDeAvariasSerializer,
        parameters=[OpenApiParameter("veiculo", int)],
        summary="Avarias abertas (tela Vistoriador)",
    )
    def get(self, request: Request) -> Response:
        qs = filtrar_por_filial(
            selectors.avarias_abertas().select_related(
                "veiculo", "vistoria", "vistoria__locacao", "foto"
            ),
            request,
            "veiculo__filial",
        )
        veiculo = request.query_params.get("veiculo")
        if veiculo:
            if not veiculo.isdigit():
                raise ErroDeValidacao({"veiculo": ["Informe o id do veículo."]})
            qs = qs.filter(veiculo_id=int(veiculo))
        resultados = [selectors.avaria_aberta(a) for a in qs.order_by("-id")]
        return Response(_para(request, ListaDeAvariasSerializer({"resultados": resultados}).data))


def _filial_da_agenda(request: Request) -> Filial:
    """A agenda é de uma filial: a do `X-Filial`, ou a única da pessoa (VIS-05)."""
    pedida = filial_pedida(request)
    if not isinstance(pedida, int):
        filiais = filiais_permitidas(request.user)
        if pedida is not None or len(filiais) != 1:
            raise ErroDeValidacao({"filial": ["Escolha a filial no cabeçalho X-Filial."]})
        pedida = next(iter(filiais))
    return Filial.objects.get(pk=pedida)


class AgendaView(APIView):
    permission_classes = FAZEM

    @extend_schema(
        responses=AgendaSerializer,
        parameters=[OpenApiParameter("dia", enum=list(DIAS))],
        summary="Agenda do vistoriador (VIS-05)",
    )
    def get(self, request: Request) -> Response:
        dia = request.query_params.get("dia", "hoje")
        if dia not in DIAS:
            raise ErroDeValidacao({"dia": ["Use hoje, amanha ou semana."]})
        return Response(
            _para(request, AgendaSerializer(selectors.agenda(_filial_da_agenda(request), dia)).data)
        )
