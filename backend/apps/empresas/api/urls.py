"""Rotas da marca e do ramo, no host da empresa (no `public` não existem: 404 do urlconf)."""

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("marca/", views.MarcaView.as_view(), name="marca"),
    path("marca/simular/", views.SimularMarcaView.as_view(), name="marca-simular"),
    path("marca/logo/", views.LogoView.as_view(), name="marca-logo"),
    path("ramo/", views.RamoView.as_view(), name="ramo"),
]
