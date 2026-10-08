"""Mudanças na configuração da empresa, sempre auditadas."""

from django.db import transaction

from comum.auditoria import Categoria, auditar

from .models import ConfiguracaoEmpresa


def criar_configuracao_padrao() -> ConfiguracaoEmpresa:
    """Linha única com os padrões. Idempotente."""
    configuracao, _ = ConfiguracaoEmpresa.objects.get_or_create(unica=1)
    return configuracao


def definir_exige_2fa_todos(valor: bool) -> ConfiguracaoEmpresa:
    """USR-02: o administrador exige 2 etapas de todos.

    Ligar derruba, no próximo uso, os tokens sem `otp` de quem ainda não confirmou o código
    (ADR 0013, item 3): a autenticação lê este valor a cada requisição.
    """
    with transaction.atomic():
        criar_configuracao_padrao()
        configuracao = ConfiguracaoEmpresa.objects.select_for_update().get(unica=1)
        if configuracao.exige_2fa_todos == valor:
            return configuracao
        with auditar(configuracao, "empresa.exigir_2fa_todos", Categoria.SEGURANCA, regra="USR-02"):
            configuracao.exige_2fa_todos = valor
            configuracao.save(update_fields=["exige_2fa_todos", "atualizado_em"])
    return configuracao
