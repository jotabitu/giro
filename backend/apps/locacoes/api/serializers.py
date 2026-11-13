"""Entrada e formato de resposta de locações (docs/api/locacoes.md).

As regras (preços, impedimentos, transições) são conferidas no serviço; aqui só a forma. Os
momentos vão como `datetime` com fuso; o formato é do renderizador de `comum` (ADR 0020).
"""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.contratos.api.serializers import ContratoResumoSerializer
from apps.veiculos.models import TipoVeiculo

from ..models import (
    FormaPagamento,
    ParcelamentoMensal,
    Periodicidade,
    PlanoCompra,
    PlanoEspecial,
    TipoLocacao,
)


def _momento(**kwargs: Any) -> serializers.DateTimeField:
    kwargs.setdefault("allow_null", True)
    return serializers.DateTimeField(**kwargs)


def _pct(**kwargs: Any) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=5, decimal_places=2, **kwargs)


# --- Entrada ---


class ExtraPedidoLocacaoSerializer(serializers.Serializer[Any]):
    extra_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1, max_value=20, default=1)


class LocacaoEntradaSerializer(serializers.Serializer[Any]):
    cliente_id = serializers.IntegerField()
    veiculo_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(
        choices=TipoLocacao.choices,
        required=False,
        default=TipoLocacao.COMUM,
        help_text="LOC-16: `intencao_compra` pede `plano_compra_id`; muda só no rascunho",
    )
    plano_compra_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="LOC-16: o plano de compra (só no tipo `intencao_compra`)",
    )
    periodicidade = serializers.ChoiceField(
        choices=Periodicidade.choices,
        required=False,
        help_text="Obrigatória na comum; na compra vem do plano",
    )
    plano_especial_id = serializers.IntegerField(required=False, allow_null=True)
    inicio = serializers.DateTimeField()
    periodos = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    fim_previsto = serializers.DateTimeField(required=False, allow_null=True)
    extras = ExtraPedidoLocacaoSerializer(many=True, required=False, default=list)
    desconto_pct = _pct(
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
        max_value=Decimal("100.00"),
    )
    forma_pagamento = serializers.ChoiceField(choices=FormaPagamento.choices)
    parcelamento_mensal = serializers.ChoiceField(
        choices=ParcelamentoMensal.choices, required=False, allow_null=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if self.partial or attrs.get("tipo") == TipoLocacao.INTENCAO_COMPRA:
            return attrs  # LOC-16: a periodicidade e os períodos vêm do plano
        if not attrs.get("periodicidade"):
            raise serializers.ValidationError({"periodicidade": ["Escolha a periodicidade."]})
        if not attrs.get("periodos") and not attrs.get("fim_previsto"):
            raise serializers.ValidationError(
                {"periodos": ["Informe os períodos ou o fim previsto."]}
            )
        return attrs


class EncerrarPorAtrasoSerializer(serializers.Serializer[Any]):
    """LOC-16: o encerramento da locação com intenção de compra pela locadora, sem APR-02."""

    motivo = serializers.CharField(
        max_length=500, allow_blank=True, error_messages={"blank": "Informe o motivo."}
    )
    data = serializers.DateField(  # type: ignore[assignment]
        required=False, allow_null=True, help_text="padrão hoje; não antes de hoje"
    )


class PlanoCompraEntradaSerializer(serializers.Serializer[Any]):
    """LOC-16 (padrão A): nome, categoria, periodicidade, parcelas (2 a 260) e valor."""

    nome = serializers.CharField(max_length=60)
    categoria_id = serializers.IntegerField()
    periodicidade = serializers.ChoiceField(choices=PlanoCompra.PeriodicidadeCompra.choices)
    parcelas = serializers.IntegerField()
    valor_parcela_centavos = serializers.IntegerField()
    condicoes = serializers.CharField(required=False, allow_blank=True, default="")


class ConfirmarLocacaoSerializer(serializers.Serializer[Any]):
    primeiro_vencimento = serializers.DateField(required=False, allow_null=True)


class RenovarLocacaoSerializer(serializers.Serializer[Any]):
    periodos = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    fim_previsto = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("periodos") and not attrs.get("fim_previsto"):
            raise serializers.ValidationError(
                {"periodos": ["Informe os períodos ou o novo fim previsto."]}
            )
        return attrs


class SimularCancelamentoSerializer(serializers.Serializer[Any]):
    data = serializers.DateField(required=False, allow_null=True)  # type: ignore[assignment]


class CancelarLocacaoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=500)
    data = serializers.DateField(required=False, allow_null=True)  # type: ignore[assignment]
    forma_devolucao = serializers.ChoiceField(
        choices=[("pix", "Pix"), ("estorno_cartao", "Estorno no cartão")],
        required=False,
        default="pix",
        help_text="Como o que foi pago volta ao cliente (LOC-12). Dinheiro sai pelo caixa.",
    )


class PlanoEspecialEntradaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60)
    periodicidade = serializers.ChoiceField(choices=Periodicidade.choices)
    regra = serializers.ChoiceField(choices=PlanoEspecial.Regra.choices)
    preco_centavos = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    desconto_pct = _pct(required=False, allow_null=True)
    a_partir_do_periodo = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    categorias = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    condicoes = serializers.CharField(required=False, allow_blank=True, default="")


# --- Saída ---


class CodigoMensagemLocacaoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    mensagem = serializers.CharField()
    link = serializers.CharField(required=False)


class LinhaSimulacaoSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    valor_centavos = serializers.IntegerField()


class ParcelaPrevistaSerializer(serializers.Serializer[Any]):
    numero = serializers.IntegerField()
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()


class CompraDaSimulacaoSerializer(serializers.Serializer[Any]):
    parcelas_total = serializers.IntegerField()
    valor_parcela_centavos = serializers.IntegerField()
    ultima_parcela_centavos = serializers.IntegerField(help_text="já com a caução abatida")
    sobra_caucao_centavos = serializers.IntegerField(
        help_text="caução maior que a parcela: volta ao cliente na quitação"
    )


class SimulacaoLocacaoSerializer(serializers.Serializer[Any]):
    fim_previsto = _momento()
    periodos = serializers.IntegerField()
    linhas = LinhaSimulacaoSerializer(many=True)
    valor_periodo_centavos = serializers.IntegerField()
    proximos_periodos_centavos = serializers.IntegerField()
    hoje_na_retirada_centavos = serializers.IntegerField()
    texto_retirada = serializers.CharField()
    parcelas_previstas = ParcelaPrevistaSerializer(many=True)
    caucao_centavos = serializers.IntegerField()
    diaria_centavos = serializers.IntegerField()
    compra = CompraDaSimulacaoSerializer(allow_null=True, help_text="LOC-16; null na comum")
    precisa_aprovacao_desconto = serializers.BooleanField()
    impedimentos = CodigoMensagemLocacaoSerializer(many=True)
    avisos = CodigoMensagemLocacaoSerializer(many=True)


class IdNomeLocacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class VeiculoDaLocacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    modelo = serializers.CharField()
    placa = serializers.CharField()
    tipo = serializers.ChoiceField(choices=TipoVeiculo.choices)


class SinaisLocacaoSerializer(serializers.Serializer[Any]):
    pagamento_atrasado = serializers.BooleanField()
    devolve_hoje = serializers.BooleanField()
    cancelamento_pendente = serializers.BooleanField()


class SituacaoLocacaoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class CaucaoNaLinhaSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField(help_text='LOC-17: "Caução R$ 300,00 · paga" ou "· em aberto"')
    tom = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    paga = serializers.BooleanField()


class PagamentoLocacaoSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField(
        help_text='LOC-17 (T-456): texto pronto, a tela não troca ("Falta R$ 629,00 · 1ª semana '
        'e caução", "R$ 329,00 vence hoje", "Pix", "Pago")'
    )
    tom = serializers.CharField()
    em_aberto_centavos = serializers.IntegerField()
    pago_centavos = serializers.IntegerField(help_text="Contas pagas da locação, sem a caução.")
    caucao = CaucaoNaLinhaSerializer(
        allow_null=True,
        help_text="LOC-17: na locação em andamento com caução; sai depois do acerto",
    )


class AcaoLocacaoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()


class LocacaoSerializer(serializers.Serializer[Any]):
    """Linha da lista. Para o vistoriador, o detalhe sai sem `pagamento` e sem `_centavos`."""

    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.CharField()
    cliente = IdNomeLocacaoSerializer()
    veiculo = VeiculoDaLocacaoSerializer()
    periodicidade = serializers.CharField()
    plano_especial = IdNomeLocacaoSerializer(allow_null=True)
    tipo = serializers.ChoiceField(choices=TipoLocacao.choices, help_text="LOC-16")
    tipo_rotulo = serializers.CharField(
        allow_null=True, help_text='"Com intenção de compra"; null na comum'
    )
    inicio = _momento()
    fim_previsto = _momento()
    sinais = SinaisLocacaoSerializer()
    situacao = SituacaoLocacaoSerializer()
    pagamento = PagamentoLocacaoSerializer(required=False)
    acao_principal = AcaoLocacaoSerializer()


class PrecosLocacaoSerializer(serializers.Serializer[Any]):
    valor_periodo_centavos = serializers.IntegerField()
    diaria_centavos = serializers.IntegerField()
    caucao_centavos = serializers.IntegerField()
    desconto_pct = _pct()
    assinado_em_preco_de = serializers.DateField(allow_null=True)


class DescontoLocacaoSerializer(serializers.Serializer[Any]):
    status = serializers.CharField()
    pedido_aprovacao_id = serializers.IntegerField(allow_null=True)
    pct = _pct(allow_null=True)


class ExtraDaLocacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    quantidade = serializers.IntegerField()
    valor_centavos = serializers.IntegerField()
    cobranca = serializers.CharField()


class CondicoesLocacaoSerializer(serializers.Serializer[Any]):
    vistoria_saida_ok_em = _momento()
    contrato_assinado_em = _momento()
    primeiro_pagamento_em = _momento()


class AcoesDaParcelaSerializer(serializers.Serializer[Any]):
    receber = serializers.BooleanField(
        help_text='"Registrar pagamento": a conta aberta e o perfil recebe no caixa (FIN-18)'
    )


class ParcelaLocacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(
        allow_null=True, help_text="null na última parcela de R$ 0,00 da compra (LOC-16)"
    )
    tipo = serializers.CharField()
    numero = serializers.IntegerField(allow_null=True)
    total_parcelas = serializers.IntegerField(allow_null=True)
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    status = serializers.CharField()
    forma = serializers.CharField(allow_null=True)
    pago_em = _momento()
    observacao = serializers.CharField(
        allow_null=True,
        help_text='LOC-16: "caução abatida" na última parcela da compra; "paga com a caução" ou '
        '"será paga com a caução" na de R$ 0,00',
    )
    paga_com_caucao = serializers.BooleanField(
        help_text="LOC-16 (CA-420-14): a última parcela de R$ 0,00 da compra, paga pela caução. "
        "Não é conta a receber: sem `id`, sem `conta_id` e sem botão; a situação é a `observacao`"
    )
    # Seção Pagamentos (FIN-18, LOC-17, T-451): a conta de `Receber`, o rótulo ("Parcela 1",
    # "Caução"), o valor de hoje (FIN-03) e se o perfil recebe no caixa.
    conta_id = serializers.IntegerField(
        allow_null=True,
        help_text="o `id` da conta em /api/financeiro/contas-receber/; null na linha "
        "`paga_com_caucao`",
    )
    rotulo = serializers.CharField()
    valor_hoje_centavos = serializers.IntegerField()
    acoes = AcoesDaParcelaSerializer()


