"""Rotas das vendas, no host da empresa (`docs/api/vendas.md`)."""

from django.urls import URLPattern, path

from . import fase_1c, views

urlpatterns: list[URLPattern] = [
    path("vendas/", views.VendasView.as_view(), name="vendas"),
    path("vendas/simular/", views.SimularView.as_view(), name="vendas-simular"),
    # Fase 1c (VEN-08, VEN-09, VEN-12, VEN-15, VEN-16): resumo, metas e o link da proposta.
    path("vendas/resumo/", fase_1c.ResumoView.as_view(), name="vendas-resumo"),
    path("vendas/metas/", fase_1c.MetasView.as_view(), name="vendas-metas"),
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
        "vendas/<int:pk>/proposta/link/",
        fase_1c.LinkDaPropostaView.as_view(),
        name="venda-proposta-link",
    ),
    path(
        "publico/propostas/consultar/",
        fase_1c.ConsultarPropostaView.as_view(),
        name="proposta-publica-consultar",
    ),
    path(
        "locacoes/<int:pk>/transferencia/",
        views.TransferenciaView.as_view(),
        name="locacao-transferencia",
    ),
]
