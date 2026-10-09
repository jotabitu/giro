"""Filiais, feriados e o vínculo das pessoas com as filiais (FIL-01 a FIL-06, USR-07).

Modelo em `docs/decisoes/modelo-de-dados.md`, item 6. Muda só por `filiais.services`.
"""

from typing import ClassVar

from django.db import models
from django.db.models.functions import Lower

from comum.campos import CentavosField
from comum.models import ModeloAtivavel, ModeloBase

FUSO_PADRAO = "America/Sao_Paulo"
DIAS_DA_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
UFS = (
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
)  # fmt: skip


class Filial(ModeloBase, ModeloAtivavel):
    nome = models.CharField(max_length=80)
    cnpj = models.CharField(max_length=14, blank=True, default="")
    inscricao_estadual = models.CharField(max_length=20, blank=True, default="")
    inscricao_municipal = models.CharField(max_length=20, blank=True, default="")
    telefone = models.CharField(max_length=13, blank=True, default="")
    whatsapp = models.CharField(max_length=13, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    preco_litro_centavos = CentavosField(null=True, blank=True)  # DEV-01
    cep = models.CharField(max_length=8)
    logradouro = models.CharField(max_length=150)
    numero = models.CharField(max_length=20)
    complemento = models.CharField(max_length=80, blank=True, default="")
    bairro = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80)
    uf = models.CharField(max_length=2)
    matriz = models.BooleanField(default=False)
    # {"seg": [{"abre": "08:00", "fecha": "18:00"}], ..., "dom": []} (LOC-11)
    horario = models.JSONField(default=dict)
    fuso = models.CharField(max_length=40, default=FUSO_PADRAO)

    # Contato e endereço são da empresa, não de pessoa: vão inteiros (ADR 0014, item 3).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": ["nome", "telefone", "whatsapp", "email", "logradouro"],
    }

    class Meta:
        verbose_name = "filial"
        verbose_name_plural = "filiais"
        ordering = ["-matriz", "nome", "id"]
        constraints = [
            models.UniqueConstraint(Lower("nome"), name="filial_nome_unico"),
            # Só uma matriz (FIL-01); o serviço troca as duas na mesma transação.
            models.UniqueConstraint(
                fields=["matriz"], condition=models.Q(matriz=True), name="filial_uma_matriz"
            ),
        ]

    def __str__(self) -> str:
        return self.nome


class FeriadoFilial(ModeloBase, ModeloAtivavel):
    """Dia em que a filial fica fechada (FIL-03); conta como fechado para LOC-11."""

    class Origem(models.TextChoices):
        NACIONAL = "nacional", "Nacional"
        LOCAL = "local", "Local"

    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="feriados")
    data = models.DateField()
    nome = models.CharField(max_length=80)
    origem = models.CharField(max_length=10, choices=Origem.choices)

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

    class Meta:
        verbose_name = "feriado da filial"
        verbose_name_plural = "feriados da filial"
        ordering = ["data"]
        constraints = [
            models.UniqueConstraint(
                fields=["filial", "data"],
                condition=models.Q(ativo=True),
                name="feriado_filial_data_unico",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.data:%d/%m/%Y} · {self.nome}"


class UsuarioFilial(ModeloAtivavel, ModeloBase):
    """Filiais a que a pessoa tem acesso (USR-07); gerentes da filial vêm daqui (FIL-02).

    Tirar a filial da pessoa desativa o vínculo (`ativo=False`), sem apagar (F-03 da T-064);
    devolver a mesma filial reativa a linha.
    """

    usuario = models.ForeignKey(
        "contas.Usuario", on_delete=models.CASCADE, related_name="filiais_ligadas"
    )
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name="usuarios_ligados")

    class Meta:
        verbose_name = "filial do usuário"
        verbose_name_plural = "filiais do usuário"
        constraints = [
            models.UniqueConstraint(fields=["usuario", "filial"], name="usuario_filial_unico"),
        ]

    def __str__(self) -> str:
        return f"{self.usuario_id} → {self.filial_id}"
