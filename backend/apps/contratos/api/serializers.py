"""Entrada e formato de resposta de contratos (docs/api/contratos.md).

Os marcadores e a limpeza do HTML (S-09) são conferidos no serviço; aqui só a forma. Os momentos
vão como `datetime` com fuso; o formato é do renderizador de `comum` (ADR 0020).
"""

from typing import Any

from rest_framework import serializers

from ..models import Finalidade, StatusContrato

# --- Modelos ---


class ModeloEntradaSerializer(serializers.Serializer[Any]):
    """`{ nome, finalidade, texto }` ou `{ nome?, a_partir_de }`."""

    nome = serializers.CharField(max_length=80, required=False)
    finalidade = serializers.ChoiceField(choices=Finalidade.choices, default=Finalidade.LOCACAO)
    texto = serializers.CharField(required=False, trim_whitespace=False)
    a_partir_de = serializers.CharField(max_length=40, required=False)

    def validate(self, dados: dict[str, Any]) -> dict[str, Any]:
        if "a_partir_de" in dados:
            return dados
        erros: dict[str, list[str]] = {}
        if not dados.get("nome"):
            erros["nome"] = ["Informe o nome do modelo."]
        if not dados.get("texto"):
            erros["texto"] = ["Escreva o texto do modelo."]
        if erros:
            raise serializers.ValidationError(erros)
        return dados


class ModeloEdicaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=80, required=False)
    texto = serializers.CharField(required=False, trim_whitespace=False)


class ModeloResumoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    grupo = serializers.UUIDField()
    nome = serializers.CharField()
    finalidade = serializers.ChoiceField(choices=Finalidade.choices)
    versao_publicada = serializers.IntegerField(allow_null=True)
    tem_rascunho = serializers.BooleanField()
    status = serializers.ChoiceField(choices=["publicado", "rascunho"])
    arquivado = serializers.BooleanField()
    contratos_gerados = serializers.IntegerField()
    editado_em = serializers.DateTimeField()


class ListaDeModelosSerializer(serializers.Serializer[Any]):
    resultados = ModeloResumoSerializer(many=True)


class VersaoDoModeloSerializer(serializers.Serializer[Any]):
    versao = serializers.IntegerField()
    publicado_em = serializers.DateTimeField()
    contratos_gerados = serializers.IntegerField()


class ModeloDetalheSerializer(ModeloResumoSerializer):
    texto = serializers.CharField()
    marcadores_usados = serializers.ListField(child=serializers.CharField())
    versoes = VersaoDoModeloSerializer(many=True)


class MarcadorSerializer(serializers.Serializer[Any]):
    chave = serializers.CharField()
    rotulo = serializers.CharField()
    exemplo = serializers.CharField()


class ListaDeMarcadoresSerializer(serializers.Serializer[Any]):
    resultados = MarcadorSerializer(many=True)


class ModeloProntoSerializer(serializers.Serializer[Any]):
    chave = serializers.CharField()
    nome = serializers.CharField()
    texto = serializers.CharField()


class ListaDeModelosProntosSerializer(serializers.Serializer[Any]):
    resultados = ModeloProntoSerializer(many=True)


class PreviaEntradaSerializer(serializers.Serializer[Any]):
    locacao_id = serializers.IntegerField(required=False, allow_null=True)


class PreviaSerializer(serializers.Serializer[Any]):
    html = serializers.CharField()


# --- Contrato de uma origem ---


class ContratoGeradoSerializer(serializers.Serializer[Any]):
    contrato_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusContrato.choices)


class ContratoResumoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusContrato.choices)
    modelo = serializers.CharField()
    versao = serializers.IntegerField(allow_null=True)
    enviado_em = serializers.DateTimeField(allow_null=True)
    assinado_em = serializers.DateTimeField(allow_null=True)
    pdf_disponivel = serializers.BooleanField()


class UrlDoPdfSerializer(serializers.Serializer[Any]):
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


# --- Link público de assinatura (S-15) ---


class TokenDeAssinaturaSerializer(serializers.Serializer[Any]):
    token = serializers.CharField(max_length=100)


class AssinarSerializer(TokenDeAssinaturaSerializer):
    aceite = serializers.BooleanField()
    nome_completo = serializers.CharField(max_length=150)

    def validate_aceite(self, valor: bool) -> bool:
        if not valor:
            raise serializers.ValidationError("Marque que leu e aceita o contrato.")
        return valor


class EmpresaDaAssinaturaSerializer(serializers.Serializer[Any]):
    nome_exibicao = serializers.CharField()
    logo_url = serializers.CharField(allow_null=True)
    cor_marca = serializers.CharField(allow_null=True)


class ContratoDaAssinaturaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    titulo = serializers.CharField()
    cliente_nome = serializers.CharField()
    pdf_url = serializers.CharField(allow_null=True)
    pdf_url_expira_em = serializers.DateTimeField(allow_null=True)
    status = serializers.ChoiceField(choices=StatusContrato.choices)


class ConsultaDaAssinaturaSerializer(serializers.Serializer[Any]):
    empresa = EmpresaDaAssinaturaSerializer()
    contrato = ContratoDaAssinaturaSerializer()


class AssinaturaFeitaSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=StatusContrato.choices)
    assinado_em = serializers.DateTimeField()
