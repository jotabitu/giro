"""Usuário e convite, nos dois schemas (ADR 0008).

No `public` a linha é da equipe da plataforma (`funcao_plataforma`); no schema da empresa, da
locadora (`perfil`). `status` segue `USR-01` e `USR-04` e só muda por `comum.estados.transicionar`.

Sessões (ADR 0014, item 1) e 2 etapas (ADR 0013, item 3) valem nos dois schemas. A semente do
autenticador fica cifrada com `GIRO_CHAVE_SEGREDOS` e os códigos de recuperação só em hash
(P-08 da T-057): quem lê o banco ou um backup não gera códigos válidos.
"""

import secrets
import time
from base64 import b32encode
from binascii import unhexlify
from datetime import datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import quote, urlencode

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django_otp.models import Device, DeviceManager
from django_otp.oath import TOTP
from django_tenants.utils import get_public_schema_name, schema_context

from comum import cripto
from comum.auditoria import Categoria
from comum.campos import CampoCifrado
from comum.conexao import conexao, schema_atual
from comum.empresa import exige_2fa_todos
from comum.estados import EstadosQuerySet, MaquinaDeEstados
from comum.models import ModeloBase, ModeloComCifra


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


class PermissaoExtra(models.TextChoices):
    """USR-03: somam ao perfil, nunca tiram."""

    APROVAR_DESCONTO = "aprovar_desconto", "Aprovar descontos acima do limite"
    CANCELAR_CONTRATO = "cancelar_contrato", "Cancelar contratos"
    RELATORIOS_TODAS_FILIAIS = "relatorios_todas_filiais", "Ver relatórios de todas as filiais"


# USR-02: perfis que sempre exigem 2 etapas.
PERFIS_COM_2FA = frozenset({"administrador", "financeiro"})


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


# O plugin do mypy não resolve o gerenciador `autenticadores` (base do django-otp sem tipos).
class Usuario(  # type: ignore[django-manager-missing]
    AbstractBaseUser, PermissionsMixin, MaquinaDeEstados, ModeloBase
):
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
    permissoes_extras = ArrayField(
        models.CharField(max_length=30, choices=PermissaoExtra.choices),
        blank=True,
        default=list,
    )
    is_staff = models.BooleanField(default=False)
    # Códigos de 2 etapas e senhas errados seguidos e o fim do bloqueio (PLT-08; USR-06 na T-011).
    tentativas_erradas = models.PositiveSmallIntegerField(default=0)
    senhas_erradas = models.PositiveSmallIntegerField(default=0)
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
    def exige_2fa_pela_regra(self) -> bool:
        """Obrigatório para a pessoa: plataforma (PLT-08), perfil ou "exigir para todos" (USR-02).

        É o `dois_fatores.obrigatorio` do `eu`; quem é obrigado não desliga o próprio.
        """
        if self.da_plataforma:
            return True
        return self.perfil in PERFIS_COM_2FA or exige_2fa_todos()

    @property
    def exige_2fa(self) -> bool:
        """ADR 0013, item 3: pela regra ou porque a pessoa ativou um autenticador."""
        return (
            self.exige_2fa_pela_regra
            or Autenticador.objects.filter(user_id=self.pk, confirmed=True).exists()
        )

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


# --- Sessões (ADR 0014, item 1; USR-06) ---


class TipoSessao(models.TextChoices):
    DESKTOP = "desktop", "Desktop"
    CELULAR = "celular", "Celular"


class MotivoRevogacao(models.TextChoices):
    SAIU = "saiu", "Saiu"
    REVOGADA_PELO_USUARIO = "revogada_pelo_usuario", "Encerrada pela pessoa"
    REVOGADA_PELO_ADMINISTRADOR = "revogada_pelo_administrador", "Encerrada pelo administrador"
    USUARIO_DESATIVADO = "usuario_desativado", "Usuário desativado"
    EXPIROU = "expirou", "Expirou"
    SENHA_ALTERADA = "senha_alterada", "Senha trocada ou redefinida"
    REFRESH_REUSADO = "refresh_reusado", "Renovação repetida (P-07)"


# USR-06: sem uso por este tempo, a sessão acaba. Não existe "manter conectado".
DURACAO_DA_SESSAO = {
    "desktop": timedelta(hours=12),
    "celular": timedelta(days=30),
}


