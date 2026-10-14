"""T-029: chave da API da subconta cifrada (ADR 0014, S-05) e carteira no parceiro.

O `id_cifra` é único: nasce nulo, cada linha que já existe ganha o seu, e só então vira único.
"""

import uuid

from django.db import migrations, models

import comum.campos


def preencher_id_cifra(apps, schema_editor):
    ContaPagamento = apps.get_model("plataforma", "ContaPagamento")
    for conta in ContaPagamento.objects.filter(id_cifra__isnull=True):
        conta.id_cifra = uuid.uuid4()
        conta.save(update_fields=["id_cifra"])


class Migration(migrations.Migration):
    dependencies = [
        ("plataforma", "0007_conta_pagamento"),
    ]

    operations = [
        migrations.AddField(
            model_name="contapagamento",
            name="id_cifra",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(preencher_id_cifra, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contapagamento",
            name="id_cifra",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="contapagamento",
            name="carteira_id",
            field=models.CharField(blank=True, default="", max_length=60),
        ),
        migrations.AddField(
            model_name="contapagamento",
            name="chave_api_cifrada",
            field=comum.campos.CampoCifrado(blank=True, default="", tipo="segredos"),
        ),
    ]
