"""Usuário, nos dois schemas (ADR 0008).

No `public` a linha é da equipe da plataforma (`funcao_plataforma`); no schema da empresa, da
locadora (`perfil`). Convite, status, permissões extras e 2FA entram com a T-011.
"""

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django_tenants.utils import get_public_schema_name

from comum.conexao import schema_atual
from comum.models import ModeloBase


class Perfil(models.TextChoices):
    ADMINISTRADOR = "administrador", "Administrador"
    GERENTE = "gerente", "Gerente"
    VENDEDOR = "vendedor", "Vendedor"
    VISTORIADOR = "vistoriador", "Vistoriador"
    FINANCEIRO = "financeiro", "Financeiro"


class FuncaoPlataforma(models.TextChoices):
    DONO = "dono", "Dono"
    SUPORTE = "suporte", "Suporte"
    FINANCEIRO = "financeiro", "Financeiro"
    SUCESSO = "sucesso", "Sucesso do cliente"


def no_schema_publico() -> bool:
    return bool(schema_atual() == get_public_schema_name())


class UsuarioManager(BaseUserManager["Usuario"]):
    def create_user(self, email: str, password: str | None = None, **campos: Any) -> "Usuario":
        if not email:
            raise ValueError("Informe o e-mail.")
        usuario = self.model(email=self.normalize_email(email).lower(), **campos)
        usuario.set_password(password)
        usuario.full_clean(exclude=["password"])
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email: str, password: str | None = None, **campos: Any) -> "Usuario":
        campos.setdefault("is_staff", True)
        campos.setdefault("is_superuser", True)
        if no_schema_publico():
            campos.setdefault("funcao_plataforma", FuncaoPlataforma.DONO)
        else:
            campos.setdefault("perfil", Perfil.ADMINISTRADOR)
        return self.create_user(email, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin, ModeloBase):
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=150)
    perfil = models.CharField(max_length=20, choices=Perfil.choices, blank=True, default="")
    funcao_plataforma = models.CharField(
        max_length=20, choices=FuncaoPlataforma.choices, blank=True, default=""
    )
    ativo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects: ClassVar[UsuarioManager] = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        verbose_name = "usuário"
        constraints = [
            # Só um dos dois: equipe da plataforma ou usuário da locadora (ADR 0008).
            models.CheckConstraint(
                condition=(
                    (~models.Q(perfil="") & models.Q(funcao_plataforma=""))
                    | (models.Q(perfil="") & ~models.Q(funcao_plataforma=""))
                ),
                name="usuario_perfil_xor_funcao_plataforma",
            ),
        ]

    def __str__(self) -> str:
        return self.nome or self.email

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.ativo

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        super().clean()
        if no_schema_publico() and self.perfil:
            raise ValidationError({"perfil": "Usuário da plataforma não tem perfil de locadora."})
        if not no_schema_publico() and self.funcao_plataforma:
            raise ValidationError(
                {"funcao_plataforma": "Usuário da locadora não tem função na plataforma."}
            )
