"""Entrada e formato de resposta de vistorias (docs/api/vistorias.md).

As regras ficam no serviço; aqui só a forma. Os campos `_centavos` são opcionais porque o
vistoriador nunca os recebe.
"""

from typing import Any

from rest_framework import serializers

from ..models import Combustivel, PosicaoFoto

# --- Entrada ---


class CriarVistoriaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=[("saida", "Saída")])


class RespostaItemSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField(max_length=40)
    ok = serializers.BooleanField(allow_null=True)
    observacao = serializers.CharField(
        max_length=300, required=False, allow_null=True, allow_blank=True
    )


class EditarVistoriaSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    combustivel = serializers.ChoiceField(
        choices=Combustivel.choices, required=False, allow_null=True
    )
    itens = RespostaItemSerializer(many=True, required=False)
    observacoes = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )


class FotoEntradaSerializer(serializers.Serializer[Any]):
    posicao = serializers.ChoiceField(choices=PosicaoFoto.choices)
    arquivo = serializers.FileField()


class AvariaEntradaSerializer(serializers.Serializer[Any]):
    descricao = serializers.CharField(max_length=200)
    foto_id = serializers.IntegerField()
    vai_para_oficina = serializers.BooleanField(required=False, default=False)
    valor_centavos = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class CorrigirVistoriaSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=500)


# --- Saída ---


class LocacaoDaVistoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()


class ResponsavelVistoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class VeiculoDaVistoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    modelo = serializers.CharField()
    ano = serializers.IntegerField(required=False)


class ClienteDaVistoriaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    cnh = serializers.CharField(allow_null=True, required=False)


class LeituraKmSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField()
    em = serializers.DateField()


class FotoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    posicao = serializers.ChoiceField(choices=PosicaoFoto.choices)
    tirada_em = serializers.DateTimeField()
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class FotosObrigatoriasSerializer(serializers.Serializer[Any]):
    feitas = serializers.IntegerField()
    total = serializers.IntegerField()
    faltam = serializers.ListField(child=serializers.CharField())


class ItemVistoriaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    ok = serializers.BooleanField(allow_null=True)
    observacao = serializers.CharField(allow_null=True)


class AvariaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    descricao = serializers.CharField()
    preexistente = serializers.BooleanField()
    foto_id = serializers.IntegerField(allow_null=True)
    vai_para_oficina = serializers.BooleanField()
    valor_centavos = serializers.IntegerField(allow_null=True, required=False)
    origem = serializers.CharField(allow_null=True)


class ResumoLocacaoSerializer(serializers.Serializer[Any]):
    periodicidade = serializers.CharField()
    inicio = serializers.DateTimeField()
    fim_previsto = serializers.DateTimeField()
    km_livre = serializers.BooleanField()
    diaria_centavos = serializers.IntegerField(required=False)
    caucao_centavos = serializers.IntegerField(required=False)
    caucao_paga = serializers.BooleanField()


class VistoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    status = serializers.CharField()
    locacao = LocacaoDaVistoriaSerializer()
    veiculo = VeiculoDaVistoriaSerializer()
    cliente = ClienteDaVistoriaSerializer()
    km = serializers.IntegerField(allow_null=True)
    km_ultima_leitura = LeituraKmSerializer()
    combustivel = serializers.ChoiceField(choices=Combustivel.choices, allow_null=True)
    fotos = FotoSerializer(many=True)
    fotos_obrigatorias = FotosObrigatoriasSerializer()
    itens = ItemVistoriaSerializer(many=True)
    avarias = AvariaSerializer(many=True)
    observacoes = serializers.CharField(allow_null=True)
    responsavel = ResponsavelVistoriaSerializer(allow_null=True)
    concluida_em = serializers.DateTimeField(allow_null=True)
    substitui = serializers.IntegerField(allow_null=True)
    motivo_correcao = serializers.CharField(allow_null=True)
    vigente = serializers.BooleanField()
    pendencias = serializers.ListField(child=serializers.CharField())
    pode_concluir = serializers.BooleanField()
    resumo_locacao = ResumoLocacaoSerializer()


class AvariaAbertaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    descricao = serializers.CharField()
    veiculo = VeiculoDaVistoriaSerializer()
    locacao = LocacaoDaVistoriaSerializer()
    registrada_em = serializers.DateTimeField(allow_null=True)
    foto = FotoSerializer(allow_null=True)
    vai_para_oficina = serializers.BooleanField()
    valor_centavos = serializers.IntegerField(allow_null=True, required=False)


class ListaDeAvariasSerializer(serializers.Serializer[Any]):
    resultados = AvariaAbertaSerializer(many=True)


class SituacaoAgendaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField(help_text="agendada, hoje, em_andamento, atrasada, concluida")
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class AcaoAgendaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField(help_text="iniciar, continuar, abrir")
    rotulo = serializers.CharField()


class ClienteDaAgendaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()


class ItemAgendaSerializer(serializers.Serializer[Any]):
    id = serializers.CharField()
    tipo = serializers.CharField(help_text="saida, devolucao")
    horario = serializers.DateTimeField()
    veiculo = VeiculoDaVistoriaSerializer()
    cliente = ClienteDaAgendaSerializer()
    locacao = LocacaoDaVistoriaSerializer()
    situacao = SituacaoAgendaSerializer()
    vistoria_id = serializers.IntegerField(allow_null=True)
    acao = AcaoAgendaSerializer()


class ProximaAgendaSerializer(serializers.Serializer[Any]):
    item_id = serializers.CharField()
    em_minutos = serializers.IntegerField()


class AgendaSerializer(serializers.Serializer[Any]):
    resumo = serializers.CharField()
    proxima = ProximaAgendaSerializer(allow_null=True)
    avarias_abertas = serializers.IntegerField()
    resultados = ItemAgendaSerializer(many=True)
