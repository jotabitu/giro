# VEN-15 (T-502, fase 1b; ADR 0042, item 6): a finalidade `venda` passa a "Compra e venda".
# Só o rótulo das choices; nenhum dado muda.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0004_finalidade_locacao_compra"),
    ]

    operations = [
        migrations.AlterField(
            model_name="modelocontrato",
            name="finalidade",
            field=models.CharField(
                choices=[
                    ("locacao", "Locação"),
                    ("locacao_compra", "Locação com intenção de compra"),
                    ("venda", "Compra e venda"),
                ],
                max_length=20,
            ),
        ),
    ]
