"""Forma da marca (`docs/api/empresas.md`)."""

from typing import Any

from rest_framework import serializers


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
