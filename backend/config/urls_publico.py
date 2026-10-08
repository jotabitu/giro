"""Rotas do schema público (admin.<DOMINIO_BASE> e hosts sem empresa).

O Django Admin exige 2FA (OTPAdminSite, PLT-08): o usuário precisa de um dispositivo TOTP. O
login passa pelo bloqueio e pela auditoria da API (`contas.login_admin`, P-01 da T-057).
"""

from django.conf import settings
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from django_otp.admin import OTPAdminSite
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.contas.api.urls import urls_plataforma as urls_contas
from apps.contas.login_admin import LoginDoAdmin
from apps.plataforma.api.urls import urls_plataforma

admin.site.__class__ = OTPAdminSite
admin.site.login_form = LoginDoAdmin

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("api/plataforma/", include(urls_contas)),
    path("api/plataforma/", include(urls_plataforma)),
]

# Documentação da API só onde EXPOR_DOCUMENTACAO_DA_API permite (fechada em produção).
if settings.EXPOR_DOCUMENTACAO_DA_API:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
