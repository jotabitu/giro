"""Contas a receber e comissões (modelo de dados, itens 18 e 24).

Parte mínima, entregue com a T-015 (parte 1): a locação confirmada cria as contas e a comissão
por `financeiro.services`. A baixa no caixa, os movimentos, as cobranças externas e a API entram
com a T-017, que acrescenta `movimento_caixa` e os demais apoios.
"""

from typing import ClassVar

from django.db import models

from comum.auditoria import Categoria
from comum.campos import CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase


class OrigemTipo(models.TextChoices):
    """Origem genérica (ADR 0011): o financeiro não conhece quem criou a conta."""

    LOCACAO = "locacao", "Locação"
    VENDA = "venda", "Venda"
    ORDEM_SERVICO = "ordem_servico", "Ordem de serviço"
    DESPESA = "despesa", "Despesa"
    DEVOLUCAO = "devolucao", "Devolução"
    CAIXA = "caixa", "Caixa"
    CLIENTE = "cliente", "Cliente"
    VEICULO = "veiculo", "Veículo"


class ComOrigem(models.Model):
    origem_tipo = models.CharField(max_length=15, choices=OrigemTipo.choices)
    origem_id = models.BigIntegerField()
    origem_codigo = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        abstract = True


class TipoConta(models.TextChoices):
    PARCELA = "parcela", "Parcela"
    CAUCAO = "caucao", "Caução"  # não é receita (LOC-04, FIN-13)
    MULTA = "multa", "Multa"
    AVARIA = "avaria", "Avaria"
    ACERTO = "acerto", "Acerto"
    OUTRO = "outro", "Outro"


class StatusConta(models.TextChoices):
    """Guardados. `vence_hoje` e `atrasada` são calculados no selector (FIN-01)."""

    ABERTA = "aberta", "Aberta"
    PAGA = "paga", "Paga"
    CANCELADA = "cancelada", "Cancelada"
    RENEGOCIADA = "renegociada", "Renegociada"


class FormaPagamento(models.TextChoices):
    PIX = "pix", "Pix"
    BOLETO = "boleto", "Boleto"
    CARTAO_DEBITO = "cartao_debito", "Cartão de débito"
    CARTAO_CREDITO = "cartao_credito", "Cartão de crédito"
    DINHEIRO = "dinheiro", "Dinheiro"
    PIX_AUTOMATICO = "pix_automatico", "Pix automático"
    CAUCAO = "caucao", "Caução"  # paga com a caução no acerto (DEV-02)


class ContaReceber(MaquinaDeEstados, ModeloBase, ComOrigem):
    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=10, choices=TipoConta.choices)
    total_parcelas = models.PositiveSmallIntegerField(null=True, blank=True)
    numero_parcela = models.PositiveSmallIntegerField(null=True, blank=True)
    vencimento = models.DateField()
    valor_centavos = CentavosField()
    multa_centavos = CentavosField(default=0)
    juros_centavos = CentavosField(default=0)
    status = models.CharField(max_length=12, choices=StatusConta.choices, default="aberta")
    forma = models.CharField(max_length=15, choices=FormaPagamento.choices, blank=True, default="")
    pago_em = models.DateTimeField(null=True, blank=True)
    observacao = models.CharField(max_length=150, blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "aberta": {"paga", "cancelada", "renegociada"},
        "paga": set(),  # paga não se edita: correção é estorno (T-017)
        "cancelada": set(),
        "renegociada": set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_conta"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "conta a receber"
        verbose_name_plural = "contas a receber"
        ordering = ["vencimento", "id"]
        indexes = [
            models.Index(fields=["status", "vencimento"], name="conta_status_vencimento"),
            models.Index(fields=["cliente", "status"], name="conta_cliente_status"),
            models.Index(fields=["filial", "vencimento"], name="conta_filial_vencimento"),
            models.Index(fields=["origem_tipo", "origem_id"], name="conta_origem"),
        ]

    def __str__(self) -> str:
        return f"{self.origem_codigo or self.origem_tipo} {self.tipo} {self.vencimento}"


class RegraComissao(models.TextChoices):
    PERCENTUAL_VENDA = "percentual_venda", "Percentual da venda"
    FIXO_LOCACAO = "fixo_locacao", "Fixo por locação"


class StatusComissao(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    CONFIRMADA = "confirmada", "Confirmada"
    PAGA = "paga", "Paga"
    ESTORNADA = "estornada", "Estornada"


class Comissao(MaquinaDeEstados, ModeloBase, ComOrigem):
    """FIN-09. A de locação nasce `pendente` na confirmação e fica `confirmada` na ativação."""

    usuario = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    base_centavos = CentavosField()
    regra = models.CharField(max_length=20, choices=RegraComissao.choices)
    pct = PercentualField(null=True, blank=True)
    valor_centavos = CentavosField()
    status = models.CharField(max_length=12, choices=StatusComissao.choices, default="pendente")
    mes_pagamento = models.DateField(null=True, blank=True)  # dia 1; paga no dia 5 desse mês

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "pendente": {"confirmada", "estornada"},
        "confirmada": {"paga", "estornada"},
        "paga": set(),
        "estornada": set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_comissao"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "comissão"
        verbose_name_plural = "comissões"
        indexes = [
            models.Index(
                fields=["usuario", "mes_pagamento", "status"], name="comissao_usuario_mes"
            ),
            models.Index(fields=["origem_tipo", "origem_id"], name="comissao_origem"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["origem_tipo", "origem_id", "usuario"],
                condition=~models.Q(status="estornada"),
                name="comissao_uma_por_origem",
            )
        ]

    def __str__(self) -> str:
        return f"{self.origem_codigo or self.origem_tipo}: {self.valor_centavos}"
