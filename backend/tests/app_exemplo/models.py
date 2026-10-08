"""Model só de teste para exercitar a fundação de `comum` como um módulo real usaria."""

from django.db import models

from comum.campos import CentavosField, PercentualField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase, ModeloComCodigo


class Pedido(ModeloComCodigo, MaquinaDeEstados, ModeloBase):
    PREFIXO_CODIGO = "LOC"
    REGRA_TRANSICAO = "LOC-00"

    class Status(models.TextChoices):
        RESERVADA = "reservada", "Reservada"
        ATIVA = "ativa", "Ativa"
        ENCERRADA = "encerrada", "Encerrada"
        CANCELADA = "cancelada", "Cancelada"

    TRANSICOES = {
        "reservada": {"ativa", "cancelada"},
        "ativa": {"encerrada"},
    }
    CAMPOS_PESSOAIS = ("cpf_cliente",)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVADA)
    cliente = models.CharField(max_length=100, default="")
    cpf_cliente = models.CharField(max_length=14, blank=True, default="")
    valor_centavos = CentavosField(default=0)
    desconto_pct = PercentualField(default=0)

    def __str__(self) -> str:
        return self.codigo
