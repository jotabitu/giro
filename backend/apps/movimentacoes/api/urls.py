"""Rotas das movimentações, no host da empresa (docs/api/movimentacoes.md)."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("movimentacoes/", views.MovimentacoesView.as_view(), name="movimentacoes"),
    path("movimentacoes/quadro/", views.QuadroView.as_view(), name="movimentacoes-quadro"),
    path("movimentacoes/pessoas/", views.PessoasView.as_view(), name="movimentacoes-pessoas"),
    path("movimentacoes/locais/", views.LocaisView.as_view(), name="movimentacoes-locais"),
    path(
        "movimentacoes/locais/<int:pk>/inativar/",
        views.InativarLocalView.as_view(),
        name="movimentacoes-local-inativar",
    ),
    path(
        "movimentacoes/locais/<int:pk>/reativar/",
        views.ReativarLocalView.as_view(),
        name="movimentacoes-local-reativar",
    ),
    path("movimentacoes/<int:pk>/", views.MovimentacaoView.as_view(), name="movimentacao"),
    path(
        "movimentacoes/<int:pk>/iniciar/", views.IniciarView.as_view(), name="movimentacao-iniciar"
    ),
    path(
        "movimentacoes/<int:pk>/cancelar/",
        views.CancelarView.as_view(),
        name="movimentacao-cancelar",
    ),
    path(
        "movimentacoes/<int:pk>/paradas/<int:parada_id>/chegada/",
        views.ChegadaNaParadaView.as_view(),
        name="movimentacao-parada-chegada",
    ),
    path(
        "movimentacoes/<int:pk>/paradas/<int:parada_id>/saida/",
        views.SaidaDaParadaView.as_view(),
        name="movimentacao-parada-saida",
    ),
    path(
        "movimentacoes/<int:pk>/chegada/fotos/",
        views.FotoDaChegadaView.as_view(),
        name="movimentacao-chegada-fotos",
    ),
    path(
        "movimentacoes/<int:pk>/chegada/", views.ChegadaView.as_view(), name="movimentacao-chegada"
    ),
    path(
        "movimentacoes/<int:pk>/recebedores/",
        views.RecebedoresView.as_view(),
        name="movimentacao-recebedores",
    ),
]
