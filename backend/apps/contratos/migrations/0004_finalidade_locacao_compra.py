# LOC-16 (T-420, ADR 0037): a finalidade "Locação com intenção de compra".

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0003_copiar_link"),
    ]

    operations = [
        migrations.AlterField(
            model_name="modelocontrato",
            name="finalidade",
            field=models.CharField(
                choices=[
                    ("locacao", "Locação"),
                    ("locacao_compra", "Locação com intenção de compra"),
                    ("venda", "Venda"),
                ],
                max_length=20,
            ),
        ),
    ]
