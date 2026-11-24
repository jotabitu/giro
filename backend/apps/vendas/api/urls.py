"""Rotas das vendas, no host da empresa (`docs/api/vendas.md`)."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("vendas/", views.VendasView.as_view(), name="vendas"),
    path("vendas/simular/", views.SimularView.as_view(), name="vendas-simular"),
    path("vendas/<int:pk>/", views.VendaView.as_view(), name="venda"),
    path("vendas/<int:pk>/enviar/", views.EnviarView.as_view(), name="venda-enviar"),
    path("vendas/<int:pk>/resposta/", views.RespostaView.as_view(), name="venda-resposta"),
    path(
        "vendas/<int:pk>/pedir-aprovacao/",
        views.PedirAprovacaoView.as_view(),
        name="venda-pedir-aprovacao",
    ),
    path("vendas/<int:pk>/perder/", views.PerderView.as_view(), name="venda-perder"),
    path(
        "locacoes/<int:pk>/transferencia/",
        views.TransferenciaView.as_view(),
        name="locacao-transferencia",
    ),
]
