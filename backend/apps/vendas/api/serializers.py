"""Entrada e saída das vendas (`docs/api/vendas.md`). Na T-420, só a venda da quitação."""

from typing import Any

from rest_framework import serializers

from ..models import OrigemVenda, StatusVenda


class RefDaVendaSerializer(serializers.Serializer[Any]):
    class Meta:
        ref_name = "RefDaVenda"

    id = serializers.IntegerField()
    nome = serializers.CharField()


class VeiculoDaVendaSerializer(serializers.Serializer[Any]):
    class Meta:
        ref_name = "VeiculoDaVenda"

    id = serializers.IntegerField()
    placa = serializers.CharField()
    modelo = serializers.CharField()


class LocacaoDaVendaSerializer(serializers.Serializer[Any]):
    class Meta:
        ref_name = "LocacaoDaVenda"

    id = serializers.IntegerField()
    codigo = serializers.CharField()


class TransferenciaSerializer(serializers.Serializer[Any]):
    feita_em = serializers.DateField(allow_null=True)
    registrada_por = RefDaVendaSerializer(allow_null=True)
    pendente = serializers.BooleanField()


class AcoesDaVendaSerializer(serializers.Serializer[Any]):
    cancelar = serializers.BooleanField()
    registrar_transferencia = serializers.BooleanField()


class VendaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.ChoiceField(choices=StatusVenda.choices)
    origem = serializers.ChoiceField(choices=OrigemVenda.choices)
    origem_rotulo = serializers.CharField()
    descricao = serializers.CharField()
    cliente = RefDaVendaSerializer()
    veiculo = VeiculoDaVendaSerializer()
    filial = RefDaVendaSerializer()
    vendedor = RefDaVendaSerializer(allow_null=True)
    locacao = LocacaoDaVendaSerializer(allow_null=True)
    preco_final_centavos = serializers.IntegerField()
    vendida_em = serializers.DateTimeField(allow_null=True)
    transferencia = TransferenciaSerializer()
    acoes = AcoesDaVendaSerializer()


class ListaDeVendasSerializer(serializers.Serializer[Any]):
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
    resultados = VendaSerializer(many=True)


class TransferenciaEntradaSerializer(serializers.Serializer[Any]):
    feita_em = serializers.DateField()
