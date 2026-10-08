"""Rotas do schema público (admin.<DOMINIO_BASE> e hosts sem empresa).

O Django Admin exige 2FA (OTPAdminSite, PLT-08): o usuário precisa de um dispositivo TOTP.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, path
from django_otp.admin import OTPAdminSite
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.__class__ = OTPAdminSite

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
]

# Documentação da API só onde EXPOR_DOCUMENTACAO_DA_API permite (fechada em produção).
if settings.EXPOR_DOCUMENTACAO_DA_API:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
