"""Evento de auditoria imutável (AUD-01, AUD-02, ADR 0010).

Três camadas: o model recusa `save()` de registro existente e `delete()`, o queryset recusa
`update()` e `delete()`, e triggers PostgreSQL (migrações 0002 e 0003) recusam UPDATE, DELETE e
TRUNCATE. Só a função `auditoria_expurgar`, do papel `giro_expurgo`, apaga evento com mais de
5 anos (ADR 0016).
Grave sempre por `comum.auditoria` (`auditar`, `registrar_evento`) ou pela máquina de estados.
"""

from typing import Any, ClassVar, NoReturn

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from comum.auditoria import Categoria, TipoAtor


class EventoImutavel(Exception):
    """Tentativa de alterar ou apagar um evento de auditoria."""


class EventoQuerySet(models.QuerySet["EventoAuditoria"]):
    def update(self, **kwargs: Any) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser alterado (AUD-01).")

    def delete(self) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser apagado (AUD-01).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser alterado (AUD-01).")


class EventoAuditoria(models.Model):
    id = models.BigAutoField(primary_key=True)
    ocorrido_em = models.DateTimeField(auto_now_add=True)
    ator_tipo = models.CharField(max_length=10, choices=TipoAtor.choices)
    ator_id = models.BigIntegerField(null=True, blank=True)
    ator_nome = models.CharField(max_length=150)
    acesso_suporte_id = models.BigIntegerField(null=True, blank=True)
    acao = models.CharField(max_length=80)
    categoria = models.CharField(max_length=15, choices=Categoria.choices)
    objeto_tipo = models.CharField(max_length=60, blank=True, default="")
    objeto_id = models.BigIntegerField(null=True, blank=True)
    objeto_codigo = models.CharField(max_length=20, blank=True, default="")
    filial_id = models.BigIntegerField(null=True, blank=True)
    antes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    depois = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    motivo = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    aparelho = models.CharField(max_length=200, blank=True, default="")
    regra = models.CharField(max_length=10, blank=True, default="")

    objects = EventoQuerySet.as_manager()

    # O próprio evento nunca é auditado; o IP do ator vai inteiro (ADR 0014, item 3).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["ip", "ator_nome"]}

    class Meta:
        verbose_name = "evento de auditoria"
        verbose_name_plural = "eventos de auditoria"
        ordering = ["-ocorrido_em", "-id"]
        indexes = [
            models.Index(fields=["-ocorrido_em"], name="aud_ocorrido_idx"),
            models.Index(fields=["objeto_tipo", "objeto_id"], name="aud_objeto_idx"),
            models.Index(fields=["categoria", "ocorrido_em"], name="aud_categoria_idx"),
            models.Index(fields=["ator_id", "ocorrido_em"], name="aud_ator_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ocorrido_em:%d/%m/%Y %H:%M} · {self.ator_nome} · {self.acao}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise EventoImutavel("Evento de auditoria não pode ser alterado (AUD-01).")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser apagado (AUD-01).")
