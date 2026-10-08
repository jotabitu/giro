"""Leituras da configuração da empresa."""

from .models import ConfiguracaoEmpresa


def configuracao() -> ConfiguracaoEmpresa:
    """A linha da empresa atual, ou uma com os padrões (sem gravar) se ainda não existir."""
    return ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()


def exige_2fa_todos() -> bool:
    """USR-02. Registrada em `comum.empresa` para `contas` ler sem importar `empresas`."""
    return bool(
        ConfiguracaoEmpresa.objects.values_list("exige_2fa_todos", flat=True).first() or False
    )
