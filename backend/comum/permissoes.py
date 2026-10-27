"""Permissões do DRF comuns a todos os apps.

Perfis e permissões extras são valores fechados de `contas.Usuario` (USR-03); aqui eles chegam
como texto para que `comum` não dependa de `contas` (ADR 0011). O escopo por filial (USR-07)
vem do app `filiais`, que registra `filiais_do_usuario` no `ready()`; `EscopoDeFilial` confere o
cabeçalho `X-Filial` em toda requisição da empresa.
"""

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from django_tenants.utils import get_public_schema_name
from rest_framework.permissions import SAFE_METHODS, BasePermission

from comum import empresa as empresa_config
from comum.empresa import STATUS_OPERANDO, STATUS_PAUSADA, STATUS_SO_LEITURA
from comum.erros import Conflito, EmpresaSemOperacao, SemPermissao

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


def _vale_para_o_metodo(valor: bool | frozenset[str], metodo: str | None) -> bool:
    return valor is True or (isinstance(valor, frozenset) and metodo in valor)


def recurso_da_view(view: "APIView", request: "Request") -> str | None:
    """O recurso do plano que a view pede (ADR 0024, item 4): `recurso_por_acao[acao ou método]`,
    senão `recurso_do_plano`. Sem nenhum dos dois, é do núcleo."""
    por_acao = getattr(view, "recurso_por_acao", None) or {}
    acao = getattr(view, "action", None) or request.method
    if acao in por_acao:
        return str(por_acao[acao]) if por_acao[acao] else None
    recurso = getattr(view, "recurso_do_plano", None)
    return str(recurso) if recurso else None


class ModuloDoPlano(BasePermission):
    """403 `PLT-12` na rota do módulo que o plano ou o ramo não ligam, em leitura e escrita, para
    qualquer perfil e para o suporte (`plataforma.md`, "Módulos por plano"). Vem antes de perfil e
    filial; o `public` não passa por ela."""

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        recurso = recurso_da_view(view, request)
        if recurso is None or empresa_config.tem_recurso(recurso):
            return True
        raise empresa_config.recusa_do_recurso(recurso)


class EmpresaOperando(BasePermission):
    """Recusa escrita quando a empresa está suspensa, pausada ou cancelada (403).

    A `suspensa` e a `pausada` têm saída, declarada na view (`PLT-13`, `PLT-06`, tabela de
    estados; T-189, T-195), numa lista explícita com teste:
    - `escreve_na_suspensa = frozenset({"PATCH"})` (ou `True`): a `suspensa` escreve, para pagar
      e voltar a `ativa`, ou para cancelar.
    - `escreve_na_pausada = frozenset({"DELETE"})`: a `pausada` escreve, para voltar da pausa ou
      cancelar. A `cancelada` nem chega aqui (`EmpresaCanceladaMiddleware`).
    - `recusa_na_suspensa = (codigo, mensagem)`, ou `{metodo: (codigo, mensagem)}`: a `suspensa`
      segue recusada, com o 409 da regra no lugar do 403 (`PLT-04`: "Pague a fatura em atraso
      antes de mudar de plano.").
    """

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        if request.method in SAFE_METHODS:
            return True
        empresa = getattr(request, "tenant", None)
        if empresa is None or empresa.schema_name == get_public_schema_name():
            return True
        status = getattr(empresa, "status", None)
        if status in STATUS_OPERANDO:
            return True
        if status in STATUS_SO_LEITURA:
            if _vale_para_o_metodo(getattr(view, "escreve_na_suspensa", False), request.method):
                return True
            recusa = getattr(view, "recusa_na_suspensa", None)
            if isinstance(recusa, Mapping):
                recusa = recusa.get(request.method)
            if recusa is not None:
                raise Conflito(*recusa)
        if status == STATUS_PAUSADA and _vale_para_o_metodo(
            getattr(view, "escreve_na_pausada", False), request.method
        ):
            return True
        raise EmpresaSemOperacao(str(status))


def com_padrao(*extras: type[BasePermission]) -> list[type[BasePermission]]:
    """As permissões padrão da API mais as da view, nunca no lugar delas (F-01 da T-064).

    `permission_classes = com_padrao(exige_perfil("administrador"))`. Declarar a lista à mão
    derruba `EmpresaOperando` e `EscopoDeFilial`; `tests/test_permissoes_das_rotas.py` confere.
    """
    from rest_framework.settings import api_settings  # lido na hora: as settings importam daqui

    padrao = cast(list[type[BasePermission]], list(api_settings.DEFAULT_PERMISSION_CLASSES))
    return [*padrao, *extras]


