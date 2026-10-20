"""Cancelar, pausar e apagar a empresa (PLT-06, AUD-08; T-195, `docs/api/cancelamento.md`)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plataforma", "0011_nome_sem_quebra"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="pausa_inicio",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="empresa",
            name="cancelamento_pedido_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="empresa",
            name="motivo_cancelamento",
            field=models.CharField(
                blank=True,
                choices=[
                    ("preco_alto", "Preço alto para o meu tamanho"),
                    ("faltou_funcao", "Faltou alguma função"),
                    ("outro_sistema", "Vou usar outro sistema"),
                    ("fechar_ou_pausar", "Vou fechar ou pausar a locadora"),
                    ("outro", "Outro motivo"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="aviso_apagamento_enviado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="empresa",
            name="apagada_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
