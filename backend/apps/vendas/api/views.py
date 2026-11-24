"""Views finas das vendas (`docs/api/vendas.md`).

- T-420: a lista e o detalhe (recurso `vendas_comissoes`) e "Transferência feita", sob a locação
  (recurso `locacoes_vistoria`, ADR 0037, item 6).
- T-502, fase 1a (ADR 0042, item 14): simular, criar, editar, enviar, resposta, pedir aprovação e
  perder. O suporte (PLT-07) não cria venda nem pede desconto: a venda e o pedido são de uma
  pessoa da empresa (o vendedor da comissão e quem pede ao gerente).
- Fase 1b: preparar e cancelar a assinatura, o contrato (link, reenvio e PDF, como na retirada)
  e a transferência no Detran da venda de balcão (`VEN-17`). O suporte não gera o link para o
  cliente, como na locação.
"""

from dataclasses import asdict
from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contratos import selectors as contratos_selectors
from apps.contratos.api.serializers import (
    ContratoGeradoSerializer,
    LinkDoContratoSerializer,
    UrlDoPdfSerializer,
)
from apps.filiais.selectors import filtrar_por_filial
from apps.locacoes import selectors as locacoes_selectors
from apps.locacoes.api.serializers import LocacaoDetalheSerializer
from apps.locacoes.models import Locacao
from apps.plataforma.models import Recurso
from comum.limites import LIMITES_DO_LINK_CONTRATO
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil
from comum.rede import ip_do_cliente

from .. import envio, selectors, services
from ..models import OrigemVenda, StatusVenda, Venda
from .serializers import (
    CriarVendaSerializer,
    EditarVendaSerializer,
    ListaDeVendasSerializer,
    PedirAprovacaoSerializer,
    PerderSerializer,
    RespostaSerializer,
    SimulacaoSerializer,
    SimularVendaSerializer,
    TransferenciaEntradaSerializer,
    VendaDetalheSerializer,
    VendaEnviadaSerializer,
    VendaSerializer,
)

# O vistoriador não vê vendas; o financeiro só lê (`vendas.md`, "Quem pode").
LEEM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro")
)
CRIAM: list[type[BasePermission]] = com_padrao(exige_perfil(*sorted(services.CRIAM)))
REGISTRAM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
SUPORTE_NAO_VENDE = ("PLT-07", "No modo suporte você não cria venda nem pede desconto.")


class ViewDeVendas(APIView):
    # PLT-12: as rotas /api/vendas/ só abrem com o recurso de vendas (ADR 0024, item 4).
    recurso_do_plano = Recurso.VENDAS_COMISSOES
    permission_classes = LEEM


class ViewDeAcao(ViewDeVendas):
    """As ações do fluxo: só quem vende (administrador, gerente, vendedor)."""

    permission_classes = CRIAM


def _venda(request: Request, pk: int) -> Venda:
    venda: Venda | None = (
        filtrar_por_filial(selectors.visiveis(request.user), request).filter(pk=pk).first()
    )
    if venda is None:
        raise Http404
    return venda


def _detalhe(venda: Venda, request: Request) -> dict[str, Any]:
    recarregada = selectors.base().get(pk=venda.pk)
    return dict(VendaDetalheSerializer(selectors.detalhe(recarregada, request.user)).data)


