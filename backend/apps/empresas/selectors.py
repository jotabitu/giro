"""Leituras da configuração da empresa, da marca e do ramo (`docs/api/empresas.md`)."""

import hashlib
from decimal import Decimal
from typing import Any

from django.core.cache import cache

from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma.models import Recurso
from apps.plataforma.selectors import empresa_atual
from comum.conexao import schema_atual

from . import marca as cores_da_marca
from .models import Atividade, ConfiguracaoEmpresa, TrabalhaCom

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


# --- Ramo (PLT-12, ADR 0024, T-224) ---

DESCRICOES_DAS_ATIVIDADES = {
    "aluga": ("Locação", "Aluguel por dia, semana ou mês"),
    "vende": ("Venda de veículos", "Novos, seminovos e consignados"),
}
TIPOS = (("motos", "Motos"), ("carros", "Carros"))
# Não aparece em "Módulos que vamos ligar": só catálogo e fila do suporte (ADR 0024, item 1).
FORA_DOS_MODULOS = frozenset({Recurso.SUPORTE_PRIORITARIO})


def atividade() -> str:
    """Registrada em `comum.empresa` para `plataforma` e `contas` lerem o ramo (ADR 0024)."""
    valor = ConfiguracaoEmpresa.objects.values_list("atividade", flat=True).first()
    return str(valor or Atividade.AMBOS)


def resumo_do_ramo() -> str:
    """O cartão `ramo` de Configurações: "Locação e venda · motos" (`configuracoes.md`)."""
    guardado = configuracao()
    return f"{Atividade(guardado.atividade).label} · {TrabalhaCom(guardado.trabalha_com).label}"


def nomes_dos_modulos(recursos: frozenset[str]) -> list[str]:
    """Os `Recurso.label` ligados, na ordem do enum."""
    return [r.label for r in Recurso if r.value in recursos and r not in FORA_DOS_MODULOS]


def ramo() -> dict[str, Any]:
    """`GET /api/ramo/`: o ramo guardado e as opções que o plano atual aceita. Sem cache."""
    guardado = configuracao()
    plano = empresa_atual().plano
    aceitas = plataforma_selectors.atividades_aceitas(plano)
    aviso_de_venda = None
    if Recurso.VENDAS_COMISSOES not in (getattr(plano, "recursos", None) or []):
        com_vendas = plataforma_selectors.primeiro_plano_com(Recurso.VENDAS_COMISSOES)
        if com_vendas is not None:
            aviso_de_venda = f"Vendas faz parte do plano {com_vendas.nome}."
    return {
        "atividade": guardado.atividade,
        "trabalha_com": guardado.trabalha_com,
        "atividades": [
            {
                "valor": valor,
                "titulo": titulo,
                "descricao": descricao,
                "aviso": aviso_de_venda if valor == "vende" else None,
            }
            for valor, (titulo, descricao) in DESCRICOES_DAS_ATIVIDADES.items()
        ],
        "atividades_aceitas": list(aceitas),
        "tipos": [{"valor": valor, "titulo": titulo} for valor, titulo in TIPOS],
        "modulos": {
            a: nomes_dos_modulos(plataforma_selectors.recursos_para(plano, a)) for a in aceitas
        },
    }


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
