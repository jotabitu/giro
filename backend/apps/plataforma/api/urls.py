"""Rotas da plataforma. `urls_plataforma` no host admin (public); `urls_empresa` no da empresa."""

from django.urls import URLPattern, path

from .views import AssinaturaView, EmpresaDetalheView, EmpresasView, PlanosView

urls_plataforma: list[URLPattern] = [
    path("planos/", PlanosView.as_view(), name="plataforma-planos"),
    path("empresas/", EmpresasView.as_view(), name="plataforma-empresas"),
    path("empresas/<int:pk>/", EmpresaDetalheView.as_view(), name="plataforma-empresa"),
]

urls_empresa: list[URLPattern] = [
    path("assinatura/", AssinaturaView.as_view(), name="assinatura"),
]