def exige_perfil(*perfis: str) -> type[BasePermission]:
    """`permission_classes = com_padrao(exige_perfil("administrador", "gerente"))`."""

    class PerfilPermitido(BasePermission):
        message = "Seu perfil não tem acesso a esta ação."

        def has_permission(self, request: "Request", view: "APIView") -> bool:
            usuario: Any = request.user
            return bool(usuario and getattr(usuario, "perfil", None) in perfis)

    PerfilPermitido.__name__ = f"Perfil_{'_'.join(perfis)}"
    return PerfilPermitido


# --- Escopo de filial (USR-07) ---

CABECALHO_FILIAL = "HTTP_X_FILIAL"
TODAS_AS_FILIAIS = "todas"
# USR-07: administrador e financeiro veem todas as filiais ativas e escolhem "Todas as filiais".
PERFIS_QUE_VEEM_TODAS = frozenset({"administrador", "financeiro"})
# USR-03: com esta extra, "Todas as filiais" vale só nas views de painel e relatórios.
EXTRA_RELATORIOS_TODAS = "relatorios_todas_filiais"

_filiais_do_usuario: Callable[[Any], set[int]] | None = None


def registrar_escopo_de_filial(funcao: Callable[[Any], set[int]]) -> None:
    """Chamado pelo `ready()` do app `filiais`: ids das filiais ativas da pessoa."""
    global _filiais_do_usuario
    _filiais_do_usuario = funcao


def filiais_permitidas(usuario: Any) -> set[int]:
    return _filiais_do_usuario(usuario) if _filiais_do_usuario is not None else set()


_resumo_das_filiais: Callable[[Any], list[dict[str, Any]]] | None = None


def registrar_resumo_de_filiais(funcao: Callable[[Any], list[dict[str, Any]]]) -> None:
    """Chamado pelo `ready()` do app `filiais`: `[{id, nome}]` das filiais ativas da pessoa."""
    global _resumo_das_filiais
    _resumo_das_filiais = funcao


def resumo_das_filiais(usuario: Any) -> list[dict[str, Any]]:
    return _resumo_das_filiais(usuario) if _resumo_das_filiais is not None else []


# --- Permissões calculadas (USR-03, USR-05) ---

_pode: Callable[[Any, str], Any] | None = None


def registrar_pode(funcao: Callable[[Any, str], Any]) -> None:
    """Chamado pelo `ready()` do app `contas` com `contas.selectors.pode`."""
    global _pode
    _pode = funcao


def pode(usuario: Any, chave: str) -> Any:
    """O valor de `eu.pode[chave]` da pessoa (`False` sem a função registrada)."""
    return _pode(usuario, chave) if _pode is not None else False


def pode_escolher_todas(usuario: Any) -> bool:
    """Administrador e financeiro, em qualquer endpoint (USR-07)."""
    return getattr(usuario, "perfil", "") in PERFIS_QUE_VEEM_TODAS


def escopo_de_relatorio(view: Any) -> bool:
    """View de painel ou relatório: declara `escopo_de_relatorio = True`."""
    return bool(getattr(view, "escopo_de_relatorio", False))


def pode_todas_nesta_view(usuario: Any, view: Any) -> bool:
    """`X-Filial: todas`: o perfil, ou a extra `relatorios_todas_filiais` só em painel e
    relatórios (USR-03); nos demais endpoints quem tem só a extra recebe 403 `USR-07`."""
    if pode_escolher_todas(usuario):
        return True
    extras = getattr(usuario, "permissoes_extras", None) or []
    return EXTRA_RELATORIOS_TODAS in extras and escopo_de_relatorio(view)


def sem_acesso_a_filial() -> SemPermissao:
    return SemPermissao("USR-07", "Você não tem acesso a esta filial")


def filial_pedida(request: "Request") -> int | str | None:
    """O `X-Filial` conferido: id, `"todas"` ou `None` (sem cabeçalho).

    Filial fora do escopo da pessoa: 403 `USR-07`.
    """
    valor = str(request.META.get(CABECALHO_FILIAL, "")).strip()
    if not valor:
        return None
    usuario = request.user
    if valor == TODAS_AS_FILIAIS:
        view = (getattr(request, "parser_context", None) or {}).get("view")
        if pode_todas_nesta_view(usuario, view):
            return TODAS_AS_FILIAIS
        raise sem_acesso_a_filial()
    if not valor.isdigit() or int(valor) not in filiais_permitidas(usuario):
        raise sem_acesso_a_filial()
    return int(valor)


class EscopoDeFilial(BasePermission):
    """Recusa `X-Filial` de filial fora do escopo da pessoa (403 `USR-07`)."""

    def has_permission(self, request: "Request", view: "APIView") -> bool:
        empresa = getattr(request, "tenant", None)
        if empresa is None or empresa.schema_name == get_public_schema_name():
            return True
        if not getattr(request.user, "is_authenticated", False):
            return True
        filial_pedida(request)
        return True
