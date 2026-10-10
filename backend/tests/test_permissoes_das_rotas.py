"""Toda view da empresa mantém as permissões padrão (F-01 da T-064).

Declarar `permission_classes` à mão derruba `EmpresaOperando` (empresa sem operação só lê) e
`EscopoDeFilial` (USR-07). Use `comum.permissoes.com_padrao(...)`. Exceção só com motivo.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from django.urls import URLPattern, URLResolver
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.views import APIView

from apps.contas.api.acesso import VIEWS_DE_ACESSO
from apps.contas.api.usuarios import VIEWS_DE_CONVITE
from apps.contratos.api.views import VIEWS_DE_ASSINATURA
from comum.permissoes import EmpresaOperando, EscopoDeFilial
from config import urls

# Documentação da API: aberta por EXPOR_DOCUMENTACAO_DA_API e fechada em produção (S-17).
# Acesso à conta (entrar, 2 etapas, renovar, sair, eu, sessões e senha, T-011): com a empresa
# suspensa as pessoas entram para ler e exportar, e cuidar da própria conta não é operação. O
# convite (consultar e aceitar, T-069) também: é criar o próprio acesso. O link de assinatura
# de contrato (S-15, T-090) é do cliente final, sem login nem filial; mantém `EmpresaOperando`.
EXCECOES: set[type[APIView]] = {
    SpectacularAPIView,
    SpectacularSwaggerView,
    *VIEWS_DE_ACESSO,
    *VIEWS_DE_CONVITE,
    *VIEWS_DE_ASSINATURA,
}
METODOS = ("get", "post", "put", "patch", "delete")


def _views(padroes: list[Any], prefixo: str = "") -> list[tuple[str, type[APIView]]]:
    achadas: list[tuple[str, type[APIView]]] = []
    for padrao in padroes:
        if isinstance(padrao, URLResolver):
            achadas += _views(padrao.url_patterns, prefixo + str(padrao.pattern))
        elif isinstance(padrao, URLPattern):
            classe = getattr(padrao.callback, "view_class", None) or getattr(
                padrao.callback, "cls", None
            )
            if classe is not None and issubclass(classe, APIView):
                achadas.append((prefixo + str(padrao.pattern), classe))
    return achadas


def test_toda_view_da_empresa_tem_as_permissoes_padrao():
    views = _views(urls.urlpatterns)
    assert len(views) > 10  # o urlconf foi mesmo percorrido
    faltando = []
    for rota, classe in views:
        if classe in EXCECOES:
            continue
        for metodo in METODOS:
            if not hasattr(classe, metodo):
                continue
            view = classe()
            view.request = SimpleNamespace(method=metodo.upper())  # type: ignore[assignment]
            tipos = {type(permissao) for permissao in view.get_permissions()}
            for exigida in (EmpresaOperando, EscopoDeFilial):
                if exigida not in tipos:
                    faltando.append(f"{metodo.upper()} {rota}: sem {exigida.__name__}")
    assert faltando == []


def test_outros_apps_filtram_filial_so_por_filtrar_por_filial():
    """Ninguém lê `filial_da_requisicao` e filtra por conta própria (F-02 da T-064)."""
    raiz = Path(__file__).resolve().parent.parent / "apps"
    usam = [
        str(arquivo.relative_to(raiz))
        for arquivo in raiz.rglob("*.py")
        if arquivo.parts[len(raiz.parts)] != "filiais"
        and "filial_da_requisicao" in arquivo.read_text(encoding="utf-8")
    ]
    assert usam == []
