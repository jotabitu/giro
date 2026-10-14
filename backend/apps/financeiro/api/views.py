"""Views finas do financeiro (docs/api/financeiro.md).

Contas, caixa e despesas seguem o `X-Filial` (USR-07); fora do escopo, 404. O vistoriador recebe
403 em todo o app, menos ao lançar despesa de manutenção (FIN-06). Receber usa o caixa aberto da
filial da requisição, que pode ser outra que a da conta (FIL-06).
"""

import hmac
from typing import Any

from django.db import transaction
from django.http import Http404
from django_tenants.utils import tenant_context
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView

from apps.filiais.models import Filial
from apps.filiais.selectors import filtrar_por_filial
from apps.plataforma.models import ContaPagamento
from comum import arquivos, leituras, relogio
from comum.erros import ErroDeValidacao, NaoAutenticado, SemPermissao
from comum.limites import WebhookPorIP
from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas
from comum.permissoes import com_padrao, exige_perfil, filiais_permitidas, filial_pedida
from integracoes.pagamentos import hash_do_token
from integracoes.pagamentos import provedor as provedor_de_pagamentos

from .. import selectors, services
from ..models import (
    Caixa,
    CategoriaDespesa,
    ContaReceber,
    Despesa,
    MovimentoCaixa,
    PendenciaPagamento,
    Reembolso,
)
from .serializers import (
    AbrirCaixaSerializer,
    CaixaSerializer,
    CobrancaEntradaSerializer,
    CobrancaSerializer,
    ComprovanteSerializer,
    ContaDetalheSerializer,
    ContaSerializer,
    ContasSerializer,
    DespesaEntradaSerializer,
    DespesaSerializer,
    FecharCaixaSerializer,
    LancamentoSerializer,
    ListaDeContasSerializer,
    ListaDeDespesasSerializer,
    LoteAceitoSerializer,
    LoteSerializer,
    MotivoFinanceiroSerializer,
    MovimentoSerializer,
    MovimentosSerializer,
    PagarDespesaSerializer,
    PendenciaPagamentoSerializer,
    PendenciasPagamentoSerializer,
    ReceberSerializer,
    ReembolsoSerializer,
    ReembolsosSerializer,
    RenegociarSerializer,
    ResolverPendenciaSerializer,
    SangriaSerializer,
    SemCaixaSerializer,
)

OPERAM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro")
)
GERENCIAM: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "financeiro")
)
PAGAM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "financeiro"))
LANCAM_DESPESA: list[type[BasePermission]] = com_padrao(
    exige_perfil("administrador", "gerente", "vendedor", "financeiro", "vistoriador")
)


def _entrada(classe: type[Serializer[Any]], request: Request) -> dict[str, Any]:
    entrada = classe(data=request.data)
    entrada.is_valid(raise_exception=True)
    return dict(entrada.validated_data)


def _perfil(request: Request) -> str:
    return str(getattr(request.user, "perfil", ""))


def _filial_unica(request: Request) -> int | None:
    """A filial do `X-Filial`, ou a única da pessoa. Com "Todas as filiais", nenhuma."""
    pedida = filial_pedida(request)
    if isinstance(pedida, int):
        return pedida
    filiais = filiais_permitidas(request.user)
    if pedida is None and len(filiais) == 1:
        return next(iter(filiais))
    return None


def _filial_do_caixa(request: Request) -> int:
    """O caixa é de uma filial só (FIN-07): com "Todas as filiais", a pessoa escolhe uma."""
    filial_id = _filial_unica(request)
    if filial_id is None:
        raise ErroDeValidacao({"filial": ["Escolha a filial no cabeçalho X-Filial."]})
    return filial_id


def _conta(request: Request, pk: int) -> ContaReceber:
    conta = filtrar_por_filial(selectors.base_das_contas(), request).filter(pk=pk).first()
    if conta is None:
        raise Http404
    return conta  # type: ignore[no-any-return]


def _conta_para_receber(request: Request, pk: int) -> ContaReceber:
    """FIL-06: a conta pode ser recebida no caixa de qualquer filial que a pessoa opera."""
    conta: ContaReceber | None = selectors.base_das_contas().filter(pk=pk).first()
    if conta is None:
        raise Http404
    return conta


