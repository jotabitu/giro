"""Compra pública (T-435, `compra.md`): `PedidoCompra`, a origem da empresa, a empresa anterior
(`PLT-16`), o CNPJ único só entre as não apagadas (B-02 da T-230) e o plano à venda (T-378,
`PLT-11`): o Completo nasce fora da venda."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


def completo_fora_da_venda(apps, schema_editor):
    Plano = apps.get_model("plataforma", "Plano")
    Plano.objects.filter(nome="Completo").update(a_venda=False)


def completo_a_venda(apps, schema_editor):
    Plano = apps.get_model("plataforma", "Plano")
    Plano.objects.filter(nome="Completo").update(a_venda=True)


def dominio_principal(apps, schema_editor):
    """A compra mora no domínio principal (`compra.md`): ele cai no schema public. Em dev,
    `localhost` já é da plataforma (0002)."""
    from django.conf import settings

    Empresa = apps.get_model("plataforma", "Empresa")
    Dominio = apps.get_model("plataforma", "Dominio")
    publica = Empresa.objects.filter(schema_name="public").first()
    if publica is None:
        return
    Dominio.objects.get_or_create(
        domain=settings.DOMINIO_BASE, defaults={"tenant": publica, "is_primary": False}
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plataforma", "0013_recursos_dos_planos"),
    ]

    operations = [
        migrations.CreateModel(
            name="PedidoCompra",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("chave", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("aguardando_confirmacao", "Aguardando confirmação"),
                            ("confirmado", "Confirmado"),
                            ("criando", "Criando"),
                            ("pronto", "Pronto"),
                            ("falhou", "Falhou"),
                            ("expirado", "Expirado"),
                        ],
                        default="aguardando_confirmacao",
                        max_length=25,
                    ),
                ),
                (
                    "ciclo",
                    models.CharField(
                        choices=[("mensal", "Mensal"), ("anual", "Anual")], max_length=10
                    ),
                ),
                (
                    "forma_pagamento",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("cartao", "Cartão de crédito"),
                            ("pix_automatico", "Pix automático"),
                            ("boleto", "Boleto"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("administrador_nome", models.CharField(blank=True, default="", max_length=150)),
                ("administrador_email", models.EmailField(blank=True, default="", max_length=254)),
                ("administrador_celular", models.CharField(blank=True, default="", max_length=13)),
                ("aceita_whatsapp", models.BooleanField(default=False)),
                ("cnpj", models.CharField(blank=True, default="", max_length=14)),
                ("razao_social", models.CharField(blank=True, default="", max_length=150)),
                ("nome_exibicao", models.CharField(blank=True, default="", max_length=80)),
                ("cidade", models.CharField(blank=True, default="", max_length=80)),
                ("uf", models.CharField(blank=True, default="", max_length=2)),
                ("subdominio", models.CharField(blank=True, default="", max_length=63)),
                (
                    "situacao_cnpj",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("nova", "Nova"),
                            ("ja_foi_cliente", "Já foi cliente"),
                            ("em_uso", "Em uso"),
                            ("fatura_em_atraso", "Fatura em atraso"),
                        ],
                        default="",
                        max_length=20,
                    ),
                ),
                ("codigo_hash", models.CharField(blank=True, default="", max_length=200)),
                ("codigo_expira_em", models.DateTimeField(blank=True, null=True)),
                ("codigo_enviado_em", models.DateTimeField(blank=True, null=True)),
                ("tentativas_codigo", models.PositiveSmallIntegerField(default=0)),
                ("reenvios", models.PositiveSmallIntegerField(default=0)),
                ("aceite_termos_versao", models.CharField(blank=True, default="", max_length=20)),
                ("aceite_termos_em", models.DateTimeField(blank=True, null=True)),
                ("ip_hash", models.CharField(blank=True, default="", max_length=64)),
                ("andamento", models.JSONField(blank=True, default=dict)),
                ("mensagem_falha", models.CharField(blank=True, default="", max_length=200)),
                ("pronto_em", models.DateTimeField(blank=True, null=True)),
                ("acesso_entregue_em", models.DateTimeField(blank=True, null=True)),
                ("expira_em", models.DateTimeField()),
                ("dados_apagados_em", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "pedido de compra",
                "verbose_name_plural": "pedidos de compra",
            },
        ),
        migrations.AddField(
            model_name="empresa",
            name="aceite_termos_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="empresa",
            name="aceite_termos_versao",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="empresa",
            name="empresa_anterior",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="plataforma.empresa",
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="origem",
            field=models.CharField(
                choices=[("admin", "Django Admin"), ("compra", "Compra pública")],
                default="admin",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="plano",
            name="a_venda",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="empresa",
            name="cnpj",
            field=models.CharField(blank=True, max_length=14, null=True),
        ),
        migrations.AddIndex(
            model_name="empresa",
            index=models.Index(fields=["cnpj"], name="empresa_cnpj_idx"),
        ),
        migrations.AddConstraint(
            model_name="empresa",
            constraint=models.UniqueConstraint(
                condition=models.Q(("apagada_em__isnull", True)),
                fields=("cnpj",),
                name="empresa_cnpj_unico_nao_apagada",
            ),
        ),
        migrations.AddField(
            model_name="pedidocompra",
            name="empresa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="plataforma.empresa",
            ),
        ),
        migrations.AddField(
            model_name="pedidocompra",
            name="plano",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="+", to="plataforma.plano"
            ),
        ),
        migrations.AddIndex(
            model_name="pedidocompra",
            index=models.Index(fields=["status", "expira_em"], name="pedido_compra_status_idx"),
        ),
        migrations.AddIndex(
            model_name="pedidocompra",
            index=models.Index(
                fields=["administrador_email", "cnpj"], name="pedido_compra_email_idx"
            ),
        ),
        migrations.RunPython(completo_fora_da_venda, completo_a_venda),
        migrations.RunPython(dominio_principal, migrations.RunPython.noop),
    ]
