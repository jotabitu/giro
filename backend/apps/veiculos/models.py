"""Categorias, preços, extras, veículos e o histórico de status, km e filial (VEI, LOC-01, LOC-02,
LOC-15).

Modelo em `docs/decisoes/modelo-de-dados.md`, itens 8 e 9. Muda só por `veiculos.services`; o
status do veículo, só por `services.transicionar` (ADR 0009).
"""

from typing import ClassVar

from django.db import models
from django.db.models.functions import Lower

from comum import arquivos
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

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

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

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

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
    EM_MOVIMENTACAO = "em_movimentacao", "Em movimentação"  # MOV-03, ADR 0028


S = StatusVeiculo
# Saíram da empresa: não contam no plano (PLT-03) nem na operação da filial (FIL-06), e só
# aparecem na frota com o filtro explícito.
FORA_DA_FROTA = (S.VENDIDO, S.BAIXADO)
# MOV-03: o que se movimenta (e chega por transferência, MOV-06).
MOVIMENTAVEIS = frozenset({S.DISPONIVEL, S.INDISPONIVEL, S.EM_MANUTENCAO, S.A_VENDA})
# Seção "Veículos" das regras, "Transições permitidas".
_BAIXAR = {S.BAIXADO}
TRANSICOES_VEICULO: dict[str, set[str]] = {
    S.DISPONIVEL: {
        S.RESERVADO,
        S.ALUGADO,
        S.EM_MANUTENCAO,
        S.INDISPONIVEL,
        S.A_VENDA,
        S.EM_MOVIMENTACAO,
        *_BAIXAR,
    },
    S.RESERVADO: {S.ALUGADO, S.DISPONIVEL, *_BAIXAR},  # DISPONIVEL: reserva cancelada (LOC-12)
    # VENDIDO: quitação da locação com intenção de compra (LOC-16, VEN-11), só por `vendas`.
    S.ALUGADO: {S.DISPONIVEL, S.EM_MANUTENCAO, S.VENDIDO},
    S.EM_MANUTENCAO: {S.DISPONIVEL, *_BAIXAR},
    S.INDISPONIVEL: {S.DISPONIVEL, *_BAIXAR},
    S.A_VENDA: {S.DISPONIVEL, S.VENDIDO, *_BAIXAR},
    S.VENDIDO: {S.A_VENDA, S.INDISPONIVEL, *_BAIXAR},
    S.BAIXADO: set(),
    # Volta pela chegada da movimentação: `indisponivel` com documento vencido (MOV-05).
    S.EM_MOVIMENTACAO: {S.DISPONIVEL, S.INDISPONIVEL, *_BAIXAR},
}


class Combustivel(models.TextChoices):
    GASOLINA = "gasolina", "Gasolina"
    ETANOL = "etanol", "Etanol"
    FLEX = "flex", "Flex"
    DIESEL = "diesel", "Diesel"
    ELETRICO = "eletrico", "Elétrico"
    HIBRIDO = "hibrido", "Híbrido"


class Especie(models.TextChoices):
    """Espécie do veículo no CRLV-e (CTB, art. 96; VEI-09)."""

    PASSAGEIRO = "passageiro", "Passageiro"
    CARGA = "carga", "Carga"
    MISTO = "misto", "Misto"
    COMPETICAO = "competicao", "Competição"
    TRACAO = "tracao", "Tração"
    ESPECIAL = "especial", "Especial"
    COLECAO = "colecao", "Coleção"


