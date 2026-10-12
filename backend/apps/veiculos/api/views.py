"""Views finas de veículos, categorias, preços e extras (docs/api/veiculos.md).

Ver a frota é de todos os perfis, no escopo das suas filiais (USR-07); fora dele, 404. O
vistoriador vê sem valores, e não abre preços nem extras (D-25, USR-09). Escrever segue a tabela
"Quem pode" do contrato.
"""

from typing import Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.selectors import filtrar_por_filial
from comum import relogio
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..models import Categoria, Extra, PrecoCategoria, Veiculo
from .serializers import (
    BaixarSerializer,
    BloquearVeiculoSerializer,
    CategoriaEdicaoSerializer,
    CategoriaEntradaSerializer,
    CategoriaSerializer,
    ColocarAVendaSerializer,
    CorrigirIdentificacaoSerializer,
    CorrigirKmSerializer,
    DesbloquearVeiculoSerializer,
    DocumentoEntradaSerializer,
    DocumentoSerializer,
    ExtraEntradaSerializer,
    ExtraSerializer,
    KmSerializer,
    ListaDeCategoriasSerializer,
    ListaDeDocumentosSerializer,
    ListaDeExtrasSerializer,
    ListaDeMudancasDePrecoSerializer,
    ListaDePrecosSerializer,
    ListaDeVeiculosSerializer,
    NovoPrecoSerializer,
    PedidoAprovacaoCriadoSerializer,
    PrecoCriadoSerializer,
    PrecoEntradaSerializer,
    PrecoHistoricoSerializer,
    TransferirSerializer,
    VeiculoDetalheSerializer,
    VeiculoEdicaoSerializer,
    VeiculoEntradaSerializer,
    VeiculoSerializer,
)

SO_ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))
GESTAO: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
LEITURA_DE_KM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vistoriador")
)
# Preços e extras são só dinheiro: todos menos o vistoriador (D-25, USR-09).
VEEM_VALORES: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro")
)


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _veiculo(request: Request, pk: int) -> Veiculo:
    """Só no escopo de filiais da pessoa; fora dele, 404 (USR-07)."""
    return get_object_or_404(
        selectors.no_escopo(request.user).select_related("categoria", "filial"), pk=pk
    )


def _representacao(
    veiculo: Veiculo, request: Request, codigo: int = status.HTTP_200_OK, detalhe: bool = False
) -> Response:
    veiculo = Veiculo.objects.select_related("categoria", "filial").get(pk=veiculo.pk)
    dados = selectors.representacao(veiculo, request.user, detalhe=detalhe)
    classe = VeiculoDetalheSerializer if detalhe else VeiculoSerializer
    return Response(_para(request, classe(dados).data), status=codigo)


def _para(request: Request, dados: Any) -> Any:
    """O vistoriador não recebe valores (D-25, USR-09)."""
    return dados if selectors.ve_valores(request.user) else selectors.sem_valores(dados)


# --- Frota ---


