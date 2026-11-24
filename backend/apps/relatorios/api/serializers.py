"""Formas das respostas do painel (`docs/api/painel.md`) e de Configurações
(`docs/api/configuracoes.md`): só descrevem o que o selector monta."""

from typing import Any

from drf_spectacular.utils import PolymorphicProxySerializer
from rest_framework import serializers

from apps.financeiro.models import StatusCaixa
from apps.vistorias.api.serializers import AgendaSerializer

# FIN-07, FIN-08: o mesmo `StatusCaixaEnum` do caixa no OpenAPI (ENUM_NAME_OVERRIDES).
STATUS_CAIXA = [s.value for s in StatusCaixa]


def _pct(**kwargs: Any) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=5, decimal_places=2, **kwargs)


class ContadoresInternosSerializer(serializers.Serializer[Any]):
    """Só vêm as chaves dos itens que a pessoa vê; `null` = módulo ainda não existe."""

    veiculos = serializers.IntegerField(required=False, allow_null=True)
    locacoes = serializers.IntegerField(required=False, allow_null=True)
    aprovacoes = serializers.IntegerField(required=False, allow_null=True)
    receber = serializers.IntegerField(required=False, allow_null=True)
    despesas = serializers.IntegerField(required=False, allow_null=True)
    usuarios = serializers.IntegerField(required=False, allow_null=True)
    agenda = serializers.IntegerField(required=False, allow_null=True)
    avarias = serializers.IntegerField(required=False, allow_null=True)
    contas_a_pagar = serializers.IntegerField(required=False, allow_null=True)
    manutencoes = serializers.IntegerField(required=False, allow_null=True)
    conciliacao = serializers.IntegerField(required=False, allow_null=True)
    propostas = serializers.IntegerField(required=False, allow_null=True)


class ContadoresSerializer(serializers.Serializer[Any]):
    atualizado_em = serializers.DateTimeField()
    contadores = ContadoresInternosSerializer()


# --- Blocos comuns ---


class ValorTipadoSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["numero", "centavos", "pct"])
    valor = serializers.JSONField(
        help_text="Inteiro para `numero` e `centavos`; texto com 2 casas para `pct`."
    )


class KpiSerializer(serializers.Serializer[Any]):
    chave = serializers.CharField()
    rotulo = serializers.CharField()
    valor = ValorTipadoSerializer(allow_null=True)
    contexto = serializers.CharField(allow_null=True)
    destaque = serializers.BooleanField(required=False)
    tendencia = serializers.ChoiceField(choices=["sobe", "desce"], required=False, allow_null=True)


class SituacaoCurtaSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class DestinoSerializer(serializers.Serializer[Any]):
    chave = serializers.CharField()
    filtro = serializers.CharField(required=False)
    id = serializers.IntegerField(required=False)


class CabecalhoDoInicioSerializer(serializers.Serializer[Any]):
    variante = serializers.ChoiceField(
        choices=["geral", "implantacao", "gerente", "vendedor", "vistoriador", "financeiro"]
    )
    saudacao = serializers.CharField()
    atualizado_em = serializers.DateTimeField()


# --- geral ---


class AtencaoSerializer(serializers.Serializer[Any]):
    quantidade = serializers.IntegerField()
    texto = serializers.CharField()


class SegmentoDaFrotaSerializer(serializers.Serializer[Any]):
    status = serializers.CharField()
    rotulo = serializers.CharField()
    quantidade = serializers.IntegerField()


class FrotaDoInicioSerializer(serializers.Serializer[Any]):
    ocupacao_pct = _pct()
    meta_ocupacao_pct = _pct()
    nota = serializers.CharField()
    segmentos = SegmentoDaFrotaSerializer(many=True)


class LinhaDeDevolucaoSerializer(serializers.Serializer[Any]):
    locacao_id = serializers.IntegerField()
    codigo = serializers.CharField()
    placa = serializers.CharField()
    veiculo = serializers.CharField()
    cliente = serializers.CharField()
    data = serializers.DateField()  # type: ignore[assignment]
    situacao = SituacaoCurtaSerializer()


class DevolucoesDaSemanaSerializer(serializers.Serializer[Any]):
    subtitulo = serializers.CharField()
    linhas = LinhaDeDevolucaoSerializer(many=True)


class ItemDePendenciaSerializer(serializers.Serializer[Any]):
    texto = serializers.CharField()
    gravidade = serializers.ChoiceField(choices=["critica", "alerta", "info"])
    destino = DestinoSerializer()


class PendenciasSerializer(serializers.Serializer[Any]):
    titulo = serializers.CharField()
    itens = ItemDePendenciaSerializer(many=True)


class CaixaHojeSerializer(serializers.Serializer[Any]):
    filial = serializers.CharField()
    data = serializers.DateField()  # type: ignore[assignment]
    status = serializers.ChoiceField(choices=STATUS_CAIXA)
    recebido_centavos = serializers.IntegerField()
    a_receber_hoje_centavos = serializers.IntegerField()
    despesas_centavos = serializers.IntegerField()
    saldo_dia_centavos = serializers.IntegerField()


