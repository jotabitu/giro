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
    path("locacoes/<int:pk>/devolucao/", views.DevolucaoDaLocacaoView.as_view()),
    path("devolucoes/<int:pk>/", views.DevolucaoView.as_view()),
    path("devolucoes/<int:pk>/acerto/", views.AcertoView.as_view()),
    path("devolucoes/<int:pk>/acerto/itens/", views.ItensDoAcertoView.as_view()),
    path("devolucoes/<int:pk>/acerto/itens/<int:item_id>/", views.ItemDoAcertoView.as_view()),
    path("devolucoes/<int:pk>/encerrar/", views.EncerrarDevolucaoView.as_view()),
    path("devolucoes/<int:pk>/recibo/", views.ReciboDaDevolucaoView.as_view()),
    path("devolucoes/<int:pk>/recibo/reenviar/", views.ReenviarReciboView.as_view()),
]
