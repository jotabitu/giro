"""Rotas do schema da empresa (<subdominio>.<DOMINIO_BASE>).

Sem Django Admin aqui: o admin só existe no schema público, com 2FA (achado 4 da T-032).
"""

from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.plataforma.api.urls import urls_empresa as urls_assinatura

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/", include(urls_assinatura)),
]

# Documentação da API só onde EXPOR_DOCUMENTACAO_DA_API permite (fechada em produção).
if settings.EXPOR_DOCUMENTACAO_DA_API:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
