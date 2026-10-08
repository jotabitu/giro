"""Empresa (tenant) e domínio. Mínimo para o django-tenants; a T-010 completa (PLT-01, PLT-03)."""

from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from comum.models import ModeloBase


class Empresa(TenantMixin, ModeloBase):  # type: ignore[django-manager-missing]
    class Status(models.TextChoices):
        EM_TESTE = "em_teste", "Em teste"
        ATIVA = "ativa", "Ativa"
        INADIMPLENTE = "inadimplente", "Inadimplente"
        SUSPENSA = "suspensa", "Suspensa"
        PAUSADA = "pausada", "Pausada"
        CANCELADA = "cancelada", "Cancelada"

    nome = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EM_TESTE)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        verbose_name = "empresa"

    def __str__(self) -> str:
        return self.nome


class Dominio(DomainMixin):
    class Meta:
        verbose_name = "domínio"

    def __str__(self) -> str:
        return str(self.domain)
