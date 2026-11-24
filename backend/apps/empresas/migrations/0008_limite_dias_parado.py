# VEI-19 (T-486): limite de dias em estoque da empresa, padrão 30, de 1 a 365. A empresa nova
# nasce com o padrão pelo `default`; as linhas que já existem também (AddField preenche).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0007_venda_juros_e_comissao"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracaoempresa",
            name="limite_dias_parado",
            field=models.PositiveSmallIntegerField(default=30),
        ),
        migrations.AddConstraint(
            model_name="configuracaoempresa",
            constraint=models.CheckConstraint(
                condition=models.Q(limite_dias_parado__gte=1, limite_dias_parado__lte=365),
                name="configuracao_limite_dias_parado_1_a_365",
            ),
        ),
    ]
