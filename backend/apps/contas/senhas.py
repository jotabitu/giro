"""Validação de senha da tela `Acesso-Senha` (contrato de contas, "Senha").

12 caracteres ou mais, com letras e números, diferente do e-mail e do nome da empresa, fora da
lista de senhas comuns do Django. Cada validador responde um texto pronto para a tela.
"""

import re
from typing import Any

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError

from comum.empresa import nome_da_empresa

TAMANHO_MINIMO = 12


class TamanhoMinimo:
    def validate(self, senha: str, user: Any = None) -> None:
        if len(senha) < TAMANHO_MINIMO:
            raise ValidationError(f"Use {TAMANHO_MINIMO} caracteres ou mais.", code="senha_curta")

    def get_help_text(self) -> str:
        return f"Use {TAMANHO_MINIMO} caracteres ou mais."


class LetrasENumeros:
    def validate(self, senha: str, user: Any = None) -> None:
        if not re.search(r"[^\W\d_]", senha) or not re.search(r"\d", senha):
            raise ValidationError("Use letras e números.", code="senha_sem_letras_e_numeros")

    def get_help_text(self) -> str:
        return "Use letras e números."


def _comparavel(texto: str) -> str:
    return re.sub(r"[\W_]", "", texto).casefold()


class DiferenteDoEmailEDaEmpresa:
    """A senha não pode ser o e-mail (nem a parte antes do @) nem o nome da empresa."""

    def validate(self, senha: str, user: Any = None) -> None:
        senha_comparavel = _comparavel(senha)
        email = str(getattr(user, "email", "") or "")
        proibidas = {_comparavel(email), _comparavel(email.split("@")[0])}
        if senha_comparavel and senha_comparavel in proibidas - {""}:
            raise ValidationError("A senha não pode ser o seu e-mail.", code="senha_e_email")
        empresa = nome_da_empresa()
        if empresa and senha_comparavel == _comparavel(empresa):
            raise ValidationError("A senha não pode ser o nome da empresa.", code="senha_e_empresa")

    def get_help_text(self) -> str:
        return "Não use o seu e-mail nem o nome da empresa."


class SenhaComum(CommonPasswordValidator):
    def validate(self, password: str, user: Any = None) -> None:
        try:
            super().validate(password, user)
        except ValidationError as erro:
            raise ValidationError(
                "Esta senha é muito comum. Escolha outra.", code="senha_comum"
            ) from erro
