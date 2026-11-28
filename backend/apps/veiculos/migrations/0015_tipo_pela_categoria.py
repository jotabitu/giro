"""Preenche o tipo do veículo pela categoria de hoje (ADR 0043, item 2; VEI-11).

Todos nasceram `moto` na `0014`; aqui só os de categoria de carro viram `carro`. Um `UPDATE` por
empresa, idempotente, pelo `_base_manager` (o excluído, o vendido e o baixado também recebem o
tipo). Na empresa nova (schema vazio) não há veículo e nada é alterado. `tipo_veiculo` não é
status: o `update()` não fere a regra de status por serviço e não gera auditoria, como a `0010`.
A reversa não faz nada.
"""

from django.db import migrations


def preencher(apps, schema_editor):  # type: ignore[no-untyped-def]
    # A conexão da migração, não a `default`: a empresa nova é migrada pela conexão do papel de
    # migração, no schema dela (ADR 0040). Sem `schema_editor` (chamada direta nos testes), a
    # `default`.
    db = schema_editor.connection.alias if schema_editor is not None else "default"
    veiculo = apps.get_model("veiculos", "Veiculo")
    (
        veiculo._base_manager.using(db)
        .filter(categoria__tipo_veiculo="carro")
        .update(tipo_veiculo="carro")
    )


class Migration(migrations.Migration):
    dependencies = [
        ("veiculos", "0014_tipo_do_veiculo"),
    ]

    operations = [
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
