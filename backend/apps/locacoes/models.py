"""Planos especiais, locações, extras e trechos (modelo de dados, itens 12 e 13; LOC-01 a LOC-15).

Muda só por `locacoes.services`; o status da locação, só por `comum.estados.transicionar`.
"""

from decimal import Decimal
from typing import ClassVar

from django.db import models

from comum.campos import CentavosComSinalField, CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase, ModeloComCodigo


class Periodicidade(models.TextChoices):
    DIARIA = "diaria", "Diária"
    SEMANAL = "semanal", "Semanal"
    MENSAL = "mensal", "Mensal"


class PlanoEspecial(ModeloBase, ModeloAtivavel):
    """LOC-01: substitui o preço do período (`preco_fixo`) ou desconta a partir de um período
    (`desconto`). Sem categorias, vale para todas."""

    class Regra(models.TextChoices):
        PRECO_FIXO = "preco_fixo", "Preço fixo"
        DESCONTO = "desconto", "Desconto"

    nome = models.CharField(max_length=60, unique=True)
    periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices)
    regra = models.CharField(max_length=12, choices=Regra.choices)
    preco_centavos = CentavosField(null=True, blank=True)
    desconto_pct = PercentualField(null=True, blank=True)
    a_partir_do_periodo = models.PositiveSmallIntegerField(null=True, blank=True)
    categorias = models.ManyToManyField("veiculos.Categoria", blank=True, related_name="+")
    condicoes = models.TextField(blank=True, default="")

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

    class Meta:
        verbose_name = "plano especial"
        verbose_name_plural = "planos especiais"
        ordering = ["nome"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        regra="preco_fixo",
                        preco_centavos__isnull=False,
                        desconto_pct__isnull=True,
                    )
                    | models.Q(
                        regra="desconto",
                        desconto_pct__isnull=False,
                        preco_centavos__isnull=True,
                    )
                ),
                name="plano_especial_campo_da_regra",
            )
        ]

    def __str__(self) -> str:
        return self.nome


