from django.urls import path

from . import views

urlpatterns = [
    path("locacoes/<int:pk>/vistorias/", views.VistoriasDaLocacaoView.as_view()),
    path("vistorias/agenda/", views.AgendaView.as_view()),
    path("vistorias/avarias/", views.AvariasAbertasView.as_view()),
    path("vistorias/<int:pk>/", views.VistoriaView.as_view()),
    path("vistorias/<int:pk>/fotos/", views.FotosDaVistoriaView.as_view()),
    path("vistorias/<int:pk>/avarias/", views.AvariasDaVistoriaView.as_view()),
    path("vistorias/<int:pk>/avarias/<int:avaria_id>/", views.AvariaDaVistoriaView.as_view()),
    path("vistorias/<int:pk>/concluir/", views.ConcluirVistoriaView.as_view()),
    path("vistorias/<int:pk>/corrigir/", views.CorrigirVistoriaView.as_view()),
]
