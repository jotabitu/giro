"""Categorias, preços, extras, veículos e o histórico de status, km e filial (VEI, LOC-01, LOC-02,
LOC-15).

Modelo em `docs/decisoes/modelo-de-dados.md`, itens 8 e 9. Muda só por `veiculos.services`; o
status do veículo, só por `services.transicionar` (ADR 0009).
"""

from typing import ClassVar

from django.db import models
from django.db.models.functions import Lower

from comum.campos import CentavosField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase


class TipoVeiculo(models.TextChoices):
    MOTO = "moto", "Moto"
    CARRO = "carro", "Carro"


class Categoria(ModeloBase, ModeloAtivavel):
    """Categoria com preço (LOC-01). `filial` nula vale para a empresa toda (FIL-04)."""

    nome = models.CharField(max_length=60)
    tipo_veiculo = models.CharField(max_length=10, choices=TipoVeiculo.choices)
    filial = models.ForeignKey(
        "filiais.Filial", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "categoria"
        ordering = ["nome", "id"]
        constraints = [
            models.UniqueConstraint(
                Lower("nome"), "filial", name="categoria_nome_filial_unico", nulls_distinct=False
            ),
        ]

    def __str__(self) -> str:
        return self.nome


class PrecoCategoria(ModeloBase):
    """Preço a partir de uma data (LOC-15): vale o de maior `vigente_desde <= data`."""

    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="precos")
    vigente_desde = models.DateField()
    diaria_centavos = CentavosField()
    semanal_centavos = CentavosField()
    mensal_centavos = CentavosField()
    caucao_centavos = CentavosField()
    alterado_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "preço da categoria"
        verbose_name_plural = "preços da categoria"
        ordering = ["-vigente_desde"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "vigente_desde"], name="preco_categoria_data_unico"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.categoria_id} desde {self.vigente_desde:%d/%m/%Y}"


class Extra(ModeloBase, ModeloAtivavel):
    """Item cobrado à parte na locação (LOC-02). A locação copia o valor quando é criada."""

    class Cobranca(models.TextChoices):
        POR_PERIODO = "por_periodo", "Por período"
        UNICA = "unica", "Única"

    nome = models.CharField(max_length=60)
    valor_centavos = CentavosField()
    cobranca = models.CharField(max_length=12, choices=Cobranca.choices)

    class Meta:
        verbose_name = "extra"
        ordering = ["nome", "id"]

    def __str__(self) -> str:
        return self.nome


class StatusVeiculo(models.TextChoices):
    DISPONIVEL = "disponivel", "Disponível"
    RESERVADO = "reservado", "Reservado"
    ALUGADO = "alugado", "Alugado"
    EM_MANUTENCAO = "em_manutencao", "Em manutenção"
    INDISPONIVEL = "indisponivel", "Indisponível"
    A_VENDA = "a_venda", "À venda"
    VENDIDO = "vendido", "Vendido"
    BAIXADO = "baixado", "Baixado"


S = StatusVeiculo
# Saíram da empresa: não contam no plano (PLT-03) nem na operação da filial (FIL-06), e só
# aparecem na frota com o filtro explícito.
FORA_DA_FROTA = (S.VENDIDO, S.BAIXADO)
# Seção "Veículos" das regras, "Transições permitidas".
_BAIXAR = {S.BAIXADO}
TRANSICOES_VEICULO: dict[str, set[str]] = {
    S.DISPONIVEL: {S.RESERVADO, S.ALUGADO, S.EM_MANUTENCAO, S.INDISPONIVEL, S.A_VENDA, *_BAIXAR},
    S.RESERVADO: {S.ALUGADO, *_BAIXAR},
    S.ALUGADO: {S.DISPONIVEL, S.EM_MANUTENCAO},
    S.EM_MANUTENCAO: {S.DISPONIVEL, *_BAIXAR},
    S.INDISPONIVEL: {S.DISPONIVEL, *_BAIXAR},
    S.A_VENDA: {S.DISPONIVEL, S.VENDIDO, *_BAIXAR},
    S.VENDIDO: {S.A_VENDA, S.INDISPONIVEL, *_BAIXAR},
    S.BAIXADO: set(),
}


