from django.urls import path

from . import views

urlpatterns = [
    path("contratos/modelos/", views.ModelosView.as_view()),
    path("contratos/modelos/<int:pk>/", views.ModeloView.as_view()),
    path("contratos/modelos/<int:pk>/previa/", views.PreviaModeloView.as_view()),
    path("contratos/modelos/<int:pk>/publicar/", views.PublicarModeloView.as_view()),
    path("contratos/modelos/<int:pk>/arquivar/", views.ArquivarModeloView.as_view()),
    path("contratos/marcadores/", views.MarcadoresView.as_view()),
    path("contratos/modelos-prontos/", views.ModelosProntosView.as_view()),
    path("publico/assinaturas/consultar/", views.ConsultarAssinaturaView.as_view()),
    path("publico/assinaturas/assinar/", views.AssinarView.as_view()),
]