class VeiculosView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        if self.request.method == "POST":
            return [permissao() for permissao in GESTAO]
        return super().get_permissions()

    @extend_schema(
        responses=ListaDeVeiculosSerializer,
        operation_id="veiculos_list",
        parameters=[
            OpenApiParameter("status", str),
            OpenApiParameter("tipo_veiculo", enum=["moto", "carro"]),
            OpenApiParameter("categoria", int),
            OpenApiParameter("busca", str),
            OpenApiParameter("ordem", enum=list(selectors.ORDENS)),
        ],
        summary="Frota (VEI-06)",
    )
    def get(self, request: Request) -> Response:
        parametros = request.query_params
        da_filial = filtrar_por_filial(Veiculo.objects.all(), request)
        da_filial = selectors.do_tipo(da_filial, parametros.get("tipo_veiculo"))
        contagens = selectors.contagens(da_filial)
        qs = selectors.filtrar(
            da_filial.select_related("categoria", "filial"),
            status=parametros.get("status"),
            categoria=parametros.get("categoria"),
            busca=parametros.get("busca"),
        )
        paginacao = PaginacaoPorCursor()
        ordem = selectors.ORDENS.get(parametros.get("ordem", ""), "placa")
        paginacao.ordering = (ordem, "id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        hoje = relogio.hoje()
        precos = selectors.precos_vigentes({v.categoria_id for v in pagina}, hoje)
        documentos = selectors.resumos_de_documentos({v.pk for v in pagina}, hoje)
        dados = [
            selectors.representacao(v, request.user, precos=precos, documentos=documentos)
            for v in pagina
        ]
        return paginacao.get_paginated_response(
            _para(request, VeiculoSerializer(dados, many=True).data),
            extras={"contagens": contagens},
        )

    @extend_schema(
        request=VeiculoEntradaSerializer,
        responses={201: VeiculoSerializer},
        summary="Cadastrar veículo (VEI-01, PLT-03)",
    )
    def post(self, request: Request) -> Response:
        veiculo = services.cadastrar(_entrada(VeiculoEntradaSerializer, request))
        return _representacao(veiculo, request, status.HTTP_201_CREATED)


class VeiculoView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        if self.request.method == "PATCH":
            return [permissao() for permissao in GESTAO]
        return super().get_permissions()

    @extend_schema(responses=VeiculoDetalheSerializer, summary="Ficha do veículo (VEI-06)")
    def get(self, request: Request, pk: int) -> Response:
        return _representacao(_veiculo(request, pk), request, detalhe=True)

    @extend_schema(
        request=VeiculoEdicaoSerializer, responses=VeiculoSerializer, summary="Editar veículo"
    )
    def patch(self, request: Request, pk: int) -> Response:
        entrada = VeiculoEdicaoSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        veiculo = services.editar(_veiculo(request, pk), dict(entrada.validated_data))
        return _representacao(veiculo, request)


class CorrigirIdentificacaoView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=CorrigirIdentificacaoSerializer,
        responses=VeiculoSerializer,
        summary="Corrigir placa ou chassi (VEI-01)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(CorrigirIdentificacaoSerializer, request)
        veiculo = services.corrigir_identificacao(
            _veiculo(request, pk), dados["motivo"], dados.get("placa"), dados.get("chassi")
        )
        return _representacao(veiculo, request)


# --- Ações de status ---


class BloquearView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=BloquearVeiculoSerializer, responses=VeiculoSerializer, summary="Bloquear"
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(BloquearVeiculoSerializer, request)
        return _representacao(services.bloquear(_veiculo(request, pk), dados["motivo"]), request)


class DesbloquearView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=DesbloquearVeiculoSerializer, responses=VeiculoSerializer, summary="Desbloquear"
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(DesbloquearVeiculoSerializer, request)
        veiculo = services.desbloquear(_veiculo(request, pk), dados.get("motivo"))
        return _representacao(veiculo, request)


class ColocarAVendaView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=ColocarAVendaSerializer,
        responses=VeiculoSerializer,
        summary="Colocar à venda (VEN-01)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(ColocarAVendaSerializer, request)
        veiculo = services.colocar_a_venda(
            _veiculo(request, pk),
            dados["valor_venda_centavos"],
            dados.get("referencia_fipe_centavos"),
        )
        return _representacao(veiculo, request)


class VoltarParaFrotaView(APIView):
    permission_classes = GESTAO

    @extend_schema(request=None, responses=VeiculoSerializer, summary="Voltar para a frota")
    def post(self, request: Request, pk: int) -> Response:
        return _representacao(services.voltar_para_frota(_veiculo(request, pk)), request)


class BaixarView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=BaixarSerializer, responses=VeiculoSerializer, summary="Baixar")
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(BaixarSerializer, request)
        veiculo = services.baixar(_veiculo(request, pk), dados["motivo"], dados["descricao"])
        return _representacao(veiculo, request)