def _conta_resposta(conta: ContaReceber, request: Request, codigo: int = 200) -> Response:
    conta = selectors.base_das_contas().get(pk=conta.pk)
    dados = selectors.representacao_completa(conta, relogio.hoje(), _perfil(request))
    return Response(ContaSerializer(dados).data, status=codigo)


# --- Contas a receber ---


class ContasReceberView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in (GERENCIAM if self.request.method == "POST" else OPERAM)]

    @extend_schema(
        responses=ListaDeContasSerializer,
        operation_id="financeiro_contas_receber_list",
        parameters=[
            OpenApiParameter("periodo", enum=list(selectors.PERIODOS)),
            OpenApiParameter("situacao", enum=list(selectors.SITUACOES)),
            OpenApiParameter("faixa", enum=list(selectors.FAIXAS)),
            OpenApiParameter("cliente", int),
            OpenApiParameter("origem_tipo", str),
            OpenApiParameter("origem_id", int),
            OpenApiParameter("forma", str),
            OpenApiParameter("busca", str),
            OpenApiParameter("ordem", enum=list(selectors.ORDENS)),
        ],
        summary="Contas a receber (FIN-01, FIN-02, FIN-03, FIN-15)",
    )
    def get(self, request: Request) -> Response:
        hoje = relogio.hoje()
        params = request.query_params
        todas = filtrar_por_filial(selectors.base_das_contas(), request)
        filiais = _filiais_do_escopo(request)
        qs = leituras.aplicar(selectors.CONTA, selectors.filtrar_contas(todas, params, hoje))
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = selectors.ORDENS.get(  # type: ignore[assignment]
            params.get("ordem", ""), selectors.ORDENS["vencimento"]
        )
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        juros = selectors.JurosDaPagina()
        perfil = _perfil(request)
        return paginacao.get_paginated_response(
            ContaSerializer(
                [selectors.representacao_completa(c, hoje, perfil, juros) for c in pagina],
                many=True,
            ).data,
            extras=selectors.indicadores_e_contagens(filiais, params, hoje),
        )

    @extend_schema(
        request=LancamentoSerializer,
        responses={201: ContaSerializer},
        summary="Novo lançamento avulso: multa, avaria ou outro",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(LancamentoSerializer, request)
        filial_id = _filial_do_caixa(request)
        origem = dados.get("origem")
        conta = services.lancar_avulsa(
            filial_id=filial_id,
            cliente_id=dados["cliente_id"],
            tipo=dados["tipo"],
            descricao=dados["descricao"],
            vencimento=dados["vencimento"],
            valor_centavos=dados["valor_centavos"],
            origem=services.Origem(origem["tipo"], origem["id"]) if origem else None,
        )
        return _conta_resposta(conta, request, status.HTTP_201_CREATED)


class ContaReceberView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(responses=ContaDetalheSerializer, summary="Conta a receber com o histórico")
    def get(self, request: Request, pk: int) -> Response:
        conta = _conta(request, pk)
        dados = selectors.representacao_completa(conta, relogio.hoje(), _perfil(request))
        dados["historico"] = selectors.historico_da_conta(conta)
        return Response(ContaDetalheSerializer(dados).data)


class ReceberView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=ReceberSerializer,
        responses={200: ContaSerializer},
        summary="Baixa no caixa: dinheiro ou cartão (FIN-01, FIN-03, FIN-04, FIN-07)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(ReceberSerializer, request)
        conta = services.receber(
            _conta_para_receber(request, pk),
            request.user,
            forma=dados["forma"],
            valor_centavos=dados["valor_centavos"],
            filial_id=_filial_do_caixa(request),
        )
        return _conta_resposta(conta, request)


class CobrancaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=CobrancaEntradaSerializer,
        responses={201: CobrancaSerializer},
        summary="Gerar Pix ou boleto do valor de hoje (FIN-03, FIN-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(CobrancaEntradaSerializer, request)
        cobranca = services.gerar_cobranca(
            _conta_para_receber(request, pk),
            tipo=dados["tipo"],
            vence_em=dados.get("vence_em"),
            caixa_filial_id=_filial_do_caixa(request) if dados.get("no_caixa") else None,
        )
        return Response(
            CobrancaSerializer(selectors.representacao_cobranca(cobranca)).data,
            status=status.HTTP_201_CREATED,
        )


class CobrarView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=None,
        responses={202: LoteAceitoSerializer},
        summary="Cobrar pelo WhatsApp, com o Pix do valor de hoje (AUT-03)",
    )
    def post(self, request: Request, pk: int) -> Response:
        enviadas = int(services.cobrar(_conta(request, pk)))
        return Response({"enviadas": enviadas}, status=status.HTTP_202_ACCEPTED)


