"""Usuário e convite, nos dois schemas (ADR 0008).

No `public` a linha é da equipe da plataforma (`funcao_plataforma`); no schema da empresa, da
locadora (`perfil`). `status` segue `USR-01` e `USR-04` e só muda por `comum.estados.transicionar`.
Sessões, permissões extras e o restante das 2 etapas da empresa entram com a T-011.
"""

from typing import Any, ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django_tenants.utils import get_public_schema_name

from comum.auditoria import Categoria
from comum.conexao import schema_atual
from comum.estados import EstadosQuerySet, MaquinaDeEstados
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


class StatusUsuario(models.TextChoices):
    CONVITE_PENDENTE = "convite_pendente", "Convite pendente"
    ATIVO = "ativo", "Ativo"
    DESATIVADO = "desativado", "Desativado"


def no_schema_publico() -> bool:
    return bool(schema_atual() == get_public_schema_name())


class UsuarioManager(BaseUserManager.from_queryset(EstadosQuerySet)):  # type: ignore[misc]
    def create_user(self, email: str, password: str | None = None, **campos: Any) -> "Usuario":
        if not email:
            raise ValueError("Informe o e-mail.")
        usuario: Usuario = self.model(email=self.normalize_email(email).lower(), **campos)
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


class Usuario(AbstractBaseUser, PermissionsMixin, MaquinaDeEstados, ModeloBase):
    email = models.EmailField(unique=True)
    nome = models.CharField(max_length=150)
    celular = models.CharField(max_length=13, blank=True, default="")
    perfil = models.CharField(max_length=20, choices=Perfil.choices, blank=True, default="")
    funcao_plataforma = models.CharField(
        max_length=20, choices=FuncaoPlataforma.choices, blank=True, default=""
    )
    status = models.CharField(
        max_length=20, choices=StatusUsuario.choices, default=StatusUsuario.ATIVO
    )
    is_staff = models.BooleanField(default=False)
    # Códigos de 2 etapas errados seguidos e o fim do bloqueio (PLT-08; USR-06 na T-011).
    tentativas_erradas = models.PositiveSmallIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    objects: ClassVar[UsuarioManager] = UsuarioManager()

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "convite_pendente": {"ativo", "desativado"},
        "ativo": {"desativado"},
        "desativado": {"ativo"},
    }
    REGRA_TRANSICAO = "transicao_usuario"
    CATEGORIA_AUDITORIA = Categoria.SEGURANCA

    # Funcionário é o ator dos eventos: nome, e-mail e celular vão inteiros (ADR 0014, item 3).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "omitir": ["password"],
        "inteiro": ["email", "celular"],
    }

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
        return self.status == StatusUsuario.ATIVO

    @property
    def da_plataforma(self) -> bool:
        return bool(self.funcao_plataforma)

    @property
    def exige_2fa(self) -> bool:
        """ADR 0013, item 3. Na plataforma é sempre (PLT-08); os perfis da empresa vêm na T-011."""
        return self.da_plataforma

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        super().clean()
        if no_schema_publico() and self.perfil:
            raise ValidationError({"perfil": "Usuário da plataforma não tem perfil de locadora."})
        if not no_schema_publico() and self.funcao_plataforma:
            raise ValidationError(
                {"funcao_plataforma": "Usuário da locadora não tem função na plataforma."}
            )


class Convite(ModeloBase):
    """Convite de 7 dias (USR-01), da equipe da plataforma ou da locadora (ADR 0008, item 3).

    Guarda só o hash do token; o token em claro sai uma vez, no link.
    """

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="convites")
    token_hash = models.CharField(max_length=64, unique=True)
    enviado_whatsapp = models.BooleanField(default=False)
    expira_em = models.DateTimeField()
    aceito_em = models.DateTimeField(null=True, blank=True)
    enviado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "convite"
        indexes = [models.Index(fields=["usuario", "-criado_em"], name="convite_usuario_idx")]

    def __str__(self) -> str:
        return f"Convite de {self.usuario_id}"
