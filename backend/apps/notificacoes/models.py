"""Avisos do sino (modelo de dados, "Notificacao"). O mínimo da T-079: alerta e tarefa urgente.

`notificacoes` é canal (ADR 0011): recebe destinatários, texto e link, e não conhece a origem.
"""

from typing import ClassVar

from django.db import models

from comum.models import ModeloBase


class Notificacao(ModeloBase):
    destinatario = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, related_name="notificacoes"
    )
    tipo = models.CharField(max_length=40)
    titulo = models.CharField(max_length=200)
    link = models.CharField(max_length=200, blank=True, default="")
    # Tarefa urgente para a pessoa (ex.: VEI-03 com o veículo alugado), não só um aviso.
    urgente = models.BooleanField(default=False)
    # Idempotência: o mesmo aviso, com a mesma chave, chega uma vez só a cada pessoa.
    chave = models.CharField(max_length=80, blank=True, default="")
    lida_em = models.DateTimeField(null=True, blank=True)

    # "chave" aqui é a de idempotência (ex.: aut06-alerta-9), não segredo.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["chave"]}

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-criado_em", "-id"]
        indexes = [models.Index(fields=["destinatario", "lida_em"], name="notificacao_nao_lidas")]
        constraints = [
            models.UniqueConstraint(
                fields=["destinatario", "chave"],
                condition=~models.Q(chave=""),
                name="notificacao_uma_por_chave",
            )
        ]

    def __str__(self) -> str:
        return f"{self.tipo} · {self.destinatario_id}"