class Sessao(ModeloBase):
    """Um login completo. Access e refresh levam o `id` na claim `sid`."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="sessoes")
    tipo = models.CharField(max_length=10, choices=TipoSessao.choices)
    aparelho = models.CharField(max_length=200, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    ultimo_uso = models.DateTimeField()
    expira_em = models.DateTimeField()
    # `jti` do refresh vigente: outro refresh da mesma sessão é reuso (P-07 da T-057).
    refresh_jti = models.CharField(max_length=64, blank=True, default="")
    revogada_em = models.DateTimeField(null=True, blank=True)
    revogada_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    motivo_revogacao = models.CharField(
        max_length=30, choices=MotivoRevogacao.choices, blank=True, default=""
    )

    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "omitir": ["refresh_jti"],
        "mascarar": ["ip"],
    }

    class Meta:
        verbose_name = "sessão"
        indexes = [models.Index(fields=["usuario", "revogada_em"], name="sessao_usuario_idx")]

    def __str__(self) -> str:
        return f"Sessão {self.pk} ({self.tipo})"

    @property
    def duracao(self) -> timedelta:
        return DURACAO_DA_SESSAO[self.tipo]

    def ativa_em(self, momento: datetime) -> bool:
        return self.revogada_em is None and self.expira_em > momento


# --- 2 etapas (ADR 0013, item 3; P-08 da T-057) ---


def empresa_da_cifra() -> int:
    """Empresa da conexão para a cifra e o hash dos segredos de 2 etapas.

    No public, fora de uma requisição (comando, teste), a conexão não tem a linha de `Empresa`;
    busca a do schema atual.
    """
    empresa_id = getattr(getattr(conexao(), "tenant", None), "pk", None)
    if empresa_id is not None:
        return int(empresa_id)
    from apps.plataforma.models import Empresa

    schema = schema_atual()
    with schema_context(get_public_schema_name()):
        return int(Empresa.objects.values_list("pk", flat=True).get(schema_name=schema))


class Autenticador(ModeloComCifra, Device):
    """TOTP de 6 dígitos e 30 s, com a semente cifrada (no lugar do `TOTPDevice`).

    É um `Device` do django-otp: o login do Django Admin (`OTPAdminSite`) marca a sessão com ele.
    """

    user = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="autenticadores")
    chave = CampoCifrado(tipo=cripto.SEGREDOS)
    ultimo_passo = models.BigIntegerField(default=-1)  # nenhum código vale duas vezes

    objects: ClassVar[models.Manager["Autenticador"]] = DeviceManager()  # `devices_for_user`

    PASSO = 30
    DIGITOS = 6
    TOLERANCIA = 1  # um passo antes e um depois

    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"omitir": ["chave"]}

    class Meta:
        verbose_name = "autenticador"

    def empresa_id_da_cifra(self) -> int:
        return empresa_da_cifra()

    def gerar_chave(self) -> None:
        self.definir_chave(secrets.token_hex(20))

    @property
    def bin_key(self) -> bytes:
        return unhexlify(self.chave_claro())

    def totp(self) -> TOTP:
        totp = TOTP(self.bin_key, self.PASSO, 0, self.DIGITOS)
        totp.time = time.time()
        return totp

    def verify_token(self, token: Any) -> bool:
        try:
            numero = int(str(token).strip())
        except ValueError:
            return False
        totp = self.totp()
        if not totp.verify(numero, self.TOLERANCIA, self.ultimo_passo + 1):
            return False
        self.ultimo_passo = totp.t()
        self.save(update_fields=["ultimo_passo"])
        return True

    def chave_legivel(self) -> str:
        """Para "Sem câmera? Digite a chave": base32 em grupos de 4."""
        texto = b32encode(self.bin_key).decode().rstrip("=")
        return " ".join(texto[i : i + 4] for i in range(0, len(texto), 4))

    def config_url_para(self, emissor: str) -> str:
        """`otpauth://` com o emissor dado: na empresa, o nome da locadora (white label)."""
        emissor = emissor.replace(":", "")
        rotulo = f"{emissor}:{self.user.get_username()}"
        parametros = urlencode(
            {
                "secret": b32encode(self.bin_key).decode(),
                "algorithm": "SHA1",
                "digits": self.DIGITOS,
                "period": self.PASSO,
            }
        )
        return f"otpauth://totp/{quote(rotulo)}?{parametros}&issuer={quote(emissor)}"


class CodigoRecuperacao(ModeloBase):
    """Código de uso único. Guarda só o HMAC com a chave da empresa (P-08)."""

    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="codigos_recuperacao"
    )
    codigo_hash = models.CharField(max_length=64)
    usado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "código de recuperação"
        indexes = [models.Index(fields=["usuario", "codigo_hash"], name="codigo_rec_idx")]

    def __str__(self) -> str:
        return f"Código de recuperação {self.pk}"


def hash_do_codigo(codigo: str) -> str:
    return cripto.hash_busca(codigo, empresa_id=empresa_da_cifra())


# --- Esqueci a senha ---


VALIDADE_DO_LINK_DE_SENHA = timedelta(hours=1)


class RedefinicaoSenha(ModeloBase):
    """Link de 1 hora e uso único. Só o hash do token; o token sai no envio do e-mail."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="+")
    token_hash = models.CharField(max_length=64, unique=True)
    pedido_em = models.DateTimeField()  # pelo relógio do Giro: conta os 3 pedidos por hora
    expira_em = models.DateTimeField()
    usado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "redefinição de senha"
        indexes = [models.Index(fields=["usuario", "-pedido_em"], name="redefinicao_usuario_idx")]

    def __str__(self) -> str:
        return f"Redefinição de senha {self.pk}"
