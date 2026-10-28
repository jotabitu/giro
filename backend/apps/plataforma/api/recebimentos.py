"""Recebimentos da empresa: ligar e ler a subconta no parceiro (`plataforma.md`, FIN-04, T-366).

Só o administrador. O suporte é recusado nos dois modos (PLT-07), porque os dados são cadastrais
e financeiros da empresa no parceiro. Sem `recebimento_parceiro` no plano (Essencial), 403 PLT-12
pelo `ModuloDoPlano` (T-196), antes do perfil. A chave da subconta e o token do webhook nunca
saem (S-05, S-14), e o corpo do `POST` vai só ao parceiro: não é gravado, auditado nem logado
(B-02 da T-384).
"""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from comum.documentos import cnpj_valido, cpf_valido, so_digitos
from comum.limites import RecebimentosPorEmpresa
from comum.permissoes import com_padrao

from .. import selectors, services
from ..models import ContaPagamento, Empresa, StatusContaPagamento
from .assinatura import SoAdministrador

SUPORTE_NOS_RECEBIMENTOS = ("PLT-07", "O suporte não mexe nos recebimentos da empresa")

DESCONECTADO = "desconectado"
TEXTOS = {
    DESCONECTADO: (
        "Não conectado",
        "Conecte para gerar Pix e boleto e dar baixa sozinho.",
    ),
    StatusContaPagamento.PENDENTE: (
        "Em análise pelo parceiro",
        "O parceiro está conferindo o cadastro. Enquanto isso, registre os pagamentos à mão em "
        "Contas a receber.",
    ),
    StatusContaPagamento.APROVADA: (
        "Recebimentos ligados",
        "Pix e boleto saem pelo parceiro, e a baixa é feita sozinha.",
    ),
    StatusContaPagamento.RECUSADA: (
        "Cadastro recusado",
        "O parceiro recusou o cadastro. Fale com a equipe Giro.",
    ),
}
# A lista do parceiro no contrato; o serviço usa as chaves internas (`integracoes.pagamentos`).
TIPOS_EMPRESA = {
    "MEI": "mei",
    "LIMITED": "limitada",
    "INDIVIDUAL": "individual",
    "ASSOCIATION": "associacao",
}


class SugestaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    documento = serializers.CharField()
    email = serializers.CharField()
    celular = serializers.CharField()
    cep = serializers.CharField()
    logradouro = serializers.CharField()
    numero = serializers.CharField()
    complemento = serializers.CharField()
    bairro = serializers.CharField()


class AcoesDosRecebimentosSerializer(serializers.Serializer[Any]):
    conectar = serializers.BooleanField()


class RecebimentosSerializer(serializers.Serializer[Any]):
    situacao = serializers.ChoiceField(choices=[DESCONECTADO, *StatusContaPagamento.values])
    rotulo = serializers.CharField()
    mensagem = serializers.CharField()
    conectado_em = serializers.DateTimeField(allow_null=True)
    sugestao = SugestaoSerializer(allow_null=True)
    acoes = AcoesDosRecebimentosSerializer()


class ConectarRecebimentosSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=150)
    documento = serializers.CharField(max_length=18)
    email = serializers.EmailField()
    celular = serializers.CharField(max_length=20)
    cep = serializers.CharField(max_length=9)
    logradouro = serializers.CharField(max_length=150)
    numero = serializers.CharField(max_length=20)
    complemento = serializers.CharField(max_length=80, required=False, allow_blank=True)
    bairro = serializers.CharField(max_length=80)
    faturamento_mensal_centavos = serializers.IntegerField()
    tipo_empresa = serializers.ChoiceField(choices=list(TIPOS_EMPRESA))

    def validate_documento(self, valor: str) -> str:
        digitos = so_digitos(valor)
        if len(digitos) == 11 and cpf_valido(digitos):
            return digitos
        if len(digitos) == 14 and cnpj_valido(digitos):
            return digitos
        raise serializers.ValidationError("Confira o CNPJ ou o CPF.")

    def validate_celular(self, valor: str) -> str:
        digitos = so_digitos(valor)
        if len(digitos) not in (10, 11):
            raise serializers.ValidationError("Informe o celular com DDD.")
        return digitos

    def validate_cep(self, valor: str) -> str:
        digitos = so_digitos(valor)
        if len(digitos) != 8:
            raise serializers.ValidationError("Informe o CEP com 8 dígitos.")
        return digitos

    def validate_faturamento_mensal_centavos(self, valor: int) -> int:
        if valor <= 0:
            raise serializers.ValidationError("Informe um faturamento maior que zero.")
        return valor


def _sugestao(empresa: Empresa, usuario: Any) -> dict[str, str]:
    """Razão social e CNPJ da empresa, e-mail e celular de quem está logado (B-03 da T-384) e o
    endereço da matriz. O administrador confere e corrige."""
    endereco = services.endereco_da_matriz() or {}
    return {
        "nome": empresa.razao_social or empresa.nome_exibicao,
        "documento": empresa.cnpj or "",
        "email": getattr(usuario, "email", "") or "",
        "celular": getattr(usuario, "celular", "") or "",
        **{
            campo: endereco.get(campo, "")
            for campo in ("cep", "logradouro", "numero", "complemento", "bairro")
        },
    }


def representar(conta: ContaPagamento | None, empresa: Empresa, usuario: Any) -> dict[str, Any]:
    situacao = conta.status if conta is not None else DESCONECTADO
    rotulo, mensagem = TEXTOS[situacao]
    return {
        "situacao": situacao,
        "rotulo": rotulo,
        "mensagem": mensagem,
        "conectado_em": conta.criado_em if conta is not None else None,
        "sugestao": _sugestao(empresa, usuario) if conta is None else None,
        "acoes": {"conectar": conta is None},
    }


class RecebimentosView(APIView):
    """GET e POST /api/recebimentos/ (`plataforma.md`, "Recebimentos da empresa")."""

    permission_classes = com_padrao(SoAdministrador)
    recurso_do_plano = selectors.RECURSO_DE_RECEBIMENTOS  # ADR 0024, item 4 (`ModuloDoPlano`)
    suporte_proibido = True
    mensagem_suporte_proibido = SUPORTE_NOS_RECEBIMENTOS

    def get_throttles(self) -> list[BaseThrottle]:
        # B-02 da T-384: 10 envios por hora por empresa; a leitura não conta.
        return [RecebimentosPorEmpresa()] if self.request.method == "POST" else []

    @extend_schema(
        responses=RecebimentosSerializer,
        summary="Situação dos recebimentos pelo parceiro (FIN-04)",
    )
    def get(self, request: Request) -> Response:
        empresa: Empresa = request.tenant  # type: ignore[attr-defined]
        conta = services.consultar_recebimentos()
        return Response(RecebimentosSerializer(representar(conta, empresa, request.user)).data)

    @extend_schema(
        request=ConectarRecebimentosSerializer,
        responses={201: RecebimentosSerializer},
        summary="Conectar os recebimentos pelo parceiro (FIN-04)",
    )
    def post(self, request: Request) -> Response:
        empresa: Empresa = request.tenant  # type: ignore[attr-defined]
        entrada = ConectarRecebimentosSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = dict(entrada.validated_data)
        dados["tipo_empresa"] = TIPOS_EMPRESA[dados["tipo_empresa"]]
        conta = services.conectar_recebimentos(**dados)
        return Response(
            RecebimentosSerializer(representar(conta, empresa, request.user)).data, status=201
        )