class VendasView(ViewDeVendas):
    suporte_proibido = frozenset({"POST"})
    mensagem_suporte_proibido = SUPORTE_NAO_VENDE

    def get_permissions(self) -> list[BasePermission]:
        classes = CRIAM if self.request.method == "POST" else LEEM
        return [p() for p in classes]

    @extend_schema(
        responses=ListaDeVendasSerializer,
        operation_id="vendas_list",
        parameters=[
            OpenApiParameter("status", enum=[s.value for s in StatusVenda]),
            OpenApiParameter("aba", enum=list(selectors.ABAS)),
            OpenApiParameter("mes", str, description="AAAA-MM"),
            OpenApiParameter("filial", int),
            OpenApiParameter("origem", enum=[o.value for o in OrigemVenda]),
            OpenApiParameter("transferencia_pendente", enum=["true"]),
            OpenApiParameter("veiculo", int),
            OpenApiParameter("cliente", int),
            OpenApiParameter(
                "ordem",
                enum=["ultimo_contato"],
                description="VEN-16: da mais antiga para a mais recente pelo último contato",
            ),
        ],
        summary="Vendas (VEN-08, VEN-11, VEN-13)",
    )
    def get(self, request: Request) -> Response:
        # B-03: a filial escolhida no cabeçalho, como as outras listas (USR-07).
        qs = filtrar_por_filial(selectors.filtrar(request.user, request.query_params), request)
        paginacao = PaginacaoPorCursor()
        ordem: Any = (
            ("ultimo_contato_em", "id")
            if request.query_params.get("ordem") == "ultimo_contato"
            else ("-id",)
        )
        paginacao.ordering = ordem
        pagina = list(paginacao.paginate_queryset(qs, request, view=self) or [])
        comissoes = selectors.comissoes(pagina)
        dados = VendaSerializer(
            [selectors.representacao(v, request.user, comissoes.get(v.pk)) for v in pagina],
            many=True,
        )
        return paginacao.get_paginated_response(dados.data)

    @extend_schema(
        request=CriarVendaSerializer,
        responses={201: VendaDetalheSerializer},
        summary="Nova venda: interessado, proposta ou pedido de aprovação (VEN-01, VEN-02, VEN-10,"
        " VEN-13, VEN-14)",
    )
    def post(self, request: Request) -> Response:
        entrada = CriarVendaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        venda = services.criar(dados, request.user, dados.pop("acao"))
        return Response(_detalhe(venda, request), status=status.HTTP_201_CREATED)


class SimularView(ViewDeAcao):
    @extend_schema(
        request=SimularVendaSerializer,
        responses=SimulacaoSerializer,
        summary="Simular a proposta, sem gravar (VEN-02, VEN-04, FIN-09, ADR 0005)",
    )
    def post(self, request: Request) -> Response:
        entrada = SimularVendaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        conta, limite = services.simular(dict(entrada.validated_data), request.user)
        dados = {**asdict(conta), "limite_desconto_pct": limite}
        return Response(SimulacaoSerializer(dados).data)


