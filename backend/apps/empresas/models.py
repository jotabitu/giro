"""Configuração da empresa (modelo de dados, "Apoio do schema da empresa").

Uma linha só por schema, criada junto com a empresa (`plataforma.empresa_criada`). Por enquanto
`exige_2fa_todos` (USR-02, T-011) e as regras configuráveis que a locação usa (T-015); marca e
ramo entram com a tela Config.
"""

from decimal import Decimal
from typing import ClassVar

from django.db import models

from comum.campos import CentavosField, PercentualField
from comum.models import ModeloBase


class ConfiguracaoEmpresa(ModeloBase):
    exige_2fa_todos = models.BooleanField(default=False)  # USR-02
    tolerancia_atraso_minutos = models.PositiveSmallIntegerField(default=60)  # LOC-10
    desconto_sem_aprovacao_pct = PercentualField(default=Decimal("5.00"))  # LOC-03, APR-01
    comissao_locacao_centavos = CentavosField(default=1600)  # FIN-09
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
