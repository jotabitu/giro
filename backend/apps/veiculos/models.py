"""Categorias, preços, extras, veículos e o histórico de status, km e filial (VEI, LOC-01, LOC-02,
LOC-15).

Modelo em `docs/decisoes/modelo-de-dados.md`, itens 8 e 9. Muda só por `veiculos.services`; o
status do veículo, só por `services.transicionar` (ADR 0009).
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import ClassVar

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower

from comum import arquivos
from comum.campos import CentavosField, PercentualField
from comum.estados import EstadosQuerySet, MaquinaDeEstados
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
    # DISPONIVEL: reserva cancelada (LOC-12); INDISPONIVEL: a mesma volta sem plano (VEI-15).
    S.RESERVADO: {S.ALUGADO, S.DISPONIVEL, S.INDISPONIVEL, *_BAIXAR},
    # VENDIDO: quitação da locação com intenção de compra (LOC-16, VEN-11), só por `vendas`.
    # INDISPONIVEL: a volta do veículo sem plano ligado, "sem preço" (VEI-15, ADR 0041, item 4).
    S.ALUGADO: {S.DISPONIVEL, S.EM_MANUTENCAO, S.VENDIDO, S.INDISPONIVEL},
    # INDISPONIVEL: a OS concluída do veículo sem plano ligado (VEI-15, "vale em todo retorno").
    S.EM_MANUTENCAO: {S.DISPONIVEL, S.INDISPONIVEL, *_BAIXAR},
    S.INDISPONIVEL: {S.DISPONIVEL, *_BAIXAR},
    # INDISPONIVEL: "Voltar para a frota" sem plano ligado, "sem preço" (VEI-15, PR #630).
    S.A_VENDA: {S.DISPONIVEL, S.VENDIDO, S.INDISPONIVEL, *_BAIXAR},
    S.VENDIDO: {S.A_VENDA, S.INDISPONIVEL, *_BAIXAR},
    S.BAIXADO: set(),
    # Volta pela chegada da movimentação: `indisponivel` com documento vencido (MOV-05).
    S.EM_MOVIMENTACAO: {S.DISPONIVEL, S.INDISPONIVEL, *_BAIXAR},
}
# VEI-15: destes, `indisponivel` só pela volta "sem preço" que `services.transicionar` decide;
# pedido direto (bloquear um alugado, por exemplo) continua recusado com 409.
SO_PELA_VOLTA_SEM_PRECO = frozenset({S.ALUGADO, S.RESERVADO, S.EM_MANUTENCAO, S.A_VENDA})


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
    # Únicos fora do veículo excluído (VEI-01, VEI-22): as constraints parciais do Meta.
    placa = models.CharField(max_length=7)
    chassi = models.CharField(max_length=17)
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
    # VEI-11 (ADR 0043): moto ou carro é do próprio veículo; sem default (a falta é erro).
    tipo_veiculo = models.CharField(max_length=10, choices=TipoVeiculo.choices)
    # Dado antigo (ADR 0043): nulo no veículo novo; só as locações antigas ainda o leem.
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, null=True, blank=True, related_name="veiculos"
    )
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
    # AUT-18 (VEI-19, T-486): a entrada no estoque (data e hora da passagem para `a_venda`, VEI-18)
    # já avisada aos gerentes. Outra entrada pode ser avisada; a mesma, não.
    estoque_aviso_entrada_em = models.DateTimeField(null=True, blank=True)
    # VEI-21 (T-507): "Oferecer aluguel". Desligado, os planos de aluguel ficam guardados e a
    # Nova locação e a troca não oferecem o veículo para aluguel; o status não muda (padrão A).
    aluguel_ligado = models.BooleanField(default=True)
    # VEI-22 (T-515): o cadastro feito por engano, sem histórico. Fica guardado e some de tudo.
    excluido_em = models.DateTimeField(null=True, blank=True)
    excluido_por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    # `objects` (da MaquinaDeEstados) tira o excluído de tudo; `todos` vê também os excluídos.
    todos = EstadosQuerySet.as_manager()

    TRANSICOES: ClassVar[dict[str, set[str]]] = TRANSICOES_VEICULO
    REGRA_TRANSICAO: ClassVar[str] = "transicao_veiculo"
    # VEI-09: dados do veículo, não de pessoa; a auditoria da empresa é lida só pelo
    # administrador (modelo de dados, item 9).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": [
            *CAMPOS_DA_VEI_09.values(),
            "aluguel_ligado",
            "excluido_em",
            "excluido_por",
            "tipo_veiculo",
        ]
    }
    # ADR 0043: a categoria é dado antigo e sai do retrato dos eventos novos.
    FORA_DO_RETRATO: ClassVar[tuple[str, ...]] = ("categoria",)

    class Meta:
        verbose_name = "veículo"
        ordering = ["placa"]
        default_manager_name = "objects"
        indexes = [
            models.Index(fields=["filial", "status"], name="veiculo_filial_status"),
            models.Index(fields=["filial", "tipo_veiculo"], name="veiculo_filial_tipo"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tipo_veiculo__in=["moto", "carro"]),
                name="veiculo_tipo_valido",
            ),
            # VEI-01: placa e chassi únicos em qualquer estado, menos no excluído (VEI-22).
            models.UniqueConstraint(
                fields=["placa"],
                condition=models.Q(excluido_em__isnull=True),
                name="veiculo_placa_unica",
            ),
            models.UniqueConstraint(
                fields=["chassi"],
                condition=models.Q(excluido_em__isnull=True),
                name="veiculo_chassi_unico",
            ),
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


# --- Preços por veículo (VEI-12 a VEI-17, ADR 0041) ---


class TipoPlano(models.TextChoices):
    DIARIA = "diaria", "Diária"
    SEMANAL = "semanal", "Semanal"
    MENSAL = "mensal", "Mensal"
    ENTREGADOR = "entregador", "Entregador"
    OUTRO = "outro", "Outro"


class PeriodoPlano(models.TextChoices):
    DIA = "dia", "Dia"
    SEMANA = "semana", "Semana"
    MES = "mes", "Mês"


class ComoPaga(models.TextChoices):
    TUDO_NA_RETIRADA = "tudo_na_retirada", "Tudo na retirada"
    SEMANA_ADIANTADO = "semana_adiantado", "Toda semana, adiantado"
    MES_UMA_PARCELA = "mes_uma_parcela", "1 parcela no mês"
    MES_DUAS_QUINZENAIS = "mes_duas_quinzenais", "2 quinzenais"
    MES_QUATRO_SEMANAIS = "mes_quatro_semanais", "4 semanais"


class FormaAceita(models.TextChoices):
    """Os mesmos valores de `locacoes.FormaPagamento`, sem importar `locacoes` (ADR 0041)."""

    PIX = "pix", "Pix"
    BOLETO = "boleto", "Boleto"
    CARTAO = "cartao", "Cartão"
    DINHEIRO = "dinheiro", "Dinheiro"


# Período fixo pelo tipo; `entregador` e `outro` escolhem (VEI-12).
PERIODO_DO_TIPO = {
    TipoPlano.DIARIA: PeriodoPlano.DIA,
    TipoPlano.SEMANAL: PeriodoPlano.SEMANA,
    TipoPlano.MENSAL: PeriodoPlano.MES,
}
# Como o cliente paga, lista fechada por período (VEI-12); o primeiro é o padrão.
COMO_PAGA_DO_PERIODO = {
    PeriodoPlano.DIA: (ComoPaga.TUDO_NA_RETIRADA,),
    PeriodoPlano.SEMANA: (ComoPaga.SEMANA_ADIANTADO,),
    PeriodoPlano.MES: (
        ComoPaga.MES_UMA_PARCELA,
        ComoPaga.MES_DUAS_QUINZENAIS,
        ComoPaga.MES_QUATRO_SEMANAIS,
    ),
}
TIPOS_FIXOS = (TipoPlano.DIARIA, TipoPlano.SEMANAL, TipoPlano.MENSAL, TipoPlano.ENTREGADOR)


def _q_periodo_do_tipo() -> models.Q:
    q = models.Q(tipo__in=[TipoPlano.ENTREGADOR, TipoPlano.OUTRO])
    for tipo, periodo in PERIODO_DO_TIPO.items():
        q |= models.Q(tipo=tipo, periodo=periodo)
    return q


def _q_como_paga() -> models.Q:
    q = models.Q()
    for periodo, formas in COMO_PAGA_DO_PERIODO.items():
        q |= models.Q(periodo=periodo, como_paga__in=list(formas))
    return q


class PlanoVeiculo(ModeloBase, ModeloAtivavel):
    """Plano de aluguel do veículo (VEI-12). `outro` retirado vira `ativo=False`; os outros tipos
    só se desligam. O preço agendado mora nos três campos `*_agendad*` (ADR 0041, item 1)."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="planos")
    tipo = models.CharField(max_length=12, choices=TipoPlano.choices)
    nome = models.CharField(max_length=40, blank=True, default="")
    periodo = models.CharField(max_length=6, choices=PeriodoPlano.choices)
    ligado = models.BooleanField(default=False)
    valor_centavos = CentavosField(default=0)
    como_paga = models.CharField(max_length=20, choices=ComoPaga.choices)
    formas_aceitas = ArrayField(
        models.CharField(max_length=10, choices=FormaAceita.choices), default=list, blank=True
    )
    caucao_centavos = CentavosField(null=True, blank=True)  # nulo = não preenchida
    caucao_parcelas = models.PositiveSmallIntegerField(default=1)
    franquia_km = models.PositiveIntegerField(null=True, blank=True)  # nulo = livre
    prazo_minimo_periodos = models.PositiveSmallIntegerField(null=True, blank=True)
    valor_agendado_centavos = CentavosField(null=True, blank=True)
    caucao_agendada_centavos = CentavosField(null=True, blank=True)
    agendado_para = models.DateField(null=True, blank=True)

    # Nome de plano dado pela locadora ("Fim de semana"), não de pessoa: vai inteiro.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

    class Meta:
        verbose_name = "plano do veículo"
        verbose_name_plural = "planos do veículo"
        ordering = ["veiculo_id", "id"]
        indexes = [
            models.Index(
                fields=["veiculo"],
                condition=models.Q(ativo=True, ligado=True),
                name="plano_veiculo_ligado",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo", "tipo"],
                condition=models.Q(ativo=True) & ~models.Q(tipo="outro"),
                name="plano_veiculo_um_por_tipo",
            ),
            models.UniqueConstraint(
                "veiculo",
                Lower("nome"),
                condition=models.Q(ativo=True, tipo="outro"),
                name="plano_veiculo_outro_nome_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(caucao_parcelas__gte=1, caucao_parcelas__lte=12),
                name="plano_veiculo_caucao_parcelas_1_a_12",
            ),
            models.CheckConstraint(
                condition=models.Q(franquia_km__isnull=True) | models.Q(franquia_km__gt=0),
                name="plano_veiculo_franquia_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(prazo_minimo_periodos__isnull=True)
                | models.Q(prazo_minimo_periodos__gt=0),
                name="plano_veiculo_prazo_minimo_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    agendado_para__isnull=True,
                    valor_agendado_centavos__isnull=True,
                    caucao_agendada_centavos__isnull=True,
                )
                | models.Q(agendado_para__isnull=False, valor_agendado_centavos__isnull=False),
                name="plano_veiculo_agendado_completo",
            ),
            models.CheckConstraint(
                condition=_q_periodo_do_tipo(), name="plano_veiculo_periodo_do_tipo"
            ),
            models.CheckConstraint(condition=_q_como_paga(), name="plano_veiculo_como_paga"),
            models.CheckConstraint(
                condition=models.Q(ligado=False)
                | models.Q(
                    valor_centavos__gt=0,
                    formas_aceitas__len__gte=1,
                    caucao_centavos__isnull=False,
                ),
                name="plano_veiculo_ligado_completo",
            ),
            models.CheckConstraint(
                condition=(models.Q(tipo="outro") & ~models.Q(nome=""))
                | (~models.Q(tipo="outro") & models.Q(nome="")),
                name="plano_veiculo_nome_so_no_outro",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.rotulo}"

    @property
    def rotulo(self) -> str:
        """ "Semanal", "Entregador" ou o nome do `outro`."""
        return self.nome if self.tipo == TipoPlano.OUTRO else TipoPlano(self.tipo).label

    def _agendado_vale(self, dia: date) -> bool:
        return self.agendado_para is not None and self.agendado_para <= dia

    def valor_em(self, dia: date) -> int:
        """O valor do dia: o agendado a partir de `agendado_para` (ADR 0041, item 1)."""
        if self._agendado_vale(dia) and self.valor_agendado_centavos is not None:
            return int(self.valor_agendado_centavos)
        return int(self.valor_centavos)

    def caucao_em(self, dia: date) -> int | None:
        if self._agendado_vale(dia) and self.caucao_agendada_centavos is not None:
            return int(self.caucao_agendada_centavos)
        return None if self.caucao_centavos is None else int(self.caucao_centavos)


