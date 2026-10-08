"""Entrada e formato de resposta das filiais (docs/api/filiais.md).

As regras (CNPJ, CEP, UF, horário, nome único) são conferidas no serviço; aqui só a forma.
"""

from typing import Any

from rest_framework import serializers

from ..models import FeriadoFilial


class EnderecoSerializer(serializers.Serializer[Any]):
    cep = serializers.CharField()
    logradouro = serializers.CharField()
    numero = serializers.CharField()
    complemento = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    bairro = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()


class ContatoSerializer(serializers.Serializer[Any]):
    telefone = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    whatsapp = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    email = serializers.EmailField(allow_null=True, allow_blank=True, required=False)


class IntervaloSerializer(serializers.Serializer[Any]):
    abre = serializers.CharField()
    fecha = serializers.CharField()


class HorarioSerializer(serializers.Serializer[Any]):
    seg = IntervaloSerializer(many=True)
    ter = IntervaloSerializer(many=True)
    qua = IntervaloSerializer(many=True)
    qui = IntervaloSerializer(many=True)
    sex = IntervaloSerializer(many=True)
    sab = IntervaloSerializer(many=True)
    dom = IntervaloSerializer(many=True)


class FilialEntradaSerializer(serializers.Serializer[Any]):
    """Forma do corpo. O horário vai como veio para o serviço validar (7 dias, intervalos)."""

    nome = serializers.CharField(max_length=80)
    matriz = serializers.BooleanField(required=False)
    cnpj = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    inscricao_estadual = serializers.CharField(
        allow_null=True, allow_blank=True, required=False, max_length=20
    )
    inscricao_municipal = serializers.CharField(
        allow_null=True, allow_blank=True, required=False, max_length=20
    )
    endereco = EnderecoSerializer()
    contato = ContatoSerializer(required=False, allow_null=True)
    preco_litro_centavos = serializers.IntegerField(allow_null=True, required=False, min_value=0)
    horario = serializers.JSONField()


class MotivoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField()


class FeriadoEntradaSerializer(serializers.Serializer[Any]):
    data = serializers.DateField()  # type: ignore[assignment]
    nome = serializers.CharField(max_length=80)
    origem = serializers.ChoiceField(choices=FeriadoFilial.Origem.choices)


class FeriadosEntradaSerializer(serializers.Serializer[Any]):
    feriados = FeriadoEntradaSerializer(many=True)


# --- Respostas (OpenAPI) ---


class GerenteSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class FeriadoProximoSerializer(serializers.Serializer[Any]):
    data = serializers.DateField()  # type: ignore[assignment]
    nome = serializers.CharField()


class FilialSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    matriz = serializers.BooleanField()
    ativo = serializers.BooleanField()
    cnpj = serializers.CharField(allow_null=True)
    inscricao_estadual = serializers.CharField(allow_null=True)
    inscricao_municipal = serializers.CharField(allow_null=True)
    endereco = EnderecoSerializer()
    contato = ContatoSerializer()
    preco_litro_centavos = serializers.IntegerField(allow_null=True)
    horario = HorarioSerializer()
    horario_resumo = serializers.CharField()
    endereco_resumo = serializers.CharField()
    gerentes = GerenteSerializer(many=True)
    feriados_proximos = FeriadoProximoSerializer(many=True)
    feriados_ano_seguinte_pendentes = serializers.BooleanField()
    criado_em = serializers.DateTimeField()


class IndicadoresSerializer(serializers.Serializer[Any]):
    veiculos = serializers.IntegerField(allow_null=True)
    locacoes_ativas = serializers.IntegerField(allow_null=True)
    usuarios = serializers.IntegerField(allow_null=True)
    ocupacao_pct = serializers.CharField(allow_null=True)


class FilialNaListaSerializer(FilialSerializer):
    indicadores = IndicadoresSerializer()


class PlanoDasFiliaisSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField(allow_null=True)
    aviso = serializers.BooleanField()
    bloqueado = serializers.BooleanField()
    nome_plano = serializers.CharField()


class ListaDeFiliaisSerializer(serializers.Serializer[Any]):
    plano = PlanoDasFiliaisSerializer()
    resultados = FilialNaListaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class MinhaFilialSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    matriz = serializers.BooleanField()
    cidade = serializers.CharField()
    uf = serializers.CharField()


class MinhasFiliaisSerializer(serializers.Serializer[Any]):
    pode_escolher_todas = serializers.BooleanField()
    resultados = MinhaFilialSerializer(many=True)


class FeriadoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    data = serializers.DateField()  # type: ignore[assignment]
    nome = serializers.CharField()
    origem = serializers.CharField()


class ListaDeFeriadosSerializer(serializers.Serializer[Any]):
    resultados = FeriadoSerializer(many=True)


class SugestaoSerializer(serializers.Serializer[Any]):
    data = serializers.DateField()  # type: ignore[assignment]
    nome = serializers.CharField()
    ja_cadastrado = serializers.BooleanField()


class ListaDeSugestoesSerializer(serializers.Serializer[Any]):
    resultados = SugestaoSerializer(many=True)


class CepSerializer(serializers.Serializer[Any]):
    cep = serializers.CharField()
    logradouro = serializers.CharField()
    bairro = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()
