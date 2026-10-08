"""Login do Django Admin com o bloqueio e a auditoria do PLT-08 (P-01 da T-057).

O formulário padrão do `OTPAdminSite` confere o código pelo django-otp, sem contagem (o atraso
progressivo está desligado nas settings). Este passa por `dois_fatores.tentar_entrar`, o mesmo
da API: linha do usuário travada, 3 códigos ou 5 senhas errados bloqueiam por 15 minutos, e
cada entrada ou falha vira evento de segurança.
"""

from typing import Any, NoReturn

from django.core.exceptions import ValidationError
from django_otp.admin import OTPAdminAuthenticationForm

from comum.erros import MuitasTentativas

from . import dois_fatores
from .models import Usuario

CREDENCIAIS_INVALIDAS = "E-mail, senha ou código incorretos"
SEM_ACESSO = "Esta conta não tem acesso ao Admin."
SEM_AUTENTICADOR = "Configure a verificação em 2 etapas no painel da plataforma antes de entrar."


class LoginDoAdmin(OTPAdminAuthenticationForm):
    def clean(self) -> dict[str, Any]:
        email = (self.cleaned_data.get("username") or "").strip().lower()
        senha = self.cleaned_data.get("password") or ""
        if not email or not senha:
            raise ValidationError(CREDENCIAIS_INVALIDAS, code="invalid_login")
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            Usuario().set_password(senha)  # mesmo tempo de resposta de quem existe
            self._falhou(None, "e-mail")
        try:
            tentativa = dois_fatores.tentar_entrar(
                usuario, senha=senha, codigo=self.cleaned_data.get("otp_token") or ""
            )
        except MuitasTentativas as bloqueado:
            raise ValidationError(bloqueado.mensagem, code="bloqueado") from bloqueado
        if tentativa.falha is not None:
            motivo = "código" if tentativa.falha == dois_fatores.Falha.CODIGO else "senha"
            self._falhou(tentativa.usuario, motivo, tentativa.bloqueio)
        usuario = tentativa.usuario
        if not usuario.is_active or not usuario.is_staff:
            self._falhou(usuario, "sem acesso ao Admin", mensagem=SEM_ACESSO)
        if tentativa.dispositivo is None:
            self._falhou(usuario, "sem autenticador", mensagem=SEM_AUTENTICADOR)
        self._auditar("usuario.entrar", usuario)
        # Com `otp_device`, o login do django-otp marca a sessão como verificada.
        usuario.otp_device = tentativa.dispositivo  # type: ignore[attr-defined]
        self.user_cache = usuario
        dados: dict[str, Any] = self.cleaned_data
        return dados

    def _falhou(
        self,
        usuario: Usuario | None,
        motivo: str,
        bloqueio: MuitasTentativas | None = None,
        mensagem: str = CREDENCIAIS_INVALIDAS,
    ) -> NoReturn:
        self._auditar("usuario.entrar_falhou", usuario, motivo)
        if bloqueio is not None:
            raise ValidationError(bloqueio.mensagem, code="bloqueado")
        raise ValidationError(mensagem, code="invalid_login")

    def _auditar(self, acao: str, usuario: Usuario | None, motivo: str = "") -> None:
        if self.request is not None:
            dois_fatores.auditar_entrada(self.request, acao, usuario, motivo)
