"""Configuração da empresa (modelo de dados, "Apoio do schema da empresa").

Uma linha só por schema, criada junto com a empresa (`plataforma.empresa_criada`). Por enquanto
`exige_2fa_todos` (USR-02, T-011), as regras configuráveis que a locação usa (T-015) e a multa e
os juros do contrato (FIN-03, T-090), a marca e a meta de ocupação (T-129, `docs/api/empresas.md`)
e o ramo (PLT-12, ADR 0024, T-262). A cor sobre a marca e as cores suaves são calculadas na leitura
(`marca.py`), nunca guardadas.
"""

from decimal import Decimal
from typing import ClassVar

from django.db import models

from comum import arquivos
from comum.campos import CentavosField, PercentualField
from comum.models import ModeloBase


class Atividade(models.TextChoices):
    """O que a empresa faz (PLT-12, passo 7 da implantação)."""

    ALUGA = "aluga", "Locação"
    VENDE = "vende", "Venda"
    AMBOS = "ambos", "Locação e venda"


class TrabalhaCom(models.TextChoices):
    MOTOS = "motos", "motos"
    CARROS = "carros", "carros"
    AMBOS = "ambos", "motos e carros"


class ConfiguracaoEmpresa(ModeloBase):
    exige_2fa_todos = models.BooleanField(default=False)  # USR-02
    tolerancia_atraso_minutos = models.PositiveSmallIntegerField(default=60)  # LOC-10
    desconto_sem_aprovacao_pct = PercentualField(default=Decimal("5.00"))  # LOC-03, APR-01
    comissao_locacao_centavos = CentavosField(default=1600)  # FIN-09
    # FIN-03: multa até 2% e juros até 1% ao mês; vão para o contrato (T-090).
    multa_atraso_pct = PercentualField(default=Decimal("2.00"))
    juros_mes_pct = PercentualField(default=Decimal("1.00"))
    # Marca (ADR 0004). Vazio ou nulo = o padrão: nome da compra e a cor do design system.
    nome_exibicao = models.CharField(max_length=80, blank=True, default="")
    logo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        null=True,
        blank=True,
    )
    logo_largura = models.PositiveIntegerField(null=True, blank=True)
    logo_altura = models.PositiveIntegerField(null=True, blank=True)
    cor_marca = models.CharField(max_length=7, blank=True, default="")  # "#RRGGBB"
    meta_ocupacao_pct = PercentualField(default=Decimal("80.00"))  # painel (VEI-06)
    # Ramo (PLT-12, ADR 0024, item 2): muda só por `services.mudar_ramo`.
    atividade = models.CharField(max_length=5, choices=Atividade.choices, default=Atividade.AMBOS)
    trabalha_com = models.CharField(
        max_length=6, choices=TrabalhaCom.choices, default=TrabalhaCom.MOTOS
    )
    # Trava de linha única: sempre 1.
    unica = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    # A marca é pública na tela de login: vai inteira. O logo entra pelo nome do arquivo, que é o
    # resumo do conteúdo limpo (T-153), nunca pelo conteúdo.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": ["nome_exibicao", "cor_marca", "logo"]
    }

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
            models.CheckConstraint(
                condition=models.Q(cor_marca="") | models.Q(cor_marca__regex=r"^#[0-9A-F]{6}$"),
                name="configuracao_cor_marca_hex",
            ),
        ]

    def __str__(self) -> str:
        return "Configuração da empresa"
