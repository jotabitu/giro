"""Rotas de filiais e da busca de CEP, no host da empresa."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("filiais/minhas/", views.MinhasView.as_view(), name="filiais-minhas"),
    path("filiais/", views.FiliaisView.as_view(), name="filiais"),
    path("filiais/<int:pk>/", views.FilialView.as_view(), name="filial"),
    path("filiais/<int:pk>/tornar-matriz/", views.TornarMatrizView.as_view(), name="filial-matriz"),
    path("filiais/<int:pk>/desativar/", views.DesativarView.as_view(), name="filial-desativar"),
    path("filiais/<int:pk>/reativar/", views.ReativarView.as_view(), name="filial-reativar"),
    path("filiais/<int:pk>/feriados/", views.FeriadosView.as_view(), name="filial-feriados"),
    path(
        "filiais/<int:pk>/feriados/sugestoes/",
        views.SugestoesView.as_view(),
        name="filial-feriados-sugestoes",
    ),
    path(
        "filiais/<int:pk>/feriados/<int:feriado_id>/remover/",
        views.RemoverFeriadoView.as_view(),
        name="filial-feriado-remover",
    ),
    path("enderecos/cep/<str:cep>/", views.CepView.as_view(), name="cep"),
]
