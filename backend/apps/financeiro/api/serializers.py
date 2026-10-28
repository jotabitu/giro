"""Entrada e formato de resposta do financeiro (docs/api/financeiro.md).

As regras ficam no serviço; aqui só a forma. Valores em centavos; a API calcula tudo e a tela
mostra (ADR 0005).
"""

from typing import Any

from rest_framework import serializers

from ..models import CategoriaDespesa, FormaDespesa, TipoCobranca

# --- Entrada ---


class ReceberSerializer(serializers.Serializer[Any]):
    forma = serializers.ChoiceField(
        choices=[
            ("dinheiro", "Dinheiro"),
            ("cartao_debito", "Débito"),
            ("cartao_credito", "Crédito"),
        ]
    )
    valor_centavos = serializers.IntegerField(min_value=1)


class CobrancaEntradaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(
        choices=[(TipoCobranca.PIX, "Pix"), (TipoCobranca.BOLETO, "Boleto")]
    )
    vence_em = serializers.DateField(required=False, allow_null=True)
    no_caixa = serializers.BooleanField(required=False, default=False)


class LoteSerializer(serializers.Serializer[Any]):
    ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=100)


class MotivoFinanceiroSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=200)


class OrigemEntradaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(
        choices=[("locacao", "Locação"), ("venda", "Venda"), ("devolucao", "Devolução")]
    )
    id = serializers.IntegerField()


class LancamentoSerializer(serializers.Serializer[Any]):
    cliente_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(
        choices=[("multa", "Multa"), ("avaria", "Avaria"), ("outro", "Outro")]
    )
    descricao = serializers.CharField(max_length=150)
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField(min_value=1)
    origem = OrigemEntradaSerializer(required=False, allow_null=True)


class ContaNovaSerializer(serializers.Serializer[Any]):
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField(min_value=1)


class RenegociarSerializer(serializers.Serializer[Any]):
    contas = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=50)
    novas = ContaNovaSerializer(many=True, min_length=1, max_length=60)  # type: ignore[call-arg]
    motivo = serializers.CharField(max_length=200)


class AbrirCaixaSerializer(serializers.Serializer[Any]):
    troco_centavos = serializers.IntegerField(min_value=0)


class SangriaSerializer(serializers.Serializer[Any]):
    valor_centavos = serializers.IntegerField(min_value=1)
    descricao = serializers.CharField(max_length=150)


class FecharCaixaSerializer(serializers.Serializer[Any]):
    contado_centavos = serializers.IntegerField(min_value=0)
    motivo_diferenca = serializers.CharField(
        max_length=200, required=False, allow_null=True, allow_blank=True
    )


class DespesaEntradaSerializer(serializers.Serializer[Any]):
    descricao = serializers.CharField(max_length=150)
    valor_centavos = serializers.IntegerField(min_value=1)
    data = serializers.DateField()  # type: ignore[assignment]
    vencimento = serializers.DateField()
    categoria = serializers.ChoiceField(choices=CategoriaDespesa.choices)
    veiculo_id = serializers.IntegerField(required=False, allow_null=True)
    nota = serializers.FileField(
        error_messages={
            "required": "Envie a foto da nota.",
            "null": "Envie a foto da nota.",
            "empty": "Envie a foto da nota.",
            "invalid": "Envie a foto da nota.",
        }
    )  # FIN-06: obrigatória no lançamento por esta rota
    pago_no_caixa = serializers.BooleanField(required=False, default=False)


class PagarDespesaSerializer(serializers.Serializer[Any]):
    forma = serializers.ChoiceField(choices=FormaDespesa.choices)
    pago_em = serializers.DateTimeField()
    comprovante = serializers.FileField(required=False, allow_null=True)


class ComprovanteSerializer(serializers.Serializer[Any]):
    comprovante = serializers.FileField(required=False, allow_null=True)


class ResolverPendenciaSerializer(serializers.Serializer[Any]):
    acao = serializers.ChoiceField(choices=[("baixar", "Baixar"), ("ignorar", "Ignorar")])
    motivo = serializers.CharField(max_length=180)


# --- Resposta ---


class RefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class OrigemDaContaSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    codigo = serializers.CharField(allow_null=True)