class Veiculo(MaquinaDeEstados, ModeloBase):
    placa = models.CharField(max_length=7, unique=True)
    chassi = models.CharField(max_length=17, unique=True)
    renavam = models.CharField(max_length=11, blank=True, default="")
    marca = models.CharField(max_length=40)
    modelo = models.CharField(max_length=60)
    ano_fabricacao = models.PositiveSmallIntegerField()
    ano_modelo = models.PositiveSmallIntegerField()
    cor = models.CharField(max_length=30)
    km_atual = models.PositiveIntegerField(default=0)  # só sobe (VEI-01), por serviço
    km_atualizado_em = models.DateTimeField(null=True, blank=True)
    capacidade_tanque_litros = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )  # DEV-01
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="veiculos")
    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=15, choices=StatusVeiculo.choices, default=S.DISPONIVEL)
    motivo_status = models.CharField(max_length=200, blank=True, default="")
    valor_compra_centavos = CentavosField(null=True, blank=True)
    data_compra = models.DateField(null=True, blank=True)
    valor_venda_centavos = CentavosField(null=True, blank=True)  # VEN-01
    referencia_fipe_centavos = CentavosField(null=True, blank=True)
    entrou_na_frota_em = models.DateField()
    km_ultima_manutencao = models.PositiveIntegerField(null=True, blank=True)  # MAN-05
    data_ultima_manutencao = models.DateField(null=True, blank=True)

    TRANSICOES: ClassVar[dict[str, set[str]]] = TRANSICOES_VEICULO
    REGRA_TRANSICAO: ClassVar[str] = "transicao_veiculo"

    class Meta:
        verbose_name = "veículo"
        ordering = ["placa"]
        indexes = [models.Index(fields=["filial", "status"], name="veiculo_filial_status")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(chassi__regex=r"^[A-Z0-9]{17}$"),
                name="veiculo_chassi_17_caracteres",
            ),
        ]

    def __str__(self) -> str:
        return self.placa


class Origem(models.TextChoices):
    """Quem levou à mudança (origem genérica, ADR 0011)."""

    CADASTRO = "cadastro", "Cadastro"
    MANUAL = "manual", "Ação na ficha"
    LOCACAO = "locacao", "Locação"
    VISTORIA = "vistoria", "Vistoria"
    ORDEM_SERVICO = "ordem_servico", "Ordem de serviço"
    VENDA = "venda", "Venda"
    DOCUMENTO = "documento", "Documento"
    APROVACAO = "aprovacao", "Aprovação"


class ComOrigem(models.Model):
    origem_tipo = models.CharField(max_length=15, choices=Origem.choices)
    origem_id = models.BigIntegerField(null=True, blank=True)
    origem_codigo = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        abstract = True


class HistoricoStatusVeiculo(ModeloBase, ComOrigem):
    """Cada mudança de status (base da ocupação, VEI-06). `de` vazio no cadastro."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="historico")
    de = models.CharField(max_length=15, choices=StatusVeiculo.choices, blank=True, default="")
    para = models.CharField(max_length=15, choices=StatusVeiculo.choices)
    em = models.DateTimeField()
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    motivo = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "histórico de status do veículo"
        ordering = ["em", "id"]
        indexes = [models.Index(fields=["veiculo", "em"], name="historico_veiculo_em")]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.de or '—'} → {self.para}"


class LeituraKm(ModeloBase, ComOrigem):
    """Cada km informado (VEI-01, VEI-02). `correcao` marca a correção para baixo (APR-06)."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="leituras_km")
    km = models.PositiveIntegerField()
    lido_em = models.DateTimeField()
    correcao = models.BooleanField(default=False)
    motivo = models.CharField(max_length=200, blank=True, default="")
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "leitura de km"
        verbose_name_plural = "leituras de km"
        ordering = ["lido_em", "id"]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.km} km"


class TransferenciaVeiculo(ModeloBase):
    """Única forma de o veículo mudar de filial (VEI-04, FIL-05)."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="transferencias")
    filial_origem = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    filial_destino = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    em = models.DateTimeField()
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    motivo = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "transferência de veículo"
        verbose_name_plural = "transferências de veículo"
        ordering = ["em", "id"]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.filial_origem_id} → {self.filial_destino_id}"
