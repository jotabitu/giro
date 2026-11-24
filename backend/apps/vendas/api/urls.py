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
    # Fase 1b (VEN-15, VEN-17, VEN-19)
    path("vendas/<int:pk>/assinatura/", views.AssinaturaView.as_view(), name="venda-assinatura"),
    path(
        "vendas/<int:pk>/contrato/link/",
        views.LinkDoContratoView.as_view(),
        name="venda-contrato-link",
    ),
    path(
        "vendas/<int:pk>/contrato/reenviar/",
        views.ReenviarContratoView.as_view(),
        name="venda-contrato-reenviar",
    ),
    path(
        "vendas/<int:pk>/contrato/pdf/",
        views.PdfDoContratoView.as_view(),
        name="venda-contrato-pdf",
    ),
    path(
        "vendas/<int:pk>/transferencia/",
        views.TransferenciaDaVendaView.as_view(),
        name="venda-transferencia",
    ),
    path(
        "locacoes/<int:pk>/transferencia/",
        views.TransferenciaView.as_view(),
        name="locacao-transferencia",
    ),
]