class ValorHojeSerializer(serializers.Serializer[Any]):
    data = serializers.DateField()  # type: ignore[assignment]
    dias_atraso = serializers.IntegerField()
    principal_centavos = serializers.IntegerField()
    multa_centavos = serializers.IntegerField()
    juros_centavos = serializers.IntegerField()
    total_centavos = serializers.IntegerField()
    cobra_juros = serializers.BooleanField()


class CobrancaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    vence_em = serializers.DateField()
    pix_copia_e_cola = serializers.CharField(allow_null=True)
    qr_code_url = serializers.CharField(allow_null=True)
    linha_digitavel = serializers.CharField(allow_null=True)
    boleto_url = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class AcoesDaContaSerializer(serializers.Serializer[Any]):
    receber = serializers.BooleanField()
    gerar_pix = serializers.BooleanField()
    gerar_boleto = serializers.BooleanField()
    cobrar = serializers.BooleanField()
    cancelar = serializers.BooleanField()
    renegociar = serializers.BooleanField()
    estornar = serializers.BooleanField()


class ContaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    numero = serializers.IntegerField(allow_null=True)
    total_parcelas = serializers.IntegerField(allow_null=True)
    origem = OrigemDaContaSerializer()
    cliente = RefSerializer()
    filial = RefSerializer()
    veiculo_placa = serializers.CharField(allow_null=True)
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=["aberta", "vence_hoje", "atrasada", "paga", "cancelada", "renegociada"]
    )
    dias_atraso = serializers.IntegerField()
    faixa_atraso = serializers.ChoiceField(choices=["1_7", "8_30", "mais_30"], allow_null=True)
    forma_prevista = serializers.CharField(allow_null=True)
    observacao = serializers.CharField(allow_null=True)
    valor_hoje = ValorHojeSerializer()
    pago_em = serializers.DateTimeField(allow_null=True)
    forma = serializers.CharField(allow_null=True)
    multa_centavos = serializers.IntegerField()
    juros_centavos = serializers.IntegerField()
    estorno_de = serializers.IntegerField(allow_null=True)
    estornada_em = serializers.DateTimeField(allow_null=True)
    cobranca_aberta = CobrancaSerializer(allow_null=True)
    acoes = AcoesDaContaSerializer()


class HistoricoDaContaSerializer(serializers.Serializer[Any]):
    em = serializers.DateTimeField()
    acao = serializers.CharField()
    por = serializers.CharField(allow_null=True)
    motivo = serializers.CharField(allow_null=True)


class ContaDetalheSerializer(ContaSerializer):
    historico = HistoricoDaContaSerializer(many=True)


class FaixasSerializer(serializers.Serializer[Any]):
    def get_fields(self) -> dict[str, Any]:
        return {f: serializers.IntegerField() for f in ("1_7", "8_30", "mais_30")}


class IndicadoresReceberSerializer(serializers.Serializer[Any]):
    previsto_mes_centavos = serializers.IntegerField()
    previsto_mes_parcelas = serializers.IntegerField()
    recebido_mes_centavos = serializers.IntegerField()
    recebido_pct = serializers.CharField(allow_null=True)
    vence_hoje_centavos = serializers.IntegerField()
    vence_hoje_parcelas = serializers.IntegerField()
    em_atraso_centavos = serializers.IntegerField()
    em_atraso_clientes = serializers.IntegerField()
    em_atraso_parcelas = serializers.IntegerField()
    faixas = FaixasSerializer()


class ContagensReceberSerializer(serializers.Serializer[Any]):
    todas = serializers.IntegerField()
    atrasadas = serializers.IntegerField()
    vencem_hoje = serializers.IntegerField()
    a_vencer = serializers.IntegerField()
    pagas = serializers.IntegerField()


class ListaDeContasSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresReceberSerializer()
    contagens = ContagensReceberSerializer()
    resultados = ContaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class ContasSerializer(serializers.Serializer[Any]):
    resultados = ContaSerializer(many=True)


class LoteAceitoSerializer(serializers.Serializer[Any]):
    enviadas = serializers.IntegerField()


class PorFormaSerializer(serializers.Serializer[Any]):
    centavos = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    texto = serializers.CharField(required=False)


class PorFormasSerializer(serializers.Serializer[Any]):
    pix = PorFormaSerializer()
    cartao = PorFormaSerializer()
    dinheiro = PorFormaSerializer()