# VEI-09 (T-421): chave da API (pontuada nos blocos `documento` e `rastreador`) → campo do model.
CAMPOS_DA_VEI_09 = {
    "documento.potencia_cv": "potencia_cv",
    "documento.cilindrada_cc": "cilindrada_cc",
    "documento.especie": "especie",
    "documento.tipo": "tipo_documento",
    "documento.carroceria": "carroceria",
    "documento.lotacao": "lotacao",
    "documento.peso_bruto_kg": "peso_bruto_kg",
    "documento.numero_motor": "numero_motor",
    "documento.observacoes": "observacoes_crlv",
    "rastreador.numero": "rastreador_numero",
    "rastreador.empresa": "rastreador_empresa",
    "anotacoes": "anotacoes",
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
    # VEI-08 (T-247): nulo nos veículos cadastrados antes, como o contrato publica (`null`).
    combustivel = models.CharField(  # noqa: DJ001
        max_length=10, choices=Combustivel.choices, null=True, blank=True
    )
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
    # VEI-09 (T-421): todos opcionais; os veículos de antes ficam vazios.
    potencia_cv = models.PositiveSmallIntegerField(null=True, blank=True)
    cilindrada_cc = models.PositiveSmallIntegerField(null=True, blank=True)
    especie = models.CharField(  # noqa: DJ001  (o contrato publica `null`)
        max_length=12, choices=Especie.choices, null=True, blank=True
    )
    tipo_documento = models.CharField(max_length=30, blank=True, default="")  # o "tipo" do CRLV-e
    carroceria = models.CharField(max_length=30, blank=True, default="")
    lotacao = models.PositiveSmallIntegerField(null=True, blank=True)
    peso_bruto_kg = models.PositiveIntegerField(null=True, blank=True)
    numero_motor = models.CharField(max_length=21, blank=True, default="")
    observacoes_crlv = models.CharField(max_length=500, blank=True, default="")
    rastreador_numero = models.CharField(max_length=20, blank=True, default="")
    rastreador_empresa = models.CharField(max_length=60, blank=True, default="")
    anotacoes = models.CharField(max_length=500, blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = TRANSICOES_VEICULO
    REGRA_TRANSICAO: ClassVar[str] = "transicao_veiculo"
    # VEI-09: dados do veículo, não de pessoa; a auditoria da empresa é lida só pelo
    # administrador (modelo de dados, item 9).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": list(CAMPOS_DA_VEI_09.values())}

    class Meta:
        verbose_name = "veículo"
        ordering = ["placa"]
        indexes = [models.Index(fields=["filial", "status"], name="veiculo_filial_status")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(chassi__regex=r"^[A-Z0-9]{17}$"),
                name="veiculo_chassi_17_caracteres",
            ),
            models.CheckConstraint(
                condition=models.Q(potencia_cv__isnull=True)
                | models.Q(potencia_cv__gte=1, potencia_cv__lte=999),
                name="veiculo_potencia_1_a_999",
            ),
            models.CheckConstraint(
                condition=models.Q(cilindrada_cc__isnull=True)
                | models.Q(cilindrada_cc__gte=1, cilindrada_cc__lte=9999),
                name="veiculo_cilindrada_1_a_9999",
            ),
            models.CheckConstraint(
                condition=models.Q(lotacao__isnull=True)
                | models.Q(lotacao__gte=1, lotacao__lte=99),
                name="veiculo_lotacao_1_a_99",
            ),
            models.CheckConstraint(
                condition=models.Q(peso_bruto_kg__isnull=True) | models.Q(peso_bruto_kg__gt=0),
                name="veiculo_peso_bruto_positivo",
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
    IMPORTACAO = "importacao", "Importação"
    MOVIMENTACAO = "movimentacao", "Movimentação"  # MOV-03, MOV-05, MOV-06


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
    # A categoria de antes e a de depois (VEI-04, FIL-04). Nulas só nas transferências antigas.
    categoria_origem = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    categoria_destino = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
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


class TipoDocumento(models.TextChoices):
    CRLV = "crlv", "CRLV"
    IPVA = "ipva", "IPVA"
    SEGURO = "seguro", "Seguro"
    RASTREADOR = "rastreador", "Rastreador"


# VEI-03: no dia do vencimento, só estes tiram o veículo disponível da frota.
DOCUMENTOS_QUE_BLOQUEIAM = frozenset({TipoDocumento.CRLV, TipoDocumento.SEGURO})


class DocumentoVeiculo(ModeloBase, ModeloAtivavel):
    """VEI-03. Renovar = novo documento, e o anterior fica `ativo=False` (histórico)."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="documentos")
    tipo = models.CharField(max_length=12, choices=TipoDocumento.choices)
    validade = models.DateField()
    exercicio = models.PositiveSmallIntegerField(null=True, blank=True)  # só no crlv (VEI-08)
    # Armazenamento privado com URL assinada de 15 minutos (AUD-05, ADR 0009).
    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    arquivo_nome = models.CharField(max_length=120, blank=True, default="")
    alerta_enviado_em = models.DateTimeField(null=True, blank=True)  # idempotência de AUT-06
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    # Nome do arquivo enviado, não de pessoa (R-02 da T-050).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["arquivo_nome"]}

    class Meta:
        verbose_name = "documento do veículo"
        verbose_name_plural = "documentos do veículo"
        ordering = ["tipo", "-validade", "-id"]
        indexes = [
            models.Index(
                fields=["validade"], condition=models.Q(ativo=True), name="documento_validade"
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo", "tipo"],
                condition=models.Q(ativo=True),
                name="documento_um_ativo_por_tipo",
            )
        ]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.tipo} até {self.validade}"


class FormatoFoto(models.TextChoices):
    JPG = "jpg", "JPG"
    PNG = "png", "PNG"


# VEI-10: até 20 fotos ativas na galeria (conferido no serviço, com o veículo travado).
LIMITE_DA_GALERIA = 20


class FotoVeiculo(ModeloBase, ModeloAtivavel):
    """Galeria do veículo (VEI-10, ADR 0036, modelo de dados item 9a): fotos de cadastro para a
    ficha e o catálogo, nunca as da vistoria. Arquivo privado, reprocessado sem metadados, com URL
    de 15 minutos (AUD-05). Apagada ou substituída, fica `ativo=False`, com o arquivo guardado."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="fotos")
    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    formato = models.CharField(max_length=3, choices=FormatoFoto.choices)
    # Ordem de envio, sequencial por veículo entre ativas e inativas; a troca herda a da antiga.
    ordem = models.PositiveSmallIntegerField()
    capa = models.BooleanField(default=False)
    enviada_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    enviada_em = models.DateTimeField()
    substituida_por = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    apagada_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "foto do veículo"
        verbose_name_plural = "fotos do veículo"
        ordering = ["-capa", "ordem", "id"]
        indexes = [
            models.Index(fields=["veiculo", "ativo", "ordem"], name="foto_veiculo_galeria"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=models.Q(ativo=True, capa=True),
                name="foto_veiculo_uma_capa",
            ),
            models.UniqueConstraint(
                fields=["veiculo", "ordem"],
                condition=models.Q(ativo=True),
                name="foto_veiculo_ordem_ativa",
            ),
            models.CheckConstraint(
                condition=models.Q(ordem__gte=1), name="foto_veiculo_ordem_positiva"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: foto {self.ordem}"
