"""Forma da marca e do ramo (`docs/api/empresas.md`)."""

from typing import Any

from rest_framework import serializers

from ..models import Atividade, TrabalhaCom


class LogoDaMarcaSerializer(serializers.Serializer[Any]):
    url = serializers.CharField(help_text="Relativa ao host, com a versão na query.")
    largura = serializers.IntegerField(allow_null=True)
    altura = serializers.IntegerField(allow_null=True)


class MarcaSerializer(serializers.Serializer[Any]):
    nome_exibicao = serializers.CharField()
    iniciais = serializers.CharField()
    logo = LogoDaMarcaSerializer(allow_null=True)
    cor = serializers.CharField()
    cor_sobre = serializers.CharField()
    cor_suave = serializers.CharField()
    cor_suave_escuro = serializers.CharField()
    personalizada = serializers.BooleanField()
    versao = serializers.CharField()


class AtividadeDoRamoSerializer(serializers.Serializer[Any]):
    valor = serializers.ChoiceField(choices=["aluga", "vende"])
    titulo = serializers.CharField()
    descricao = serializers.CharField()
    aviso = serializers.CharField(allow_null=True)


class TipoDoRamoSerializer(serializers.Serializer[Any]):
    valor = serializers.ChoiceField(choices=["motos", "carros"])
    titulo = serializers.CharField()


class RamoSerializer(serializers.Serializer[Any]):
    atividade = serializers.ChoiceField(choices=Atividade.choices)
    trabalha_com = serializers.ChoiceField(choices=TrabalhaCom.choices)
    atividades = AtividadeDoRamoSerializer(many=True)
    atividades_aceitas = serializers.ListField(child=serializers.ChoiceField(Atividade.choices))
    tipos = TipoDoRamoSerializer(many=True)
    modulos = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Por atividade aceita, os módulos que o plano liga (Recurso.label).",
    )


class MudarRamoSerializer(serializers.Serializer[Any]):
    atividade = serializers.ChoiceField(choices=Atividade.choices)
    trabalha_com = serializers.ChoiceField(choices=TrabalhaCom.choices)