class GavetaSerializer(serializers.Serializer[Any]):
    troco_centavos = serializers.IntegerField()
    entradas_dinheiro_centavos = serializers.IntegerField()
    saidas_dinheiro_centavos = serializers.IntegerField()
    esperado_centavos = serializers.IntegerField()


class ResumoCaixaSerializer(serializers.Serializer[Any]):
    entrou_hoje_centavos = serializers.IntegerField()
    recebimentos = serializers.IntegerField()
    por_forma = PorFormasSerializer()
    gaveta = GavetaSerializer()


class FechamentoSerializer(serializers.Serializer[Any]):
    contado_centavos = serializers.IntegerField(allow_null=True)
    esperado_centavos = serializers.IntegerField(allow_null=True)
    diferenca_centavos = serializers.IntegerField(allow_null=True)
    motivo_diferenca = serializers.CharField(allow_null=True)
    fechado_por = RefSerializer(allow_null=True)
    fechado_em = serializers.DateTimeField(allow_null=True)
    pedido_aprovacao_id = serializers.IntegerField(allow_null=True)


class AcoesDoCaixaSerializer(serializers.Serializer[Any]):
    sangria = serializers.BooleanField()
    fechar = serializers.BooleanField()
    receber = serializers.BooleanField()


class CaixaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    filial = RefSerializer()
    data = serializers.DateField()  # type: ignore[assignment]
    status = serializers.ChoiceField(
        choices=["aberto", "aguardando_aprovacao", "fechado", "fechado_sem_conferencia"]
    )
    aberto_por = RefSerializer()
    aberto_em = serializers.DateTimeField()
    resumo = ResumoCaixaSerializer()
    fechamento = FechamentoSerializer(allow_null=True)
    acoes = AcoesDoCaixaSerializer()


class SemCaixaSerializer(serializers.Serializer[Any]):
    caixa = serializers.JSONField(allow_null=True)
    pode_abrir = serializers.BooleanField()


class MovimentoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    hora = serializers.DateTimeField()
    tipo = serializers.ChoiceField(choices=["entrada", "saida", "sangria"])
    forma = serializers.CharField()
    descricao = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    origem = OrigemDaContaSerializer(allow_null=True)
    registrado_por = serializers.CharField()
    estorno_de = serializers.IntegerField(allow_null=True)


class MovimentosSerializer(serializers.Serializer[Any]):
    resultados = MovimentoSerializer(many=True)


class OrigemDaDespesaSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    codigo = serializers.CharField(allow_null=True)


class NotaSerializer(serializers.Serializer[Any]):
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class VeiculoRefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()


class DespesaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    data = serializers.DateField()  # type: ignore[assignment]
    descricao = serializers.CharField()
    categoria = serializers.ChoiceField(choices=CategoriaDespesa.choices)
    veiculo = VeiculoRefSerializer(allow_null=True)
    filial = RefSerializer()
    valor_centavos = serializers.IntegerField()
    vencimento = serializers.DateField()
    status = serializers.ChoiceField(
        choices=["aguardando_aprovacao", "a_pagar", "paga", "recusada"]
    )
    pago_em = serializers.DateTimeField(allow_null=True)
    forma = serializers.CharField(allow_null=True)
    lancada_por = RefSerializer()
    nota = NotaSerializer(allow_null=True)
    sem_nota = serializers.BooleanField()
    origem = OrigemDaDespesaSerializer(allow_null=True)
    pedido_aprovacao_id = serializers.IntegerField(allow_null=True)
    rotulo_situacao = serializers.CharField()


class AnexarNotaSerializer(serializers.Serializer[Any]):
    nota = serializers.FileField(error_messages={"required": "Envie a foto da nota."})


class PorCategoriaSerializer(serializers.Serializer[Any]):
    def get_fields(self) -> dict[str, Any]:
        return {c: serializers.IntegerField(required=False) for c in CategoriaDespesa.values}


class IndicadoresDespesasSerializer(serializers.Serializer[Any]):
    gasto_mes_centavos = serializers.IntegerField()
    despesa_por_veiculo_centavos = serializers.IntegerField(allow_null=True)
    aguardando_aprovacao_centavos = serializers.IntegerField()
    aguardando_aprovacao_quantidade = serializers.IntegerField()
    a_pagar_semana_centavos = serializers.IntegerField()
    por_categoria = PorCategoriaSerializer()


