"""Movimentações de veículos e locais de apoio (modelo de dados, itens 26 e 27; MOV-01 a MOV-06,
ADR 0028).

Muda só por `movimentacoes.services`; o status da movimentação, só por
`comum.estados.transicionar`.
"""

from typing import ClassVar

from django.db import models

from comum import arquivos
from comum.campos import CentavosField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase, ModeloComCodigo


class TipoLocal(models.TextChoices):
    LAVA_JATO = "lava_jato", "Lava-jato"
    OFICINA = "oficina", "Oficina"
    DESPACHANTE = "despachante", "Despachante"
    OUTRO = "outro", "Outro"


class LocalApoio(ModeloBase, ModeloAtivavel):
    """Da empresa, vale para todas as filiais (MOV-01). Inativado, nunca apagado."""

    nome = models.CharField(max_length=80)
    # Minúsculas, sem acento e com espaços normalizados: o nome único da MOV-01.
    nome_busca = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=15, choices=TipoLocal.choices)

    class Meta:
        verbose_name = "local de apoio"
        verbose_name_plural = "locais de apoio"
        ordering = ["nome", "id"]

    def __str__(self) -> str:
        return self.nome


class StatusMovimentacao(models.TextChoices):
    AGENDADA = "agendada", "Agendada"
    EM_TRANSITO = "em_transito", "Em trânsito"
    NO_LOCAL = "no_local", "No local de apoio"
    CONCLUIDA = "concluida", "Concluída"
    CANCELADA = "cancelada", "Cancelada"


class Combustivel(models.TextChoices):
    """O mesmo enum da vistoria (VIS-03); `vistorias` fica no mesmo nível e não se importa."""

    RESERVA = "reserva", "Reserva"
    UM_QUARTO = "um_quarto", "1/4"
    MEIO = "meio", "1/2"
    TRES_QUARTOS = "tres_quartos", "3/4"
    CHEIO = "cheio", "Cheio"


S = StatusMovimentacao
# Uma por veículo (MOV-03): a restrição do banco segura a corrida.
ABERTAS = (S.AGENDADA, S.EM_TRANSITO, S.NO_LOCAL)


class Movimentacao(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO: ClassVar[str] = "MOV"

    veiculo = models.ForeignKey("veiculos.Veiculo", on_delete=models.PROTECT, related_name="+")
    filial_saida = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    destino = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    categoria_destino = models.ForeignKey(
        "veiculos.Categoria", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    levado_por = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    criada_por = models.ForeignKey("contas.Usuario", on_delete=models.PROTECT, related_name="+")
    agendada_para = models.DateTimeField(null=True, blank=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True, default="")
    vistoria_rapida = models.BooleanField(default=False)
    km_saida = models.PositiveIntegerField(null=True, blank=True)
    km_chegada = models.PositiveIntegerField(null=True, blank=True)
    combustivel_chegada = models.CharField(
        max_length=12, choices=Combustivel.choices, blank=True, default=""
    )
    recebido_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=12, choices=StatusMovimentacao.choices)

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.AGENDADA: {S.EM_TRANSITO, S.CANCELADA},
        # A iniciada só se cancela pela baixa do veículo (MOV-03, opção B do dono); o
        # "Cancelar" da tela segue só na agendada (`services.cancelar`, CA-246-06).
        S.EM_TRANSITO: {S.NO_LOCAL, S.CONCLUIDA, S.CANCELADA},
        S.NO_LOCAL: {S.EM_TRANSITO, S.CANCELADA},
        S.CONCLUIDA: set(),
        S.CANCELADA: set(),
    }
    REGRA_TRANSICAO: ClassVar[str] = "transicao_movimentacao"

    class Meta:
        verbose_name = "movimentação"
        verbose_name_plural = "movimentações"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["filial_saida", "status"], name="mov_saida_status"),
            models.Index(fields=["destino", "status"], name="mov_destino_status"),
            models.Index(fields=["levado_por", "status"], name="mov_levado_status"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=models.Q(status__in=["agendada", "em_transito", "no_local"]),
                name="mov_uma_aberta_por_veiculo",
            ),
            models.CheckConstraint(
                condition=models.Q(destino=models.F("filial_saida"))
                | models.Q(vistoria_rapida=True),
                name="mov_transferencia_com_vistoria",
            ),
            models.CheckConstraint(
                condition=~models.Q(destino=models.F("filial_saida"))
                | models.Q(categoria_destino__isnull=True),
                name="mov_categoria_so_na_transferencia",
            ),
        ]

    def __str__(self) -> str:
        return self.codigo

    @property
    def transferencia(self) -> bool:
        return self.destino_id != self.filial_saida_id


class ParadaMovimentacao(ModeloBase):
    movimentacao = models.ForeignKey(Movimentacao, on_delete=models.PROTECT, related_name="paradas")
    ordem = models.PositiveSmallIntegerField()
    local = models.ForeignKey(LocalApoio, on_delete=models.PROTECT, related_name="+")
    servico = models.CharField(max_length=80)
    # Uma das categorias da despesa (FIN-06): padrão `outros`, `manutencao` na oficina (MOV-04).
    categoria = models.CharField(max_length=15)
    valor_previsto_centavos = CentavosField(default=0)
    chegou_em = models.DateTimeField(null=True, blank=True)
    saiu_em = models.DateTimeField(null=True, blank=True)
    valor_pago_centavos = CentavosField(null=True, blank=True)
    despesa = models.ForeignKey(
        "financeiro.Despesa", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "parada da movimentação"
        verbose_name_plural = "paradas da movimentação"
        ordering = ["ordem"]
        constraints = [
            models.UniqueConstraint(fields=["movimentacao", "ordem"], name="mov_parada_ordem"),
        ]

    def __str__(self) -> str:
        return f"{self.movimentacao_id}: {self.ordem}"


class PosicaoFoto(models.TextChoices):
    FRENTE = "frente", "Frente"
    TRASEIRA = "traseira", "Traseira"
    LADO_ESQUERDO = "lado_esquerdo", "Lado esquerdo"
    LADO_DIREITO = "lado_direito", "Lado direito"


class FotoChegadaMovimentacao(ModeloBase):
    """Vistoria rápida da chegada (MOV-05). Arquivo privado, sem metadados de localização, com
    URL de 15 minutos (AUD-05). A foto nova da mesma posição substitui o arquivo."""

    movimentacao = models.ForeignKey(
        Movimentacao, on_delete=models.PROTECT, related_name="fotos_chegada"
    )
    posicao = models.CharField(max_length=15, choices=PosicaoFoto.choices)
    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "foto da chegada"
        verbose_name_plural = "fotos da chegada"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["movimentacao", "posicao"], name="mov_foto_posicao"),
        ]

    def __str__(self) -> str:
        return f"{self.movimentacao_id}: {self.posicao}"
