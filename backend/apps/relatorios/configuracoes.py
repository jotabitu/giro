"""Textos da tela Configurações (`docs/api/configuracoes.md`; USR-05, PLT-03, PLT-07, IMP-01,
IMP-04, IMP-05).

Funções puras: recebem o que os selectors dos outros apps já contaram e devolvem os cartões e a
faixa da implantação prontos. A tela não conta nem monta texto (ADR 0005).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
CIDADES_NO_RESUMO = 3  # com 4 cidades ou mais, só a contagem

# Ordem fixa da tela. `integracoes` e `notificacoes` não vêm no MVP (sem tela nem contrato).
TITULOS = {
    "marca": "Empresa e marca",
    "filiais": "Filiais",
    "usuarios": "Usuários e perfis",
    "precos": "Tabelas de preço",
    "modelos_contrato": "Modelos de contrato",
    "assinatura": "Assinatura",
    "auditoria": "Auditoria",
    "exportar": "Exportar dados",
}
# Cartão → app que precisa estar em `GIRO_MODULOS_ATIVOS` (USR-05). Os que também são item do
# menu usam o app do item (`contas.navegacao.ITENS`), passado por quem chama.
MODULO_PROPRIO = {"precos": "veiculos", "modelos_contrato": "contratos", "exportar": "auditoria"}
SO_FORA_DO_SUPORTE = frozenset({"auditoria", "exportar"})  # PLT-07

FIXOS = {
    "marca": "Logo, cor, nome e endereço do sistema",
    "auditoria": "Quem fez o quê no sistema",
    # O MVP exporta só a auditoria (T-151); "Baixe tudo quando quiser" volta na fase 2.
    "exportar": "Baixe a auditoria em CSV",
}

# IMP-05: os nomes dos passos na frase "Faltam ...".
NOMES_DOS_PASSOS = {
    "conta": "conta e acesso",
    "marca": "empresa e marca",
    "filial": "primeira filial",
    "ramo": "o que a empresa faz",
    "precos": "tabela de preços",
    "contrato": "contrato",
    "recebimentos": "recebimentos",
    "importar": "importar dados",
    "equipe": "equipe",
    "primeira_locacao": "a 1ª locação",
}
ACAO_DA_PRIMEIRA_LOCACAO = {"rotulo": "Fazer uma locação de teste", "destino": "nova_locacao"}


def _plural(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def _juntar(itens: list[str]) -> str:
    """ "A", "A e B", "A, B e C"."""
    if len(itens) <= 1:
        return "".join(itens)
    return f"{', '.join(itens[:-1])} e {itens[-1]}"


def _dia_mes(dia: date) -> str:
    return f"{dia.day:02d} {MESES[dia.month - 1]}"


def resumo_filiais(ativas: int, cidades: list[str], unica: dict[str, Any] | None) -> str:
    if unica is not None:
        return f"1 filial · {unica['nome']}, {unica['cidade']}"
    if ativas == 0:
        return "Nenhuma filial ativa"
    if len(cidades) > CIDADES_NO_RESUMO:
        return f"{ativas} filiais em {len(cidades)} cidades"
    return f"{ativas} filiais · {_juntar(cidades)}"


def resumo_usuarios(usado: int, limite: int | None, convites: int) -> str:
    """PLT-03: o convite pendente já conta no `usado`."""
    texto = f"{usado} de {limite} usuários" if limite is not None else f"{usado} usuários"
    if convites:
        texto += f" · {_plural(convites, 'convite', 'convites')}"
    return texto


def resumo_precos(categorias: int, planos_especiais: int | None) -> str:
    """`planos_especiais` é `None` com `locacoes` fora de `GIRO_MODULOS_ATIVOS`."""
    if categorias == 0:
        return "Nenhuma categoria cadastrada"
    texto = _plural(categorias, "categoria", "categorias")
    if planos_especiais:
        texto += f" · {_plural(planos_especiais, 'plano especial', 'planos especiais')}"
    return texto


def resumo_modelos(modelos: int, rascunhos: int, tem_publicado_de_locacao: bool) -> str:
    """IMP-04: sem modelo de locação publicado, a 1ª locação trava; é o que o cartão diz."""
    if not tem_publicado_de_locacao:
        return "Nenhum modelo publicado"
    texto = _plural(modelos, "modelo", "modelos")
    if rascunhos:
        texto += f" · {_plural(rascunhos, 'rascunho', 'rascunhos')}"
    return texto


def resumo_assinatura(
    plano: str, status: str, ciclo: str, teste_fim: date | None, pausada_ate: date | None
) -> str:
    if status == "em_teste":
        situacao = f"teste até {_dia_mes(teste_fim)}" if teste_fim else "em teste"
    elif status == "ativa":
        situacao = ciclo  # "mensal" ou "anual"
    elif status == "inadimplente":
        situacao = "fatura em atraso"
    elif status == "pausada":
        situacao = f"pausada até {_dia_mes(pausada_ate)}" if pausada_ate else "pausada"
    else:  # suspensa, cancelada
        situacao = status
    return f"{plano} · {situacao}" if plano else situacao


def implantacao(passos: list[dict[str, Any]]) -> dict[str, Any] | None:
    """`passos` como em `plataforma.selectors.implantacao` (`passo`, `concluido_em`), na ordem.
    `None` depois da 1ª locação (IMP-01): a faixa some de vez."""
    feitos = {p["passo"] for p in passos if p["concluido_em"]}
    if "primeira_locacao" in feitos:
        return None
    abertos = [p["passo"] for p in passos if p["passo"] not in feitos]
    concluidos, total = len(feitos), len(passos)
    nomes = [NOMES_DOS_PASSOS.get(passo, passo) for passo in abertos]
    faltam = f"{'Falta' if len(nomes) == 1 else 'Faltam'} {_juntar(nomes)}."
    return {
        "concluidos": concluidos,
        "total": total,
        "titulo": f"Implantação concluída em {concluidos} de {total} passos",
        "faltam": faltam,
        # O assistente ainda não tem contrato: só a 1ª locação tem destino (painel.md).
        "acao": dict(ACAO_DA_PRIMEIRA_LOCACAO) if abertos == ["primeira_locacao"] else None,
    }


@dataclass(frozen=True)
class Fontes:
    """O que os selectors contaram. Um campo `None` é de cartão que não vem."""

    filiais: dict[str, Any] | None = None
    usuarios: tuple[int, int | None, int] | None = None  # usado, limite, convites
    precos: tuple[int, int | None] | None = None  # categorias, planos especiais
    modelos: dict[str, Any] | None = None
    assinatura: dict[str, Any] | None = None


def cartoes(visiveis: list[str], fontes: Fontes) -> list[dict[str, str]]:
    """Um cartão por chave de `visiveis` (já na ordem da tela e filtradas)."""
    resumos: dict[str, str] = dict(FIXOS)
    if fontes.filiais is not None:
        resumos["filiais"] = resumo_filiais(**fontes.filiais)
    if fontes.usuarios is not None:
        resumos["usuarios"] = resumo_usuarios(*fontes.usuarios)
    if fontes.precos is not None:
        resumos["precos"] = resumo_precos(*fontes.precos)
    if fontes.modelos is not None:
        resumos["modelos_contrato"] = resumo_modelos(**fontes.modelos)
    if fontes.assinatura is not None:
        resumos["assinatura"] = resumo_assinatura(**fontes.assinatura)
    return [
        {"chave": chave, "titulo": TITULOS[chave], "resumo": resumos[chave]}
        for chave in visiveis
        if chave in resumos
    ]


def visiveis(modulo_do_cartao: dict[str, str], modulos: frozenset[str], suporte: bool) -> list[str]:
    """USR-05: só cartão de app ativo; PLT-07: o suporte não vê auditoria nem exportar."""
    return [
        chave
        for chave in TITULOS
        if modulo_do_cartao[chave] in modulos and not (suporte and chave in SO_FORA_DO_SUPORTE)
    ]
