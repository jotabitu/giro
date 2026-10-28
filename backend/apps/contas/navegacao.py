"""Navegação do `eu` (USR-05, USR-08; contrato de contas, "Menu e início", T-047).

A API monta o menu pronto; o frontend só liga cada `chave` à rota e ao ícone. Um item só vem
quando valem, ao mesmo tempo: a permissão da pessoa (`pode`), o recurso do plano
(`Plano.recursos`), a atividade da empresa (aluga, vende ou os dois) e o módulo entregue
(`settings.GIRO_MODULOS_ATIVOS`). Item sem permissão não vem; nunca vem desabilitado.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.plataforma.models import Recurso
from comum import empresa as empresa_config
from comum import leituras

from .models import Perfil

ALVO_USUARIO = "contas.Usuario"
# Sem empresa (testes da navegação), os dois; na empresa, `ConfiguracaoEmpresa.atividade`.
ATIVIDADE_PADRAO = "ambos"

Pode = dict[str, Any]


@dataclass(frozen=True)
class Item:
    chave: str
    rotulo: str
    contador: str | None = None
    permissao: Callable[[Pode], bool] = lambda pode: True
    recurso: str | None = None
    atividade: str | None = None  # "aluga" ou "vende"
    modulo: str | None = None  # app que precisa estar em GIRO_MODULOS_ATIVOS
    # Também para quem leva uma movimentação aberta (`pode.movimentacoes = levar`, MOV-02).
    ou_se_leva: bool = False


@dataclass(frozen=True)
class Contexto:
    pode: Pode
    recursos: frozenset[str]
    atividade: str
    modulos: frozenset[str]
    levando: int = 0  # movimentações abertas que a pessoa leva (MOV-02)


def decide_pedidos(pode: Pode) -> bool:
    """Gerente, administrador ou permissão extra de aprovar (APR, USR-03)."""
    return pode["desconto_acima_limite"] in ("aprova", "sim") or pode["locacoes_cancelar"] in (
        "aprova",
        "sim",
    )


def _ve_painel(pode: Pode) -> bool:
    return pode["painel"] in ("todas_filiais", "filial")


# Os itens, uma vez só; os menus escolhem quais usam e podem trocar o rótulo.
ITENS: dict[str, Item] = {
    item.chave: item
    for item in [
        # USR-05: todos menos o vistoriador, que não vê painel; o rótulo é o do início do perfil.
        Item("inicio", "Visão geral", None, lambda p: p["painel"] != "nao"),
        Item("aprovacoes", "Aprovações", "aprovacoes", decide_pedidos, modulo="aprovacoes"),
        Item(
            "veiculos",
            "Veículos",
            "veiculos",
            lambda p: p["veiculos"] != "nao",
            None,
            None,
            "veiculos",
        ),
        Item(
            "locacoes",
            "Locações",
            "locacoes",
            # O vistoriador não lista locações: chega à vistoria pela agenda (USR-05, VIS-05).
            lambda p: bool(p["locacoes_criar"]),
            Recurso.LOCACOES_VISTORIA,
            "aluga",
            "locacoes",
        ),
        Item(
            "vendas",
            "Vendas",
            None,
            lambda p: bool(p["vendas_criar"]),
            Recurso.VENDAS_COMISSOES,
            "vende",
            "vendas",
        ),
        Item(
            "clientes",
            "Clientes",
            None,
            lambda p: bool(p["clientes_cadastrar"] or p["caixa_receber"]),
            modulo="clientes",
        ),
        Item(
            "manutencoes",
            "Manutenções",
            "manutencoes",
            lambda p: bool(p["os_abrir"]),
            Recurso.MANUTENCAO_DESPESAS,
            modulo="manutencao",
        ),
        Item(
            "movimentacoes",
            "Movimentações",
            "movimentacoes",
            lambda p: p["movimentacoes"] == "gerir",
            modulo="movimentacoes",
            ou_se_leva=True,
        ),
        Item(
            "caixa",
            "Caixa do dia",
            None,
            lambda p: bool(p["caixa_receber"] or p["caixa_abrir_fechar"]),
            Recurso.CONTAS_RECEBER,
            modulo="financeiro",
        ),
        Item(
            "receber",
            "Contas a receber",
            "receber",
            lambda p: bool(p["caixa_receber"]),
            Recurso.CONTAS_RECEBER,
            modulo="financeiro",
        ),
        Item(
            "despesas",
            "Despesas",
            "despesas",
            lambda p: p["despesas_lancar"] != "nao",
            Recurso.MANUTENCAO_DESPESAS,
            modulo="financeiro",
        ),
        Item(
            "reembolsos",
            "Reembolsos",
            "reembolsos",
            # Administrador, gerente e financeiro: os perfis de `reembolsos/` (T-358, DEV-02).
            lambda p: bool(p["lancamento_avulso"]),
            Recurso.LOCACOES_VISTORIA,
            "aluga",
            "financeiro",
        ),
        Item(
            "pendencias_pagamento",
            "Pendências do pagamento",
            "pendencias_pagamento",
            lambda p: bool(p["financeiro_pagar"]),  # administrador e financeiro (T-358, AUT-05)
            Recurso.RECEBIMENTO_PARCEIRO,  # PLT-12
            modulo="financeiro",
        ),
        Item(
            "comissoes",
            "Comissões",
            None,
            lambda p: bool(p["financeiro_pagar"]),
            Recurso.VENDAS_COMISSOES,
            modulo="vendas",
        ),
        Item(
            "conciliacao",
            "Conciliação",
            "conciliacao",
            lambda p: bool(p["financeiro_pagar"]),
            Recurso.CONCILIACAO,
            modulo="conciliacao",  # fase 2 (FIN-11, FIN-12): fica fora com o financeiro ligado
        ),
        Item("relatorios", "Relatórios", None, _ve_painel, Recurso.RELATORIOS, None, "relatorios"),
        Item(
            "config",
            "Configurações",
            None,
            lambda p: bool(p["administracao"]),
            modulo="configuracoes",  # chave própria: "marca" fica em "empresas" (T-181)
        ),
        Item(
            "marca", "Empresa e marca", None, lambda p: bool(p["administracao"]), modulo="empresas"
        ),
        Item("filiais", "Filiais", None, lambda p: bool(p["administracao"]), modulo="filiais"),
        Item(
            "usuarios", "Usuários", "usuarios", lambda p: bool(p["administracao"]), modulo="contas"
        ),
        Item(
            "assinatura",
            "Assinatura",
            None,
            lambda p: bool(p["administracao"]),
            modulo="plataforma",
        ),
        Item(
            "auditoria", "Auditoria", None, lambda p: bool(p["administracao"]), modulo="auditoria"
        ),
        # Itens próprios das telas iniciais.
        Item(
            "agenda",
            "Vistorias de hoje",
            "agenda",
            lambda p: bool(p["vistorias_fazer"]),
            Recurso.LOCACOES_VISTORIA,
            "aluga",
            "vistorias",
        ),
        Item(
            "consultar_veiculo",
            "Consultar veículo",
            None,
            lambda p: p["veiculos"] != "nao",
            modulo="veiculos",
        ),
        Item(
            "avarias",
            "Avarias abertas",
            "avarias",
            lambda p: bool(p["vistorias_fazer"]),
            Recurso.LOCACOES_VISTORIA,
            "aluga",
            "vistorias",
        ),
        Item(
            "propostas",
            "Propostas",
            "propostas",
            lambda p: bool(p["vendas_criar"]),
            Recurso.VENDAS_COMISSOES,
            "vende",
            "vendas",
        ),
        Item(
            "minhas_vendas",
            "Minhas vendas",
            None,
            lambda p: bool(p["vendas_criar"]),
            Recurso.VENDAS_COMISSOES,
            "vende",
            "vendas",
        ),
        Item(
            "veiculos_a_venda",
            "Veículos à venda",
            None,
            lambda p: bool(p["vendas_criar"]),
            Recurso.VENDAS_COMISSOES,
            "vende",
            "vendas",
        ),
        Item(
            "minhas_comissoes",
            "Minhas comissões",
            None,
            lambda p: bool(p["vendas_criar"]),
            Recurso.VENDAS_COMISSOES,
            "vende",
            "vendas",
        ),
        Item(
            "contas_a_pagar",
            "Contas a pagar",
            "contas_a_pagar",
            lambda p: bool(p["financeiro_pagar"]),
            Recurso.MANUTENCAO_DESPESAS,
            modulo="financeiro",
        ),
        Item(
            "caixa_e_bancos",
            "Caixa e bancos",
            None,
            lambda p: bool(p["caixa_abrir_fechar"]),
            Recurso.CONTAS_RECEBER,
            modulo="financeiro",
        ),
    ]
}

Grupos = list[tuple[str | None, list[str | tuple[str, str]]]]

# Tabela "Itens do menu_completo" do contrato, na ordem.
MENU_COMPLETO: Grupos = [
    (None, ["inicio", "aprovacoes", "veiculos"]),
    ("Operação", ["locacoes", "vendas", "clientes", "manutencoes", "movimentacoes"]),
    (
        "Financeiro",
        [
            "caixa",
            "receber",
            "despesas",
            "reembolsos",
            "pendencias_pagamento",
            "comissoes",
            "conciliacao",
            "relatorios",
        ],
    ),
    ("Administração", ["config", "marca", "filiais", "usuarios", "assinatura", "auditoria"]),
]

# Menu da tela inicial de cada variante (telas Gerente, Vendedor, Vistoriador e Financeiro).
# Um par (chave, rótulo) troca o rótulo do item naquela tela.
MENU_INICIO: dict[str, Grupos] = {
    "gerente": [
        (None, [("inicio", "Visão da filial"), "aprovacoes", "veiculos"]),
        ("Operação", ["locacoes", "vendas", "clientes", "manutencoes", "movimentacoes"]),
        ("Filial", [("caixa", "Caixa da filial"), "relatorios"]),
    ],
    "vendedor": [
        (None, [("inicio", "Início")]),
        ("Operação", ["locacoes", "veiculos", "clientes", "movimentacoes"]),
        ("Vendas", ["propostas", "minhas_vendas", "veiculos_a_venda", "minhas_comissoes"]),
    ],
    "vistoriador": [(None, ["agenda", "consultar_veiculo", "avarias", "movimentacoes"])],
    "financeiro": [
        (
            None,
            [
                ("inicio", "Início"),
                "receber",
                "contas_a_pagar",
                "caixa_e_bancos",
                "veiculos",
                "comissoes",
            ],
        ),
    ],
}

VARIANTE_DO_PERFIL: dict[str, str] = {
    Perfil.GERENTE: "gerente",
    Perfil.VENDEDOR: "vendedor",
    Perfil.VISTORIADOR: "vistoriador",
    Perfil.FINANCEIRO: "financeiro",
}

# O rótulo do item `inicio` no menu completo é o do início do perfil (USR-05).
ROTULO_DO_INICIO: dict[str, str] = {
    "gerente": "Visão da filial",
    "vendedor": "Início",
    "financeiro": "Início",
}

BARRA_CELULAR = ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]


def modulos_ativos() -> frozenset[str]:
    """`GIRO_MODULOS_ATIVOS`: o menu e os cartões de Configurações seguem a mesma lista."""
    return frozenset(settings.GIRO_MODULOS_ATIVOS)


def _aparece(item: Item, ctx: Contexto) -> bool:
    if item.modulo is not None and item.modulo not in ctx.modulos:
        return False
    if item.recurso is not None and item.recurso not in ctx.recursos:
        return False
    if item.atividade is not None and ctx.atividade not in (item.atividade, "ambos"):
        return False
    if item.ou_se_leva and ctx.pode.get("movimentacoes") == "levar" and ctx.levando > 0:
        return True
    return item.permissao(ctx.pode)


def _contador(item: Item, ctx: Contexto) -> str | None:
    # Despesas: o número é do que a pessoa pode aprovar; quem não aprova fica sem contador.
    if item.chave == "despesas" and not ctx.pode["despesas_aprovar"]:
        return None
    return item.contador


def _com_rotulo_do_inicio(grupos: Grupos, qual: str) -> Grupos:
    rotulo = ROTULO_DO_INICIO.get(qual)
    if rotulo is None:
        return grupos
    return [
        (grupo, [("inicio", rotulo) if entrada == "inicio" else entrada for entrada in chaves])
        for grupo, chaves in grupos
    ]


def _montar(grupos: Grupos, ctx: Contexto) -> list[dict[str, Any]]:
    menu = []
    for grupo, chaves in grupos:
        itens = []
        for entrada in chaves:
            chave, rotulo = entrada if isinstance(entrada, tuple) else (entrada, None)
            item = ITENS[chave]
            if _aparece(item, ctx):
                itens.append(
                    {
                        "chave": item.chave,
                        "rotulo": rotulo or item.rotulo,
                        "contador": _contador(item, ctx),
                    }
                )
        if itens:
            menu.append({"grupo": grupo, "itens": itens})
    return menu


def variante(perfil: str, implantacao_concluida: bool) -> str:
    """USR-08. O administrador (e o suporte) vê a implantação até a 1ª locação ou venda
    (IMP-01)."""
    if perfil == Perfil.ADMINISTRADOR:
        return "geral" if implantacao_concluida else "implantacao"
    return VARIANTE_DO_PERFIL.get(perfil, "geral")


def montar(
    *,
    perfil: str,
    pode: Pode,
    recursos: list[str] | frozenset[str],
    implantacao_concluida: bool,
    atividade: str = ATIVIDADE_PADRAO,
    modulos: list[str] | frozenset[str] | None = None,
    levando: int = 0,
) -> dict[str, Any]:
    ctx = Contexto(
        pode=pode,
        recursos=frozenset(recursos),
        atividade=atividade,
        modulos=frozenset(settings.GIRO_MODULOS_ATIVOS if modulos is None else modulos),
        levando=levando,
    )
    qual = variante(perfil, implantacao_concluida)
    menu_inicio = _montar(MENU_INICIO[qual], ctx) if qual in MENU_INICIO else None
    # USR-05: o vistoriador tem um menu só; o completo dele é o do início.
    if qual == "vistoriador" and menu_inicio is not None:
        completo = menu_inicio
    else:
        completo = _montar(_com_rotulo_do_inicio(MENU_COMPLETO, qual), ctx)
    visiveis = {item["chave"] for grupo in completo for item in grupo["itens"]}
    barra = {
        "inicio": True,
        "veiculos": bool(visiveis & {"veiculos", "consultar_veiculo"}),
        "nova_locacao": "locacoes" in visiveis and bool(pode["locacoes_criar"]),
        "locacoes": "locacoes" in visiveis,
        "mais": True,
    }
    return {
        "inicio": {"rota": "/inicio", "variante": qual},
        "menu_inicio": completo if menu_inicio is None else menu_inicio,
        "menu_completo": completo,
        "barra_celular": [chave for chave in BARRA_CELULAR if barra[chave]],
    }


def levando(usuario: Any) -> int:
    """Movimentações abertas que a pessoa leva, pelo contador que o app `movimentacoes`
    registra (ADR 0015); 0 sem o app."""
    pk = getattr(usuario, "pk", None)
    if pk is None:
        return 0
    return leituras.contar(ALVO_USUARIO, pk, ["movimentacoes_levando"])["movimentacoes_levando"]


def da_empresa(empresa: Any, perfil: str, pode: Pode, *, levando: int = 0) -> dict[str, Any]:
    """A navegação de quem está na empresa: recursos do plano e a implantação (IMP-01)."""
    from apps.plataforma.models import UsoEmpresa
    from apps.plataforma.selectors import recursos_para

    plano = getattr(empresa, "plano", None)
    atividade = empresa_config.atividade()  # PLT-12: o ramo guardado
    passos = (
        UsoEmpresa.objects.filter(empresa=empresa)
        .values_list("passos_implantacao", flat=True)
        .first()
    ) or {}
    return montar(
        perfil=perfil,
        pode=pode,
        recursos=recursos_para(plano, atividade),  # `recursos_da_empresa` (ADR 0024, item 3)
        implantacao_concluida="primeira_locacao" in passos,
        atividade=atividade,
        levando=levando,
    )
