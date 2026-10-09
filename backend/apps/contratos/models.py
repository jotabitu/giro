"""Modelos de contrato versionados (modelo de dados, item 16; ADR 0011).

Parte 1 da T-015: só o model e a leitura do modelo publicado, para a `IMP-04` da locação. A API
dos modelos (S-09), o contrato gerado, o PDF e a assinatura (S-15) entram na parte 2.
"""

import uuid
from typing import ClassVar

from django.db import models

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
