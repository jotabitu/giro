"""Rotas de veículos, categorias, preços e extras, no host da empresa."""

from django.urls import URLPattern, path

from . import views

ACOES = {
    "bloquear": views.BloquearView,
    "desbloquear": views.DesbloquearView,
    "colocar-a-venda": views.ColocarAVendaView,
    "voltar-para-frota": views.VoltarParaFrotaView,
    "baixar": views.BaixarView,
    "km": views.KmView,
    "corrigir-km": views.CorrigirKmView,
    "corrigir-identificacao": views.CorrigirIdentificacaoView,
}

urlpatterns: list[URLPattern] = [
    path("veiculos/", views.VeiculosView.as_view(), name="veiculos"),
    path("veiculos/modelos/", views.ModelosView.as_view(), name="veiculos-modelos"),
    path("veiculos/<int:pk>/", views.VeiculoView.as_view(), name="veiculo"),
    *[
        path(f"veiculos/<int:pk>/{acao}/", view.as_view(), name=f"veiculo-{acao}")
        for acao, view in ACOES.items()
    ],
    path(
        "veiculos/<int:pk>/documentos/", views.DocumentosView.as_view(), name="veiculo-documentos"
    ),
    path(
        "veiculos/<int:pk>/documentos/historico/",
        views.HistoricoDeDocumentosView.as_view(),
        name="veiculo-documentos-historico",
    ),
    path("categorias/", views.CategoriasView.as_view(), name="categorias"),
    path("categorias/<int:pk>/", views.CategoriaView.as_view(), name="categoria"),
    path(
        "categorias/<int:pk>/desativar/",
        views.DesativarCategoriaView.as_view(),
        name="categoria-desativar",
    ),
    path(
        "categorias/<int:pk>/reativar/",
        views.ReativarCategoriaView.as_view(),
        name="categoria-reativar",
    ),
    path("categorias/<int:pk>/precos/", views.PrecosView.as_view(), name="categoria-precos"),
    path(
        "categorias/<int:pk>/precos/<str:vigente_desde>/",
        views.PrecoAgendadoView.as_view(),
        name="categoria-preco-agendado",
    ),
    path("precos/historico/", views.HistoricoDePrecosView.as_view(), name="precos-historico"),
    path("extras/", views.ExtrasView.as_view(), name="extras"),
    path("extras/<int:pk>/", views.ExtraView.as_view(), name="extra"),
    path("extras/<int:pk>/desativar/", views.DesativarExtraView.as_view(), name="extra-desativar"),
]
