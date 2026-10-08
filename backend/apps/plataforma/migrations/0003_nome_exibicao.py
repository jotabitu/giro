"""`Empresa.nome` passa a `nome_exibicao` (modelo de dados, item 2)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0002_empresa_publica")]

    operations = [
        migrations.RenameField("empresa", "nome", "nome_exibicao"),
        migrations.AlterField("empresa", "nome_exibicao", models.CharField(max_length=80)),
    ]
