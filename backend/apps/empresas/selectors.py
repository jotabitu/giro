"""Leituras da configuração da empresa e da marca (`docs/api/empresas.md`)."""

import hashlib
from decimal import Decimal
from typing import Any

from django.core.cache import cache

from apps.plataforma.selectors import empresa_atual
from comum.conexao import schema_atual

from . import marca as cores_da_marca
from .models import ConfiguracaoEmpresa

PRAZO_DA_MARCA = 60 * 60  # 1 hora; a escrita da marca (Admin-Marca) apaga a chave
TIPOS_DO_LOGO = {"svg": "image/svg+xml", "png": "image/png"}


def configuracao() -> ConfiguracaoEmpresa:
    """A linha da empresa atual, ou uma com os padrões (sem gravar) se ainda não existir."""
    return ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()


def exige_2fa_todos() -> bool:
    """USR-02. Registrada em `comum.empresa` para `contas` ler sem importar `empresas`."""
    return bool(
        ConfiguracaoEmpresa.objects.values_list("exige_2fa_todos", flat=True).first() or False
    )


def meta_ocupacao_pct() -> Decimal:
    """Meta de ocupação do painel (`relatorios`). Sem a linha, o padrão 80,00."""
    valor = ConfiguracaoEmpresa.objects.values_list("meta_ocupacao_pct", flat=True).first()
    return valor if valor is not None else Decimal("80.00")


# --- Marca (ADR 0004, `docs/api/empresas.md`) ---


def chave_da_marca() -> str:
    return f"marca:{schema_atual()}"


def logo() -> tuple[bytes, str, str] | None:
    """`(conteúdo, tipo, extensão)` do logo guardado, ou `None` sem logo."""
    configuracao = ConfiguracaoEmpresa.objects.first()
    if configuracao is None or not configuracao.logo:
        return None
    extensao = configuracao.logo.name.rsplit(".", 1)[-1].lower()
    with configuracao.logo.open("rb") as arquivo:
        conteudo = arquivo.read()
    return conteudo, TIPOS_DO_LOGO.get(extensao, "application/octet-stream"), extensao


def _montar_marca() -> dict[str, Any]:
    configuracao = ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()
    nome = configuracao.nome_exibicao.strip() or empresa_atual().nome_exibicao
    arquivo = logo()
    resumo = hashlib.sha256()
    resumo.update(nome.encode())
    resumo.update(b"|" + (configuracao.cor_marca or "").encode() + b"|")
    if arquivo is not None:
        resumo.update(arquivo[0])
    versao = resumo.hexdigest()[:8]
    return {
        "nome_exibicao": nome,
        "iniciais": cores_da_marca.iniciais(nome),
        "logo": (
            {
                "url": f"/api/marca/logo/?v={versao}",
                "largura": configuracao.logo_largura,
                "altura": configuracao.logo_altura,
            }
            if arquivo is not None
            else None
        ),
        **cores_da_marca.cores(configuracao.cor_marca),
        "personalizada": bool(configuracao.cor_marca) or arquivo is not None,
        "versao": versao,
    }


def marca() -> dict[str, Any]:
    """A marca da empresa do schema atual, do cache por schema. Registrada em `comum.empresa`:
    `contas`, `notificacoes` e `contratos` leem o nome por ela, sem importar `empresas`."""
    dados = cache.get(chave_da_marca())
    if dados is None:
        dados = _montar_marca()
        cache.set(chave_da_marca(), dados, PRAZO_DA_MARCA)
    return dict(dados)
