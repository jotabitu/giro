from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("financeiro", "0004_caixa_cobrancas_despesas"),
    ]

    operations = [
        migrations.AddField(
            model_name="contareceber",
            name="bloqueio_pedido_em",
            field=models.DateField(blank=True, null=True),
        ),
    ]
