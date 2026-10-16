"""Leituras de `contas`: permissões calculadas (`pode`, USR-03, USR-05) e o `eu`.

`pode` segue a tabela de perfis do contrato de contas mais as permissões extras, que só somam
(USR-03). O frontend monta menu e botões só com isso.
"""

import unicodedata
from typing import Any

from django.db.models import Count, Exists, Max, OuterRef, Q, Subquery

from comum import permissoes
from comum.empresa import STATUS_OPERANDO, nome_da_empresa

from . import navegacao
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
    # Vendedor e financeiro consultam a Frota e a ficha só para ler (USR-05, USR-09, T-287).
    "veiculos": {ADM: "editar", GER: "editar", VEN: "ver", VIS: "km_e_avarias", FIN: "ver"},
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
    "despesas_exportar": _so(ADM, FIN),  # FIN-16, AUD-07 (T-177)
    "financeiro_pagar": _so(ADM, FIN),
    # Lançamento avulso em contas a receber, cancelar, renegociar, estornar: linha da tabela de
    # perfis (T-232) e de `financeiro.md` ("Quem pode"). A extra `cancelar_contrato` não dá.
    "lancamento_avulso": _so(ADM, GER, FIN),
    "os_abrir": _so(ADM, GER, VIS),
    # MOV-02 (T-286): `levar` só registra as chegadas das movimentações que a pessoa leva.
    "movimentacoes": {ADM: "gerir", GER: "gerir", VEN: "levar", VIS: "levar", FIN: "nao"},
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


# --- Usuários (Administração; contrato de contas) ---

SITUACOES = {
    "ativos": StatusUsuario.ATIVO,
    "convites": StatusUsuario.CONVITE_PENDENTE,
    "desativados": StatusUsuario.DESATIVADO,
}


def usuarios(
    *,
    situacao: str | None = None,
    perfil: str | None = None,
    filial: str | None = None,
    busca: str | None = None,
) -> Any:
    """A lista de `GET /api/usuarios/`, com o que cada item precisa já anotado."""
    from .models import Autenticador, Convite

    convite_aberto = Convite.objects.filter(
        usuario=OuterRef("pk"), aceito_em__isnull=True
    ).order_by("-criado_em")
    qs = Usuario.objects.exclude(perfil="").annotate(
        ultimo_acesso_em=Max("sessoes__ultimo_uso"),
        convite_expira=Subquery(convite_aberto.values("expira_em")[:1]),
        dois_fatores=Exists(Autenticador.objects.filter(user=OuterRef("pk"), confirmed=True)),
    )
    if situacao in SITUACOES:
        qs = qs.filter(status=SITUACOES[situacao])
    if perfil in Perfil.values:
        qs = qs.filter(perfil=perfil)
    if filial and filial.isdigit():
        ligados = Usuario.objects.filter(
            filiais_ligadas__filial_id=int(filial), filiais_ligadas__ativo=True
        ).values("pk")
        qs = qs.filter(Q(perfil__in=permissoes.PERFIS_QUE_VEEM_TODAS) | Q(pk__in=ligados))
    if busca and busca.strip():
        termo = busca.strip()
        qs = qs.filter(Q(nome__icontains=termo) | Q(email__icontains=termo))
    return qs


def contagens_de_usuarios() -> dict[str, int]:
    filtros = {nome: Count("pk", filter=Q(status=status)) for nome, status in SITUACOES.items()}
    totais = Usuario.objects.exclude(perfil="").aggregate(todos=Count("pk"), **filtros)
    return {chave: int(valor) for chave, valor in totais.items()}


def convites_pendentes() -> int:
    """Convites ainda não aceitos: o contador `usuarios` do painel e o cartão de Configurações."""
    return int(
        Usuario.objects.exclude(perfil="").filter(status=StatusUsuario.CONVITE_PENDENTE).count()
    )


