"""Recursos dos três planos pela ADR 0024 (PLT-12, PLT-11; T-196, tabela "Planos" de
`docs/api/plataforma.md`): entram `conciliacao`, `recebimento_parceiro` e `cobranca_whatsapp`,
saem `dominio_proprio` e `api_integracoes`, e `contrato_digital` passa ao Essencial."""

from django.db import migrations, models

import apps.plataforma.models

ESSENCIAL = ["locacoes_vistoria", "contas_receber", "contrato_digital"]
PROFISSIONAL = [
    *ESSENCIAL,
    "vendas_comissoes",
    "manutencao_despesas",
    "conciliacao",
    "relatorios",
    "recebimento_parceiro",
    "cobranca_whatsapp",
]
COMPLETO = [*PROFISSIONAL, "suporte_prioritario"]
RECURSOS = {"Essencial": ESSENCIAL, "Profissional": PROFISSIONAL, "Completo": COMPLETO}
SAIRAM = {"dominio_proprio", "api_integracoes"}


def regravar(apps, schema_editor):
    Plano = apps.get_model("plataforma", "Plano")
    for plano in Plano.objects.all():
        if plano.nome in RECURSOS:
            plano.recursos = RECURSOS[plano.nome]
        else:  # plano criado à mão: só tira os que saíram do enum
            plano.recursos = [r for r in plano.recursos or [] if r not in SAIRAM]
        plano.save(update_fields=["recursos"])


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0012_cancelar_e_pausar")]

    operations = [
        migrations.AlterField(
            model_name="plano",
            name="recursos",
            field=models.JSONField(
                blank=True, default=list, validators=[apps.plataforma.models.validar_recursos]
            ),
        ),
        migrations.RunPython(regravar, migrations.RunPython.noop),
    ]
