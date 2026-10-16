"""Entrada e saída das movimentações (docs/api/movimentacoes.md). Os campos `_centavos` são
opcionais na saída porque o vistoriador os recebe ausentes (USR-09)."""

from typing import Any

from rest_framework import serializers

from apps.financeiro.models import CategoriaDespesa

from ..models import Combustivel, PosicaoFoto, StatusMovimentacao, TipoLocal

ABERTAS_DO_QUADRO = ["agendada", "em_transito", "no_local", "concluida"]


class RefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class VeiculoRefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    modelo = serializers.CharField()
    status = serializers.CharField()


class LocalSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    tipo = serializers.ChoiceField(choices=TipoLocal.choices)
    ativo = serializers.BooleanField()


class DespesaDaParadaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.CharField()
    sem_nota = serializers.BooleanField()


class ParadaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    ordem = serializers.IntegerField()
    local = LocalSerializer()
    servico = serializers.CharField()
    categoria = serializers.ChoiceField(choices=CategoriaDespesa.choices)
    valor_previsto_centavos = serializers.IntegerField(required=False)
    chegou_em = serializers.DateTimeField(allow_null=True)
    saiu_em = serializers.DateTimeField(allow_null=True)
    valor_pago_centavos = serializers.IntegerField(allow_null=True, required=False)
    despesa = DespesaDaParadaSerializer(allow_null=True)


class FotoSerializer(serializers.Serializer[Any]):
    posicao = serializers.ChoiceField(choices=PosicaoFoto.choices)
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class ChegadaSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField()
    combustivel = serializers.ChoiceField(choices=Combustivel.choices, allow_null=True)
    recebido_por = RefSerializer(allow_null=True)
    fotos = FotoSerializer(many=True)


class AcoesSerializer(serializers.Serializer[Any]):
    editar = serializers.BooleanField()
    iniciar = serializers.BooleanField()
    cancelar = serializers.BooleanField()
    chegar_parada = serializers.BooleanField()
    sair_parada = serializers.BooleanField()
    registrar_chegada = serializers.BooleanField()


class _BaseSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.ChoiceField(choices=StatusMovimentacao.choices)
    veiculo = VeiculoRefSerializer()
    filial_saida = RefSerializer()
    destino = RefSerializer()
    transferencia = serializers.BooleanField()
    categoria_destino = RefSerializer(allow_null=True)
    rota = serializers.CharField()
    levado_por = RefSerializer()
    agendada_para = serializers.DateTimeField(allow_null=True)
    iniciada_em = serializers.DateTimeField(allow_null=True)
    concluida_em = serializers.DateTimeField(allow_null=True)
    duracao_minutos = serializers.IntegerField(allow_null=True)
    vistoria_rapida = serializers.BooleanField()
    km_saida = serializers.IntegerField(allow_null=True)
    cancelada_em = serializers.DateTimeField(allow_null=True)
    motivo_cancelamento = serializers.CharField(allow_null=True)
    proxima_etapa = serializers.CharField(allow_null=True)
    custo_centavos = serializers.IntegerField(required=False)
    acoes = AcoesSerializer()


class MovimentacaoSerializer(_BaseSerializer):
    paradas = ParadaSerializer(many=True)
    fotos_chegada = FotoSerializer(many=True)
    chegada = ChegadaSerializer(allow_null=True)


class LinhaSerializer(_BaseSerializer):
    paradas_total = serializers.IntegerField()
    resumo = serializers.CharField()


class ColunaSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=ABERTAS_DO_QUADRO)
    rotulo = serializers.CharField()
    total = serializers.IntegerField()
    itens = LinhaSerializer(many=True)


class QuadroSerializer(serializers.Serializer[Any]):
    colunas = ColunaSerializer(many=True)


class ListaSerializer(serializers.Serializer[Any]):
    resultados = LinhaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class NovaParadaSerializer(serializers.Serializer[Any]):
    local_id = serializers.IntegerField()
    servico = serializers.CharField(max_length=80)
    valor_previsto_centavos = serializers.IntegerField(min_value=0, required=False, default=0)
    categoria = serializers.ChoiceField(
        choices=CategoriaDespesa.choices, required=False, allow_null=True
    )


class EdicaoSerializer(serializers.Serializer[Any]):
    paradas = NovaParadaSerializer(many=True, required=False, default=list)
    destino_filial_id = serializers.IntegerField()
    categoria_destino_id = serializers.IntegerField(required=False, allow_null=True)
    levado_por_id = serializers.IntegerField()
    agendada_para = serializers.DateTimeField(required=False, allow_null=True)
    vistoria_rapida = serializers.BooleanField(required=False, default=False)


class NovaMovimentacaoSerializer(EdicaoSerializer):
    veiculo_id = serializers.IntegerField()
    sair_agora = serializers.BooleanField(required=False, default=False)


class CancelarSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=200)


class SaidaDaParadaSerializer(serializers.Serializer[Any]):
    valor_pago_centavos = serializers.IntegerField(min_value=0)
    nota = serializers.FileField(required=False, allow_null=True)


class FotoEntradaSerializer(serializers.Serializer[Any]):
    posicao = serializers.ChoiceField(choices=PosicaoFoto.choices)
    arquivo = serializers.FileField()


class ChegadaEntradaSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0)
    combustivel = serializers.ChoiceField(
        choices=Combustivel.choices, required=False, allow_null=True
    )
    recebido_por_id = serializers.IntegerField(required=False, allow_null=True)


class PessoaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    perfil = serializers.CharField()
    perfil_rotulo = serializers.CharField()
    eu = serializers.BooleanField()


class PessoasSerializer(serializers.Serializer[Any]):
    resultados = PessoaSerializer(many=True)


class ListaDeLocaisSerializer(serializers.Serializer[Any]):
    resultados = LocalSerializer(many=True)


class NovoLocalSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=80)
    tipo = serializers.ChoiceField(choices=TipoLocal.choices)
