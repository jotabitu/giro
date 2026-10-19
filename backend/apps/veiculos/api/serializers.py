"""Entrada e formato de resposta de veículos, categorias, preços e extras (docs/api/veiculos.md).

As regras (placa, chassi, categoria da filial, unicidade, transições) são conferidas no
serviço; aqui só a forma.
"""

from typing import Any

from rest_framework import serializers

from ..models import Extra, StatusVeiculo, TipoDocumento, TipoVeiculo
from ..services import MOTIVOS_DE_BAIXA

# --- Entrada ---


class VeiculoEntradaSerializer(serializers.Serializer[Any]):
    placa = serializers.CharField(max_length=10)
    chassi = serializers.CharField(max_length=20)
    renavam = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    marca = serializers.CharField(max_length=40)
    modelo = serializers.CharField(max_length=60)
    ano_fabricacao = serializers.IntegerField()
    ano_modelo = serializers.IntegerField()
    cor = serializers.CharField(max_length=30)
    km_atual = serializers.IntegerField(min_value=0, required=False)
    categoria_id = serializers.IntegerField()
    filial_id = serializers.IntegerField()
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, required=False, allow_null=True, min_value=0
    )
    valor_compra_centavos = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    data_compra = serializers.DateField(required=False, allow_null=True)
    entrou_na_frota_em = serializers.DateField(required=False)


class VeiculoEdicaoSerializer(serializers.Serializer[Any]):
    renavam = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    marca = serializers.CharField(max_length=40, required=False)
    modelo = serializers.CharField(max_length=60, required=False)
    ano_fabricacao = serializers.IntegerField(required=False)
    ano_modelo = serializers.IntegerField(required=False)
    cor = serializers.CharField(max_length=30, required=False)
    categoria_id = serializers.IntegerField(required=False)
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, required=False, allow_null=True, min_value=0
    )
    valor_compra_centavos = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    data_compra = serializers.DateField(required=False, allow_null=True)


class CorrigirIdentificacaoSerializer(serializers.Serializer[Any]):
    placa = serializers.CharField(max_length=10, required=False)
    chassi = serializers.CharField(max_length=20, required=False)
    motivo = serializers.CharField()


class BloquearVeiculoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField()


class DesbloquearVeiculoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(required=False, allow_blank=True)


class ColocarAVendaSerializer(serializers.Serializer[Any]):
    valor_venda_centavos = serializers.IntegerField(min_value=1)
    referencia_fipe_centavos = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )


class BaixarSerializer(serializers.Serializer[Any]):
    motivo = serializers.ChoiceField(choices=list(MOTIVOS_DE_BAIXA))
    descricao = serializers.CharField(required=False, allow_blank=True, default="")


class KmSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0)


class CorrigirKmSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0)
    motivo = serializers.CharField()


class PrecoEntradaSerializer(serializers.Serializer[Any]):
    diaria_centavos = serializers.IntegerField(min_value=0)
    semanal_centavos = serializers.IntegerField(min_value=0)
    mensal_centavos = serializers.IntegerField(min_value=0)
    caucao_centavos = serializers.IntegerField(min_value=0)


class NovoPrecoSerializer(PrecoEntradaSerializer):
    vigente_desde = serializers.DateField(required=False)


class CategoriaEntradaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60)
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    filial_id = serializers.IntegerField(required=False, allow_null=True)
    preco = PrecoEntradaSerializer()


class CategoriaEdicaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60, required=False)
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices, required=False)
    filial_id = serializers.IntegerField(required=False, allow_null=True)


class ExtraEntradaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60)
    valor_centavos = serializers.IntegerField(min_value=0)
    cobranca = serializers.ChoiceField(choices=Extra.Cobranca.choices)


# --- Respostas (OpenAPI) ---


class IdNomeSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class PrecoSerializer(serializers.Serializer[Any]):
    diaria_centavos = serializers.IntegerField()
    semanal_centavos = serializers.IntegerField()
    mensal_centavos = serializers.IntegerField()
    caucao_centavos = serializers.IntegerField()


class PrecoComDataSerializer(PrecoSerializer):
    vigente_desde = serializers.DateField()


class SituacaoDoVeiculoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class AcoesDoVeiculoSerializer(serializers.Serializer[Any]):
    editar = serializers.BooleanField()
    colocar_a_venda = serializers.BooleanField()
    voltar_para_frota = serializers.BooleanField()
    bloquear = serializers.BooleanField()
    desbloquear = serializers.BooleanField()
    transferir = serializers.BooleanField()
    baixar = serializers.BooleanField()
    registrar_km = serializers.BooleanField()
    corrigir_km = serializers.BooleanField()
    movimentar = serializers.BooleanField()  # MOV-02, MOV-03
    motivo_movimentar = serializers.CharField(allow_null=True)
    aviso_baixar = serializers.CharField(allow_null=True)  # MOV-03 (T-311)


class MovimentacaoAbertaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.ChoiceField(choices=["agendada", "em_transito", "no_local"])
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class VeiculoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    chassi = serializers.CharField()
    renavam = serializers.CharField(allow_null=True)
    marca = serializers.CharField()
    modelo = serializers.CharField()
    ano_fabricacao = serializers.IntegerField()
    ano_modelo = serializers.IntegerField()
    cor = serializers.CharField()
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    categoria = IdNomeSerializer()
    filial = IdNomeSerializer()
    status = serializers.ChoiceField(choices=StatusVeiculo.choices)
    motivo_status = serializers.CharField(allow_null=True)
    km_atual = serializers.IntegerField()
    km_atualizado_em = serializers.DateTimeField(allow_null=True)
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, allow_null=True
    )
    # Ausentes para o vistoriador, que não vê valores (D-25, USR-09).
    preco_vigente = PrecoSerializer(allow_null=True, required=False)
    valor_venda_centavos = serializers.IntegerField(allow_null=True, required=False)
    referencia_fipe_centavos = serializers.IntegerField(allow_null=True, required=False)
    valor_compra_centavos = serializers.IntegerField(allow_null=True, required=False)
    data_compra = serializers.DateField(allow_null=True, required=False)
    entrou_na_frota_em = serializers.DateField()
    situacao = SituacaoDoVeiculoSerializer()
    locacao_atual = serializers.JSONField(allow_null=True)
    manutencao = serializers.JSONField(allow_null=True)
    documentos_resumo = serializers.JSONField(allow_null=True)
    movimentacao_aberta = MovimentacaoAbertaSerializer(allow_null=True)  # MOV-03
    acoes = AcoesDoVeiculoSerializer()


class OcupacaoSerializer(serializers.Serializer[Any]):
    pct = serializers.CharField()
    periodo_dias = serializers.IntegerField()


class HistoricoStatusSerializer(serializers.Serializer[Any]):
    de = serializers.CharField(allow_null=True)
    para = serializers.CharField()
    em = serializers.DateTimeField()
    origem_tipo = serializers.CharField()
    origem_codigo = serializers.CharField(allow_null=True)
    motivo = serializers.CharField(allow_null=True)


class FotoDaVistoriaRecenteSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    posicao = serializers.ChoiceField(
        choices=["frente", "traseira", "lado_esquerdo", "lado_direito", "painel"]
    )
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class AvariaDaVistoriaRecenteSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    descricao = serializers.CharField()
    registrada_em = serializers.DateTimeField()
    preexistente = serializers.BooleanField()
    locacao_codigo = serializers.CharField(allow_null=True)
    foto_id = serializers.IntegerField(allow_null=True)


class VistoriaRecenteSerializer(serializers.Serializer[Any]):
    """VIS-01, T-275: a última vistoria concluída, com as fotos fixas e as avarias abertas."""

    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=["saida", "devolucao"])
    concluida_em = serializers.DateTimeField()
    vistoriador = IdNomeSerializer(allow_null=True)
    locacao_codigo = serializers.CharField(allow_null=True)
    total_fotos = serializers.IntegerField()
    fotos = FotoDaVistoriaRecenteSerializer(many=True)
    avarias = AvariaDaVistoriaRecenteSerializer(many=True)


class VeiculoDetalheSerializer(VeiculoSerializer):
    # Só para administrador, gerente e financeiro; ausente para os demais (USR-09, T-156).
    indicadores_financeiros = serializers.JSONField(allow_null=True, required=False)
    # Ausente para vistoriador e financeiro (T-275).
    movimentacoes = serializers.JSONField(allow_null=True, required=False)
    # Ausente para o financeiro; `null` se o veículo nunca teve vistoria (T-275).
    vistoria_recente = VistoriaRecenteSerializer(allow_null=True, required=False)
    ocupacao = OcupacaoSerializer()
    historico_status = HistoricoStatusSerializer(many=True)

    def to_representation(self, instance: Any) -> Any:
        dados = super().to_representation(instance)
        # O campo com allow_null viraria `null` quando a chave falta; aqui ela some.
        for chave in ("indicadores_financeiros", "movimentacoes", "vistoria_recente"):
            if chave not in instance:
                dados.pop(chave, None)
        return dados