class RegrasVeiculo(ModeloBase):
    """As regras do veículo (VEI-14): dia de atraso (LOC-10), multa mínima (LOC-12), desconto sem
    aprovação (LOC-03, APR-01), prazo da caução (DEV-02) e km excedente (só guardado)."""

    veiculo = models.OneToOneField(Veiculo, on_delete=models.PROTECT, related_name="regras")
    km_excedente_centavos = CentavosField(default=0)
    dia_atraso_centavos = CentavosField(default=0)
    multa_minima_centavos = CentavosField(default=0)
    desconto_sem_aprovacao_pct = PercentualField(default=Decimal("5.00"))
    prazo_devolucao_caucao_dias = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "regras do veículo"
        verbose_name_plural = "regras do veículo"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    desconto_sem_aprovacao_pct__gte=0, desconto_sem_aprovacao_pct__lte=100
                ),
                name="regras_veiculo_desconto_0_a_100",
            ),
        ]

    def __str__(self) -> str:
        return f"regras de {self.veiculo_id}"


class CustosVeiculo(ModeloBase):
    """Custos e ocupação esperada do veículo (VEI-13). O valor de venda é o do `Veiculo`; o pago
    na moto se calcula na leitura (compra + despesas, FIN-17)."""

    veiculo = models.OneToOneField(Veiculo, on_delete=models.PROTECT, related_name="custos")
    manutencao_mes_centavos = CentavosField(default=0)
    seguro_mes_centavos = CentavosField(default=0)
    rastreador_mes_centavos = CentavosField(default=0)
    ipva_ano_centavos = CentavosField(default=0)
    revenda_estimada_centavos = CentavosField(null=True, blank=True)
    ocupacao_esperada_pct = PercentualField(null=True, blank=True)

    class Meta:
        verbose_name = "custos do veículo"
        verbose_name_plural = "custos do veículo"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ocupacao_esperada_pct__isnull=True)
                | models.Q(ocupacao_esperada_pct__gte=0, ocupacao_esperada_pct__lte=100),
                name="custos_veiculo_ocupacao_0_a_100",
            ),
        ]

    def __str__(self) -> str:
        return f"custos de {self.veiculo_id}"


