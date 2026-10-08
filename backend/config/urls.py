"""Rotas do schema da empresa (<subdominio>.<DOMINIO_BASE>).

Sem Django Admin aqui: o admin só existe no schema público, com 2FA (achado 4 da T-032).
"""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
