"""Contas a receber, despesas, caixa do dia, reembolsos e comissões (modelo de dados, itens 18,
19, 21, 22 e 24).

A T-015 trouxe as contas e a comissão; a T-091, o `Reembolso`; a T-017, o caixa do dia e os
movimentos, a baixa, o estorno, as cobranças externas (Pix e boleto), as pendências do webhook e
as despesas.
"""

from datetime import date
from typing import Any, ClassVar

from django.db import models
from django.utils import timezone

from comum import arquivos
from comum.auditoria import Categoria
from comum.campos import CentavosComSinalField, CentavosField, PercentualField
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


class Renegociacao(ModeloBase, ComOrigem):
    """Contas `renegociada` trocadas por contas novas (FIN-01). N originais viram M novas: as
    originais apontam para cá por `renegociada_em`, e as novas por `nasceu_de`. No acerto da
    devolução (DEV-02), as parcelas que a caução não cobre viram a conta `acerto` (origem
    `devolucao`, sem `por`: é o sistema)."""

    motivo = models.CharField(max_length=200)
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    em = models.DateTimeField()

    class Meta:
        verbose_name = "renegociação"
        verbose_name_plural = "renegociações"
        indexes = [models.Index(fields=["origem_tipo", "origem_id"], name="renegociacao_origem")]

    def __str__(self) -> str:
        return f"{self.origem_codigo or self.origem_tipo}: {self.motivo}"


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
    # Duas ligações, porque uma conta nova pode ser renegociada de novo (FIN-01, DEV-02).
    renegociada_em = models.ForeignKey(
        Renegociacao, on_delete=models.PROTECT, null=True, blank=True, related_name="originais"
    )
    nasceu_de = models.ForeignKey(
        Renegociacao, on_delete=models.PROTECT, null=True, blank=True, related_name="novas"
    )
    movimento_caixa = models.ForeignKey(
        "MovimentoCaixa", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # Paga não se edita: o estorno reabre uma conta nova igual, que aponta para a original.
    estorno_de = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="estornos"
    )
    estornada_em = models.DateTimeField(null=True, blank=True)

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


class FormaReembolso(models.TextChoices):
    PIX = "pix", "Pix"
    DINHEIRO = "dinheiro", "Dinheiro"
    ESTORNO_CARTAO = "estorno_cartao", "Estorno no cartão"


class StatusReembolso(models.TextChoices):
    A_FAZER = "a_fazer", "A fazer"
    FEITO = "feito", "Feito"


class Reembolso(MaquinaDeEstados, ModeloBase, ComOrigem):
    """Dinheiro que volta ao cliente (DEV-02, LOC-12, LOC-13). Pix e estorno no cartão nascem
    `a_fazer`: a pessoa faz pela conta da locadora e marca como feito, com o comprovante. O
    dinheiro sai pelo caixa aberto da filial e nasce `feito` (`movimento_caixa`)."""

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="+")
    valor_centavos = CentavosField()
    forma = models.CharField(max_length=15, choices=FormaReembolso.choices)
    status = models.CharField(max_length=10, choices=StatusReembolso.choices, default="a_fazer")
    motivo = models.CharField(max_length=200, blank=True, default="")
    feito_em = models.DateTimeField(null=True, blank=True)
    feito_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    comprovante = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    movimento_caixa = models.ForeignKey(
        "MovimentoCaixa", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    TRANSICOES: ClassVar[dict[str, set[str]]] = {"a_fazer": {"feito"}, "feito": set()}
    REGRA_TRANSICAO: ClassVar[str] = "transicao_reembolso"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "reembolso"
        verbose_name_plural = "reembolsos"
        ordering = ["criado_em", "id"]
        indexes = [
            models.Index(fields=["status", "filial"], name="reembolso_status_filial"),
            models.Index(fields=["origem_tipo", "origem_id"], name="reembolso_origem"),
        ]

    def __str__(self) -> str:
        return f"{self.origem_codigo or self.origem_tipo}: {self.valor_centavos}"


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


# --- Caixa do dia (FIN-07, FIN-08, APR-04) ---


class StatusCaixa(models.TextChoices):
    ABERTO = "aberto", "Aberto"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao", "Aguardando aprovação"
    FECHADO = "fechado", "Fechado"
    FECHADO_SEM_CONFERENCIA = "fechado_sem_conferencia", "Fechado sem conferência"


class Caixa(MaquinaDeEstados, ModeloBase):
    """Um por filial por dia (FIN-07), no dia de `America/Sao_Paulo`. A gaveta esperada é troco
    + entradas em dinheiro − saídas em dinheiro."""

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    data = models.DateField()
    aberto_por = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    troco_centavos = CentavosField()
    contado_centavos = CentavosField(null=True, blank=True)
    esperado_centavos = CentavosField(null=True, blank=True)
    diferenca_centavos = CentavosComSinalField(null=True, blank=True)
    motivo_diferenca = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=25, choices=StatusCaixa.choices, default="aberto")
    fechado_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    fechado_em = models.DateTimeField(null=True, blank=True)
    pedido_aprovacao_id = models.BigIntegerField(null=True, blank=True)  # APR-04

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "aberto": {"aguardando_aprovacao", "fechado", "fechado_sem_conferencia"},
        "aguardando_aprovacao": {"fechado", "aberto"},  # recusada: a pessoa conta de novo
        "fechado": set(),
        "fechado_sem_conferencia": set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "FIN-07"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "caixa do dia"
        verbose_name_plural = "caixas do dia"
        ordering = ["-data", "id"]
        indexes = [models.Index(fields=["status", "data"], name="caixa_status_data")]
        constraints = [
            models.UniqueConstraint(fields=["filial", "data"], name="caixa_um_por_filial_por_dia")
        ]

    def __str__(self) -> str:
        return f"Caixa {self.filial_id} {self.data}"


