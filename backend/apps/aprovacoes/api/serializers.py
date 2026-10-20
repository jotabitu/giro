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


class CelulaDoResumoSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    valor = serializers.CharField()


class ResumoDoPedidoSerializer(serializers.Serializer[Any]):
    celulas = CelulaDoResumoSerializer(many=True)
    nota = serializers.CharField(allow_null=True)


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
    resumo = ResumoDoPedidoSerializer(
        allow_null=True, help_text="Células prontas do cartão (T-201); `null` antes dela."
    )
    pode_decidir = serializers.BooleanField()
    pode_cancelar = serializers.BooleanField()
    proprio_pedido = serializers.BooleanField()


class ContagensDePedidosSerializer(serializers.Serializer[Any]):
    pendente = serializers.IntegerField()
    aprovado = serializers.IntegerField()
    recusado = serializers.IntegerField()
    minhas_pendentes = serializers.IntegerField()


class EsperandoSerializer(serializers.Serializer[Any]):
    quantidade = serializers.IntegerField()
    mais_antigo_em = serializers.DateTimeField(allow_null=True)
    contexto = serializers.CharField(allow_null=True)


class AprovadasSerializer(serializers.Serializer[Any]):
    titulo = serializers.CharField()
    quantidade = serializers.IntegerField()
    tempo_medio_min = serializers.IntegerField(allow_null=True)
    contexto = serializers.CharField(allow_null=True)


class RecusadasSerializer(serializers.Serializer[Any]):
    titulo = serializers.CharField()
    quantidade = serializers.IntegerField()
    contexto = serializers.CharField()


class DescontosSerializer(serializers.Serializer[Any]):
    titulo = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    contexto = serializers.CharField()


class IndicadoresDePedidosSerializer(serializers.Serializer[Any]):
    """APR-12 (T-201): da tela inteira, não dependem da aba nem do filtro."""

    mes = serializers.CharField()
    esperando = EsperandoSerializer()
    aprovadas = AprovadasSerializer()
    recusadas = RecusadasSerializer()
    descontos = DescontosSerializer()


class ListaDePedidosSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresDePedidosSerializer()
    contagens = ContagensDePedidosSerializer()
    resultados = PedidoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
