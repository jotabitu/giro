# T-410, ADR 0035: a conta da locação que espera a retirada (LOC-05, FIN-03).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0008_despesa_origem"),
    ]

    operations = [
        migrations.AddField(
            model_name="contareceber",
            name="aguarda_retirada",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="contareceber",
            name="liberada_em",
            field=models.DateField(blank=True, null=True),
        ),
    ]
