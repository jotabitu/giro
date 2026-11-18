"""Preços novos dos planos (PLT-11, decisão do dono de 16 nov 2026, T-482).

Essencial 19900 → 13000 e Profissional 44900 → 16000; o Completo fica em 89900. O anual é
derivado (`meses_cobrados_no_anual`), não guardado. PLT-05 opção A: só o catálogo muda; o
`preco_contratado_centavos` de quem já assina fica como está. Idempotente, com reverso.
"""

from django.db import migrations

NOVOS = {"Essencial": 13000, "Profissional": 16000}
ANTIGOS = {"Essencial": 19900, "Profissional": 44900}


def _aplicar(apps, precos):
    plano = apps.get_model("plataforma", "Plano")
    for nome, preco in precos.items():
        plano.objects.filter(nome=nome).update(preco_mensal_centavos=preco)


def precos_novos(apps, schema_editor):
    _aplicar(apps, NOVOS)


def precos_antigos(apps, schema_editor):
    _aplicar(apps, ANTIGOS)


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0015_schema_pronto_em")]

    operations = [migrations.RunPython(precos_novos, precos_antigos)]