# --- Estoque à venda e ticket médio (VEI-18, VEI-20, VEN-12; T-486, T-487) ---


class EstoqueAVendaSerializer(serializers.Serializer[Any]):
    """VEI-20. Só para administrador e gerente; ausente para os outros perfis."""

    quantidade = serializers.IntegerField(help_text="Veículos `a_venda` no escopo.")
    capital_imobilizado_centavos = serializers.IntegerField()
    veiculos_na_conta = serializers.IntegerField(help_text="Os com valor de compra.")
    custo_medio_centavos = serializers.IntegerField(allow_null=True)
    margem_centavos = serializers.IntegerField(allow_null=True)
    margem_pct = serializers.DecimalField(max_digits=7, decimal_places=2, allow_null=True)
    margem_negativa = serializers.BooleanField()
    sem_valor_compra = serializers.IntegerField()
    sem_valor_venda = serializers.IntegerField()
    subtitulo = serializers.CharField()
    legenda_capital = serializers.CharField()
    legenda_custo_medio = serializers.CharField(allow_null=True)
    margem_texto = serializers.CharField(allow_null=True, help_text="Com o sinal: −R$ 750,00.")
    legenda_margem = serializers.CharField(allow_null=True)
    avisos = serializers.ListField(child=serializers.CharField())


class ParadoAVendaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    veiculo = serializers.CharField()
    dias_em_estoque = serializers.IntegerField(allow_null=True)
    parado = serializers.BooleanField()


class ParadosAVendaSerializer(serializers.Serializer[Any]):
    """VEI-18, VEI-19: os 5 com mais dias da filial, na ordem da lista."""

    limite_dias_parado = serializers.IntegerField()
    acima_do_limite = serializers.IntegerField()
    subtitulo = serializers.CharField()
    itens = ParadoAVendaSerializer(many=True)


class VendasDoMesSerializer(serializers.Serializer[Any]):
    mes = serializers.CharField()
    vendas = serializers.IntegerField()
    soma_centavos = serializers.IntegerField()
    ticket_centavos = serializers.IntegerField(allow_null=True)


class TicketMedioSerializer(VendasDoMesSerializer):
    """VEN-12. Só para administrador e gerente; ausente para os outros perfis."""

    subtitulo = serializers.CharField()
    rotulo = serializers.CharField()
    resumo = serializers.CharField(allow_null=True, help_text="4 vendas · R$ 31.200,00")
    vazio = serializers.CharField(allow_null=True, help_text="Sem vendas em novembro.")
    mes_anterior = VendasDoMesSerializer()
    variacao_pct = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    comparacao = serializers.CharField(allow_null=True)


class InicioGeralSerializer(CabecalhoDoInicioSerializer):
    atencao = AtencaoSerializer()
    kpis = KpiSerializer(many=True)
    frota = FrotaDoInicioSerializer()
    devolucoes_semana = DevolucoesDaSemanaSerializer()
    pendencias = PendenciasSerializer()
    caixa_hoje = CaixaHojeSerializer(allow_null=True)
    estoque_a_venda = EstoqueAVendaSerializer(required=False)
    ticket_medio = TicketMedioSerializer(required=False)


# --- implantacao ---


class TesteDoInicioSerializer(serializers.Serializer[Any]):
    fim = serializers.DateField()
    dias_restantes = serializers.IntegerField()
    texto = serializers.CharField()


class AcaoDoPassoSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    destino = serializers.CharField()


class PassoDoInicioSerializer(serializers.Serializer[Any]):
    chave = serializers.CharField()
    rotulo = serializers.CharField()
    detalhe = serializers.CharField()
    concluido = serializers.BooleanField()
    acao = AcaoDoPassoSerializer(required=False)


class PrimeirosPassosSerializer(serializers.Serializer[Any]):
    concluidos = serializers.IntegerField()
    total = serializers.IntegerField()
    pct = _pct()
    itens = PassoDoInicioSerializer(many=True)


class ConviteDoInicioSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    contato = serializers.CharField()
    perfil = serializers.CharField()
    status = serializers.ChoiceField(choices=["aceito", "pendente"])


class IndicadoresDaImplantacaoSerializer(serializers.Serializer[Any]):
    frota_cadastrada = serializers.IntegerField()
    alugados_agora = serializers.IntegerField()
    clientes = serializers.IntegerField()
    a_receber_centavos = serializers.IntegerField()


class InicioImplantacaoSerializer(CabecalhoDoInicioSerializer):
    teste = TesteDoInicioSerializer(allow_null=True)
    primeiros_passos = PrimeirosPassosSerializer()
    convites = ConviteDoInicioSerializer(many=True)
    indicadores = IndicadoresDaImplantacaoSerializer()


# --- gerente ---


class ItemDeAprovacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    titulo = serializers.CharField()
    detalhe = serializers.CharField(allow_blank=True)
    acoes = serializers.ListField(child=serializers.CharField())


class AprovacoesDoInicioSerializer(serializers.Serializer[Any]):
    total = serializers.IntegerField()
    mais_antigo = serializers.CharField(allow_null=True)
    itens = ItemDeAprovacaoSerializer(many=True)