class Periodicidade(models.TextChoices):
    DIARIA = "diaria", "Diária"
    SEMANAL = "semanal", "Semanal"
    QUINZENAL = "quinzenal", "Quinzenal"
    MENSAL = "mensal", "Mensal"


class ModoParcela(models.TextChoices):
    CALCULAR = "calcular", "Calcular pelos juros"
    DIGITAR = "digitar", "Digitar a parcela"


class PlanoCompraVeiculo(ModeloBase):
    """Locação com compra do veículo (VEI-16, detalha a LOC-16), um por veículo."""

    veiculo = models.OneToOneField(Veiculo, on_delete=models.PROTECT, related_name="plano_compra")
    ligado = models.BooleanField(default=False)
    periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices)
    parcelas = models.PositiveSmallIntegerField()
    entrada_centavos = CentavosField(default=0)
    juros_mes_pct = PercentualField(default=Decimal("0.00"))
    modo = models.CharField(max_length=8, choices=ModoParcela.choices)
    parcela_moto_centavos = CentavosField(default=0)
    adicional_centavos = CentavosField(default=0)
    caucao_centavos = CentavosField(default=0)

    class Meta:
        verbose_name = "plano de compra do veículo"
        verbose_name_plural = "planos de compra do veículo"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(parcelas__gte=2, parcelas__lte=1000),
                name="plano_compra_veiculo_parcelas_2_a_1000",
            ),
            models.CheckConstraint(
                condition=models.Q(juros_mes_pct__gte=0), name="plano_compra_veiculo_juros_positivo"
            ),
            models.CheckConstraint(
                condition=models.Q(ligado=False) | models.Q(parcela_moto_centavos__gt=0),
                name="plano_compra_veiculo_ligado_com_parcela",
            ),
        ]

    def __str__(self) -> str:
        return f"compra de {self.veiculo_id}"


