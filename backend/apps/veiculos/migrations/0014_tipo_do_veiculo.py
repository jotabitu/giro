"""Moto ou carro passa a ser do próprio veículo (ADR 0043, item 2; VEI-11).

O default `moto` só preenche as linhas que já existem; o model fica sem default. A `0015` corrige
os veículos de categoria de carro. A `categoria` vira nula (dado antigo). A reversa volta a
`categoria` a obrigatória e só funciona antes do primeiro veículo novo sem categoria.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("veiculos", "0013_excluido"),
    ]

    operations = [
        migrations.AddField(
            model_name="veiculo",
            name="tipo_veiculo",
            field=models.CharField(
                choices=[("moto", "Moto"), ("carro", "Carro")], default="moto", max_length=10
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="veiculo",
            name="categoria",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="veiculos",
                to="veiculos.categoria",
            ),
        ),
        migrations.AddIndex(
            model_name="veiculo",
            index=models.Index(fields=["filial", "tipo_veiculo"], name="veiculo_filial_tipo"),
        ),
        migrations.AddConstraint(
            model_name="veiculo",
            constraint=models.CheckConstraint(
                condition=models.Q(("tipo_veiculo__in", ["moto", "carro"])),
                name="veiculo_tipo_valido",
            ),
        ),
    ]
