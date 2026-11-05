"""Rotas da compra pública (`docs/api/compra.md`, T-435): sem login, só no domínio principal
(`urls_publico`), com limite por IP. A validação é do serviço (`plataforma.compra`), que junta os
erros de campo num 400 só; os serializers daqui descrevem o formato para o OpenAPI.
"""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.limites import (
    CompraCnpjPorIP,
    CompraConfirmarPorIP,
    CompraPedidoPorIPDia,
    CompraPedidoPorIPHora,
    CompraReenviarPorIP,
    CompraSubdominioPorIP,
)
from comum.rede import ip_do_cliente

from .. import compra

# --- Formato (OpenAPI) ---


class LimitesDoPlanoSerializer(serializers.Serializer[Any]):
    veiculos = serializers.IntegerField(allow_null=True)
    filiais = serializers.IntegerField(allow_null=True)
    usuarios = serializers.IntegerField(allow_null=True)


class PlanoAVendaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    nome = serializers.CharField()
    descricao = serializers.CharField()
    mensal_centavos = serializers.IntegerField()
    anual_centavos = serializers.IntegerField()
    limites = LimitesDoPlanoSerializer()
    inclui = serializers.ListField(child=serializers.CharField())
    destaque = serializers.BooleanField()


class DatasDoTesteSerializer(serializers.Serializer[Any]):
    dias = serializers.IntegerField()
    inicio = serializers.DateField()
    fim = serializers.DateField()
    lembrete = serializers.DateField()
    primeira_fatura = serializers.DateField()


class CatalogoDaCompraSerializer(serializers.Serializer[Any]):
    planos = PlanoAVendaSerializer(many=True)
    teste = DatasDoTesteSerializer()


class CnpjEntradaSerializer(serializers.Serializer[Any]):
    cnpj = serializers.CharField()


class DadosDoCnpjSerializer(serializers.Serializer[Any]):
    razao_social = serializers.CharField()
    nome_fantasia = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()
    ativo = serializers.BooleanField()


class SituacaoDoCnpjSerializer(serializers.Serializer[Any]):
    pode_comprar = serializers.BooleanField()
    teste_gratis = serializers.BooleanField(required=False)
    aviso = serializers.CharField(allow_null=True, required=False)
    primeira_fatura = serializers.DateField(required=False)
    dados = DadosDoCnpjSerializer(allow_null=True, required=False)
    codigo = serializers.CharField(required=False)
    mensagem = serializers.CharField(required=False)


class SubdominioEntradaSerializer(serializers.Serializer[Any]):
    subdominio = serializers.CharField(required=False)
    nome = serializers.CharField(required=False)


class SubdominioSerializer(serializers.Serializer[Any]):
    subdominio = serializers.CharField()
    disponivel = serializers.BooleanField()
    endereco = serializers.CharField(required=False)
    sugestao = serializers.CharField(allow_null=True, required=False)
    mensagem = serializers.CharField(required=False)


class AdministradorDaCompraSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    email = serializers.CharField()
    celular = serializers.CharField()
    aceita_whatsapp = serializers.BooleanField(required=False)


class EmpresaDaCompraSerializer(serializers.Serializer[Any]):
    cnpj = serializers.CharField()
    razao_social = serializers.CharField()
    nome_exibicao = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()
    subdominio = serializers.CharField()


class PedidoEntradaSerializer(serializers.Serializer[Any]):
    plano = serializers.CharField()
    ciclo = serializers.ChoiceField(choices=["mensal", "anual"])
    forma_pagamento = serializers.CharField(
        allow_null=True, required=False, help_text="cartao, pix_automatico ou boleto (PLT-13)"
    )
    administrador = AdministradorDaCompraSerializer()
    empresa = EmpresaDaCompraSerializer()
    aceite_termos = serializers.BooleanField()


class PedidoCriadoSerializer(serializers.Serializer[Any]):
    chave = serializers.UUIDField()
    status = serializers.CharField()
    email = serializers.CharField()
    codigo_expira_em = serializers.DateTimeField()
    mensagem = serializers.CharField()


class CodigoEntradaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()


class CodigoReenviadoSerializer(serializers.Serializer[Any]):
    codigo_expira_em = serializers.DateTimeField()
    mensagem = serializers.CharField()


class PassoDaCriacaoSerializer(serializers.Serializer[Any]):
    passo = serializers.ChoiceField(choices=["administrador", "banco", "endereco", "assinatura"])
    texto = serializers.CharField()
    feito_em = serializers.DateTimeField(allow_null=True)


class AdministradorDoPedidoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    email = serializers.CharField()


class EmpresaDoPedidoSerializer(serializers.Serializer[Any]):
    nome_exibicao = serializers.CharField()
    endereco = serializers.CharField()


class AcessarSerializer(serializers.Serializer[Any]):
    url = serializers.CharField()
    uma_vez = serializers.BooleanField()


class AndamentoDoPedidoSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(
        choices=["aguardando_confirmacao", "confirmado", "criando", "pronto", "falhou"]
    )
    mensagem = serializers.CharField(required=False)
    administrador = AdministradorDoPedidoSerializer(required=False)
    empresa = EmpresaDoPedidoSerializer(required=False)
    passos = PassoDaCriacaoSerializer(many=True, required=False)
    acessar = AcessarSerializer(allow_null=True, required=False)


# --- Views ---


class CompraView(APIView):
    """Base: sem login, sem sessão, sem cache; 429 no formato da compra (`compra.md`)."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def finalize_response(
        self, request: Request, response: Response, *args: Any, **kwargs: Any
    ) -> Response:
        resposta = super().finalize_response(request, response, *args, **kwargs)
        resposta.setdefault("Cache-Control", "no-store")
        return resposta

    def handle_exception(self, exc: Exception) -> Response:
        resposta = super().handle_exception(exc)
        if resposta.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            if isinstance(exc, exceptions.Throttled):
                resposta.data = {
                    "codigo": "limite",
                    "mensagem": "Muitas tentativas. Tente de novo mais tarde.",
                }
            if not resposta.has_header("Retry-After"):
                espera = 60 if getattr(exc, "codigo", "") == "limite_reenvio" else 3600
                resposta["Retry-After"] = str(espera)
        return resposta


def _json(dados: dict[str, Any]) -> dict[str, Any]:
    """Os serializers daqui só descrevem o OpenAPI: a resposta é o dicionário do serviço, sem
    campos nulos que o contrato não tem. Datas e UUID saem pelo renderizador."""
    return dados


def _corpo(request: Request) -> dict[str, Any]:
    return request.data if isinstance(request.data, dict) else {}


class CatalogoView(CompraView):
    @extend_schema(
        responses=CatalogoDaCompraSerializer,
        operation_id="compra_planos",
        summary="Planos à venda e as datas do teste (PLT-11, PLT-01)",
    )
    def get(self, request: Request) -> Response:
        resposta = Response(_json(compra.catalogo_a_venda()))
        resposta["Cache-Control"] = "public, max-age=300"
        return resposta


class CnpjView(CompraView):
    throttle_classes = [CompraCnpjPorIP]

    @extend_schema(
        request=CnpjEntradaSerializer,
        responses=SituacaoDoCnpjSerializer,
        operation_id="compra_cnpj",
        summary="Checagem do CNPJ (PLT-16) e dados públicos da Receita (ADR 0039)",
    )
    def post(self, request: Request) -> Response:
        dados = compra.checar_cnpj(_corpo(request).get("cnpj"))
        return Response(_json(dados))


class SubdominioView(CompraView):
    throttle_classes = [CompraSubdominioPorIP]

    @extend_schema(
        request=SubdominioEntradaSerializer,
        responses=SubdominioSerializer,
        operation_id="compra_subdominio",
        summary="Endereço de acesso: disponível ou sugestão (D-430-02)",
    )
    def post(self, request: Request) -> Response:
        return Response(_json(compra.checar_subdominio(_corpo(request))))


class PedidosView(CompraView):
    throttle_classes = [CompraPedidoPorIPHora, CompraPedidoPorIPDia]

    @extend_schema(
        request=PedidoEntradaSerializer,
        responses={202: PedidoCriadoSerializer},
        operation_id="compra_pedido_criar",
        summary="Criar minha conta: grava o pedido e manda o código (D-430-01)",
    )
    def post(self, request: Request) -> Response:
        dados = compra.criar_pedido_compra(request.data, ip_do_cliente(request))
        return Response(_json(dados), status=status.HTTP_202_ACCEPTED)


class ConfirmarView(CompraView):
    throttle_classes = [CompraConfirmarPorIP]

    @extend_schema(
        request=CodigoEntradaSerializer,
        responses={202: AndamentoDoPedidoSerializer, 200: AndamentoDoPedidoSerializer},
        operation_id="compra_pedido_confirmar",
        summary="Confirma o código e cria a empresa",
    )
    def post(self, request: Request, chave: str) -> Response:
        dados = compra.confirmar_pedido_compra(chave, _corpo(request).get("codigo"))
        ja_confirmado = dados["status"] not in ("criando", "confirmado")
        codigo = status.HTTP_200_OK if ja_confirmado else status.HTTP_202_ACCEPTED
        return Response(_json(dados), status=codigo)


class ReenviarView(CompraView):
    throttle_classes = [CompraReenviarPorIP]

    @extend_schema(
        request=None,
        responses={202: CodigoReenviadoSerializer},
        operation_id="compra_pedido_reenviar_codigo",
        summary="Código novo (até 3, 60 s entre eles)",
    )
    def post(self, request: Request, chave: str) -> Response:
        dados = compra.reenviar_codigo(chave)
        return Response(_json(dados), status=status.HTTP_202_ACCEPTED)


class PedidoView(CompraView):
    @extend_schema(
        responses=AndamentoDoPedidoSerializer,
        operation_id="compra_pedido_andamento",
        summary="Andamento da criação para a Compra-Pronto",
    )
    def get(self, request: Request, chave: str) -> Response:
        return Response(_json(compra.andamento_do_pedido(chave)))