class StatusLocacao(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    AGUARDANDO_RETIRADA = "aguardando_retirada", "Aguardando retirada"
    ATIVA = "ativa", "Ativa"
    DEVOLUCAO_ATRASADA = "devolucao_atrasada", "Devolução atrasada"
    ENCERRADA = "encerrada", "Encerrada"
    CANCELADA = "cancelada", "Cancelada"


S = StatusLocacao
# Ocupam o veículo: uma por veículo (restrição do banco, LOC-03).
ABERTAS = (S.AGUARDANDO_RETIRADA, S.ATIVA, S.DEVOLUCAO_ATRASADA)
TRANSICOES_LOCACAO: dict[str, set[str]] = {
    S.RASCUNHO: {S.AGUARDANDO_RETIRADA, S.CANCELADA},
    S.AGUARDANDO_RETIRADA: {S.ATIVA, S.CANCELADA},
    S.ATIVA: {S.DEVOLUCAO_ATRASADA, S.ENCERRADA, S.CANCELADA},
    S.DEVOLUCAO_ATRASADA: {S.ATIVA, S.ENCERRADA, S.CANCELADA},
    S.ENCERRADA: set(),
    S.CANCELADA: set(),
}


class FormaPagamento(models.TextChoices):
    PIX = "pix", "Pix"
    PIX_AUTOMATICO = "pix_automatico", "Pix automático"
    CARTAO = "cartao", "Cartão"
    BOLETO = "boleto", "Boleto"
    DINHEIRO = "dinheiro", "Dinheiro"


class ParcelamentoMensal(models.TextChoices):
    A_VISTA = "a_vista", "À vista"
    QUATRO_SEMANAIS = "quatro_semanais", "4 parcelas semanais"


class StatusDesconto(models.TextChoices):
    """Pedido `APR-01` do desconto acima do limite (`LOC-03`) e `APR-02` do cancelamento
    (`LOC-12`). Vazio: sem pedido."""

    PENDENTE = "pendente", "Pendente"
    APROVADO = "aprovado", "Aprovado"
    RECUSADO = "recusado", "Recusado"
    CANCELADO = "cancelado", "Cancelado"


class Locacao(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO: ClassVar[str] = "LOC"

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="+")
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    vendedor = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices)
    plano_especial = models.ForeignKey(
        PlanoEspecial, on_delete=models.PROTECT, null=True, blank=True, related_name="locacoes"
    )
    periodos = models.PositiveSmallIntegerField(default=1)
    inicio = models.DateTimeField()
    fim_previsto = models.DateTimeField()
    devolvida_em = models.DateTimeField(null=True, blank=True)
    # Preço do período pela tabela ou pelo plano de preço fixo, sem descontos; congelado na
    # confirmação (LOC-15). Base de LOC-12.
    valor_periodo_centavos = CentavosField(default=0)
    diaria_centavos = CentavosField(default=0)  # base de LOC-10 e da multa mínima (LOC-12)
    caucao_centavos = CentavosField(default=0)  # LOC-04
    precos_de = models.DateField(null=True, blank=True)  # data da tabela congelada
    desconto_pct = PercentualField(default=Decimal("0.00"))  # o que vale nas parcelas
    desconto_pedido_pct = PercentualField(null=True, blank=True)  # APR-01
    desconto_status = models.CharField(
        max_length=10, choices=StatusDesconto.choices, blank=True, default=""
    )
    pedido_desconto_id = models.BigIntegerField(null=True, blank=True)  # ADR 0019, sem FK
    forma_pagamento = models.CharField(max_length=15, choices=FormaPagamento.choices)
    parcelamento_mensal = models.CharField(
        max_length=15, choices=ParcelamentoMensal.choices, blank=True, default=""
    )
    primeiro_vencimento = models.DateField(null=True, blank=True)
    # Formulário do rascunho: [{extra_id, quantidade}]. Na confirmação vira `ExtraLocacao`.
    extras_rascunho = models.JSONField(default=list, blank=True)
    # Último uso do rascunho, pelo relógio do domínio; com 24 h sem uso ele é cancelado.
    usado_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusLocacao.choices, default=S.RASCUNHO)
    vistoria_saida_ok_em = models.DateTimeField(null=True, blank=True)
    contrato_assinado_em = models.DateTimeField(null=True, blank=True)
    primeiro_pagamento_em = models.DateTimeField(null=True, blank=True)
    renovacoes = models.PositiveSmallIntegerField(default=0)  # LOC-08
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True, default="")
    km_saida = models.PositiveIntegerField(null=True, blank=True)
    encerramento_antecipado_aprovado_em = models.DateTimeField(null=True, blank=True)
    multa_encerramento_centavos = CentavosField(null=True, blank=True)
    # Pedido `APR-02` (LOC-12), como o do desconto: vazio sem pedido; sem FK (ADR 0019).
    cancelamento_status = models.CharField(
        max_length=10, choices=StatusDesconto.choices, blank=True, default=""
    )
    pedido_cancelamento_id = models.BigIntegerField(null=True, blank=True)
    cancelamento_data = models.DateField(null=True, blank=True)  # dia do encerramento
    cancelamento_forma = models.CharField(max_length=15, blank=True, default="")  # da devolução
    # LOC-13: semanas (ou diárias) não usadas, a creditar no acerto da devolução (T-016). No
    # mensal em 4 semanais, menos as parcelas canceladas: é um saldo e pode ser negativo.
    credito_encerramento_centavos = CentavosComSinalField(null=True, blank=True)
    # LOC-08: o atraso já corrido quando a locação é renovada depois do prazo; continua cobrado.
    atraso_anterior_dias = models.PositiveSmallIntegerField(default=0)
    atraso_anterior_centavos = CentavosField(default=0)

    TRANSICOES: ClassVar[dict[str, set[str]]] = TRANSICOES_LOCACAO
    REGRA_TRANSICAO: ClassVar[str] = "transicao_locacao"

    class Meta:
        verbose_name = "locação"
        verbose_name_plural = "locações"
        ordering = ["-numero"]
        indexes = [
            models.Index(fields=["filial", "status"], name="locacao_filial_status"),
            models.Index(fields=["status", "fim_previsto"], name="locacao_status_fim"),
            models.Index(fields=["cliente"], name="locacao_cliente"),
            models.Index(fields=["veiculo"], name="locacao_veiculo"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=models.Q(status__in=ABERTAS),
                name="uma_locacao_aberta_por_veiculo",
            ),
            models.CheckConstraint(
                condition=models.Q(fim_previsto__gt=models.F("inicio")),
                name="locacao_fim_depois_do_inicio",
            ),
        ]

    def __str__(self) -> str:
        return self.codigo


