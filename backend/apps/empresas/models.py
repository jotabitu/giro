"""Configuração da empresa (modelo de dados, "Apoio do schema da empresa").

Uma linha só por schema, criada junto com a empresa (`plataforma.empresa_criada`). Por enquanto
só `exige_2fa_todos` (USR-02, T-011); marca, ramo e regras configuráveis entram com a tela Config.
"""

from typing import ClassVar

from django.db import models

from comum.models import ModeloBase


class ConfiguracaoEmpresa(ModeloBase):
    exige_2fa_todos = models.BooleanField(default=False)  # USR-02
    # Trava de linha única: sempre 1.
    unica = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {}

    class Meta:
        verbose_name = "configuração da empresa"
        constraints = [
            models.CheckConstraint(condition=models.Q(unica=1), name="configuracao_linha_unica")
        ]

    def __str__(self) -> str:
        return "Configuração da empresa"