class DevolucaoPrevistaSerializer(serializers.Serializer[Any]):
    prevista_para = _momento(
        help_text="LOC-16: na compra, null sem encerramento; com ele, o fim do dia do encerramento"
    )
    faltam_minutos = serializers.IntegerField(allow_null=True)
    aviso_atraso = serializers.CharField(allow_null=True)
    devolucao_id = serializers.IntegerField(allow_null=True)


class TrechoLocacaoSerializer(serializers.Serializer[Any]):
    veiculo = serializers.CharField()
    inicio = _momento()
    fim = _momento()


class AcoesLocacaoSerializer(serializers.Serializer[Any]):
    editar = serializers.BooleanField()
    confirmar = serializers.BooleanField()
    renovar = serializers.BooleanField()
    registrar_devolucao = serializers.BooleanField()
    trocar_veiculo = serializers.BooleanField()
    cancelar_troca = serializers.BooleanField()
    cancelar = serializers.JSONField(help_text='"direto", "pedir" ou false')
    gerar_contrato = serializers.BooleanField(help_text="T-263: o POST .../contrato/ passaria")
    imprimir_contrato = serializers.BooleanField()
    reenviar_contrato = serializers.BooleanField()
    copiar_link_contrato = serializers.BooleanField(
        help_text="T-411: o POST .../contrato/link/ passaria pelo perfil e pelo estado"
    )
    continuar_vistoria = serializers.BooleanField()
    receber = serializers.BooleanField()
    registrar_retirada = serializers.BooleanField(
        help_text="LOC-17: administrador e gerente, locação aguardando retirada"
    )
    encerrar_por_atraso = serializers.BooleanField(
        help_text="LOC-16: administrador e gerente, compra ativa com parcela atrasada"
    )


class CancelamentoLocacaoSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=[("pendente", "Pendente"), ("aprovado", "Aprovado")])
    pedido_aprovacao_id = serializers.IntegerField(allow_null=True)
    antes_da_retirada = serializers.BooleanField()
    automatico = serializers.BooleanField(
        help_text="cancelada pela AUT-17, não retirada em 3 dias (LOC-12, T-410)"
    )
    por_atraso = serializers.BooleanField(
        help_text="LOC-16: encerrada pela locadora por atraso, sem APR-02"
    )
    data = serializers.DateField(allow_null=True)  # type: ignore[assignment]
    multa_centavos = serializers.IntegerField()
    credito_centavos = serializers.IntegerField()
    devolver_centavos = serializers.IntegerField()
    cobrar_centavos = serializers.IntegerField()
    motivo = serializers.CharField()


class PrazoRetiradaSerializer(serializers.Serializer[Any]):
    """LOC-12, AUT-17 (T-410): só na locação `aguardando_retirada`."""

    ultimo_dia = serializers.DateField()
    cancela_em = serializers.DateField()


class AcaoDaRetiradaSerializer(serializers.Serializer[Any]):
    codigo = serializers.ChoiceField(
        choices=[
            "continuar_vistoria",
            "gerar_contrato",
            "reenviar_contrato",
            "copiar_link_contrato",
        ],
        help_text="a mesma chave de `acoes`, que a tela já sabe executar",
    )
    rotulo = serializers.CharField()


class PassoDaRetiradaSerializer(serializers.Serializer[Any]):
    codigo = serializers.ChoiceField(choices=["vistoria_saida", "contrato", "pagamento"])
    feito = serializers.BooleanField()
    texto = serializers.CharField(help_text='"Feita em 07 out, 09:20", "Falta a vistoria de saída"')
    acoes = AcaoDaRetiradaSerializer(many=True, help_text="só as que o perfil pode fazer")


class RegistrarRetiradaSerializer(serializers.Serializer[Any]):
    """O botão "Registrar retirada" (LOC-17) e a confirmação, com textos prontos."""

    rotulo = serializers.CharField()
    disponivel = serializers.BooleanField(help_text="false sem a vistoria de saída concluída")
    aviso = serializers.CharField(
        allow_null=True, help_text='"Faça a vistoria de saída antes da retirada."'
    )
    titulo = serializers.CharField(help_text='"Registrar retirada?"')
    faltas = serializers.ListField(
        child=serializers.CharField(), help_text="os textos dos passos que faltam"
    )
    motivo_obrigatorio = serializers.CharField(help_text='"Informe o motivo."')