def item_de_usuario(usuario: Usuario, eu: Usuario) -> dict[str, Any]:
    """Um item da lista. `usuario` vem de `usuarios()`, com as anotações."""
    pendente = usuario.status == StatusUsuario.CONVITE_PENDENTE
    return {
        "id": usuario.pk,
        "nome": usuario.nome,
        "email": usuario.email,
        "celular": usuario.celular or None,
        "perfil": usuario.perfil,
        "filiais": permissoes.resumo_das_filiais(usuario),
        "todas_filiais": permissoes.pode_escolher_todas(usuario),
        "status": usuario.status,
        "dois_fatores_ativo": bool(getattr(usuario, "dois_fatores", False)),
        "ultimo_acesso_em": getattr(usuario, "ultimo_acesso_em", None),
        "convite_expira_em": getattr(usuario, "convite_expira", None) if pendente else None,
        "eu": usuario.pk == eu.pk,
        "acoes": acoes_do_convite(usuario, eu),
    }


def acoes_do_convite(usuario: Usuario, eu: Any) -> dict[str, bool]:
    """Os três botões do convite (USR-01, T-250): só com o convite pendente, vencido ou não, e
    para o administrador com token próprio; o suporte Giro não escreve em usuários (PLT-07)."""
    pode = (
        usuario.status == StatusUsuario.CONVITE_PENDENTE
        and getattr(eu, "perfil", "") == Perfil.ADMINISTRADOR
        and getattr(eu, "acesso_suporte_id", None) is None
    )
    return dict.fromkeys(("reenviar_convite", "copiar_link_convite", "cancelar_convite"), pode)


def detalhe_de_usuario(usuario: Usuario, eu: Usuario) -> dict[str, Any]:
    """O item mais as permissões extras (marcada e padrão do perfil) e quando entrou."""
    from .models import Convite

    usuario = usuarios().get(pk=usuario.pk)
    aceito = (
        Convite.objects.filter(usuario=usuario, aceito_em__isnull=False)
        .order_by("aceito_em")
        .values_list("aceito_em", flat=True)
        .first()
    )
    if aceito is None and usuario.status != StatusUsuario.CONVITE_PENDENTE:
        aceito = usuario.criado_em  # criado sem convite (seed, createsuperuser)
    return {
        **item_de_usuario(usuario, eu),
        "permissoes_extras": [
            {
                "chave": extra,
                "marcada": extra in usuario.permissoes_extras
                or extra_e_padrao_do_perfil(usuario.perfil, extra),
                "padrao_do_perfil": extra_e_padrao_do_perfil(usuario.perfil, extra),
            }
            for extra in PermissaoExtra.values
        ],
        "entrou_em": aceito,
    }


# --- Modo suporte (PLT-07; ADR 0013, item 2) ---

# No "só ver", o `pode` mantém só o que abre telas de leitura; o resto vem desligado.
CHAVES_DE_LEITURA = frozenset({"painel", "veiculos", "administracao"})


def pode_do_suporte(permissao: str) -> dict[str, Any]:
    """`pode` de administrador; com `ver`, só as chaves de leitura (contrato de contas)."""
    tudo = pode_do_perfil(Perfil.ADMINISTRADOR)
    if permissao != "ver":
        return tudo
    desligado = {
        chave: ("nao" if isinstance(valor, str) else False) for chave, valor in tudo.items()
    }
    return {**desligado, **{chave: tudo[chave] for chave in CHAVES_DE_LEITURA}}


def dados_do_eu_suporte(ator: Any, empresa: Any) -> dict[str, Any]:
    """`GET /api/auth/eu/` com o token de suporte: administrador em todas as filiais, com a
    faixa `suporte` preenchida."""
    status_empresa = str(getattr(empresa, "status", ""))
    return {
        "id": None,
        "nome": ator.nome,
        "email": None,
        "celular": None,
        "perfil": Perfil.ADMINISTRADOR,
        "permissoes_extras": [],
        "filiais": permissoes.resumo_das_filiais(ator),
        "dois_fatores": {"ativo": False, "obrigatorio": False, "codigos_recuperacao_restantes": 0},
        "pode": pode_do_suporte(ator.permissao),
        # USR-08: no modo suporte, a variante é a do administrador.
        "navegacao": navegacao.da_empresa(
            empresa, Perfil.ADMINISTRADOR, pode_do_suporte(ator.permissao)
        ),
        "suporte": {
            "acesso_suporte_id": ator.acesso_suporte_id,
            "nome": ator.nome,
            "permissao": ator.permissao,
            "fim": ator.fim,
            "motivo": ator.motivo,
        },
        "empresa": {
            "nome_exibicao": nome_da_empresa(),  # o mesmo de GET /api/marca/
            "status": status_empresa,
            "somente_leitura": status_empresa not in STATUS_OPERANDO,
        },
    }


