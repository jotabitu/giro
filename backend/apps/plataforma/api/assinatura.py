"""Rotas da assinatura do lado da empresa (`docs/api/assinatura.md`; T-185).

Só o administrador (tabela de perfis; PLT-04, PLT-13, PLT-15). O suporte Giro lê e nunca
escreve, nem com "ver e editar" (PLT-07, CA-ASS-19). Com a empresa `suspensa`, só as rotas de
pagar escrevem (`escreve_na_suspensa`, PLT-13, CA-ASS-27); mudar de plano responde o 409 da
`PLT-04` (`recusa_na_suspensa`). `pausada` e `cancelada`: 403 `empresa_sem_operacao`.
"""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.erros import SemPermissao
from comum.permissoes import com_padrao

from .. import selectors, services
from ..models import Empresa
from .serializers import (
    AssinaturaSerializer,
    DadosFiscaisSerializer,
    EnderecoDaNotaSerializer,
    representar_assinatura,
)

SO_O_ADMINISTRADOR = ("permissao", "Só o administrador mexe na assinatura")
SUPORTE_NA_ASSINATURA = ("PLT-07", "O suporte não mexe na assinatura da empresa")


class SoAdministrador(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if getattr(request.user, "perfil", None) != "administrador":
            raise SemPermissao(*SO_O_ADMINISTRADOR)
        return True


class LeituraDaAssinatura(APIView):
    permission_classes = com_padrao(SoAdministrador)
    suporte_somente_leitura = True


class EscritaDaAssinatura(APIView):
    """Nenhuma escrita da assinatura aceita o token de suporte (PLT-07, T-189)."""

    permission_classes = com_padrao(SoAdministrador)
    suporte_proibido = True
    mensagem_suporte_proibido = SUPORTE_NA_ASSINATURA


def _empresa(request: Request) -> Empresa:
    empresa: Empresa = request.tenant  # type: ignore[attr-defined]
    return empresa


def _assinatura(request: Request) -> dict[str, Any]:
    with services.no_publico():
        return representar_assinatura(selectors.assinatura(_empresa(request), request.user))


# --- Planos e mudança de plano (PLT-04, PLT-05, PLT-11) ---


class LimiteExcedidoSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField()


class AbertoSerializer(serializers.Serializer[Any]):
    grupo = serializers.CharField()
    quantidade = serializers.IntegerField()
    texto = serializers.CharField()


class ExcedeSerializer(serializers.Serializer[Any]):
    veiculos = LimiteExcedidoSerializer(required=False)
    filiais = LimiteExcedidoSerializer(required=False)
    usuarios = LimiteExcedidoSerializer(required=False)
    abertos = AbertoSerializer(many=True, required=False)
    abertos_texto = serializers.CharField(required=False)


class PlanoParaMudarSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    ordem = serializers.IntegerField()
    atual = serializers.BooleanField()
    preco_mensal_centavos = serializers.IntegerField()
    preco_anual_centavos = serializers.IntegerField()
    preco_contratado_centavos = serializers.IntegerField(required=False)
    limite_veiculos = serializers.IntegerField(allow_null=True)
    limite_filiais = serializers.IntegerField(allow_null=True)
    limite_usuarios = serializers.IntegerField(allow_null=True)
    itens = serializers.ListField(child=serializers.CharField())
    mudanca = serializers.ChoiceField(choices=["upgrade", "downgrade"], allow_null=True)
    cabe = serializers.BooleanField()
    excede = ExcedeSerializer()


class PlanosParaMudarSerializer(serializers.Serializer[Any]):
    ciclo_atual = serializers.ChoiceField(choices=Empresa.Ciclo.choices)
    resultados = PlanoParaMudarSerializer(many=True)


class PedidoDeMudancaSerializer(serializers.Serializer[Any]):
    plano_id = serializers.IntegerField()
    ciclo = serializers.ChoiceField(choices=Empresa.Ciclo.choices)


class ConfirmarMudancaSerializer(PedidoDeMudancaSerializer):
    confirmar_valor_centavos = serializers.IntegerField(min_value=0)


class FaturaDaDiferencaSerializer(serializers.Serializer[Any]):
    valor_centavos = serializers.IntegerField()
    vencimento = serializers.DateField()
    descricao = serializers.CharField()


class ProximaFaturaDaMudancaSerializer(serializers.Serializer[Any]):
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    descricao = serializers.CharField()


class SimulacaoSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["upgrade", "downgrade"])
    vale_em = serializers.DateField()
    preco_novo_centavos = serializers.IntegerField()
    diferenca_centavos = serializers.IntegerField()
    fatura_diferenca = FaturaDaDiferencaSerializer(allow_null=True)
    proxima_fatura = ProximaFaturaDaMudancaSerializer(allow_null=True)
    mensagem = serializers.CharField()


