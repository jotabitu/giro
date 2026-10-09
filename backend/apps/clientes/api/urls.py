"""Rotas de clientes, no host da empresa."""

from django.urls import URLPattern, path

from . import views

ACOES = {
    "bloquear": views.BloquearView,
    "desbloquear": views.DesbloquearView,
    "inativar": views.InativarView,
    "reativar": views.ReativarView,
    "documentos": views.DocumentosView,
    "analise": views.AnaliseView,
}

urlpatterns: list[URLPattern] = [
    path("clientes/", views.ClientesView.as_view(), name="clientes"),
    path("clientes/analisar/", views.AnalisarView.as_view(), name="clientes-analisar"),
    path("clientes/<int:pk>/", views.ClienteView.as_view(), name="cliente"),
    *[
        path(f"clientes/<int:pk>/{acao}/", view.as_view(), name=f"cliente-{acao}")
        for acao, view in ACOES.items()
    ],
]
