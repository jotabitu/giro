"""Vistorias de saída e de chegada, fotos e avarias (modelo de dados, item 14; VIS-01 a VIS-05).

Muda só por `vistorias.services`; o status da vistoria, só por `comum.estados.transicionar`.
"""

from typing import ClassVar

from django.db import models

from comum import arquivos
from comum.campos import CentavosField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase


class TipoVistoria(models.TextChoices):
    SAIDA = "saida", "Saída"
    DEVOLUCAO = "devolucao", "Devolução"


class StatusVistoria(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    CONCLUIDA = "concluida", "Concluída"
    DESCARTADA = "descartada", "Descartada"  # só pelo cancelamento da troca (LOC-09)


class Combustivel(models.TextChoices):
    """VIS-03: os 5 níveis. Na conta da DEV-01 valem 0, 1/4, 1/2, 3/4 e 1."""

    RESERVA = "reserva", "Reserva"
    UM_QUARTO = "um_quarto", "1/4"
    MEIO = "meio", "1/2"
    TRES_QUARTOS = "tres_quartos", "3/4"
    CHEIO = "cheio", "Cheio"


class PosicaoFoto(models.TextChoices):
    FRENTE = "frente", "Frente"
    TRASEIRA = "traseira", "Traseira"
    LADO_ESQUERDO = "lado_esquerdo", "Lado esquerdo"
    LADO_DIREITO = "lado_direito", "Lado direito"
    PAINEL = "painel", "Painel"
    AVARIA = "avaria", "Avaria"


# VIS-01: as 5 posições fixas. A foto de avaria não conta.
POSICOES_OBRIGATORIAS: tuple[str, ...] = (
    PosicaoFoto.FRENTE,
    PosicaoFoto.TRASEIRA,
    PosicaoFoto.LADO_ESQUERDO,
    PosicaoFoto.LADO_DIREITO,
    PosicaoFoto.PAINEL,
)

S = StatusVistoria


class Vistoria(MaquinaDeEstados, ModeloBase):
    """Presa à locação (VIS-04). Concluída não se edita; a correção é uma vistoria nova que
    `substitui` a anterior e, concluída, passa a ser a `vigente`."""

    locacao = models.ForeignKey("locacoes.Locacao", on_delete=models.PROTECT, related_name="+")
    # Pode diferir do veículo atual da locação depois de uma troca (LOC-09).
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=10, choices=TipoVistoria.choices)
    status = models.CharField(max_length=10, choices=StatusVistoria.choices, default=S.RASCUNHO)
    km = models.PositiveIntegerField(null=True, blank=True)  # VEI-01
    combustivel = models.CharField(
        max_length=12, choices=Combustivel.choices, blank=True, default=""
    )
    # VIS-02: [{codigo, rotulo, ok (null sem resposta), observacao}], na ordem da lista.
    itens = models.JSONField(default=list, blank=True)
    observacoes = models.TextField(blank=True, default="")
    responsavel = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    concluida_em = models.DateTimeField(null=True, blank=True)
    substitui = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="correcoes"
    )
    motivo_correcao = models.TextField(blank=True, default="")
    # Falso quando uma correção concluída passou a valer no lugar dela (VIS-04).
    vigente = models.BooleanField(default=True)
    # O rascunho da troca cancelada fica guardado, com fotos e respostas (LOC-09).
    descartada_em = models.DateTimeField(null=True, blank=True)
    motivo_descarte = models.TextField(blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.RASCUNHO: {S.CONCLUIDA, S.DESCARTADA},
        S.CONCLUIDA: set(),
        S.DESCARTADA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_vistoria"

    class Meta:
        verbose_name = "vistoria"
        verbose_name_plural = "vistorias"
        ordering = ["-id"]
        indexes = [models.Index(fields=["locacao", "tipo"], name="vistoria_locacao_tipo")]
        constraints = [
            models.UniqueConstraint(
                fields=["locacao", "veiculo", "tipo"],
                condition=models.Q(status="concluida", vigente=True),
                name="uma_vistoria_vigente",
            ),
            models.UniqueConstraint(
                fields=["locacao", "veiculo", "tipo"],
                condition=models.Q(status="rascunho"),
                name="um_rascunho_de_vistoria",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.locacao_id}: {self.tipo} ({self.status})"


class FotoVistoria(ModeloBase, ModeloAtivavel):
    """VIS-01. Nova foto de posição fixa no rascunho deixa a anterior `ativo=False` (guardada).
    Arquivo privado, sem metadados de localização, com URL de 15 minutos (AUD-05)."""

    vistoria = models.ForeignKey(Vistoria, on_delete=models.PROTECT, related_name="fotos")
    posicao = models.CharField(max_length=15, choices=PosicaoFoto.choices)
    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    tirada_em = models.DateTimeField()
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "foto da vistoria"
        verbose_name_plural = "fotos da vistoria"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.vistoria_id}: {self.posicao}"


class Avaria(ModeloBase):
    """Na saída, toda avaria é `preexistente` (não se cobra na devolução, VIS-01). Na chegada, é
    nova e pode ter valor (DEV-01) e ir para a oficina (DEV-04). Fica aberta até a OS ligada a
    ela ser concluída (`resolvida_em`)."""

    vistoria = models.ForeignKey(Vistoria, on_delete=models.PROTECT, related_name="avarias")
    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    descricao = models.CharField(max_length=200)
    preexistente = models.BooleanField(default=False)
    valor_centavos = CentavosField(null=True, blank=True)
    vai_para_oficina = models.BooleanField(default=False)
    foto = models.ForeignKey(
        FotoVistoria, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # A OS fica no app `manutencao` (DEV-04); sem FK enquanto ele não existe.
    ordem_servico_id = models.BigIntegerField(null=True, blank=True)
    resolvida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "avaria"
        verbose_name_plural = "avarias"
        ordering = ["id"]
        indexes = [models.Index(fields=["veiculo", "resolvida_em"], name="avaria_aberta")]

    def __str__(self) -> str:
        return self.descricao


# --- Devolução e acerto (DEV-01 a DEV-06, LOC-09 a LOC-13) ---


class StatusDevolucao(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    CONCLUIDA = "concluida", "Concluída"


class FormaDevolucao(models.TextChoices):
    PIX = "pix", "Pix"
    DINHEIRO = "dinheiro", "Dinheiro"
    ESTORNO_CARTAO = "estorno_cartao", "Estorno no cartão"


class Devolucao(MaquinaDeEstados, ModeloBase):
    """Um acerto só por locação (LOC-09). Em `rascunho`, o acerto é recalculado a cada leitura e
    a cada mudança; ao encerrar, fica `concluida` e congelado: o preço do litro e os valores dos
    itens não mudam mais (DEV-06)."""

    locacao = models.OneToOneField("locacoes.Locacao", on_delete=models.PROTECT, related_name="+")
    # Nula só depois de uma troca cancelada com a chegada descartada, até o veículo voltar.
    vistoria = models.ForeignKey(
        Vistoria, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    status = models.CharField(
        max_length=10, choices=StatusDevolucao.choices, default=StatusDevolucao.RASCUNHO
    )
    caucao_centavos = CentavosField(default=0)
    saldo_centavos = models.BigIntegerField(default=0)  # DEV-02: positivo devolve, negativo cobra
    forma_devolucao = models.CharField(
        max_length=15, choices=FormaDevolucao.choices, blank=True, default=""
    )
    preco_litro_centavos = CentavosField(null=True, blank=True)  # congelado ao encerrar
    devolvida_em = models.DateTimeField(null=True, blank=True)  # LOC-11
    concluida_em = models.DateTimeField(null=True, blank=True)
    encerrada_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    recibo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    recibo_enviado_em = models.DateTimeField(null=True, blank=True)

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        StatusDevolucao.RASCUNHO: {StatusDevolucao.CONCLUIDA},
        StatusDevolucao.CONCLUIDA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_devolucao"

    class Meta:
        verbose_name = "devolução"
        verbose_name_plural = "devoluções"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.locacao_id}: devolução ({self.status})"


class TipoItemAcerto(models.TextChoices):
    COMBUSTIVEL = "combustivel", "Combustível"
    AVARIA = "avaria", "Avaria"
    ATRASO = "atraso", "Atraso"
    KM_EXCEDENTE = "km_excedente", "Km excedente"
    PARCELA_ABERTA = "parcela_aberta", "Parcela em aberto"
    MULTA_TRANSITO = "multa_transito", "Multa de trânsito"
    MULTA_ENCERRAMENTO = "multa_encerramento", "Multa do encerramento antecipado"
    SEMANAS_NAO_USADAS = "semanas_nao_usadas", "Semanas não usadas"  # crédito, LOC-13
    DIAS_NAO_USADOS = "dias_nao_usados", "Diárias não usadas"  # crédito, LOC-12 (diária)
    DIFERENCA_TROCA = "diferenca_troca", "Diferença do período na troca"  # LOC-09


class NaturezaItem(models.TextChoices):
    COBRANCA = "cobranca", "Cobrança"
    CREDITO = "credito", "Crédito"


class ModoItem(models.TextChoices):
    INFORMADO = "informado", "Informado"
    CALCULADO = "calculado", "Calculado"


class ItemAcerto(ModeloBase):
    """Um item do acerto. Os `calculado` são refeitos a cada recálculo e não se editam; os
    `informado` (avaria, multa de trânsito e o combustível que não pôde ser calculado) guardam o
    valor dado por quem fecha a conta (DEV-01)."""

    devolucao = models.ForeignKey(Devolucao, on_delete=models.PROTECT, related_name="itens")
    tipo = models.CharField(max_length=20, choices=TipoItemAcerto.choices)
    natureza = models.CharField(
        max_length=10, choices=NaturezaItem.choices, default=NaturezaItem.COBRANCA
    )
    modo = models.CharField(max_length=10, choices=ModoItem.choices)
    descricao = models.CharField(max_length=200)
    valor_centavos = CentavosField(default=0)
    avaria = models.ForeignKey(
        Avaria, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # A parcela em aberto que o acerto paga com a caução (origem genérica, ADR 0011).
    conta_id = models.BigIntegerField(null=True, blank=True)
    # De qual veículo é o combustível: com troca (LOC-09), cada veículo devolvido tem o seu.
    veiculo = models.ForeignKey(
        "veiculos.Veiculo", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # A diferença do período em curso de cada troca concluída (LOC-09).
    troca = models.ForeignKey(
        "locacoes.TrocaVeiculo", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "item do acerto"
        verbose_name_plural = "itens do acerto"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.devolucao_id}: {self.tipo} {self.valor_centavos}"
