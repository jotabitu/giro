"""Vendas (modelo de dados, item 17; ADR 0037, item 5; ADR 0042, itens 2 e 3).

A tabela nasceu inteira na T-420; a T-502 acrescenta os campos do fluxo da venda de balcão:
interessado sem cadastro, desconto e aprovação, as datas do funil e o último contato. A venda da
quitação (`VEN-11`) fica igual. Muda só por `vendas.services`; o status, só por
`comum.estados.transicionar`.
"""

from decimal import Decimal
from typing import ClassVar

from django.db import models

from comum.campos import CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase, ModeloComCodigo


class StatusVenda(models.TextChoices):
    INTERESSADO = "interessado", "Interessado"
    PROPOSTA = "proposta", "Proposta"
    NEGOCIACAO = "negociacao", "Negociação"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao", "Aguardando aprovação"
    VENDIDA = "vendida", "Vendida"
    PERDIDA = "perdida", "Perdida"
    CANCELADA = "cancelada", "Cancelada"


class FormaVenda(models.TextChoices):
    A_VISTA = "a_vista", "À vista"
    ENTRADA_PARCELAS = "entrada_parcelas", "Entrada e parcelas"
    FINANCIAMENTO = "financiamento", "Financiamento"


class AntesDaAprovacao(models.TextChoices):
    """O estado de antes do pedido de desconto, para onde a decisão volta (`VEN-13`)."""

    INTERESSADO = "interessado", "Interessado"
    PROPOSTA = "proposta", "Proposta"
    NEGOCIACAO = "negociacao", "Negociação"


class SituacaoAprovacao(models.TextChoices):
    """A situação do último pedido de desconto (`APR-01`)."""

    PENDENTE = "pendente", "Pendente"
    APROVADO = "aprovado", "Aprovado"
    RECUSADO = "recusado", "Recusado"
    CANCELADO = "cancelado", "Cancelado"


class OrigemVenda(models.TextChoices):
    """`VEN-11`: só a `balcao` entra em funil, conversão, meta e comissão."""

    BALCAO = "balcao", "Balcão"
    QUITACAO_LOCACAO = "quitacao_locacao", "Quitação de locação"


S = StatusVenda
# Uma venda aberta por veículo (VEN-10); `interessado` não conta.
ABERTAS = (S.PROPOSTA, S.NEGOCIACAO, S.AGUARDANDO_APROVACAO)
# O que ainda não fechou: pode ser perdido (VEN-13).
EM_ANDAMENTO = (S.INTERESSADO, *ABERTAS)