class TipoMovimento(models.TextChoices):
    ENTRADA = "entrada", "Entrada"
    SAIDA = "saida", "Saída"
    SANGRIA = "sangria", "Sangria"


class FormaMovimento(models.TextChoices):
    DINHEIRO = "dinheiro", "Dinheiro"
    PIX = "pix", "Pix"
    CARTAO_DEBITO = "cartao_debito", "Cartão de débito"
    CARTAO_CREDITO = "cartao_credito", "Cartão de crédito"


class MovimentoImutavel(RuntimeError):
    """Movimento de caixa não se edita nem se apaga: a correção é um estorno (CA-017-17)."""


class MovimentoCaixa(ModeloBase):
    """Entrada, saída ou sangria de um caixa `aberto`. Imutável: a correção é um movimento de
    estorno (`estorno_de`), do mesmo tipo e forma, que o resumo do dia desconta."""

    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name="movimentos")
    tipo = models.CharField(max_length=10, choices=TipoMovimento.choices)
    forma = models.CharField(max_length=15, choices=FormaMovimento.choices)
    valor_centavos = CentavosField()
    # Origem genérica opcional (ADR 0011): conta a receber, despesa, devolução.
    origem_tipo = models.CharField(
        max_length=15, choices=OrigemTipo.choices, blank=True, default=""
    )
    origem_id = models.BigIntegerField(null=True, blank=True)
    origem_codigo = models.CharField(max_length=20, blank=True, default="")
    descricao = models.CharField(max_length=150)
    # Nulo quando é o Sistema (Pix gerado no caixa e pago pelo webhook).
    registrado_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    estorno_de = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="estorno"
    )

    class Meta:
        verbose_name = "movimento de caixa"
        verbose_name_plural = "movimentos de caixa"
        ordering = ["criado_em", "id"]
        indexes = [models.Index(fields=["caixa", "tipo", "forma"], name="movimento_caixa_tipo")]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise MovimentoImutavel("Movimento de caixa não se edita. Faça um estorno.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise MovimentoImutavel("Movimento de caixa não se apaga. Faça um estorno.")

    def __str__(self) -> str:
        return f"{self.tipo} {self.forma} {self.valor_centavos}"


# --- Cobranças externas e pendências do webhook (FIN-04, AUT-05, S-14) ---


class TipoCobranca(models.TextChoices):
    PIX = "pix", "Pix"
    BOLETO = "boleto", "Boleto"
    CARTAO_LINK = "cartao_link", "Link de cartão"
    RECORRENTE = "recorrente", "Recorrente"


class StatusCobranca(models.TextChoices):
    AGUARDANDO = "aguardando", "Aguardando"
    PAGA = "paga", "Paga"
    CANCELADA = "cancelada", "Cancelada"
    VENCIDA = "vencida", "Vencida"
    DIVERGENTE = "divergente", "Divergente"


class CobrancaExterna(MaquinaDeEstados, ModeloBase):
    """Pix ou boleto gerado no parceiro para uma conta. O valor é o devido no dia (FIN-03) e é
    comparado com o valor pago antes da baixa (S-14). Uma `aguardando` por conta."""

    conta_receber = models.ForeignKey(
        ContaReceber, on_delete=models.PROTECT, related_name="cobrancas"
    )
    tipo = models.CharField(max_length=12, choices=TipoCobranca.choices)
    externo_id = models.CharField(max_length=60, unique=True)
    valor_centavos = CentavosField()
    vence_em = models.DateField()
    # O dia (America/Sao_Paulo, pelo `comum.relogio`) em que a cobrança foi gerada: a multa e os
    # juros da baixa são os desse dia (T-144). Nulo nas anteriores à T-029, que usam `criado_em`.
    gerada_no_dia = models.DateField(null=True, blank=True)
    pix_copia_e_cola = models.TextField(blank=True, default="")
    linha_digitavel = models.CharField(max_length=60, blank=True, default="")
    url = models.CharField(max_length=300, blank=True, default="")
    # Gerada pela tela Caixa: a baixa pelo webhook entra nesse caixa (FIN-07).
    caixa = models.ForeignKey(
        Caixa, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=12, choices=StatusCobranca.choices, default="aguardando")

    def dia_da_geracao(self) -> date:
        return self.gerada_no_dia or timezone.localdate(self.criado_em)

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "aguardando": {"paga", "cancelada", "vencida", "divergente"},
        "paga": set(),
        "cancelada": set(),
        "vencida": set(),
        "divergente": set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_cobranca"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "cobrança externa"
        verbose_name_plural = "cobranças externas"
        ordering = ["criado_em", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["conta_receber"],
                condition=models.Q(status="aguardando"),
                name="cobranca_uma_aguardando_por_conta",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tipo} {self.externo_id}"


class MotivoPendencia(models.TextChoices):
    VALOR_DIFERENTE = "valor_diferente", "Valor pago diferente"
    ESTORNADA_NO_PARCEIRO = "estornada_no_parceiro", "Estornada no parceiro"
    SEM_CONTA = "sem_conta", "Sem conta"


class StatusPendencia(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    RESOLVIDA = "resolvida", "Resolvida"


class PendenciaPagamento(MaquinaDeEstados, ModeloBase):
    """Pagamento que o sistema não baixou sozinho (S-14): o financeiro decide."""

    cobranca = models.ForeignKey(CobrancaExterna, on_delete=models.PROTECT, related_name="+")
    motivo = models.CharField(max_length=25, choices=MotivoPendencia.choices)
    valor_pago_centavos = CentavosField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusPendencia.choices, default="aberta")
    resolucao = models.CharField(max_length=200, blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = {"aberta": {"resolvida"}, "resolvida": set()}
    REGRA_TRANSICAO: ClassVar[str] = "transicao_pendencia"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "pendência de pagamento"
        verbose_name_plural = "pendências de pagamento"
        ordering = ["criado_em", "id"]

    def __str__(self) -> str:
        return f"{self.motivo} {self.cobranca_id}"


# --- Despesas (FIN-05, FIN-06, APR-03) ---


class CategoriaDespesa(models.TextChoices):
    FIXAS = "fixas", "Fixas"
    MANUTENCAO = "manutencao", "Manutenção"
    RASTREAMENTO = "rastreamento", "Rastreamento"
    IMPOSTOS = "impostos", "Impostos"
    PESSOAL = "pessoal", "Pessoal"
    OUTROS = "outros", "Outros"


class StatusDespesa(models.TextChoices):
    AGUARDANDO_APROVACAO = "aguardando_aprovacao", "Aguardando aprovação"
    A_PAGAR = "a_pagar", "A pagar"
    PAGA = "paga", "Paga"
    RECUSADA = "recusada", "Recusada"


class FormaDespesa(models.TextChoices):
    PIX = "pix", "Pix"
    BOLETO = "boleto", "Boleto"
    CARTAO = "cartao", "Cartão"
    TRANSFERENCIA = "transferencia", "Transferência"
    DINHEIRO = "dinheiro", "Dinheiro"


class Despesa(MaquinaDeEstados, ModeloBase):
    """Conta a pagar (FIN-05). Acima de R$ 500 nasce `aguardando_aprovacao` (APR-03); até R$ 500,
    `a_pagar`, ou `paga` quando lançada como paga no caixa."""

    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    data = models.DateField()
    descricao = models.CharField(max_length=150)
    categoria = models.CharField(max_length=15, choices=CategoriaDespesa.choices)
    valor_centavos = CentavosField()
    vencimento = models.DateField()
    # Custo do veículo (FIN-06, VEI-05).
    veiculo = models.ForeignKey(
        "veiculos.Veiculo", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    nota = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    comprovante = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=25, choices=StatusDespesa.choices)
    pago_em = models.DateTimeField(null=True, blank=True)
    forma = models.CharField(max_length=15, choices=FormaDespesa.choices, blank=True, default="")
    movimento_caixa = models.ForeignKey(
        MovimentoCaixa, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    lancada_por = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    pedido_aprovacao_id = models.BigIntegerField(null=True, blank=True)  # APR-03
    motivo_recusa = models.CharField(max_length=300, blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "aguardando_aprovacao": {"a_pagar", "recusada"},
        "a_pagar": {"paga"},
        "paga": set(),
        "recusada": set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_despesa"
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.FINANCEIRO

    class Meta:
        verbose_name = "despesa"
        verbose_name_plural = "despesas"
        ordering = ["-data", "-id"]
        indexes = [
            models.Index(fields=["status", "vencimento"], name="despesa_status_vencimento"),
            models.Index(fields=["veiculo"], name="despesa_veiculo"),
            models.Index(fields=["filial", "vencimento"], name="despesa_filial_vencimento"),
        ]

    def __str__(self) -> str:
        return f"{self.descricao}: {self.valor_centavos}"
