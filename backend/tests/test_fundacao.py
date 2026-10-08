"""Conferências da fundação que não são de um app só."""

from django.conf import settings

from apps.plataforma.models import Dominio, Empresa
from comum.empresa import STATUS_OPERANDO, STATUS_SO_LEITURA


def test_status_conhecidos_pelo_comum_existem_na_empresa():
    assert set(Empresa.Status.values) >= STATUS_OPERANDO | STATUS_SO_LEITURA


def test_apps_dos_dois_schemas_conforme_adr_0011():
    dos_dois = {
        "comum",
        "apps.auditoria",
        "apps.contas",
        "django.contrib.auth",
        "rest_framework_simplejwt.token_blacklist",
        "django_otp",
    }
    assert dos_dois <= set(settings.SHARED_APPS)
    assert dos_dois <= set(settings.TENANT_APPS)
    assert "apps.plataforma" not in settings.TENANT_APPS
    assert "apps.locacoes" not in settings.SHARED_APPS


def test_plataforma_tem_linha_em_empresa_e_dominio_admin(publico):
    # ADR 0013: o public também tem linha em Empresa (empresa_id dos tokens da plataforma).
    plataforma = Empresa.objects.get(schema_name="public")
    assert Dominio.objects.filter(tenant=plataforma, domain="admin.localhost").exists()


def test_fuso_e_moeda():
    assert settings.TIME_ZONE == "America/Sao_Paulo"
    assert settings.USE_TZ is True
    assert settings.CELERY_TIMEZONE == "America/Sao_Paulo"
