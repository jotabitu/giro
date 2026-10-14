"""Rotas do painel, no host da empresa. Respondem sempre, sem depender de `relatorios` em
`GIRO_MODULOS_ATIVOS`: aquela chave liga o item "Relatórios" do menu, não o início. Configurações
também responde sempre (`configuracoes` liga só o item do menu)."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("painel/contadores/", views.ContadoresView.as_view(), name="painel-contadores"),
    path("painel/inicio/", views.InicioView.as_view(), name="painel-inicio"),
    path("configuracoes/", views.ConfiguracoesView.as_view(), name="configuracoes"),
]
