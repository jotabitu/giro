"""Busca das despesas (FIN-16, T-178): a descrição normalizada, preenchida nas que já existem."""

import unicodedata

from django.db import migrations, models


def _texto_de_busca(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def preencher(apps, schema_editor):  # type: ignore[no-untyped-def]
    Despesa = apps.get_model("financeiro", "Despesa")
    for despesa in Despesa.objects.only("pk", "descricao").iterator():
        Despesa.objects.filter(pk=despesa.pk).update(
            descricao_busca=_texto_de_busca(despesa.descricao)
        )


class Migration(migrations.Migration):
    dependencies = [("financeiro", "0006_dia_da_cobranca")]

    operations = [
        migrations.AddField(
            model_name="despesa",
            name="descricao_busca",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
