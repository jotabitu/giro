"""Rotas da plataforma. `urls_plataforma` no host admin (public); `urls_empresa` no da empresa."""

from django.urls import URLPattern, path

from . import auditoria, suporte
from .views import AssinaturaView, EmpresaDetalheView, EmpresasView, PlanosView

urls_plataforma: list[URLPattern] = [
    path("planos/", PlanosView.as_view(), name="plataforma-planos"),
    path("empresas/", EmpresasView.as_view(), name="plataforma-empresas"),
    path("empresas/<int:pk>/", EmpresaDetalheView.as_view(), name="plataforma-empresa"),
    path(
        "empresas/<int:pk>/acessos-suporte/",
        suporte.AbrirAcessoSuporteView.as_view(),
        name="plataforma-empresa-acessos-suporte",
    ),
    path(
        "auditoria/eventos/",
        auditoria.EventosDaPlataformaView.as_view(),
        name="plataforma-auditoria-eventos",
    ),
    path(
        "auditoria/eventos/<int:pk>/",
        auditoria.EventoDaPlataformaView.as_view(),
        name="plataforma-auditoria-evento",
    ),
]

urls_empresa: list[URLPattern] = [
    path("assinatura/", AssinaturaView.as_view(), name="assinatura"),
    path("suporte/", suporte.SuporteView.as_view(), name="suporte"),
    path("suporte/bloquear/", suporte.BloquearSuporteView.as_view(), name="suporte-bloquear"),
    path("suporte/liberar/", suporte.LiberarSuporteView.as_view(), name="suporte-liberar"),
    path(
        "suporte/acessos/<int:pk>/revogar/",
        suporte.RevogarAcessoSuporteView.as_view(),
        name="suporte-acesso-revogar",
    ),
]
