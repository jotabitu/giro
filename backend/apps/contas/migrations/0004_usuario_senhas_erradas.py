from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contas", "0003_convite_2_etapas"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="senhas_erradas",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
