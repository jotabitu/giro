"""Entrada e formato de resposta de vistorias (docs/api/vistorias.md).

As regras ficam no serviço; aqui só a forma. Os campos `_centavos` são opcionais porque o
vistoriador nunca os recebe.
"""

from typing import Any

from rest_framework import serializers

from ..models import Combustivel, FormaDevolucao, PosicaoFoto, TipoItemAcerto

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


class TrocarVeiculoSerializer(serializers.Serializer[Any]):
    veiculo_novo_id = serializers.IntegerField()
    motivo = serializers.CharField(max_length=500)


class TrocaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.CharField()
    devolucao_vistoria_id = serializers.IntegerField(allow_null=True)
    saida_vistoria_id = serializers.IntegerField(allow_null=True)


class TrocaPedidaSerializer(serializers.Serializer[Any]):
    troca = TrocaSerializer()


class CancelarTrocaSerializer(serializers.Serializer[Any]):
    # Vazio, o serviço responde com a mensagem do contrato (LOC-09).
    motivo = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class PecaDaTrocaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.CharField()


class TrocaCanceladaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.CharField()
    cancelada_em = serializers.DateTimeField()
    saida_vistoria = PecaDaTrocaSerializer(allow_null=True)
    devolucao_vistoria = PecaDaTrocaSerializer(allow_null=True)
    conta_caucao = PecaDaTrocaSerializer(allow_null=True)
    devolucao_id = serializers.IntegerField(allow_null=True)


class TrocaCanceladaRespostaSerializer(serializers.Serializer[Any]):
    troca = TrocaCanceladaSerializer()


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
    """USR-09: o que o vistoriador vê do cliente, vindo com a vistoria."""

    nome = serializers.CharField()
    celular = serializers.CharField()
    cnh = serializers.CharField(allow_null=True, required=False)
    retirada_liberada = serializers.BooleanField(
        allow_null=True,
        help_text="Na saída, se a retirada está liberada (CLI-02, CLI-03, CLI-05); "
        "`null` na devolução.",
    )


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


# --- Devolução e acerto ---


class ItemAcertoEntradaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoItemAcerto.choices)
    descricao = serializers.CharField(max_length=200)
    valor_centavos = serializers.IntegerField(min_value=0)


class EditarItemAcertoSerializer(serializers.Serializer[Any]):
    descricao = serializers.CharField(max_length=200, required=False)
    valor_centavos = serializers.IntegerField(min_value=0, required=False)


class FormaDevolucaoSerializer(serializers.Serializer[Any]):
    forma_devolucao = serializers.ChoiceField(choices=FormaDevolucao.choices)


class LocacaoDaDevolucaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.CharField()
    cliente = serializers.CharField()
    veiculo = serializers.CharField()
    no_horario = serializers.BooleanField()


class KmComparadoSerializer(serializers.Serializer[Any]):
    saida = serializers.IntegerField(allow_null=True)
    agora = serializers.IntegerField(allow_null=True)
    rodou = serializers.IntegerField(allow_null=True)
    texto = serializers.CharField()


class CombustivelComparadoSerializer(serializers.Serializer[Any]):
    saida = serializers.CharField(allow_null=True)
    agora = serializers.CharField(allow_null=True)
    faltou = serializers.CharField(allow_null=True)
    litros_faltantes = serializers.CharField(allow_null=True)


class FotoComparadaSerializer(serializers.Serializer[Any]):
    posicao = serializers.CharField()
    saida = FotoSerializer(allow_null=True)
    agora = FotoSerializer(allow_null=True)


class ItemComparadoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    saida = serializers.CharField(allow_null=True)
    agora = serializers.CharField(allow_null=True)
    novo = serializers.BooleanField()


class ComparacaoSerializer(serializers.Serializer[Any]):
    km = KmComparadoSerializer()
    combustivel = CombustivelComparadoSerializer()
    fotos = FotoComparadaSerializer(many=True)
    itens = ItemComparadoSerializer(many=True)


class ItemAcertoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    descricao = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    modo = serializers.CharField(help_text="calculado, informado")
    avaria_id = serializers.IntegerField(allow_null=True)
    conta_id = serializers.IntegerField(allow_null=True)


class ResultadoAcertoSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField(help_text="devolver, cobrar, zerado")
    valor_centavos = serializers.IntegerField()
    texto = serializers.CharField()
    botao = serializers.CharField()


class AvisoAcertoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField(help_text="DEV-07")
    mensagem = serializers.CharField()


class AcertoSerializer(serializers.Serializer[Any]):
    status = serializers.CharField(help_text="rascunho, concluido")
    caucao_centavos = serializers.IntegerField()
    itens = ItemAcertoSerializer(many=True)
    creditos = ItemAcertoSerializer(many=True)
    total_cobrancas_centavos = serializers.IntegerField()
    total_creditos_centavos = serializers.IntegerField()
    saldo_centavos = serializers.IntegerField()
    resultado = ResultadoAcertoSerializer()
    avisos = AvisoAcertoSerializer(
        many=True,
        help_text=(
            "Vazia quando a devolução não é antecipada, já tem a aprovação "
            "ou o acerto está concluído."
        ),
    )
    forma_devolucao = serializers.CharField(allow_null=True)


class DevolucaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.CharField(help_text="rascunho, concluida")
    locacao = LocacaoDaDevolucaoSerializer()
    vistoria = VistoriaSerializer(allow_null=True)
    comparacao = ComparacaoSerializer(allow_null=True)
    acerto = AcertoSerializer(required=False)
    devolvida_em = serializers.DateTimeField(allow_null=True)
    concluida_em = serializers.DateTimeField(allow_null=True)
    recibo_enviado_em = serializers.DateTimeField(allow_null=True)


class ReciboSerializer(serializers.Serializer[Any]):
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()
