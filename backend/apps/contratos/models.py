"""Modelos de contrato versionados e contratos gerados (modelo de dados, itens 15 e 16; ADR 0011).

O contrato não conhece a origem: guarda a origem genérica (`locacao`; `venda` na fase 2). O PDF
fica no armazenamento privado (AUD-05) e o link de assinatura guarda só o hash do token (S-15).
"""

import uuid
from typing import ClassVar

from django.db import models

from comum import arquivos
from comum.auditoria import Categoria
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase


class Finalidade(models.TextChoices):
    LOCACAO = "locacao", "Locação"
    VENDA = "venda", "Venda"


class ModeloContrato(ModeloBase):
    """Editar um modelo publicado cria uma linha nova com `versao + 1`; a anterior não muda
    (`LOC-15`). `grupo` junta as versões do mesmo modelo."""

    nome = models.CharField(max_length=80)
    finalidade = models.CharField(max_length=10, choices=Finalidade.choices)
    arquivado = models.BooleanField(default=False)
    versao = models.PositiveIntegerField(default=1)
    texto = models.TextField()
    publicado = models.BooleanField(default=False)
    publicado_em = models.DateTimeField(null=True, blank=True)
    grupo = models.UUIDField(default=uuid.uuid4)

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

    class Meta:
        verbose_name = "modelo de contrato"
        verbose_name_plural = "modelos de contrato"
        ordering = ["nome", "-versao"]
        constraints = [
            models.UniqueConstraint(fields=["grupo", "versao"], name="modelo_grupo_versao_unico"),
            models.UniqueConstraint(
                fields=["grupo"],
                condition=models.Q(publicado=True, arquivado=False),
                name="modelo_um_publicado_por_grupo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome} v{self.versao}"


class OrigemContrato(models.TextChoices):
    LOCACAO = "locacao", "Locação"
    VENDA = "venda", "Venda"


class TipoContrato(models.TextChoices):
    CONTRATO = "contrato", "Contrato"
    ADITIVO = "aditivo", "Aditivo"  # LOC-08


class StatusContrato(models.TextChoices):
    GERADO = "gerado", "Gerado"
    ENVIADO = "enviado", "Enviado"
    ASSINADO = "assinado", "Assinado"
    CANCELADO = "cancelado", "Cancelado"


S = StatusContrato


class Contrato(MaquinaDeEstados, ModeloBase):
    """Fluxo da retirada, passo 3: `gerado` (PDF na fila) → `enviado` (link no WhatsApp) →
    `assinado`. O texto final fica em `versao_texto_html` e não muda (`LOC-15`)."""

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.GERADO: {S.ENVIADO, S.CANCELADO},
        S.ENVIADO: {S.ASSINADO, S.CANCELADO},
        S.ASSINADO: set(),
        S.CANCELADO: set(),
    }
    REGRA_TRANSICAO = "transicao_contrato"
    CATEGORIA_AUDITORIA = Categoria.OPERACAO

    origem_tipo = models.CharField(max_length=10, choices=OrigemContrato.choices)
    origem_id = models.BigIntegerField()
    origem_codigo = models.CharField(max_length=20)
    filial = models.ForeignKey("filiais.Filial", on_delete=models.PROTECT, related_name="+")
    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="+")
    # Nulo no aditivo, que usa o texto padrão do sistema.
    modelo = models.ForeignKey(
        ModeloContrato, on_delete=models.PROTECT, null=True, blank=True, related_name="contratos"
    )
    versao_modelo = models.PositiveIntegerField(null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=TipoContrato.choices)
    titulo = models.CharField(max_length=120)
    status = models.CharField(max_length=10, choices=StatusContrato.choices, default=S.GERADO)
    versao_texto_html = models.TextField()
    clausula_juros = models.BooleanField(default=False)  # FIN-03
    pdf = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    hash_pdf = models.CharField(max_length=64, blank=True, default="")
    pdf_assinado = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    hash_pdf_assinado = models.CharField(max_length=64, blank=True, default="")
    enviado_em = models.DateTimeField(null=True, blank=True)
    assinado_em = models.DateTimeField(null=True, blank=True)
    assinado_ip = models.GenericIPAddressField(null=True, blank=True)
    assinatura_aparelho = models.CharField(max_length=200, blank=True, default="")
    token_assinatura_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    token_assinatura_expira_em = models.DateTimeField(null=True, blank=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True, default="")
    lembrete_aditivo_em = models.DateTimeField(null=True, blank=True)  # LOC-08

    # O texto final tem os dados do cliente (CPF, endereço): não vai para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "omitir": ["versao_texto_html"],
        "mascarar": ["assinado_ip"],
        "inteiro": ["token_assinatura_expira_em"],
    }

    class Meta:
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        indexes = [
            models.Index(fields=["origem_tipo", "origem_id"], name="contrato_origem_idx"),
            models.Index(fields=["status"], name="contrato_status_idx"),
        ]
        constraints = [
            # Um contrato vigente (não cancelado) por origem; aditivos são vários.
            models.UniqueConstraint(
                fields=["origem_tipo", "origem_id"],
                condition=models.Q(tipo="contrato") & ~models.Q(status="cancelado"),
                name="contrato_um_vigente_por_origem",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.titulo} ({self.origem_codigo})"
