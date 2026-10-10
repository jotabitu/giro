from django.urls import path

from . import views

urlpatterns = [
    path("locacoes/", views.LocacoesView.as_view()),
    path("locacoes/simular/", views.SimularLocacaoView.as_view()),
    path("locacoes/<int:pk>/", views.LocacaoView.as_view()),
    path("locacoes/<int:pk>/confirmar/", views.ConfirmarLocacaoView.as_view()),
    path("locacoes/<int:pk>/historico/", views.HistoricoLocacaoView.as_view()),
    path("locacoes/<int:pk>/renovar/simular/", views.SimularRenovacaoView.as_view()),
    path("locacoes/<int:pk>/renovar/", views.RenovarLocacaoView.as_view()),
    path("locacoes/<int:pk>/cancelamento/simular/", views.SimularCancelamentoView.as_view()),
    path("locacoes/<int:pk>/cancelar/", views.CancelarLocacaoView.as_view()),
    path("locacoes/<int:pk>/contrato/", views.ContratoLocacaoView.as_view()),
    path("locacoes/<int:pk>/contrato/pdf/", views.PdfDoContratoView.as_view()),
    path("locacoes/<int:pk>/contrato/reenviar/", views.ReenviarContratoView.as_view()),
    path("planos-especiais/", views.PlanosEspeciaisView.as_view()),
    path("planos-especiais/<int:pk>/", views.PlanoEspecialView.as_view()),
    path("planos-especiais/<int:pk>/desativar/", views.DesativarPlanoEspecialView.as_view()),
]
