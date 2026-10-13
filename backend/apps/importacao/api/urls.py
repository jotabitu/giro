"""Rotas da importação por planilha, no host da empresa."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("importacoes/", views.ImportacoesView.as_view(), name="importacoes"),
    path("importacoes/modelo/", views.ModeloView.as_view(), name="importacoes-modelo"),
    path("importacoes/<int:pk>/", views.ImportacaoView.as_view(), name="importacao"),
    path("importacoes/<int:pk>/linhas/", views.LinhasView.as_view(), name="importacao-linhas"),
    path(
        "importacoes/<int:pk>/linhas/<int:numero>/",
        views.LinhaView.as_view(),
        name="importacao-linha",
    ),
    path(
        "importacoes/<int:pk>/linhas/<int:numero>/ignorar/",
        views.IgnorarLinhaView.as_view(),
        name="importacao-linha-ignorar",
    ),
    path(
        "importacoes/<int:pk>/importar/", views.ImportarView.as_view(), name="importacao-importar"
    ),
    path(
        "importacoes/<int:pk>/cancelar/", views.CancelarView.as_view(), name="importacao-cancelar"
    ),
]