class CobrarEmLoteView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=LoteSerializer,
        responses={202: LoteAceitoSerializer},
        summary="Cobrar todos pelo WhatsApp (até 100, uma vez por conta por dia)",
    )
    def post(self, request: Request) -> Response:
        ids = _entrada(LoteSerializer, request)["ids"]
        contas = filtrar_por_filial(selectors.base_das_contas(), request).filter(pk__in=ids)
        enviadas = sum(int(services.cobrar(conta)) for conta in contas)
        return Response({"enviadas": enviadas}, status=status.HTTP_202_ACCEPTED)


class CancelarContaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        request=MotivoFinanceiroSerializer,
        responses={200: ContaSerializer},
        summary="Cancelar (FIN-01)",
    )
    def post(self, request: Request, pk: int) -> Response:
        motivo = _entrada(MotivoFinanceiroSerializer, request)["motivo"]
        conta = services.cancelar(_conta(request, pk), motivo=motivo)
        return _conta_resposta(conta, request)


class RenegociarView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        request=RenegociarSerializer,
        responses={201: ContasSerializer},
        summary="Renegociar: as originais vão para renegociada e nascem as novas (FIN-01)",
    )
    def post(self, request: Request) -> Response:
        dados = _entrada(RenegociarSerializer, request)
        contas = list(
            filtrar_por_filial(ContaReceber.objects.all(), request).filter(pk__in=dados["contas"])
        )
        if len(contas) != len(set(dados["contas"])):
            raise Http404
        novas = services.renegociar(
            contas,
            [services.ContaNova(n["vencimento"], n["valor_centavos"]) for n in dados["novas"]],
            motivo=dados["motivo"],
            usuario=request.user,
        )
        hoje, perfil = relogio.hoje(), _perfil(request)
        resultado = [
            selectors.representacao_completa(c, hoje, perfil)
            for c in selectors.base_das_contas().filter(pk__in=[n.pk for n in novas])
        ]
        return Response(
            ContasSerializer({"resultados": resultado}).data, status=status.HTTP_201_CREATED
        )


class EstornarContaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        request=MotivoFinanceiroSerializer,
        responses={200: ContaSerializer},
        summary="Estornar a conta paga: nasce uma conta aberta igual (CA-017-09)",
    )
    def post(self, request: Request, pk: int) -> Response:
        motivo = _entrada(MotivoFinanceiroSerializer, request)["motivo"]
        nova = services.estornar(
            _conta(request, pk), request.user, motivo=motivo, filial_id=_filial_unica(request)
        )
        return _conta_resposta(nova, request)


# --- Reembolsos ---


class ReembolsosView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        responses=ReembolsosSerializer,
        parameters=[OpenApiParameter("status", enum=["a_fazer", "feito"])],
        summary="Devoluções ao cliente (DEV-02)",
    )
    def get(self, request: Request) -> Response:
        qs = filtrar_por_filial(Reembolso.objects.select_related("cliente"), request)
        if request.query_params.get("status") in ("a_fazer", "feito"):
            qs = qs.filter(status=request.query_params["status"])
        return envelope_sem_paginas(
            ReembolsosSerializer(
                {"resultados": [selectors.representacao_reembolso(r) for r in qs[:200]]}
            ).data["resultados"]
        )


class ReembolsoFeitoView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        request={"multipart/form-data": ComprovanteSerializer},
        responses={200: ReembolsoSerializer},
        summary="Marcar a devolução como feita, com o comprovante",
    )
    def post(self, request: Request, pk: int) -> Response:
        reembolso = filtrar_por_filial(Reembolso.objects.all(), request).filter(pk=pk).first()
        if reembolso is None:
            raise Http404
        comprovante = _entrada(ComprovanteSerializer, request).get("comprovante")
        if comprovante is not None:
            arquivos.validar(comprovante, "comprovante")
        feito = services.marcar_reembolso_feito(
            reembolso, usuario=request.user, comprovante=comprovante
        )
        return Response(ReembolsoSerializer(selectors.representacao_reembolso(feito)).data)