class Venda(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO: ClassVar[str] = "VEN"

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    # Nulo só no `interessado` sem cadastro (e na `perdida` que veio dele), `VEN-14`.
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    interessado_nome = models.CharField(max_length=150, blank=True, default="")
    interessado_celular = models.CharField(max_length=13, blank=True, default="")  # só dígitos
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    vendedor = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    preco_tabela_centavos = CentavosField(null=True, blank=True)  # VEN-01
    desconto_pct = PercentualField(default=Decimal("0"))
    desconto_centavos = CentavosField(default=0)  # VEN-02
    preco_final_centavos = CentavosField(default=0)
    # Vazio na venda da quitação, que não tem forma (VEN-11).
    forma = models.CharField(max_length=20, choices=FormaVenda.choices, blank=True, default="")
    entrada_centavos = CentavosField(null=True, blank=True)
    num_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    juros_pct = PercentualField(default=Decimal("0"))  # VEN-04
    parcela_centavos = CentavosField(null=True, blank=True)  # VEN-04; a última leva a diferença
    troca_veiculo = models.ForeignKey(
        "veiculos.Veiculo", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    troca_valor_centavos = CentavosField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=StatusVenda.choices)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True, default="")
    cancelada_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    motivo_perda = models.CharField(max_length=200, blank=True, default="")
    # Desconto acima do limite (VEN-02, APR-01, ADR 0042, item 3).
    status_antes_aprovacao = models.CharField(
        max_length=12, choices=AntesDaAprovacao.choices, blank=True, default=""
    )
    aprovacao = models.CharField(
        max_length=10, choices=SituacaoAprovacao.choices, blank=True, default=""
    )
    pedido_aprovacao_id = models.BigIntegerField(null=True, blank=True)  # origem genérica, sem FK
    desconto_aprovado_pct = PercentualField(null=True, blank=True)
    # Guardados na venda para o texto do VEN-19 sem ler `aprovacoes` (ADR 0019): o desconto do
    # último pedido e quem o decidiu (vem no evento `aprovacoes.pedido_decidido`).
    desconto_pedido_pct = PercentualField(null=True, blank=True)
    aprovacao_decidida_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    motivo_recusa = models.CharField(max_length=300, blank=True, default="")
    # Datas do funil (VEN-08): a primeira entrada, nunca reescrita.
    entrou_proposta_em = models.DateTimeField(null=True, blank=True)
    entrou_negociacao_em = models.DateTimeField(null=True, blank=True)
    proposta_enviada_em = models.DateTimeField(null=True, blank=True)  # o último envio (VEN-13)
    perdida_em = models.DateTimeField(null=True, blank=True)
    ultimo_contato_em = models.DateTimeField(null=True, blank=True)  # VEN-16
    # Assinatura e entrada (VEN-15), usados a partir da fase 1b.
    contrato = models.ForeignKey(
        "contratos.Contrato", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    contrato_assinado_em = models.DateTimeField(null=True, blank=True)
    conta_entrada = models.ForeignKey(
        "financeiro.ContaReceber",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    entrada_paga_em = models.DateTimeField(null=True, blank=True)
    vendida_em = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(
        max_length=20, choices=OrigemVenda.choices, default=OrigemVenda.BALCAO
    )
    locacao = models.OneToOneField(
        "locacoes.Locacao",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    descricao = models.CharField(max_length=120, blank=True, default="")
    transferencia_feita_em = models.DateField(null=True, blank=True)
    transferencia_registrada_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    # ADR 0042, item 2 (VEN-13). `aguardando_aprovacao` volta ao estado de antes do pedido; a
    # que vinha de `interessado` volta a ele só na recusa (aprovada, vira `proposta`). Reenviar a
    # proposta em `negociacao` não muda o estado. `vendida` só pela conclusão (fase 1b).
    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.INTERESSADO: {S.PROPOSTA, S.AGUARDANDO_APROVACAO, S.PERDIDA},
        S.PROPOSTA: {S.NEGOCIACAO, S.AGUARDANDO_APROVACAO, S.VENDIDA, S.PERDIDA},
        S.NEGOCIACAO: {S.AGUARDANDO_APROVACAO, S.VENDIDA, S.PERDIDA},
        S.AGUARDANDO_APROVACAO: {S.INTERESSADO, S.PROPOSTA, S.NEGOCIACAO, S.PERDIDA},
        S.VENDIDA: {S.CANCELADA},
        S.PERDIDA: set(),
        S.CANCELADA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_venda"

    # O interessado sem cadastro é dado pessoal: mascarado na auditoria, como o do cliente.
    CAMPOS_AUDITORIA: ClassVar[dict[str, dict[str, str]]] = {
        "mascarar": {"interessado_nome": "nome", "interessado_celular": "telefone"}
    }

    class Meta:
        verbose_name = "venda"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["filial", "status"], name="venda_filial_status"),
            models.Index(fields=["vendedor", "status"], name="venda_vendedor_status"),
            # As duas origens (VEN-17); a quitação é sempre `vendida`.
            models.Index(
                fields=["filial"],
                condition=models.Q(status="vendida", transferencia_feita_em__isnull=True),
                name="venda_transferencia_pendente",
            ),
            # Ticket, meta e funil (VEN-08, VEN-09, VEN-12) só leem a venda de balcão.
            models.Index(
                fields=["filial", "vendida_em"],
                condition=models.Q(origem="balcao"),
                name="venda_balcao_vendida_em",
            ),
            models.Index(
                fields=["filial", "criado_em"],
                condition=models.Q(origem="balcao"),
                name="venda_balcao_criado_em",
            ),
            # A rotina do vencimento (AUT-19).
            models.Index(
                fields=["proposta_enviada_em"],
                condition=models.Q(status="proposta"),
                name="venda_proposta_enviada",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=models.Q(status__in=["proposta", "negociacao", "aguardando_aprovacao"]),
                name="uma_venda_aberta_por_veiculo",
            ),
            models.CheckConstraint(
                condition=~models.Q(origem="quitacao_locacao")
                | models.Q(locacao__isnull=False, preco_final_centavos=0, status="vendida"),
                name="venda_quitacao_campos",
            ),
            models.CheckConstraint(
                condition=~models.Q(origem="balcao") | models.Q(locacao__isnull=True),
                name="venda_balcao_sem_locacao",
            ),
            # VEN-14: sem cadastro, só `interessado` (ou a `perdida` que veio dele), com o nome.
            models.CheckConstraint(
                condition=models.Q(cliente__isnull=False)
                | models.Q(status__in=["interessado", "perdida"]),
                name="venda_sem_cliente_so_interessado",
            ),
            models.CheckConstraint(
                condition=models.Q(cliente__isnull=False) | ~models.Q(interessado_nome=""),
                name="venda_sem_cliente_com_nome",
            ),
            models.CheckConstraint(
                condition=models.Q(desconto_pct__gte=0, desconto_pct__lte=100),
                name="venda_desconto_0_a_100",
            ),
            models.CheckConstraint(
                condition=~models.Q(forma="entrada_parcelas")
                | models.Q(num_parcelas__gte=2, num_parcelas__lte=24),
                name="venda_parcelas_2_a_24",
            ),
        ]

    def __str__(self) -> str:
        return self.codigo


class MetaVenda(ModeloBase):
    """Meta de vendas do vendedor na filial e no mês (`VEN-09`, ADR 0042, item 3). O serviço e as
    rotas entram na fase 1c. "Sem meta" é não ter linha."""

    vendedor = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    mes = models.DateField()  # dia 1
    valor_centavos = CentavosField()
    definida_por = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = "meta de vendas"
        verbose_name_plural = "metas de vendas"
        constraints = [
            models.UniqueConstraint(
                fields=["vendedor", "filial", "mes"], name="meta_venda_vendedor_filial_mes"
            ),
            models.CheckConstraint(
                condition=models.Q(valor_centavos__gt=0), name="meta_venda_valor_positivo"
            ),
        ]

    def __str__(self) -> str:
        return f"Meta de {self.mes:%m/%Y}"