class ContagensDespesasSerializer(serializers.Serializer[Any]):
    aguardando_aprovacao = serializers.IntegerField()
    a_pagar = serializers.IntegerField()
    paga = serializers.IntegerField()
    recusada = serializers.IntegerField()


class ListaDeDespesasSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresDespesasSerializer()
    contagens = ContagensDespesasSerializer()
    resultados = DespesaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class OrigemDoReembolsoSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["devolucao", "cancelamento", "credito"])
    codigo = serializers.CharField(allow_null=True)
    id = serializers.IntegerField(allow_null=True, help_text="a locação, para o Ver acerto")
    veiculo = serializers.CharField(allow_null=True, help_text="QXA-4B21 · Honda CG 160 Fan")


class AcoesDoReembolsoSerializer(serializers.Serializer[Any]):
    marcar_feito = serializers.BooleanField()


class ReembolsoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    criado_em = serializers.DateTimeField()
    cliente = RefSerializer()
    origem = OrigemDoReembolsoSerializer()
    origem_rotulo = serializers.CharField()
    motivo = serializers.CharField()
    forma = serializers.ChoiceField(choices=["pix", "dinheiro", "estorno_cartao"])
    forma_rotulo = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["a_fazer", "feito"])
    status_rotulo = serializers.CharField()
    feito_em = serializers.DateTimeField(allow_null=True)
    feito_por = RefSerializer(allow_null=True)
    comprovante = NotaSerializer(allow_null=True)
    acoes = AcoesDoReembolsoSerializer()


class IndicadorDeReembolsosSerializer(serializers.Serializer[Any]):
    valor_centavos = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    texto = serializers.CharField()


class IndicadoresReembolsosSerializer(serializers.Serializer[Any]):
    a_fazer = IndicadorDeReembolsosSerializer()
    feitos = IndicadorDeReembolsosSerializer()


class ContagensReembolsosSerializer(serializers.Serializer[Any]):
    a_fazer = serializers.IntegerField()
    feito = serializers.IntegerField()
    todos = serializers.IntegerField()


class ListaDeReembolsosSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresReembolsosSerializer()
    contagens = ContagensReembolsosSerializer()
    resultados = ReembolsoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class CobrancaDaPendenciaSerializer(serializers.Serializer[Any]):
    id_no_parceiro = serializers.CharField()
    forma = serializers.CharField()
    forma_rotulo = serializers.CharField()


class OrigemDaPendenciaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField(allow_null=True)
    conta_id = serializers.IntegerField()
    parcela = serializers.CharField(help_text="parcela 2 de 5")


class ResolucaoDaPendenciaSerializer(serializers.Serializer[Any]):
    texto = serializers.CharField()
    em = serializers.DateTimeField()


class AcoesDaPendenciaSerializer(serializers.Serializer[Any]):
    resolver = serializers.BooleanField()
    baixar = serializers.BooleanField()


class PendenciaPagamentoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    criado_em = serializers.DateTimeField()
    cobranca = CobrancaDaPendenciaSerializer()
    cliente = RefSerializer()
    origem = OrigemDaPendenciaSerializer()
    motivo = serializers.ChoiceField(
        choices=["valor_diferente", "estornada_no_parceiro", "sem_conta"]
    )
    motivo_rotulo = serializers.CharField()
    detalhe = serializers.CharField()
    valor_pago_centavos = serializers.IntegerField(allow_null=True)
    status = serializers.ChoiceField(choices=["aberta", "resolvida"])
    status_rotulo = serializers.CharField()
    resolucao = ResolucaoDaPendenciaSerializer(allow_null=True)
    acoes = AcoesDaPendenciaSerializer()


class IndicadorDePendenciasSerializer(serializers.Serializer[Any]):
    quantidade = serializers.IntegerField()
    valor_centavos = serializers.IntegerField()
    texto = serializers.CharField()


class IndicadoresPendenciasSerializer(serializers.Serializer[Any]):
    abertas = IndicadorDePendenciasSerializer()
    resolvidas = IndicadorDePendenciasSerializer()


class ContagensPendenciasSerializer(serializers.Serializer[Any]):
    aberta = serializers.IntegerField()
    resolvida = serializers.IntegerField()
    todas = serializers.IntegerField()


class ListaDePendenciasPagamentoSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresPendenciasSerializer()
    contagens = ContagensPendenciasSerializer()
    resultados = PendenciaPagamentoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
