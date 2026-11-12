"""Vendas (modelo de dados, item 17; ADR 0037, item 5).

A tabela nasce inteira na T-420, para o módulo de vendas (T-418 e seguintes) não migrar dado
depois. Por enquanto só existe a venda da quitação da locação com intenção de compra (`VEN-11`).
Muda só por `vendas.services`; o status, só por `comum.estados.transicionar`.
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


class OrigemVenda(models.TextChoices):
    """`VEN-11`: só a `balcao` entra em funil, conversão, meta e comissão."""

    BALCAO = "balcao", "Balcão"
    QUITACAO_LOCACAO = "quitacao_locacao", "Quitação de locação"


S = StatusVenda
# Uma venda aberta por veículo (VEN-10); `interessado` não conta.
ABERTAS = (S.PROPOSTA, S.NEGOCIACAO, S.AGUARDANDO_APROVACAO)


class Venda(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO: ClassVar[str] = "VEN"

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="+")
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    vendedor = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    preco_tabela_centavos = CentavosField(null=True, blank=True)  # VEN-01
    desconto_pct = PercentualField(default=Decimal("0"))
    preco_final_centavos = CentavosField(default=0)
    # Vazio na venda da quitação, que não tem forma (VEN-11).
    forma = models.CharField(max_length=20, choices=FormaVenda.choices, blank=True, default="")
    entrada_centavos = CentavosField(null=True, blank=True)
    num_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    juros_pct = PercentualField(default=Decimal("0"))  # VEN-04
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
    proposta_enviada_em = models.DateTimeField(null=True, blank=True)
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

    # A tabela completa das transições do funil é da T-418; aqui fica o que as regras já dizem:
    # `perdida` antes de `vendida`, `cancelada` só a partir de `vendida` (VEN-07).
    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.INTERESSADO: {S.PROPOSTA, S.PERDIDA},
        S.PROPOSTA: {S.NEGOCIACAO, S.AGUARDANDO_APROVACAO, S.VENDIDA, S.PERDIDA},
        S.NEGOCIACAO: {S.PROPOSTA, S.AGUARDANDO_APROVACAO, S.VENDIDA, S.PERDIDA},
        S.AGUARDANDO_APROVACAO: {S.PROPOSTA, S.NEGOCIACAO, S.VENDIDA, S.PERDIDA},
        S.VENDIDA: {S.CANCELADA},
        S.PERDIDA: set(),
        S.CANCELADA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_venda"

    class Meta:
        verbose_name = "venda"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["filial", "status"], name="venda_filial_status"),
            models.Index(fields=["vendedor", "status"], name="venda_vendedor_status"),
            models.Index(
                fields=["filial"],
                condition=models.Q(origem="quitacao_locacao", transferencia_feita_em__isnull=True),
                name="venda_transferencia_pendente",
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
        ]

    def __str__(self) -> str:
        return self.codigo
