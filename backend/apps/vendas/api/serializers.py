"""Entrada e saída das vendas (`docs/api/vendas.md`): a venda da quitação (T-420) e o fluxo de
balcão das fases 1a e 1b da T-502 (ADR 0042, item 14)."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.contratos.api.serializers import ContratoResumoSerializer
from apps.financeiro.models import StatusConta

from ..models import FormaVenda, OrigemVenda, SituacaoAprovacao, StatusVenda
from ..services import Acao

PCT = {"max_digits": 5, "decimal_places": 2, "min_value": Decimal("0")}


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


class InteressadoSerializer(serializers.Serializer[Any]):
    class Meta:
        ref_name = "InteressadoDaVenda"

    nome = serializers.CharField(max_length=150)
    celular = serializers.CharField(max_length=20)


class TransferenciaSerializer(serializers.Serializer[Any]):
    feita_em = serializers.DateField(allow_null=True)
    registrada_por = RefDaVendaSerializer(allow_null=True)
    pendente = serializers.BooleanField()


class AcoesDaVendaSerializer(serializers.Serializer[Any]):
    editar = serializers.BooleanField()
    enviar = serializers.BooleanField()
    registrar_resposta = serializers.BooleanField()
    pedir_aprovacao = serializers.BooleanField()
    perder = serializers.BooleanField()
    cancelar = serializers.BooleanField()
    registrar_transferencia = serializers.BooleanField()
    # Fase 1b (VEN-15, VEN-19): a etapa "Assinatura".
    preparar_assinatura = serializers.BooleanField()
    cancelar_assinatura = serializers.BooleanField()
    copiar_link_contrato = serializers.BooleanField()
    reenviar_contrato = serializers.BooleanField()


class VendaSerializer(serializers.Serializer[Any]):
    """O item da lista."""

    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.ChoiceField(choices=StatusVenda.choices)
    origem = serializers.ChoiceField(choices=OrigemVenda.choices)
    origem_rotulo = serializers.CharField()
    descricao = serializers.CharField()
    cliente = RefDaVendaSerializer(allow_null=True)
    interessado = InteressadoSerializer(allow_null=True)
    comprador_nome = serializers.CharField()
    veiculo = VeiculoDaVendaSerializer()
    filial = RefDaVendaSerializer()
    vendedor = RefDaVendaSerializer(allow_null=True)
    locacao = LocacaoDaVendaSerializer(allow_null=True)
    valor = serializers.IntegerField()
    preco_final_centavos = serializers.IntegerField()
    forma = serializers.CharField()
    forma_texto = serializers.CharField()
    situacao_texto = serializers.CharField()
    motivo_perda = serializers.CharField(allow_null=True)
    proposta_enviada_em = serializers.DateTimeField(allow_null=True)
    proposta_vence_em = serializers.DateField(allow_null=True)
    ultimo_contato_em = serializers.DateTimeField(allow_null=True)
    perdida_em = serializers.DateTimeField(allow_null=True)
    vendida_em = serializers.DateTimeField(allow_null=True)
    comissao_centavos = serializers.IntegerField(allow_null=True)
    transferencia = TransferenciaSerializer()
    acoes = AcoesDaVendaSerializer()


class CalculoDaVendaSerializer(serializers.Serializer[Any]):
    """O que a API calcula (ADR 0042, item 4); a tela só mostra."""

    class Meta:
        ref_name = "CalculoDaVenda"

    preco_tabela_centavos = serializers.IntegerField()
    desconto_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    desconto_centavos = serializers.IntegerField()
    preco_final_centavos = serializers.IntegerField()
    forma = serializers.CharField()
    entrada_centavos = serializers.IntegerField(allow_null=True)
    saldo_centavos = serializers.IntegerField()
    num_parcelas = serializers.IntegerField(allow_null=True)
    juros_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    parcela_centavos = serializers.IntegerField(allow_null=True)
    ultima_parcela_centavos = serializers.IntegerField(allow_null=True)
    total_parcelas_centavos = serializers.IntegerField()
    comissao_centavos = serializers.IntegerField()
    precisa_aprovacao = serializers.BooleanField()
    limite_desconto_pct = serializers.DecimalField(max_digits=5, decimal_places=2)


class AprovacaoDaVendaSerializer(serializers.Serializer[Any]):
    situacao = serializers.ChoiceField(choices=SituacaoAprovacao.choices)
    pedido_id = serializers.IntegerField(allow_null=True)
    desconto_pedido_pct = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    desconto_aprovado_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    motivo_recusa = serializers.CharField(allow_null=True)
    texto = serializers.CharField(allow_null=True)


class ContratoDaVendaSerializer(ContratoResumoSerializer):
    class Meta:
        ref_name = "ContratoDaVenda"

    situacao_texto = serializers.CharField()


class ContaEntradaSerializer(serializers.Serializer[Any]):
    """A entrada (ou o total à vista) em Contas a receber (VEN-15): "Entrada de R$ 5.000,00",
    "Aguardando pagamento · vence hoje"."""

    class Meta:
        ref_name = "ContaEntradaDaVenda"

    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusConta.choices)
    valor_centavos = serializers.IntegerField()
    vencimento = serializers.DateField()
    rotulo = serializers.CharField()
    texto = serializers.CharField()


class DocumentosDaVendaSerializer(serializers.Serializer[Any]):
    """A etapa "Documentos" (VEN-14, VEN-19): as pendências do cadastro (`CLI-03`, os códigos
    de `clientes`) e o texto pronto do cliente bloqueado ou inativo (`CLI-05`)."""

    class Meta:
        ref_name = "DocumentosDaVenda"

    pendencias = serializers.ListField(child=serializers.CharField())
    # Texto, não enum: a lista `critica`/`alerta` colidiria com o `GravidadeEnum` do painel.
    gravidade = serializers.CharField(
        allow_null=True, help_text="`critica` (CLI-05) ou `alerta` (CLI-03)"
    )
    texto = serializers.CharField(allow_null=True)
    pode_preparar = serializers.BooleanField()


class VendaDetalheSerializer(VendaSerializer):
    calculo = CalculoDaVendaSerializer(allow_null=True)
    aprovacao = AprovacaoDaVendaSerializer(allow_null=True)
    # Fase 1b (VEN-15, VEN-19): assinatura e entrada, com os textos prontos.
    contrato = ContratoDaVendaSerializer(allow_null=True)
    conta_entrada = ContaEntradaSerializer(allow_null=True)
    documentos = DocumentosDaVendaSerializer(allow_null=True)
    perder_texto = serializers.CharField(allow_null=True)
    conclusao_texto = serializers.CharField(allow_null=True)


class ListaDeVendasSerializer(serializers.Serializer[Any]):
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
    resultados = VendaSerializer(many=True)


class TransferenciaEntradaSerializer(serializers.Serializer[Any]):
    feita_em = serializers.DateField()


# --- Entrada do fluxo de balcão (T-502, fase 1a) ---


class PropostaSerializer(serializers.Serializer[Any]):
    """Os campos da proposta que a pessoa digita (VEN-02, VEN-03, VEN-04)."""

    forma = serializers.ChoiceField(choices=FormaVenda.choices, required=False, allow_blank=True)
    desconto_pct = serializers.DecimalField(required=False, **PCT)  # type: ignore[arg-type]
    entrada_centavos = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    num_parcelas = serializers.IntegerField(required=False, allow_null=True, min_value=0)


class SimularVendaSerializer(PropostaSerializer):
    """`venda_id` (a venda que se edita) ou `veiculo_id` (a Nova venda)."""

    venda_id = serializers.IntegerField(required=False)
    veiculo_id = serializers.IntegerField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("venda_id") and not attrs.get("veiculo_id"):
            raise serializers.ValidationError({"veiculo_id": ["Escolha um veículo à venda."]})
        return attrs


class SimulacaoSerializer(CalculoDaVendaSerializer):
    class Meta:
        ref_name = "SimulacaoDaVenda"

    erros = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


class CriarVendaSerializer(PropostaSerializer):
    veiculo_id = serializers.IntegerField()
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    interessado = InteressadoSerializer(required=False, allow_null=True)
    acao = serializers.ChoiceField(choices=list(Acao.TODAS))
    motivo = serializers.CharField(max_length=300, required=False, allow_blank=True)


class EditarVendaSerializer(PropostaSerializer):
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    interessado = InteressadoSerializer(required=False, allow_null=True)


class RespostaSerializer(serializers.Serializer[Any]):
    nota = serializers.CharField(max_length=300, required=False, allow_blank=True)


class PedirAprovacaoSerializer(serializers.Serializer[Any]):
    desconto_pct = serializers.DecimalField(**PCT)  # type: ignore[arg-type]
    motivo = serializers.CharField(max_length=300, required=False, allow_blank=True)


class PerderSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)


class VendaEnviadaSerializer(serializers.Serializer[Any]):
    """`email_enviado` fica `false` até o envio por e-mail da fase 1c."""

    email_enviado = serializers.BooleanField()
    venda = VendaDetalheSerializer()