def dados_do_eu(usuario: Usuario, empresa: Any) -> dict[str, Any]:
    """`GET /api/auth/eu/` com a navegação (USR-05, USR-08). O suporte usa outra função."""
    from . import dois_fatores

    status_empresa = str(getattr(empresa, "status", ""))
    pode = calcular_pode(usuario.perfil, list(usuario.permissoes_extras))
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
        "pode": pode,
        "navegacao": navegacao.da_empresa(
            empresa, usuario.perfil, pode, levando=navegacao.levando(usuario)
        ),
        "suporte": None,
        "empresa": {
            "nome_exibicao": nome_da_empresa(),  # o mesmo de GET /api/marca/
            "status": status_empresa,
            "somente_leitura": status_empresa not in STATUS_OPERANDO,
        },
    }


# --- Painel (`relatorios`, docs/api/painel.md) ---

STATUS_DO_CONVITE = {StatusUsuario.ATIVO: "aceito", StatusUsuario.CONVITE_PENDENTE: "pendente"}


def convites_enviados() -> list[dict[str, Any]]:
    """Quem foi convidado (aceitou ou não), na ordem do convite: a implantação (USR-08)."""
    return [
        {
            "nome": usuario.nome,
            "contato": usuario.email,
            "perfil": usuario.perfil,
            "status": STATUS_DO_CONVITE[StatusUsuario(usuario.status)],
        }
        for usuario in Usuario.objects.filter(
            convites__isnull=False, status__in=list(STATUS_DO_CONVITE)
        )
        .annotate(primeiro=Max("convites__criado_em"))
        .order_by("primeiro", "id")
    ]


def ativos_com_ultimo_uso(ids: set[int]) -> list[Usuario]:
    """Pessoas ativas entre `ids`, com `ultimo_uso` (a sessão usada por último, ou `None`)."""
    return list(
        Usuario.objects.filter(pk__in=ids, status=StatusUsuario.ATIVO)
        .annotate(ultimo_uso=Max("sessoes__ultimo_uso"))
        .order_by("nome", "id")
    )


def navegacao_de(usuario: Any, empresa: Any) -> dict[str, Any]:
    """A mesma navegação do `eu` (USR-05, USR-08): o painel tira dela a variante e as chaves
    dos contadores. O suporte tem a variante e o alcance do administrador."""
    if getattr(usuario, "e_suporte", False):
        return navegacao.da_empresa(
            empresa, Perfil.ADMINISTRADOR, pode_do_suporte(usuario.permissao)
        )
    pode = calcular_pode(usuario.perfil, list(usuario.permissoes_extras))
    return navegacao.da_empresa(empresa, usuario.perfil, pode, levando=navegacao.levando(usuario))


# --- Quem leva e quem recebe (movimentações, T-300) ---


def pessoas_da_filial(filial_id: int, excluir_perfis: tuple[str, ...] = ()) -> list[Usuario]:
    """Usuários ativos ligados à filial (o administrador em todas, USR-07), pelo nome: base das
    listas de quem leva e quem recebe e da validação de `levado_por_id` e `recebido_por_id`
    (MOV-02, MOV-06). O vínculo vem de `comum.permissoes` (ADR 0011)."""
    ativos = Usuario.objects.filter(status=StatusUsuario.ATIVO).exclude(perfil__in=excluir_perfis)
    ligados = [u for u in ativos if filial_id in permissoes.filiais_permitidas(u)]
    return sorted(ligados, key=lambda u: (_sem_acento(u.nome), u.pk))


def _sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).casefold()


def chaves_de_contador(nav: dict[str, Any]) -> set[str]:
    """As chaves `contador` dos itens que a navegação montou para a pessoa."""
    return {
        item["contador"]
        for menu in ("menu_inicio", "menu_completo")
        for grupo in nav[menu]
        for item in grupo["itens"]
        if item["contador"]
    }


def emails_de_usuarios(ids: set[int]) -> dict[int, str]:
    """Para a auditoria (login bloqueado de quem) e o aviso da exportação pronta (T-018)."""
    return dict(Usuario.objects.filter(pk__in=ids).values_list("pk", "email"))