def _simulacao(simulacao: services.Simulacao) -> dict[str, Any]:
    avulsa, proxima = simulacao.fatura_diferenca, simulacao.proxima
    return {
        "tipo": simulacao.tipo,
        "vale_em": simulacao.vale_em,
        "preco_novo_centavos": simulacao.preco_novo_centavos,
        "diferenca_centavos": simulacao.diferenca_centavos,
        "fatura_diferenca": (
            {
                "valor_centavos": avulsa.valor_centavos,
                "vencimento": avulsa.vencimento,
                "descricao": avulsa.descricao,
            }
            if avulsa
            else None
        ),
        "proxima_fatura": (
            {
                "vencimento": proxima.vencimento,
                "valor_centavos": proxima.valor_centavos,
                "descricao": proxima.descricao,
            }
            if proxima
            else None
        ),
        "mensagem": simulacao.mensagem,
    }


class PlanosDaAssinaturaView(LeituraDaAssinatura):
    @extend_schema(
        responses=PlanosParaMudarSerializer,
        operation_id="assinatura_planos_list",
        summary="Planos para mudar e comparar (PLT-04, PLT-11)",
    )
    def get(self, request: Request) -> Response:
        with services.no_publico():
            dados = selectors.planos_da_assinatura(_empresa(request))
        return Response(PlanosParaMudarSerializer(dados).data)


class MudancaDePlano(EscritaDaAssinatura):
    recusa_na_suspensa = services.PAGUE_ANTES  # PLT-04, CA-ASS-17


class SimularMudancaPlanoView(MudancaDePlano):
    @extend_schema(
        request=PedidoDeMudancaSerializer,
        responses=SimulacaoSerializer,
        summary="Simular a mudança de plano, sem gravar (PLT-04)",
    )
    def post(self, request: Request) -> Response:
        pedido = PedidoDeMudancaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        empresa = _empresa(request)
        plano = services.plano_para_mudar(pedido.validated_data["plano_id"], empresa)
        simulacao = services.simular_mudanca_plano(empresa, plano, pedido.validated_data["ciclo"])
        return Response(SimulacaoSerializer(_simulacao(simulacao)).data)


class MudancaPlanoView(MudancaDePlano):
    @extend_schema(
        request=ConfirmarMudancaSerializer,
        responses=AssinaturaSerializer,
        summary="Mudar de plano (PLT-04, PLT-05)",
    )
    def post(self, request: Request) -> Response:
        pedido = ConfirmarMudancaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        empresa = _empresa(request)
        plano = services.plano_para_mudar(pedido.validated_data["plano_id"], empresa)
        services.mudar_plano(
            empresa,
            plano,
            pedido.validated_data["ciclo"],
            confirmar_valor_centavos=pedido.validated_data["confirmar_valor_centavos"],
        )
        return Response(_assinatura(request))

    @extend_schema(
        request=None,
        responses=AssinaturaSerializer,
        summary="Desfazer o downgrade agendado (PLT-04)",
    )
    def delete(self, request: Request) -> Response:
        services.desfazer_mudanca_plano(_empresa(request))
        return Response(_assinatura(request))


# --- Dados fiscais (PLT-15) ---


class PedidoDeDadosFiscaisSerializer(serializers.Serializer[Any]):
    """Parcial. `endereco` vem inteiro (nulo é recusado); o CNPJ não muda por aqui."""

    razao_social = serializers.CharField(required=False, max_length=150)
    endereco = EnderecoDaNotaSerializer(required=False)
    email_cobranca = serializers.EmailField(required=False)


class RespostaDosDadosFiscaisSerializer(serializers.Serializer[Any]):
    dados_fiscais = DadosFiscaisSerializer()


class DadosFiscaisView(EscritaDaAssinatura):
    escreve_na_suspensa = frozenset({"PATCH"})  # a suspensa paga (PLT-13, CA-ASS-27)

    @extend_schema(
        request=PedidoDeDadosFiscaisSerializer,
        responses=RespostaDosDadosFiscaisSerializer,
        summary="Dados da nota fiscal da assinatura (PLT-15)",
    )
    def patch(self, request: Request) -> Response:
        dados = request.data if isinstance(request.data, dict) else {}
        empresa = services.atualizar_dados_fiscais(_empresa(request), dados)
        with services.no_publico():
            resposta = {"dados_fiscais": selectors.dados_fiscais(empresa)}
        return Response(RespostaDosDadosFiscaisSerializer(resposta).data)