class ExtraLocacao(ModeloBase):
    """LOC-02: valor do cadastro congelado na confirmação."""

    locacao = models.ForeignKey(Locacao, on_delete=models.PROTECT, related_name="extras")
    extra = models.ForeignKey("veiculos.Extra", on_delete=models.PROTECT, related_name="+")
    nome = models.CharField(max_length=60)
    quantidade = models.PositiveSmallIntegerField(default=1)
    valor_centavos = CentavosField()
    cobranca = models.CharField(max_length=12)  # por_periodo ou unica, como no cadastro

    # Nome do extra, não de pessoa (R-02 da T-050).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

    class Meta:
        verbose_name = "extra da locação"
        verbose_name_plural = "extras da locação"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.locacao_id}: {self.nome} × {self.quantidade}"


class TrechoLocacao(ModeloBase):
    """Cada veículo da locação (LOC-09). Um trecho aberto por vez."""

    locacao = models.ForeignKey(Locacao, on_delete=models.PROTECT, related_name="trechos")
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    inicio = models.DateTimeField()
    fim = models.DateTimeField(null=True, blank=True)
    valor_periodo_centavos = CentavosField()
    diaria_centavos = CentavosField()

    class Meta:
        verbose_name = "trecho da locação"
        verbose_name_plural = "trechos da locação"
        ordering = ["inicio", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["locacao"],
                condition=models.Q(fim__isnull=True),
                name="um_trecho_aberto_por_locacao",
            )
        ]

    def __str__(self) -> str:
        return f"{self.locacao_id}: {self.veiculo_id}"


class StatusTroca(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    CONCLUIDA = "concluida", "Concluída"
    CANCELADA = "cancelada", "Cancelada"


class TrocaVeiculo(MaquinaDeEstados, ModeloBase):
    """LOC-09: a devolução do veículo antigo e a saída do novo, na mesma locação. Pendente até as
    duas vistorias serem concluídas. Uma pendente por locação."""

    locacao = models.ForeignKey(Locacao, on_delete=models.PROTECT, related_name="trocas")
    veiculo_antigo = models.ForeignKey(
        "veiculos.Veiculo", on_delete=models.PROTECT, related_name="+"
    )
    veiculo_novo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    motivo = models.TextField()
    status = models.CharField(max_length=10, choices=StatusTroca.choices, default="pendente")
    pedida_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # As vistorias ficam em `vistorias`, acima de `locacoes` (ADR 0011): só os ids, sem FK.
    vistoria_devolucao_id = models.BigIntegerField(null=True, blank=True)
    vistoria_saida_id = models.BigIntegerField(null=True, blank=True)
    # A diferença de caução cobrada na troca, quando a nova categoria pede mais (LOC-09).
    conta_caucao_id = models.BigIntegerField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        StatusTroca.PENDENTE: {StatusTroca.CONCLUIDA, StatusTroca.CANCELADA},
        StatusTroca.CONCLUIDA: set(),
        StatusTroca.CANCELADA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_troca"

    class Meta:
        verbose_name = "troca de veículo"
        verbose_name_plural = "trocas de veículo"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["locacao"],
                condition=models.Q(status="pendente"),
                name="uma_troca_pendente_por_locacao",
            )
        ]

    def __str__(self) -> str:
        return f"{self.locacao_id}: {self.veiculo_antigo_id} → {self.veiculo_novo_id}"