# --- Pendências do webhook (S-14) ---


class PendenciasView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in PAGAM]

    @extend_schema(
        responses=PendenciasPagamentoSerializer, summary="Pagamentos para conferir (S-14)"
    )
    def get(self, request: Request) -> Response:
        qs = PendenciaPagamento.objects.select_related("cobranca__conta_receber__cliente").filter(
            cobranca__conta_receber__filial_id__in=_filiais_do_escopo(request)
        )
        if request.query_params.get("status") in ("aberta", "resolvida"):
            qs = qs.filter(status=request.query_params["status"])
        return envelope_sem_paginas(
            PendenciasPagamentoSerializer(
                {"resultados": [selectors.representacao_pendencia(p) for p in qs[:200]]}
            ).data["resultados"]
        )


def _filiais_do_escopo(request: Request) -> list[int]:
    return list(
        filtrar_por_filial(Filial.objects.all(), request, campo="pk").values_list("pk", flat=True)
    )


class ResolverPendenciaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in PAGAM]

    @extend_schema(
        request=ResolverPendenciaSerializer,
        responses={200: PendenciaPagamentoSerializer},
        summary="Resolver a pendência: baixar ou ignorar, com o motivo",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(ResolverPendenciaSerializer, request)
        pendencia = PendenciaPagamento.objects.filter(
            pk=pk, cobranca__conta_receber__filial_id__in=_filiais_do_escopo(request)
        ).first()
        if pendencia is None:
            raise Http404
        resolvida = services.resolver_pendencia(
            pendencia, acao=dados["acao"], motivo=dados["motivo"]
        )
        resolvida = PendenciaPagamento.objects.select_related(
            "cobranca__conta_receber__cliente"
        ).get(pk=resolvida.pk)
        return Response(
            PendenciaPagamentoSerializer(selectors.representacao_pendencia(resolvida)).data
        )


# --- Caixa do dia ---


def _caixa(request: Request, pk: int) -> Caixa:
    caixa = (
        filtrar_por_filial(Caixa.objects.select_related("filial", "aberto_por"), request)
        .filter(pk=pk)
        .first()
    )
    if caixa is None:
        raise Http404
    return caixa  # type: ignore[no-any-return]


def _caixa_resposta(caixa: Caixa, request: Request, codigo: int = 200) -> Response:
    caixa = Caixa.objects.select_related("filial", "aberto_por", "fechado_por").get(pk=caixa.pk)
    return Response(
        CaixaSerializer(selectors.representacao_caixa(caixa, _perfil(request))).data, status=codigo
    )


class CaixaHojeView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        responses={200: OpenApiResponse(CaixaSerializer, description="Ou `{caixa: null}`")},
        summary="Caixa de hoje da filial (FIN-07)",
    )
    def get(self, request: Request) -> Response:
        filial_id = _filial_do_caixa(request)
        caixa = selectors.caixa_do_dia(filial_id, relogio.hoje())
        if caixa is None:
            return Response(SemCaixaSerializer({"caixa": None, "pode_abrir": True}).data)
        return _caixa_resposta(caixa, request)


class CaixasView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=AbrirCaixaSerializer,
        responses={201: CaixaSerializer},
        summary="Abrir o caixa do dia com o troco (FIN-07)",
    )
    def post(self, request: Request) -> Response:
        troco = _entrada(AbrirCaixaSerializer, request)["troco_centavos"]
        filial = Filial.objects.get(pk=_filial_do_caixa(request))
        caixa = services.abrir_caixa(filial, request.user, troco)
        return _caixa_resposta(caixa, request, status.HTTP_201_CREATED)


class CaixaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(responses=CaixaSerializer, summary="Caixa do dia")
    def get(self, request: Request, pk: int) -> Response:
        return _caixa_resposta(_caixa(request, pk), request)


class MovimentosView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        responses=MovimentosSerializer,
        parameters=[OpenApiParameter("tipo", enum=["entrada", "saida", "sangria"])],
        summary="Movimentos do caixa",
    )
    def get(self, request: Request, pk: int) -> Response:
        qs = _caixa(request, pk).movimentos.select_related("registrado_por")
        if request.query_params.get("tipo") in ("entrada", "saida", "sangria"):
            qs = qs.filter(tipo=request.query_params["tipo"])
        return envelope_sem_paginas(
            MovimentosSerializer(
                {"resultados": [selectors.representacao_movimento(m) for m in qs]}
            ).data["resultados"]
        )


class SangriaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=SangriaSerializer,
        responses={201: MovimentoSerializer},
        summary="Sangria: dinheiro tirado da gaveta (FIN-07)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(SangriaSerializer, request)
        movimento = services.sangria(
            _caixa(request, pk),
            request.user,
            valor_centavos=dados["valor_centavos"],
            descricao=dados["descricao"],
        )
        return Response(
            MovimentoSerializer(selectors.representacao_movimento(movimento)).data,
            status=status.HTTP_201_CREATED,
        )


class EstornarMovimentoView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in GERENCIAM]

    @extend_schema(
        request=MotivoFinanceiroSerializer,
        responses={201: MovimentoSerializer},
        summary="Estornar um movimento: o original não muda (CA-017-17)",
    )
    def post(self, request: Request, pk: int, mid: int) -> Response:
        motivo = _entrada(MotivoFinanceiroSerializer, request)["motivo"]
        movimento = MovimentoCaixa.objects.filter(caixa=_caixa(request, pk), pk=mid).first()
        if movimento is None:
            raise Http404
        estorno = services.estornar_movimento(movimento, request.user, motivo=motivo)
        return Response(
            MovimentoSerializer(selectors.representacao_movimento(estorno)).data,
            status=status.HTTP_201_CREATED,
        )


class FecharCaixaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(
        request=FecharCaixaSerializer,
        responses={200: CaixaSerializer},
        summary="Fechar o caixa: diferença exige motivo e vai para o gerente (FIN-07, APR-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(FecharCaixaSerializer, request)
        caixa = services.fechar_caixa(
            _caixa(request, pk),
            request.user,
            contado_centavos=dados["contado_centavos"],
            motivo_diferenca=dados.get("motivo_diferenca"),
        )
        return _caixa_resposta(caixa, request)


# --- Despesas ---


def _despesa(request: Request, pk: int) -> Despesa:
    despesa = filtrar_por_filial(selectors.base_das_despesas(), request).filter(pk=pk).first()
    if despesa is None:
        raise Http404
    return despesa  # type: ignore[no-any-return]


class DespesasView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self) -> Any:
        return [p() for p in (LANCAM_DESPESA if self.request.method == "POST" else OPERAM)]

    @extend_schema(
        responses=ListaDeDespesasSerializer,
        operation_id="financeiro_despesas_list",
        parameters=[
            OpenApiParameter("mes", str, description="2026-10"),
            OpenApiParameter(
                "status", enum=["aguardando_aprovacao", "a_pagar", "paga", "recusada"]
            ),
            OpenApiParameter("categoria", enum=CategoriaDespesa.values),
            OpenApiParameter("veiculo", int),
            OpenApiParameter(
                "busca", str, description="descrição ou placa, até 60 caracteres (FIN-16)"
            ),
        ],
        summary="Despesas do mês (FIN-05, FIN-06, FIN-16)",
    )
    def get(self, request: Request) -> Response:
        hoje = relogio.hoje()
        todas = filtrar_por_filial(selectors.base_das_despesas(), request)
        qs = selectors.filtrar_despesas(todas, request.query_params, hoje)
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("-data", "-id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(qs, request, view=self) or []
        return paginacao.get_paginated_response(
            DespesaSerializer([selectors.representacao_despesa(d) for d in pagina], many=True).data,
            extras=selectors.indicadores_das_despesas(
                todas, request.query_params, hoje, _filiais_do_escopo(request)
            ),
        )

    @extend_schema(
        request={"multipart/form-data": DespesaEntradaSerializer},
        responses={201: DespesaSerializer},
        summary="Lançar despesa: acima de R$ 500 vai para o gerente (FIN-05, FIN-06, APR-03)",
    )
    def post(self, request: Request) -> Response:
        # As recusas de perfil vêm antes da validação dos campos (docs/api/financeiro.md).
        if _perfil(request) == "vistoriador":
            if request.data.get("categoria") != "manutencao":
                raise SemPermissao("FIN-06", "Seu perfil lança só despesas de manutenção.")
            pago_no_caixa = str(request.data.get("pago_no_caixa", "")).lower()
            if pago_no_caixa in serializers.BooleanField.TRUE_VALUES:
                raise SemPermissao("FIN-05", "Seu perfil não paga despesa pelo caixa.")
        dados = _entrada(DespesaEntradaSerializer, request)
        arquivos.validar(dados["nota"], "nota")
        veiculo_id = dados.get("veiculo_id")
        despesa = services.lancar_despesa(
            filial=Filial.objects.get(pk=_filial_do_caixa(request)),
            usuario=request.user,
            descricao=dados["descricao"],
            valor_centavos=dados["valor_centavos"],
            data=dados["data"],
            vencimento=dados["vencimento"],
            categoria=dados["categoria"],
            veiculo_id=_veiculo_existente(veiculo_id),
            nota=dados["nota"],
            pago_no_caixa=dados.get("pago_no_caixa", False),
        )
        despesa = selectors.base_das_despesas().get(pk=despesa.pk)
        return Response(
            DespesaSerializer(selectors.representacao_despesa(despesa)).data,
            status=status.HTTP_201_CREATED,
        )


def _veiculo_existente(veiculo_id: int | None) -> int | None:
    if veiculo_id is None:
        return None
    from apps.veiculos.models import Veiculo

    if not Veiculo.objects.filter(pk=veiculo_id).exists():
        raise ErroDeValidacao({"veiculo_id": ["Veículo não encontrado."]})
    return veiculo_id


class DespesaView(APIView):
    def get_permissions(self) -> Any:
        return [p() for p in OPERAM]

    @extend_schema(responses=DespesaSerializer, summary="Despesa (nota com link de 15 minutos)")
    def get(self, request: Request, pk: int) -> Response:
        return Response(
            DespesaSerializer(selectors.representacao_despesa(_despesa(request, pk))).data
        )


class PagarDespesaView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self) -> Any:
        return [p() for p in PAGAM]

    @extend_schema(
        request={"multipart/form-data": PagarDespesaSerializer},
        responses={200: DespesaSerializer},
        summary="Pagar a despesa a pagar (FIN-05)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = _entrada(PagarDespesaSerializer, request)
        if dados.get("comprovante") is not None:
            arquivos.validar(dados["comprovante"], "comprovante")
        despesa = services.pagar_despesa(
            _despesa(request, pk),
            request.user,
            forma=dados["forma"],
            pago_em=dados["pago_em"],
            comprovante=dados.get("comprovante"),
        )
        despesa = selectors.base_das_despesas().get(pk=despesa.pk)
        return Response(DespesaSerializer(selectors.representacao_despesa(despesa)).data)


# --- Webhook do parceiro (host da plataforma, schema public; S-14) ---


class WebhookAsaasView(APIView):
    """Sem login: o token do cabeçalho tem de conferir com o hash guardado de uma
    `ContaPagamento` (`hmac.compare_digest`). Grava o aviso no schema da empresa (`evento_id`
    único: o repetido não faz nada) e responde 200 na hora; a baixa é da tarefa AUT-05."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookPorIP]

    @extend_schema(exclude=True)
    def post(self, request: Request) -> Response:
        cabecalhos = {k.lower(): v for k, v in request.headers.items()}
        evento = provedor_de_pagamentos().validar_webhook(cabecalhos, request.body)
        if evento is None or not evento.token:
            raise NaoAutenticado("webhook_invalido", "Aviso não reconhecido.")
        esperado = hash_do_token(evento.token)
        conta = (
            ContaPagamento.objects.select_related("empresa")
            .filter(webhook_token_hash=esperado)
            .first()
        )
        if conta is None or not hmac.compare_digest(conta.webhook_token_hash, esperado):
            raise NaoAutenticado("webhook_invalido", "Aviso não reconhecido.")
        empresa = conta.empresa
        with tenant_context(empresa):
            webhook = services.registrar_webhook(evento, request.data)
            if webhook is not None:
                from ..tasks import aut_05_processar_webhook

                schema, webhook_id = empresa.schema_name, webhook.pk
                transaction.on_commit(lambda: aut_05_processar_webhook.delay(schema, webhook_id))
        return Response({"recebido": True})
