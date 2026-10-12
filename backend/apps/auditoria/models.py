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

from comum import relogio
from comum.auditoria import Categoria, TipoAtor
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase


class EventoImutavel(Exception):
    """Tentativa de alterar ou apagar um evento de auditoria."""


class EventoQuerySet(models.QuerySet["EventoAuditoria"]):
    def update(self, **kwargs: Any) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser alterado (AUD-01).")

    def delete(self) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser apagado (AUD-01).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise EventoImutavel("Evento de auditoria não pode ser alterado (AUD-01).")


def _agora() -> Any:
    """Pelo relógio do domínio, como o resto da API (os testes congelam 07 out 2026)."""
    return relogio.agora()


class EventoAuditoria(models.Model):
    id = models.BigAutoField(primary_key=True)
    ocorrido_em = models.DateTimeField(default=_agora, editable=False)
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


# --- Exportação (AUD-07, S-15) ---


class ItemExportacao(models.TextChoices):
    CLIENTES = "clientes", "Clientes"
    VEICULOS = "veiculos", "Veículos"
    LOCACOES_CONTRATOS = "locacoes_contratos", "Locações e contratos"
    FINANCEIRO = "financeiro", "Financeiro"
    VISTORIAS_FOTOS = "vistorias_fotos", "Vistorias e fotos"
    AUDITORIA = "auditoria", "Auditoria"


class FormatoExportacao(models.TextChoices):
    PLANILHA = "planilha", "Planilha"
    CSV = "csv", "CSV"
    ZIP = "zip", "Backup completo"


class StatusExportacao(models.TextChoices):
    NA_FILA = "na_fila", "Na fila"
    PRONTA = "pronta", "Pronta"
    EXPIRADA = "expirada", "Expirada"
    FALHOU = "falhou", "Falhou"


class Exportacao(MaquinaDeEstados, ModeloBase):
    """Arquivo pedido pelo administrador (ou pelo backup automático, `AUT-11`). O link vale
    7 dias a partir de `pronta`; depois o arquivo sai do storage e a linha fica `expirada`.

    Quem pediu é copiado como na auditoria (`solicitada_por_id` nulo = "Automático").
    """

    solicitada_por_id = models.BigIntegerField(null=True, blank=True)
    solicitada_por_nome = models.CharField(max_length=150, blank=True, default="")
    itens = models.JSONField(default=list)
    formato = models.CharField(max_length=10, choices=FormatoExportacao.choices)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fim = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=StatusExportacao.choices, default=StatusExportacao.NA_FILA
    )
    arquivo = models.CharField(max_length=300, blank=True, default="")  # caminho no storage
    tamanho_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    expira_em = models.DateTimeField(null=True, blank=True)

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "na_fila": {"pronta", "falhou"},
        "pronta": {"expirada"},
        "expirada": set(),
        "falhou": set(),
    }
    REGRA_TRANSICAO = "AUD-07"
    CATEGORIA_AUDITORIA = Categoria.SEGURANCA
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["solicitada_por_nome"]}

    class Meta:
        verbose_name = "exportação"
        verbose_name_plural = "exportações"
        ordering = ["-criado_em", "-id"]

    def __str__(self) -> str:
        return f"Exportação {self.pk} · {self.formato} · {self.status}"
