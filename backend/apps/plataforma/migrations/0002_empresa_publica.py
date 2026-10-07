"""Linha da plataforma em Empresa (schema public, ADR 0013) e seus domínios.

admin.<DOMINIO_BASE> sempre; em dev (DOMINIO_BASE=localhost) também localhost e 127.0.0.1,
para a API e o /api/schema/ responderem em localhost:8000.
"""

from django.conf import settings
from django.db import migrations


def dominios_da_plataforma() -> list[str]:
    dominios = [f"{settings.SUBDOMINIO_PLATAFORMA}.{settings.DOMINIO_BASE}"]
    if settings.DOMINIO_BASE == "localhost":
        dominios += ["localhost", "127.0.0.1"]
    return dominios


def criar(apps, schema_editor):
    Empresa = apps.get_model("plataforma", "Empresa")
    Dominio = apps.get_model("plataforma", "Dominio")
    empresa, _ = Empresa.objects.get_or_create(
        schema_name="public", defaults={"nome": "Giro", "status": "ativa"}
    )
    for posicao, dominio in enumerate(dominios_da_plataforma()):
        Dominio.objects.get_or_create(
            domain=dominio, defaults={"tenant": empresa, "is_primary": posicao == 0}
        )


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0001_initial")]

    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