class OrigemPreco(models.TextChoices):
    TELA_PRECOS = "tela_precos", "Tela de preços"
    FICHA = "ficha", "Ficha do veículo"
    CADASTRO = "cadastro", "Cadastro"
    IMPORTACAO = "importacao", "Importação"
    MIGRACAO = "migracao", "Migração"
    AGENDAMENTO = "agendamento", "Preço agendado"


class AlvoPreco(models.TextChoices):
    PLANO = "plano", "Plano"
    REGRAS = "regras", "Regras"
    CUSTOS = "custos", "Custos"
    PLANO_COMPRA = "plano_compra", "Locação com compra"
    VALOR_VENDA = "valor_venda", "Valor de venda"
    ALUGUEL = "aluguel", "Aluguel"  # VEI-21


class HistoricoPrecoVeiculo(ModeloBase):
    """Uma linha por campo mudado (VEI-17). Imutável: só o serviço escreve, sem update nem
    delete. `por` nulo = Sistema ou migração."""

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="historico_precos")
    em = models.DateTimeField()
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    origem = models.CharField(max_length=12, choices=OrigemPreco.choices)
    alvo = models.CharField(max_length=12, choices=AlvoPreco.choices)
    alvo_id = models.BigIntegerField(null=True, blank=True)
    alvo_nome = models.CharField(max_length=60, blank=True, default="")
    campo = models.CharField(max_length=40)
    de = models.JSONField(null=True, blank=True)
    para = models.JSONField(null=True, blank=True)
    lote = models.UUIDField(default=uuid.uuid4)

    # O nome do plano copiado ("Semanal", "Entregador", o do `outro`), não de pessoa: vai inteiro.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["alvo_nome"]}

    class Meta:
        verbose_name = "histórico de preço do veículo"
        verbose_name_plural = "histórico de preços do veículo"
        ordering = ["em", "id"]
        indexes = [models.Index(fields=["veiculo", "em"], name="historico_preco_veiculo_em")]

    def __str__(self) -> str:
        return f"{self.veiculo_id}: {self.alvo}.{self.campo}"


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
