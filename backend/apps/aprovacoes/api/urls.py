"""Rotas das aprovações, no host da empresa."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("aprovacoes/", views.AprovacoesView.as_view(), name="aprovacoes"),
    path("aprovacoes/<int:pk>/aprovar/", views.AprovarView.as_view(), name="aprovacao-aprovar"),
    path("aprovacoes/<int:pk>/recusar/", views.RecusarView.as_view(), name="aprovacao-recusar"),
    path("aprovacoes/<int:pk>/cancelar/", views.CancelarView.as_view(), name="aprovacao-cancelar"),
]
