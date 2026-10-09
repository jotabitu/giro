from django.urls import path

from . import views

urlpatterns = [
    path("locacoes/", views.LocacoesView.as_view()),
    path("locacoes/simular/", views.SimularLocacaoView.as_view()),
    path("locacoes/<int:pk>/", views.LocacaoView.as_view()),
    path("locacoes/<int:pk>/confirmar/", views.ConfirmarLocacaoView.as_view()),
    path("locacoes/<int:pk>/historico/", views.HistoricoLocacaoView.as_view()),
    path("planos-especiais/", views.PlanosEspeciaisView.as_view()),
    path("planos-especiais/<int:pk>/", views.PlanoEspecialView.as_view()),
    path("planos-especiais/<int:pk>/desativar/", views.DesativarPlanoEspecialView.as_view()),
]
