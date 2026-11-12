"""Rotas das vendas, no host da empresa (`docs/api/vendas.md`)."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("vendas/", views.VendasView.as_view(), name="vendas"),
    path("vendas/<int:pk>/", views.VendaView.as_view(), name="venda"),
    path(
        "locacoes/<int:pk>/transferencia/",
        views.TransferenciaView.as_view(),
        name="locacao-transferencia",
    ),
]
