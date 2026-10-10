"""Configuração da empresa (modelo de dados, "Apoio do schema da empresa").

Uma linha só por schema, criada junto com a empresa (`plataforma.empresa_criada`). Por enquanto
`exige_2fa_todos` (USR-02, T-011), as regras configuráveis que a locação usa (T-015) e a multa e
os juros do contrato (FIN-03, T-090); marca e ramo entram com a tela Config.
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
    # FIN-03: multa até 2% e juros até 1% ao mês; vão para o contrato (T-090).
    multa_atraso_pct = PercentualField(default=Decimal("2.00"))
    juros_mes_pct = PercentualField(default=Decimal("1.00"))
    # Trava de linha única: sempre 1.
    unica = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {}

    class Meta:
        verbose_name = "configuração da empresa"
        constraints = [
            models.CheckConstraint(condition=models.Q(unica=1), name="configuracao_linha_unica"),
            models.CheckConstraint(
                condition=models.Q(multa_atraso_pct__gte=0, multa_atraso_pct__lte=Decimal("2.00")),
                name="configuracao_multa_ate_2_pct",
            ),
            models.CheckConstraint(
                condition=models.Q(juros_mes_pct__gte=0, juros_mes_pct__lte=Decimal("1.00")),
                name="configuracao_juros_ate_1_pct",
            ),
        ]

    def __str__(self) -> str:
        return "Configuração da empresa"