class ContagensDaFrotaSerializer(serializers.Serializer[Any]):
    todos = serializers.IntegerField()
    disponivel = serializers.IntegerField()
    alugado = serializers.IntegerField()
    reservado = serializers.IntegerField()
    em_manutencao = serializers.IntegerField()
    a_venda = serializers.IntegerField()
    indisponivel = serializers.IntegerField()
    em_movimentacao = serializers.IntegerField()
    motos = serializers.IntegerField()
    carros = serializers.IntegerField()


class ListaDeVeiculosSerializer(serializers.Serializer[Any]):
    contagens = ContagensDaFrotaSerializer()
    resultados = VeiculoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class CategoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    filial = IdNomeSerializer(allow_null=True)
    ativo = serializers.BooleanField()
    modelos_resumo = serializers.CharField()
    veiculos = serializers.IntegerField()
    # Ausentes para o vistoriador (D-25, USR-09).
    preco_vigente = PrecoComDataSerializer(allow_null=True, required=False)
    proximo_preco = PrecoComDataSerializer(allow_null=True, required=False)


class ListaDeCategoriasSerializer(serializers.Serializer[Any]):
    resultados = CategoriaSerializer(many=True)


class PrecoHistoricoSerializer(PrecoComDataSerializer):
    alterado_por = serializers.CharField(allow_null=True)
    alterado_em = serializers.DateTimeField()


class ListaDePrecosSerializer(serializers.Serializer[Any]):
    resultados = PrecoHistoricoSerializer(many=True)


class PrecoCriadoSerializer(PrecoHistoricoSerializer):
    locacoes_em_andamento_mantidas = serializers.IntegerField()


class MudancaDePrecoSerializer(serializers.Serializer[Any]):
    categoria = IdNomeSerializer()
    vigente_desde = serializers.DateField()
    campo = serializers.CharField()
    antes_centavos = serializers.IntegerField(allow_null=True)
    depois_centavos = serializers.IntegerField()
    alterado_por = serializers.CharField(allow_null=True)
    alterado_em = serializers.DateTimeField()


class ListaDeMudancasDePrecoSerializer(serializers.Serializer[Any]):
    resultados = MudancaDePrecoSerializer(many=True)


class ExtraSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    cobranca = serializers.ChoiceField(choices=Extra.Cobranca.choices)
    ativo = serializers.BooleanField()


class ListaDeExtrasSerializer(serializers.Serializer[Any]):
    resultados = ExtraSerializer(many=True)


class ModeloSerializer(serializers.Serializer[Any]):
    marca = serializers.CharField()
    modelo = serializers.CharField()
    tipo = serializers.ChoiceField(choices=["moto", "carro"])

    class Meta:
        # Nome próprio no OpenAPI: `contratos` já tem um `Modelo` (T-265).
        ref_name = "ModeloDoCatalogo"


class ListaDeModelosSerializer(serializers.Serializer[Any]):
    resultados = ModeloSerializer(many=True)

    class Meta:
        # Nome próprio no OpenAPI: `contratos` já tem um `ListaDeModelos` (T-265).
        ref_name = "ListaDeModelosDoCatalogo"


class FiltroDeModelosSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["moto", "carro"], required=False)
    marca = serializers.CharField(required=False, allow_blank=True, max_length=100)
    busca = serializers.CharField(required=False, allow_blank=True, max_length=100)


class PedidoRefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    status = serializers.CharField()


class PedidoAprovacaoCriadoSerializer(serializers.Serializer[Any]):
    pedido_aprovacao = PedidoRefSerializer()


# --- Documentos (VEI-03, AUD-05) ---


class DocumentoEntradaSerializer(serializers.Serializer[Any]):
    """`multipart/form-data`. O arquivo é conferido pelo conteúdo no serviço (PDF, JPG ou PNG,
    até 10 MB)."""

    tipo = serializers.ChoiceField(choices=TipoDocumento.choices)
    validade = serializers.DateField()
    arquivo = serializers.FileField(required=False, allow_null=True)


class ArquivoAssinadoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class DocumentoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoDocumento.choices)
    validade = serializers.DateField()
    situacao = serializers.ChoiceField(choices=["em_dia", "vence_em_breve", "vencido"])
    dias_para_vencer = serializers.IntegerField(allow_null=True)
    ativo = serializers.BooleanField()
    arquivo = ArquivoAssinadoSerializer(allow_null=True)


class ListaDeDocumentosSerializer(serializers.Serializer[Any]):
    resultados = DocumentoSerializer(many=True)
