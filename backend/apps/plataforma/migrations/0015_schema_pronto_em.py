"""ADR 0040 (T-477): `Empresa.schema_pronto_em`, a origem e quem pediu no `PedidoCompra`.

A migração de dados (item 5) preenche `schema_pronto_em` só das empresas cujo schema existe no
`pg_namespace` e está totalmente migrado (a última migração de cada app do tenant nesta versão
registrada no `django_migrations` dele), com a data de criação delas. Recusa `public`,
`information_schema` e `pg_*`; empresa que não passa fica nula e vai ao log. A empresa já apagada
(AUD-08) teve schema pronto e o perdeu de propósito: recebe a data de criação também.
"""

import logging
import re

from django.db import migrations, models

logger = logging.getLogger(__name__)

_SCHEMA_DE_EMPRESA = re.compile(r"^[a-z0-9_]{3,30}$")


def _schema_recusado(nome: str) -> bool:
    return (
        not _SCHEMA_DE_EMPRESA.match(nome)
        or nome in ("public", "information_schema")
        or nome.startswith("pg_")
    )


# A última migração de cada app do tenant nesta versão (igual à v0.1.2). Fixa de propósito: no
# deploy, o `migrate_schemas` migra o `public` antes dos schemas de empresa, então uma migração de
# tenant que viesse junto ainda não estaria aplicada quando esta roda.
_ULTIMAS_DO_TENANT = {
    ("comum", "0003_aviso_sem_cartao"),
    ("auditoria", "0005_exportacao_parametros"),
    ("contas", "0006_email_unico_sem_caixa"),
    ("empresas", "0005_ramo"),
    ("filiais", "0003_nome_curto"),
    ("notificacoes", "0001_initial"),
    ("clientes", "0001_clientes"),
    ("veiculos", "0008_fotos_do_veiculo"),
    ("contratos", "0004_finalidade_locacao_compra"),
    ("aprovacoes", "0003_resumo_e_indice"),
    ("financeiro", "0010_categorias_do_veiculo"),
    ("locacoes", "0008_locacao_com_intencao_de_compra"),
    ("vistorias", "0005_copiar_link"),
    ("movimentacoes", "0001_movimentacoes"),
    ("vendas", "0001_vendas"),
    ("importacao", "0001_importacao"),
}


def _totalmente_migrado(cursor, schema: str, esperadas: set[tuple[str, str]]) -> bool:
    cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [schema])
    if cursor.fetchone() is None:
        return False
    cursor.execute("SELECT to_regclass(%s)", [f'"{schema}".django_migrations'])
    linha = cursor.fetchone()
    if linha is None or linha[0] is None:
        return False
    # O nome passou por `_schema_recusado` (só [a-z0-9_]).
    cursor.execute(f'SELECT app, name FROM "{schema}".django_migrations')  # noqa: S608
    aplicadas = {(app, nome) for app, nome in cursor.fetchall()}
    return esperadas <= aplicadas


def preencher_schema_pronto_em(apps, schema_editor):
    Empresa = apps.get_model("plataforma", "Empresa")
    esperadas = _ULTIMAS_DO_TENANT
    with schema_editor.connection.cursor() as cursor:
        for empresa in Empresa.objects.filter(schema_pronto_em__isnull=True).order_by("pk"):
            nome = str(empresa.schema_name)
            if nome == "public":
                continue  # a plataforma não é empresa: fica nula e o `prontas()` a inclui
            if empresa.apagada_em is not None:
                Empresa.objects.filter(pk=empresa.pk).update(schema_pronto_em=empresa.criado_em)
                continue
            if _schema_recusado(nome) or not _totalmente_migrado(cursor, nome, esperadas):
                logger.warning(
                    "ADR 0040: empresa %s (schema %r) sem schema pronto; fica nula.",
                    empresa.pk,
                    nome,
                )
                continue
            Empresa.objects.filter(pk=empresa.pk).update(schema_pronto_em=empresa.criado_em)


class Migration(migrations.Migration):
    dependencies = [("plataforma", "0014_compra_publica")]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="schema_pronto_em",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="pedidocompra",
            name="origem",
            field=models.CharField(
                choices=[("admin", "Django Admin"), ("compra", "Compra pública")],
                default="compra",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="pedidocompra",
            name="solicitado_por_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(preencher_schema_pronto_em, migrations.RunPython.noop),
    ]