class ParaRetirarSerializer(serializers.Serializer[Any]):
    """LOC-17 (T-451): os três passos, na ordem vistoria, contrato, pagamento, e o prazo da
    LOC-12. Só na `aguardando_retirada`; textos prontos da API."""

    passos = PassoDaRetiradaSerializer(many=True)
    prazo = serializers.CharField()
    registrar_retirada = RegistrarRetiradaSerializer(
        allow_null=True, help_text="o botão, só para administrador e gerente (LOC-17)"
    )


class PendenciasDaRetiradaSerializer(serializers.Serializer[Any]):
    """LOC-17: na locação retirada à mão, só os passos que ainda faltam. Nulo sem pendência."""

    passos = PassoDaRetiradaSerializer(many=True)


class RegistrarRetiradaEntradaSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(
        max_length=200, allow_blank=True, error_messages={"blank": "Informe o motivo."}
    )


class VeiculoDaTrocaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    modelo = serializers.CharField()


class VistoriaDaTrocaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=[("rascunho", "Rascunho"), ("concluida", "Concluída"), ("descartada", "Descartada")]
    )


class PrecoDaTrocaSerializer(serializers.Serializer[Any]):
    valor_periodo_centavos = serializers.IntegerField()
    diaria_centavos = serializers.IntegerField()
    caucao_centavos = serializers.IntegerField()
    preco_do_dia = serializers.DateField(allow_null=True)


class CaucaoDaTrocaSerializer(serializers.Serializer[Any]):
    conta_id = serializers.IntegerField()
    valor_centavos = serializers.IntegerField()
    status = serializers.CharField()


class TrocaPendenteSerializer(serializers.Serializer[Any]):
    """LOC-09 (T-122): a troca pendente; o vistoriador recebe sem `preco` e sem `caucao`."""

    id = serializers.IntegerField()
    status = serializers.CharField()
    motivo = serializers.CharField()
    pedida_em = _momento()
    veiculo_antigo = VeiculoDaTrocaSerializer()
    veiculo_novo = VeiculoDaTrocaSerializer()
    devolucao_vistoria = VistoriaDaTrocaSerializer(allow_null=True)
    saida_vistoria = VistoriaDaTrocaSerializer(allow_null=True)
    preco = PrecoDaTrocaSerializer(required=False)
    caucao = CaucaoDaTrocaSerializer(allow_null=True, required=False)


class ClienteDaLocacaoSerializer(serializers.Serializer[Any]):
    """USR-09: o que a ficha da locação mostra do cliente, sem abrir a ficha dele."""

    id = serializers.IntegerField()
    nome = serializers.CharField()
    celular = serializers.CharField(allow_null=True)
    cnh_categoria = serializers.CharField(allow_null=True)
    ficha_liberada = serializers.BooleanField(
        help_text="O perfil abre a ficha do cliente; falso para o vistoriador (USR-09)."
    )


class TransferenciaDaVendaSerializer(serializers.Serializer[Any]):
    feita_em = serializers.DateField(allow_null=True)
    registrada_por = IdNomeLocacaoSerializer(allow_null=True)
    pendente = serializers.BooleanField()


class AcoesDaVendaDaCompraSerializer(serializers.Serializer[Any]):
    registrar_transferencia = serializers.BooleanField(
        help_text="POST /api/locacoes/{id}/transferencia/ (administrador e gerente)"
    )


class VendaDaCompraSerializer(serializers.Serializer[Any]):
    """VEN-11: a venda de R$ 0,00 da quitação, fornecida por `vendas` (ADR 0015)."""

    id = serializers.IntegerField()
    codigo = serializers.CharField()
    transferencia = TransferenciaDaVendaSerializer()
    acoes = AcoesDaVendaDaCompraSerializer()


