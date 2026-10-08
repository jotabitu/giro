"""Leituras de `contas`: permissões calculadas (`pode`, USR-03, USR-05) e o `eu`.

`pode` segue a tabela de perfis do contrato de contas mais as permissões extras, que só somam
(USR-03). O frontend monta menu e botões só com isso.
"""

from typing import Any

from comum import permissoes
from comum.empresa import STATUS_OPERANDO

from .models import Perfil, PermissaoExtra, StatusUsuario, Usuario

ADM, GER, VEN, VIS, FIN = (
    Perfil.ADMINISTRADOR,
    Perfil.GERENTE,
    Perfil.VENDEDOR,
    Perfil.VISTORIADOR,
    Perfil.FINANCEIRO,
)


def _so(*perfis: str) -> dict[str, bool]:
    return {perfil: perfil in perfis for perfil in Perfil.values}


# Contrato de contas, "Permissões calculadas (pode)".
TABELA_DO_PODE: dict[str, dict[str, Any]] = {
    "painel": {
        ADM: "todas_filiais",
        GER: "filial",
        VEN: "proprios",
        VIS: "nao",
        FIN: "todas_filiais",
    },
    "veiculos": {ADM: "editar", GER: "editar", VEN: "nao", VIS: "km_e_avarias", FIN: "nao"},
    "clientes_cadastrar": _so(ADM, GER, VEN),
    "locacoes_criar": _so(ADM, GER, VEN),
    "vistorias_fazer": _so(ADM, GER, VEN, VIS),
    "locacoes_cancelar": {ADM: "sim", GER: "aprova", VEN: "pede", VIS: "nao", FIN: "nao"},
    "desconto_acima_limite": {ADM: "sim", GER: "aprova", VEN: "pede", VIS: "nao", FIN: "nao"},
    "vendas_criar": _so(ADM, GER, VEN),
    "caixa_receber": _so(ADM, GER, VEN, FIN),
    "caixa_abrir_fechar": _so(ADM, GER, VEN, FIN),
    "despesas_lancar": {ADM: "todas", GER: "todas", VEN: "todas", VIS: "manutencao", FIN: "todas"},
    "despesas_aprovar": _so(ADM, GER),
    "financeiro_pagar": _so(ADM, FIN),
    "os_abrir": _so(ADM, GER, VIS),
    "administracao": _so(ADM),
}

# Ordem de cada escala, da menor para a maior: a extra só vale se aumentar.
ESCALAS = {
    "painel": ["nao", "proprios", "filial", "todas_filiais"],
    "locacoes_cancelar": ["nao", "pede", "aprova", "sim"],
    "desconto_acima_limite": ["nao", "pede", "aprova", "sim"],
}

# USR-03: o que cada permissão extra dá.
EFEITO_DAS_EXTRAS: dict[str, tuple[str, str]] = {
    PermissaoExtra.APROVAR_DESCONTO: ("desconto_acima_limite", "aprova"),
    PermissaoExtra.CANCELAR_CONTRATO: ("locacoes_cancelar", "aprova"),
    PermissaoExtra.RELATORIOS_TODAS_FILIAIS: ("painel", "todas_filiais"),
}


def _maior(chave: str, atual: Any, novo: Any) -> Any:
    escala = ESCALAS[chave]
    return novo if escala.index(novo) > escala.index(atual) else atual


def pode_do_perfil(perfil: str) -> dict[str, Any]:
    return {chave: valores.get(perfil, False) for chave, valores in TABELA_DO_PODE.items()}


def calcular_pode(perfil: str, extras: list[str]) -> dict[str, Any]:
    """Tabela do perfil mais as extras, que nunca reduzem (USR-03)."""
    resultado = pode_do_perfil(perfil)
    for extra in extras:
        if extra in EFEITO_DAS_EXTRAS:
            chave, valor = EFEITO_DAS_EXTRAS[extra]
            resultado[chave] = _maior(chave, resultado[chave], valor)
    return resultado


def extra_e_padrao_do_perfil(perfil: str, extra: str) -> bool:
    """O perfil já dá o que a extra daria (a tela mostra marcada e travada)."""
    chave, valor = EFEITO_DAS_EXTRAS[extra]
    return bool(
        pode_do_perfil(perfil)[chave] == _maior(chave, pode_do_perfil(perfil)[chave], valor)
    )


def pode(usuario: Any, chave: str) -> Any:
    """O mesmo cálculo de `eu.pode` (registrado em `comum.permissoes`)."""
    perfil = getattr(usuario, "perfil", "") or ""
    if not perfil:
        return False
    return calcular_pode(perfil, list(getattr(usuario, "permissoes_extras", []) or []))[chave]


def administradores() -> Any:
    """Destinatários dos avisos ao administrador (USR-06, PLT-03)."""
    return Usuario.objects.filter(perfil=Perfil.ADMINISTRADOR, status=StatusUsuario.ATIVO)


def dados_do_eu(usuario: Usuario, empresa: Any) -> dict[str, Any]:
    """`GET /api/auth/eu/` sem a navegação (T-071) e sem o modo suporte (T-070)."""
    from . import dois_fatores

    status_empresa = str(getattr(empresa, "status", ""))
    return {
        "id": usuario.pk,
        "nome": usuario.nome,
        "email": usuario.email,
        "celular": usuario.celular or None,
        "perfil": usuario.perfil,
        "permissoes_extras": list(usuario.permissoes_extras),
        "filiais": permissoes.resumo_das_filiais(usuario),
        "dois_fatores": {
            "ativo": dois_fatores.tem_2fa(usuario),
            "obrigatorio": usuario.exige_2fa_pela_regra,
            "codigos_recuperacao_restantes": dois_fatores.codigos_restantes(usuario),
        },
        "pode": calcular_pode(usuario.perfil, list(usuario.permissoes_extras)),
        "suporte": None,
        "empresa": {
            "nome_exibicao": getattr(empresa, "nome_exibicao", ""),
            "status": status_empresa,
            "somente_leitura": status_empresa not in STATUS_OPERANDO,
        },
    }
