# AUT-18 (VEI-19, T-486): a entrada no estoque à venda já avisada aos gerentes. Nula nos veículos
# que já existem e nos novos: nenhum foi avisado ainda.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("veiculos", "0010_copiar_precos_da_categoria"),
    ]

    operations = [
        migrations.AddField(
            model_name="veiculo",
            name="estoque_aviso_entrada_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
