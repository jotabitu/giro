"""Pedidos de aprovação (APR-01 a APR-10, ADR 0019).

Modelo em `docs/decisoes/modelo-de-dados.md` ("PedidoAprovacao"). O pedido não conhece a
origem: guarda a origem genérica da ADR 0011 e os textos prontos que a origem montou.
"""

from typing import ClassVar

from django.db import models

from comum.campos import CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase


class TipoPedido(models.TextChoices):
    APR_01 = "APR-01", "Desconto"
    APR_02 = "APR-02", "Cancelamento de locação"
    APR_03 = "APR-03", "Despesa ou orçamento de OS"
    APR_04 = "APR-04", "Diferença no caixa"
    APR_05 = "APR-05", "Desbloqueio de cliente"
    APR_06 = "APR-06", "Correção de km para baixo"


class OrigemPedido(models.TextChoices):
    """Origem genérica (ADR 0011, item 2)."""

    LOCACAO = "locacao", "Locação"
    VENDA = "venda", "Venda"
    ORDEM_SERVICO = "ordem_servico", "Ordem de serviço"
    DESPESA = "despesa", "Despesa"
    DEVOLUCAO = "devolucao", "Devolução"
    CAIXA = "caixa", "Caixa"
    CLIENTE = "cliente", "Cliente"
    VEICULO = "veiculo", "Veículo"


class PedidoAprovacao(MaquinaDeEstados, ModeloBase):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADO = "aprovado", "Aprovado"
        RECUSADO = "recusado", "Recusado"
        CANCELADO = "cancelado", "Cancelado"

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "pendente": {"aprovado", "recusado", "cancelado"},
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_pedido"  # 409 em pedido já decidido

    tipo = models.CharField(max_length=6, choices=TipoPedido.choices)
    origem_tipo = models.CharField(max_length=15, choices=OrigemPedido.choices)
    origem_id = models.BigIntegerField()
    origem_codigo = models.CharField(max_length=20, blank=True, default="")
    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    solicitante = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, related_name="pedidos_feitos"
    )
    aprovador = models.ForeignKey(
        "contas.Usuario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedidos_decididos",
    )
    motivo_pedido = models.CharField(max_length=300, blank=True, default="")
    titulo = models.CharField(max_length=120)
    detalhe = models.CharField(max_length=300)
    valor_centavos = CentavosField(null=True, blank=True)
    pct = PercentualField(null=True, blank=True)
    # Chaves fixas por tipo, sem dado pessoal (contrato de aprovações, "dados por tipo").
    dados = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    motivo_recusa = models.CharField(max_length=300, blank=True, default="")
    decidido_em = models.DateTimeField(null=True, blank=True)
    lembrete_enviado_em = models.DateTimeField(null=True, blank=True)  # APR-08
    # APR-09 (T-250): o administrador decidiu o próprio pedido; a API devolve `proprio_pedido`.
    decidido_pelo_solicitante = models.BooleanField(default=False)

    class Meta:
        verbose_name = "pedido de aprovação"
        verbose_name_plural = "pedidos de aprovação"
        ordering = ["criado_em", "id"]
        indexes = [
            models.Index(fields=["origem_tipo", "origem_id"], name="pedido_origem"),
            models.Index(fields=["filial", "status"], name="pedido_filial_status"),
        ]
        constraints = [
            # APR-09: quem pediu não decide o próprio pedido, salvo o administrador, sempre com
            # a marca. O perfil é conferido no serviço; o banco garante a marca (T-250).
            models.CheckConstraint(
                condition=models.Q(aprovador__isnull=True)
                | ~models.Q(aprovador=models.F("solicitante"))
                | models.Q(decidido_pelo_solicitante=True),
                name="pedido_quem_pede_nao_aprova",
            ),
            models.CheckConstraint(
                condition=models.Q(decidido_pelo_solicitante=False)
                | models.Q(aprovador=models.F("solicitante")),
                name="pedido_marca_so_do_solicitante",
            ),
            models.UniqueConstraint(
                fields=["tipo", "origem_tipo", "origem_id"],
                condition=models.Q(status="pendente"),
                name="pedido_um_pendente_por_origem",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} · {self.origem_tipo} {self.origem_id} · {self.status}"