class FaltaParaQuitarSerializer(serializers.Serializer[Any]):
    conta_id = serializers.IntegerField(
        allow_null=True, help_text="null na caução que não tem conta aberta para receber"
    )
    rotulo = serializers.CharField()
    valor_centavos = serializers.IntegerField(required=False, help_text="o valor do dia (FIN-03)")


class CompraLocacaoSerializer(serializers.Serializer[Any]):
    """LOC-16 (T-420): o plano congelado e o andamento, com os textos prontos da API. O
    vistoriador recebe sem os campos `_centavos`."""

    plano = IdNomeLocacaoSerializer(allow_null=True)
    parcelas_total = serializers.IntegerField()
    parcelas_pagas = serializers.IntegerField()
    valor_parcela_centavos = serializers.IntegerField(required=False)
    ultima_parcela_centavos = serializers.IntegerField(required=False)
    sobra_caucao_centavos = serializers.IntegerField(required=False)
    andamento = serializers.CharField(
        allow_null=True, help_text='"Parcela 1 de 24 · faltam 23 para a transferência"'
    )
    falta_para_quitar = FaltaParaQuitarSerializer(many=True)
    quitada_em = _momento()
    venda = VendaDaCompraSerializer(allow_null=True)


class LocacaoDetalheSerializer(LocacaoSerializer):
    cliente = ClienteDaLocacaoSerializer()  # type: ignore[assignment]
    filial = IdNomeLocacaoSerializer()
    vendedor = IdNomeLocacaoSerializer()
    periodos = serializers.IntegerField()
    precos = PrecosLocacaoSerializer(required=False)
    desconto = DescontoLocacaoSerializer(allow_null=True, required=False)
    extras = ExtraDaLocacaoSerializer(many=True, required=False)
    km_saida = serializers.IntegerField(allow_null=True)
    km_livre = serializers.BooleanField()
    forma_pagamento = serializers.CharField()
    parcelamento_mensal = serializers.CharField(allow_null=True)
    primeiro_vencimento = serializers.DateField(allow_null=True)
    condicoes = CondicoesLocacaoSerializer()
    parcelas = ParcelaLocacaoSerializer(many=True, required=False)
    total_pago_centavos = serializers.IntegerField(required=False)
    contrato = ContratoResumoSerializer(allow_null=True)
    devolucao = DevolucaoPrevistaSerializer()
    trechos = TrechoLocacaoSerializer(many=True)
    cancelamento = CancelamentoLocacaoSerializer(allow_null=True)
    prazo_retirada = PrazoRetiradaSerializer(allow_null=True)
    para_retirar = ParaRetirarSerializer(allow_null=True)
    pendencias_retirada = PendenciasDaRetiradaSerializer(
        allow_null=True, help_text="LOC-17: o que faltava na retirada à mão"
    )
    troca = TrocaPendenteSerializer(allow_null=True)
    compra = CompraLocacaoSerializer(allow_null=True, help_text="LOC-16; null na comum")
    acoes = AcoesLocacaoSerializer()


class IndicadoresLocacoesSerializer(serializers.Serializer[Any]):
    ativas = serializers.IntegerField()
    frota_alugada_pct = serializers.CharField(allow_null=True)
    devolvem_hoje = serializers.IntegerField()
    devolvem_hoje_ate_12h = serializers.IntegerField()
    devolucao_atrasada = serializers.IntegerField()
    devolucao_atrasada_destaque = serializers.CharField(allow_null=True)
    pagamentos_atrasados = serializers.IntegerField()
    pagamentos_atrasados_centavos = serializers.IntegerField()


class ContagensLocacoesSerializer(serializers.Serializer[Any]):
    abertas = serializers.IntegerField()
    precisam_acao = serializers.IntegerField()
    devolvem_hoje = serializers.IntegerField()
    encerradas = serializers.IntegerField()
    canceladas = serializers.IntegerField()
    rascunhos = serializers.IntegerField()


class ListaDeLocacoesSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresLocacoesSerializer()
    contagens = ContagensLocacoesSerializer()
    resultados = LocacaoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class ItemHistoricoLocacaoSerializer(serializers.Serializer[Any]):
    em = _momento()
    rotulo = serializers.CharField()
    detalhe = serializers.CharField(allow_blank=True)
    tipo = serializers.CharField()


class HistoricoLocacaoSerializer(serializers.Serializer[Any]):
    resultados = ItemHistoricoLocacaoSerializer(many=True)


class PlanoEspecialSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    periodicidade = serializers.CharField()
    regra = serializers.CharField()
    preco_centavos = serializers.IntegerField(allow_null=True)
    desconto_pct = _pct(allow_null=True)
    a_partir_do_periodo = serializers.IntegerField(allow_null=True)
    categorias = IdNomeLocacaoSerializer(many=True)
    condicoes = serializers.CharField(allow_blank=True)
    locacoes_ativas = serializers.IntegerField()
    ativo = serializers.BooleanField()


class PlanoCompraSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    categoria = IdNomeLocacaoSerializer()
    periodicidade = serializers.CharField()
    parcelas = serializers.IntegerField()
    valor_parcela_centavos = serializers.IntegerField()
    condicoes = serializers.CharField(allow_blank=True)
    caucao_centavos = serializers.IntegerField(help_text="a caução vigente da categoria")
    ultima_parcela_centavos = serializers.IntegerField(help_text="max(0, parcela − caução)")
    locacoes_ativas = serializers.IntegerField()
    ativo = serializers.BooleanField()


class ListaDePlanosCompraSerializer(serializers.Serializer[Any]):
    resultados = PlanoCompraSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class ListaDePlanosEspeciaisSerializer(serializers.Serializer[Any]):
    resultados = PlanoEspecialSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


# --- Renovação e cancelamento (LOC-08, LOC-12, LOC-13, APR-02) ---


class SimulacaoRenovacaoSerializer(serializers.Serializer[Any]):
    fim_previsto_atual = _momento()
    fim_previsto = _momento()
    periodos = serializers.IntegerField()
    valor_periodo_centavos = serializers.IntegerField()
    parcelas_novas = ParcelaPrevistaSerializer(many=True)
    total_centavos = serializers.IntegerField()


class PeriodoAtualSerializer(serializers.Serializer[Any]):
    inicio = serializers.DateField()
    fim = serializers.DateField()
    dias = serializers.IntegerField()


class CreditoSemanasSerializer(serializers.Serializer[Any]):
    semanas = serializers.IntegerField()
    valor_centavos = serializers.IntegerField()


class CreditoDiasSerializer(serializers.Serializer[Any]):
    dias = serializers.IntegerField()
    valor_centavos = serializers.IntegerField()


class SimulacaoCancelamentoSerializer(serializers.Serializer[Any]):
    antes_da_retirada = serializers.BooleanField()
    periodo_atual = PeriodoAtualSerializer(allow_null=True)
    dias_restantes = serializers.IntegerField()
    valor_restante_centavos = serializers.IntegerField()
    multa_centavos = serializers.IntegerField()
    credito_semanas = CreditoSemanasSerializer()
    credito_dias = CreditoDiasSerializer(help_text="Diária: os dias não usados (LOC-12).")
    parcelas_canceladas_centavos = serializers.IntegerField(
        help_text="Mensal em 4 semanais: as parcelas do mês que o encerramento cancela, "
        "descontadas do crédito das semanas (LOC-13)."
    )
    devolver_centavos = serializers.IntegerField()
    cobrar_centavos = serializers.IntegerField()
    avisos = CodigoMensagemLocacaoSerializer(
        many=True, help_text="Diária: o acerto final usa a hora da devolução (LOC-12)."
    )


class PedidoAprovacaoRefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    status = serializers.CharField()


class CancelamentoPedidoSerializer(serializers.Serializer[Any]):
    pedido_aprovacao = PedidoAprovacaoRefSerializer()