class TransferirView(APIView):
    permission_classes = GESTAO

    @extend_schema(
        request=TransferirSerializer, responses=VeiculoSerializer, summary="Transferir (VEI-04)"
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(TransferirSerializer, request)
        veiculo = services.transferir(
            _veiculo(request, pk),
            dados["filial_destino_id"],
            dados["motivo"],
            categoria_id=dados.get("categoria_id"),
        )
        return _representacao(veiculo, request)


# --- Km ---


class KmView(APIView):
    permission_classes = LEITURA_DE_KM

    @extend_schema(request=KmSerializer, responses=VeiculoSerializer, summary="Registrar km")
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(KmSerializer, request)
        return _representacao(services.atualizar_km(_veiculo(request, pk), dados["km"]), request)


class CorrigirKmView(APIView):
    """Gerente e administrador corrigem na hora (200). O vistoriador abre o pedido APR-06 e
    recebe 202 com o pedido; o km só muda quando o gerente aprovar."""

    permission_classes = LEITURA_DE_KM

    @extend_schema(
        request=CorrigirKmSerializer,
        responses={200: VeiculoSerializer, 202: PedidoAprovacaoCriadoSerializer},
        summary="Corrigir km (VEI-01, APR-06)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(CorrigirKmSerializer, request)
        veiculo = _veiculo(request, pk)
        if getattr(request.user, "perfil", "") == "vistoriador":
            pedido = services.pedir_correcao_km(veiculo, dados["km"], dados["motivo"], request.user)
            return Response(
                {"pedido_aprovacao": pedido.como_dict()}, status=status.HTTP_202_ACCEPTED
            )
        veiculo = services.corrigir_km(veiculo, dados["km"], dados["motivo"])
        return _representacao(veiculo, request)


# --- Documentos (VEI-03, AUD-05) ---


def _documentos(veiculo: Veiculo, historico: bool = False) -> Response:
    hoje = relogio.hoje()
    dados = [
        selectors.representacao_documento(d, hoje)
        for d in selectors.documentos(veiculo, historico=historico)
    ]
    return Response(ListaDeDocumentosSerializer({"resultados": dados}).data)


class DocumentosView(APIView):
    """Ver é de todos no escopo de filiais; enviar, de administrador e gerente."""

    parser_classes = [MultiPartParser, FormParser]
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        if self.request.method == "POST":
            return [permissao() for permissao in GESTAO]
        return super().get_permissions()

    @extend_schema(
        responses=ListaDeDocumentosSerializer,
        operation_id="veiculos_documentos_list",
        summary="Documentos ativos, com URL assinada de 15 minutos (VEI-03, AUD-05)",
    )
    def get(self, request: Request, pk: int) -> Response:
        return _documentos(_veiculo(request, pk))

    @extend_schema(
        request={"multipart/form-data": DocumentoEntradaSerializer},
        responses={201: DocumentoSerializer},
        summary="Enviar ou renovar documento (VEI-03)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(DocumentoEntradaSerializer, request)
        documento = services.enviar_documento(
            _veiculo(request, pk), dados["tipo"], dados["validade"], dados.get("arquivo")
        )
        corpo = selectors.representacao_documento(documento, relogio.hoje())
        return Response(DocumentoSerializer(corpo).data, status=status.HTTP_201_CREATED)


class HistoricoDeDocumentosView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    @extend_schema(
        responses=ListaDeDocumentosSerializer,
        operation_id="veiculos_documentos_historico",
        summary="Todos os documentos, inclusive os renovados (VEI-03)",
    )
    def get(self, request: Request, pk: int) -> Response:
        return _documentos(_veiculo(request, pk), historico=True)


# --- Categorias e preços ---


def _categoria(categoria: Categoria, codigo: int = status.HTTP_200_OK) -> Response:
    categoria = Categoria.objects.select_related("filial").get(pk=categoria.pk)
    return Response(
        CategoriaSerializer(selectors.representacao_categoria(categoria)).data, status=codigo
    )


class CategoriasView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        if self.request.method == "POST":
            return [permissao() for permissao in SO_ADMINISTRADOR]
        return super().get_permissions()

    @extend_schema(
        responses=ListaDeCategoriasSerializer,
        operation_id="categorias_list",
        parameters=[
            OpenApiParameter("filial", int),
            OpenApiParameter("tipo_veiculo", enum=["moto", "carro"]),
            OpenApiParameter("ativo", enum=["true", "false"]),
        ],
        summary="Categorias e preços vigentes (LOC-01)",
    )
    def get(self, request: Request) -> Response:
        filial = request.query_params.get("filial", "")
        qs = selectors.categorias(
            int(filial) if filial.isdigit() else None,
            request.query_params.get("tipo_veiculo"),
            request.query_params.get("ativo"),
        ).select_related("filial")
        dados = [selectors.representacao_categoria(c) for c in qs]
        return Response({"resultados": _para(request, CategoriaSerializer(dados, many=True).data)})

    @extend_schema(
        request=CategoriaEntradaSerializer,
        responses={201: CategoriaSerializer},
        summary="Nova categoria (LOC-01)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(CategoriaEntradaSerializer, request)
        preco = dados.pop("preco")
        return _categoria(services.criar_categoria(dados, preco), status.HTTP_201_CREATED)


class CategoriaView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=CategoriaEdicaoSerializer, responses=CategoriaSerializer, summary="Editar categoria"
    )
    def patch(self, request: Request, pk: int) -> Response:
        entrada = CategoriaEdicaoSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        categoria = get_object_or_404(Categoria, pk=pk)
        return _categoria(services.editar_categoria(categoria, dict(entrada.validated_data)))


class DesativarCategoriaView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=CategoriaSerializer, summary="Desativar categoria")
    def post(self, request: Request, pk: int) -> Response:
        return _categoria(services.desativar_categoria(get_object_or_404(Categoria, pk=pk)))


class ReativarCategoriaView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=CategoriaSerializer, summary="Reativar categoria")
    def post(self, request: Request, pk: int) -> Response:
        return _categoria(services.reativar_categoria(get_object_or_404(Categoria, pk=pk)))


def _preco_criado(preco: PrecoCategoria) -> dict[str, Any]:
    linha = next(
        item
        for item in selectors.historico_de_precos(preco.categoria)
        if item["vigente_desde"] == preco.vigente_desde
    )
    return {
        **linha,
        "locacoes_em_andamento_mantidas": services.locacoes_em_andamento(preco.categoria),
    }


class PrecosView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        permissoes = SO_ADMINISTRADOR if self.request.method == "POST" else VEEM_VALORES
        return [permissao() for permissao in permissoes]

    @extend_schema(
        responses=ListaDePrecosSerializer,
        operation_id="categorias_precos_list",
        summary="Histórico de preços da categoria (LOC-15)",
    )
    def get(self, request: Request, pk: int) -> Response:
        categoria = get_object_or_404(Categoria, pk=pk)
        dados = selectors.historico_de_precos(categoria)
        return Response({"resultados": PrecoHistoricoSerializer(dados, many=True).data})

    @extend_schema(
        request=NovoPrecoSerializer,
        responses={201: PrecoCriadoSerializer},
        summary="Novo preço (LOC-15)",
    )
    def post(self, request: Request, pk: int) -> Response:
        categoria = get_object_or_404(Categoria, pk=pk)
        dados = _entrada(NovoPrecoSerializer, request)
        vigente_desde = dados.pop("vigente_desde", None)
        preco = services.criar_preco(categoria, dados, vigente_desde)
        return Response(
            PrecoCriadoSerializer(_preco_criado(preco)).data, status=status.HTTP_201_CREATED
        )


class PrecoAgendadoView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=PrecoEntradaSerializer,
        responses=PrecoCriadoSerializer,
        summary="Trocar preço agendado (LOC-15)",
    )
    def put(self, request: Request, pk: int, vigente_desde: str) -> Response:
        preco = PrecoCategoria.objects.filter(categoria_id=pk, vigente_desde=vigente_desde).first()
        if preco is None:
            raise Http404
        preco = services.trocar_preco_futuro(preco, _entrada(PrecoEntradaSerializer, request))
        return Response(PrecoCriadoSerializer(_preco_criado(preco)).data)