class PessoaDaEquipeSerializer(serializers.Serializer[Any]):
    usuario_id = serializers.IntegerField()
    nome = serializers.CharField()
    perfil = serializers.CharField()
    resumo = serializers.CharField()
    online = serializers.BooleanField()


class SegmentoSimplesSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    quantidade = serializers.IntegerField()


class FrotaDaFilialSerializer(serializers.Serializer[Any]):
    total = serializers.IntegerField()
    segmentos = SegmentoSimplesSerializer(many=True)


class InicioGerenteSerializer(CabecalhoDoInicioSerializer):
    aprovacoes = AprovacoesDoInicioSerializer()
    kpis = KpiSerializer(many=True)
    equipe_hoje = PessoaDaEquipeSerializer(many=True)
    pendencias = PendenciasSerializer()
    frota_filial = FrotaDaFilialSerializer()
    estoque_a_venda = EstoqueAVendaSerializer(required=False)
    parados_a_venda = ParadosAVendaSerializer(required=False)
    ticket_medio = TicketMedioSerializer(required=False)


# --- vendedor ---


class ParcelaAtrasadaSerializer(serializers.Serializer[Any]):
    conta_id = serializers.IntegerField()
    cliente = serializers.CharField()
    locacao = serializers.CharField()
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    dias = serializers.IntegerField()
    acao = serializers.CharField()


class LocacaoQuePrecisaDeAcaoSerializer(serializers.Serializer[Any]):
    locacao_id = serializers.IntegerField()
    codigo = serializers.CharField()
    cliente = serializers.CharField()
    situacao = SituacaoCurtaSerializer()


class InicioVendedorSerializer(CabecalhoDoInicioSerializer):
    kpis = KpiSerializer(many=True)
    parcelas_atrasadas = ParcelaAtrasadaSerializer(many=True)
    precisam_acao = LocacaoQuePrecisaDeAcaoSerializer(many=True)
    meta = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")
    funil = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")
    comissao_prevista = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")
    propostas = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")


# --- vistoriador ---


class InicioVistoriadorSerializer(CabecalhoDoInicioSerializer):
    agenda = AgendaSerializer()
    avarias_abertas = serializers.IntegerField()


# --- financeiro ---


class ParaHojeSerializer(serializers.Serializer[Any]):
    texto = serializers.CharField()
    tipo = serializers.ChoiceField(choices=["reembolso", "despesa"])
    destino = DestinoSerializer()


class CaixaDoDiaSerializer(serializers.Serializer[Any]):
    filial = serializers.CharField()
    status = serializers.ChoiceField(choices=STATUS_CAIXA)
    aberto_por = serializers.CharField()
    esperado_gaveta_centavos = serializers.IntegerField()


class InicioFinanceiroSerializer(CabecalhoDoInicioSerializer):
    kpis = KpiSerializer(many=True)
    caixas_do_dia = CaixaDoDiaSerializer(many=True, allow_null=True)
    para_hoje = ParaHojeSerializer(many=True)
    fluxo_previsto = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")
    conciliacao = serializers.JSONField(allow_null=True, help_text="Fase 2: sempre `null`.")


SERIALIZER_DA_VARIANTE: dict[str, Any] = {
    "geral": InicioGeralSerializer,
    "implantacao": InicioImplantacaoSerializer,
    "gerente": InicioGerenteSerializer,
    "vendedor": InicioVendedorSerializer,
    "vistoriador": InicioVistoriadorSerializer,
    "financeiro": InicioFinanceiroSerializer,
}

INICIO_RESPOSTA = PolymorphicProxySerializer(
    component_name="InicioDoPainel",
    serializers=SERIALIZER_DA_VARIANTE,
    resource_type_field_name="variante",
)


# --- Configurações (`docs/api/configuracoes.md`) ---


class CartaoDeConfiguracoesSerializer(serializers.Serializer[Any]):
    chave = serializers.ChoiceField(
        choices=[
            "marca",
            "ramo",
            "filiais",
            "usuarios",
            "precos",
            "modelos_contrato",
            "integracoes",
            "notificacoes",
            "assinatura",
            "auditoria",
            "exportar",
            "suporte",
        ]
    )
    titulo = serializers.CharField()
    resumo = serializers.CharField()


class AcaoDaImplantacaoSerializer(serializers.Serializer[Any]):
    rotulo = serializers.CharField()
    destino = serializers.ChoiceField(choices=["nova_locacao", "implantacao"])
    passo = serializers.CharField(required=False)


class ImplantacaoDeConfiguracoesSerializer(serializers.Serializer[Any]):
    concluidos = serializers.IntegerField()
    total = serializers.IntegerField()
    titulo = serializers.CharField()
    faltam = serializers.CharField()
    acao = AcaoDaImplantacaoSerializer(allow_null=True)


class ConfiguracoesSerializer(serializers.Serializer[Any]):
    cartoes = CartaoDeConfiguracoesSerializer(many=True)
    implantacao = ImplantacaoDeConfiguracoesSerializer(allow_null=True)
