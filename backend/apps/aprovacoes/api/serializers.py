"""Entrada e formato de resposta das aprovações (docs/api/aprovacoes.md)."""

from typing import Any

from rest_framework import serializers

from ..models import OrigemPedido, PedidoAprovacao, TipoPedido


class AprovarSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=300)


class RecusarSerializer(serializers.Serializer[Any]):
    """Recusar exige motivo (APR-07)."""

    motivo = serializers.CharField(max_length=300)


class ResumoIdNomeSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class OrigemSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=OrigemPedido.choices)
    id = serializers.IntegerField()
    codigo = serializers.CharField(allow_null=True)


class PedidoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoPedido.choices)
    status = serializers.ChoiceField(choices=PedidoAprovacao.Status.choices)
    titulo = serializers.CharField()
    detalhe = serializers.CharField()
    origem = OrigemSerializer()
    filial = ResumoIdNomeSerializer()
    solicitante = ResumoIdNomeSerializer()
    pedido_em = serializers.DateTimeField()
    motivo_pedido = serializers.CharField(allow_null=True)
    valor_centavos = serializers.IntegerField(allow_null=True)
    pct = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    decidido_por = ResumoIdNomeSerializer(allow_null=True)
    decidido_em = serializers.DateTimeField(allow_null=True)
    motivo_recusa = serializers.CharField(allow_null=True)
    pode_decidir = serializers.BooleanField()
    proprio_pedido = serializers.BooleanField()


class ContagensDePedidosSerializer(serializers.Serializer[Any]):
    pendente = serializers.IntegerField()


class ListaDePedidosSerializer(serializers.Serializer[Any]):
    contagens = ContagensDePedidosSerializer()
    resultados = PedidoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