class HistoricoDePrecosView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        responses=ListaDeMudancasDePrecoSerializer, summary="Mudanças de preço da empresa"
    )
    def get(self, request: Request) -> Response:
        return Response(
            ListaDeMudancasDePrecoSerializer({"resultados": selectors.mudancas_de_preco()}).data
        )


# --- Extras (LOC-02) ---


def _extra(extra: Extra, codigo: int = status.HTTP_200_OK) -> Response:
    return Response(ExtraSerializer(selectors.representacao_extra(extra)).data, status=codigo)


class ExtrasView(APIView):
    suporte_somente_leitura = True  # o suporte em "só ver" lê (PLT-07)

    def get_permissions(self) -> Any:
        permissoes = SO_ADMINISTRADOR if self.request.method == "POST" else VEEM_VALORES
        return [permissao() for permissao in permissoes]

    @extend_schema(
        responses=ListaDeExtrasSerializer,
        operation_id="extras_list",
        parameters=[OpenApiParameter("ativo", enum=["true", "false"])],
        summary="Extras da locação (LOC-02)",
    )
    def get(self, request: Request) -> Response:
        dados = [
            selectors.representacao_extra(e)
            for e in selectors.extras(request.query_params.get("ativo"))
        ]
        return Response({"resultados": ExtraSerializer(dados, many=True).data})

    @extend_schema(
        request=ExtraEntradaSerializer, responses={201: ExtraSerializer}, summary="Novo extra"
    )
    def post(self, request: Request) -> Response:
        extra = services.criar_extra(_entrada(ExtraEntradaSerializer, request))
        return _extra(extra, status.HTTP_201_CREATED)


class ExtraView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=ExtraEntradaSerializer, responses=ExtraSerializer, summary="Editar")
    def patch(self, request: Request, pk: int) -> Response:
        entrada = ExtraEntradaSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        extra = get_object_or_404(Extra, pk=pk)
        return _extra(services.editar_extra(extra, dict(entrada.validated_data)))


class DesativarExtraView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(request=None, responses=ExtraSerializer, summary="Desativar extra")
    def post(self, request: Request, pk: int) -> Response:
        return _extra(services.desativar_extra(get_object_or_404(Extra, pk=pk)))
