"""Rotas da auditoria e da exportação, no host da empresa."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("auditoria/eventos/", views.EventosView.as_view(), name="auditoria-eventos"),
    path("auditoria/eventos/<int:pk>/", views.EventoView.as_view(), name="auditoria-evento"),
    path("auditoria/pessoas/", views.PessoasView.as_view(), name="auditoria-pessoas"),
    path("exportacoes/", views.ExportacoesView.as_view(), name="exportacoes"),
    path(
        "exportacoes/<int:pk>/baixar/",
        views.BaixarExportacaoView.as_view(),
        name="exportacao-baixar",
    ),
]
