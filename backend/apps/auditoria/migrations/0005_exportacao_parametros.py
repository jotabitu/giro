from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auditoria", "0004_exportacao_e_relogio"),
    ]

    operations = [
        migrations.AddField(
            model_name="exportacao",
            name="parametros",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
