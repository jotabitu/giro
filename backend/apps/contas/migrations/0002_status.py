"""`Usuario.ativo` (bool) vira `status` (USR-01, USR-04; conferência T-045)."""

from django.db import migrations, models


def copiar(apps, schema_editor):
    Usuario = apps.get_model("contas", "Usuario")
    Usuario.objects.filter(ativo=False).update(status="desativado")


class Migration(migrations.Migration):
    dependencies = [("contas", "0001_initial")]

    operations = [
        migrations.AddField(
            "usuario",
            "status",
            models.CharField(
                choices=[
                    ("convite_pendente", "Convite pendente"),
                    ("ativo", "Ativo"),
                    ("desativado", "Desativado"),
                ],
                default="ativo",
                max_length=20,
            ),
        ),
        migrations.RunPython(copiar, migrations.RunPython.noop),
        migrations.RemoveField("usuario", "ativo"),
    ]
