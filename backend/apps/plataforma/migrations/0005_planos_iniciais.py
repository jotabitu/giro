"""Os três planos (PLT-03; preços nas "Decisões de 07 out 2026"; recursos da tela Compra-Planos).

Essencial: locação, vistoria e contas a receber. Profissional: tudo do Essencial, mais
contrato digital, vendas, manutenção e despesas, comissões e relatórios. Completo: tudo.
"""

from django.db import migrations

ESSENCIAL = ["locacoes_vistoria", "contas_receber"]
PROFISSIONAL = [
    *ESSENCIAL,
    "contrato_digital",
    "vendas_comissoes",
    "manutencao_despesas",
    "relatorios",
]
COMPLETO = [*PROFISSIONAL, "dominio_proprio", "api_integracoes", "suporte_prioritario"]

PLANOS = [
    ("Essencial", 19900, 30, 1, 3, ESSENCIAL, 1),
    ("Profissional", 44900, 150, 3, 10, PROFISSIONAL, 2),
    ("Completo", 89900, None, None, None, COMPLETO, 3),
]


def criar(apps, schema_editor):
    Plano = apps.get_model("plataforma", "Plano")
    for nome, mensal, veiculos, filiais, usuarios, recursos, ordem in PLANOS:
        Plano.objects.get_or_create(
            nome=nome,
            defaults={
                "preco_mensal_centavos": mensal,
                "meses_cobrados_no_anual": 10,
                "limite_veiculos": veiculos,
                "limite_filiais": filiais,
                "limite_usuarios": usuarios,
                "recursos": recursos,
                "ordem": ordem,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0004_planos_empresa_uso")]

    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