class VendaView(ViewDeVendas):
    def get_permissions(self) -> list[BasePermission]:
        classes = CRIAM if self.request.method == "PATCH" else LEEM
        return [p() for p in classes]

    @extend_schema(responses=VendaDetalheSerializer, summary="Detalhe da venda")
    def get(self, request: Request, pk: int) -> Response:
        venda = _venda(request, pk)
        return Response(VendaDetalheSerializer(selectors.detalhe(venda, request.user)).data)

    @extend_schema(
        request=EditarVendaSerializer,
        responses=VendaDetalheSerializer,
        summary="Editar a proposta antes da assinatura (VEN-02, VEN-14, FIN-09)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        entrada = EditarVendaSerializer(data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        venda = services.editar(_venda(request, pk), dict(entrada.validated_data), request.user)
        return Response(_detalhe(venda, request))


class EnviarView(ViewDeAcao):
    @extend_schema(
        request=None,
        responses=VendaEnviadaSerializer,
        summary="Enviar ou reenviar a proposta, com o PDF por e-mail (VEN-13, VEN-15, VEN-19)",
    )
    def post(self, request: Request, pk: int) -> Response:
        venda, enviado = services.enviar_proposta(_venda(request, pk), request.user)
        return Response(
            {
                "email_enviado": enviado,
                "texto": envio.texto_do_envio(venda),
                "venda": _detalhe(venda, request),
            }
        )


class RespostaView(ViewDeAcao):
    @extend_schema(
        request=RespostaSerializer,
        responses=VendaDetalheSerializer,
        summary="Registrar a resposta do cliente: proposta → negociação (VEN-13)",
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = RespostaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        venda = services.registrar_resposta(
            _venda(request, pk), request.user, entrada.validated_data.get("nota", "")
        )
        return Response(_detalhe(venda, request))


class PedirAprovacaoView(ViewDeAcao):
    suporte_proibido = True
    mensagem_suporte_proibido = SUPORTE_NAO_VENDE

    @extend_schema(
        request=PedirAprovacaoSerializer,
        responses=VendaDetalheSerializer,
        summary="Pedir aprovação do gerente para o desconto acima de 5% (VEN-02, APR-01, FIN-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = PedirAprovacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        venda = services.pedir_desconto(
            _venda(request, pk),
            entrada.validated_data["desconto_pct"],
            entrada.validated_data.get("motivo", ""),
            request.user,
        )
        return Response(_detalhe(venda, request))


class PerderView(ViewDeAcao):
    @extend_schema(
        request=PerderSerializer,
        responses=VendaDetalheSerializer,
        summary="Marcar como perdida, com motivo (VEN-13, FIN-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = PerderSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        venda = services.perder(
            _venda(request, pk), entrada.validated_data.get("motivo", ""), request.user
        )
        return Response(_detalhe(venda, request))


class AssinaturaView(ViewDeAcao):
    """A etapa "Assinatura" (VEN-15, VEN-19; ADR 0042, item 6)."""

    @extend_schema(
        request=None,
        responses=VendaDetalheSerializer,
        summary="Preparar a assinatura: contrato e conta da entrada (VEN-15, VEN-14, CLI-03,"
        " CLI-05, IMP-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        venda = services.preparar_assinatura(_venda(request, pk), request.user)
        return Response(_detalhe(venda, request))

    @extend_schema(
        request=None,
        responses=VendaDetalheSerializer,
        summary="Cancelar a assinatura para mudar a proposta (VEN-19, VEN-06)",
    )
    def delete(self, request: Request, pk: int) -> Response:
        venda = services.cancelar_assinatura(_venda(request, pk), request.user)
        return Response(_detalhe(venda, request))


class LinkDoContratoView(ViewDeAcao):
    """Copiar link para assinar (VEN-15), como na retirada (T-411): o link sai só nesta resposta,
    sem cache, e não vai para log."""

    throttle_classes = LIMITES_DO_LINK_CONTRATO
    suporte_proibido = True
    mensagem_suporte_proibido = ("PLT-07", "No modo suporte você não gera link para o cliente.")

    @extend_schema(
        request=None,
        responses=LinkDoContratoSerializer,
        summary="Copiar link para assinar o contrato da venda (S-15, VEN-15)",
    )
    def post(self, request: Request, pk: int) -> Response:
        link, vigente = services.copiar_link_do_contrato(
            _venda(request, pk), request.user, ip_do_cliente(request)
        )
        corpo = {
            "link": link,
            "expira_em": vigente.token_assinatura_expira_em,
            "aviso": "O link anterior deixa de valer.",
            "contrato": contratos_selectors.resumo(vigente),
        }
        return Response(LinkDoContratoSerializer(corpo).data, headers={"Cache-Control": "no-store"})


class ReenviarContratoView(ViewDeAcao):
    @extend_schema(
        request=None,
        responses={202: ContratoGeradoSerializer},
        summary="Reenviar o contrato da venda (novo link; o anterior deixa de valer, S-15)",
    )
    def post(self, request: Request, pk: int) -> Response:
        reenviado = services.reenviar_contrato(_venda(request, pk), request.user)
        return Response(
            {"contrato_id": reenviado.pk, "status": reenviado.status},
            status=status.HTTP_202_ACCEPTED,
        )


class PdfDoContratoView(ViewDeVendas):
    @extend_schema(
        responses=UrlDoPdfSerializer,
        summary="PDF do contrato da venda, o assinado se houver (URL de 15 min, AUD-05)",
    )
    def get(self, request: Request, pk: int) -> Response:
        contrato = _venda(request, pk).contrato
        url = contratos_selectors.url_do_pdf(contrato) if contrato else None
        if url is None:
            raise Http404
        return Response({"url": url.url, "url_expira_em": url.expira_em})


class TransferenciaDaVendaView(ViewDeVendas):
    """`VEN-17`: "Transferência feita" na venda de balcão (e na da quitação, pela venda)."""

    permission_classes = REGISTRAM

    @extend_schema(
        request=TransferenciaEntradaSerializer,
        responses=VendaDetalheSerializer,
        summary="Transferência feita no Detran (VEN-17, VEN-11): fecha a tarefa da venda",
    )
    def post(self, request: Request, pk: int) -> Response:
        entrada = TransferenciaEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        venda = services.registrar_transferencia(
            _venda(request, pk), entrada.validated_data["feita_em"], request.user
        )
        return Response(_detalhe(venda, request))


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
