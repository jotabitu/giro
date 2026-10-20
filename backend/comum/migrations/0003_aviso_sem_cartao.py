"""M-01 da T-189 (ADR 0023, item 2): os avisos já gravados saem sem `payment.creditCard`.

`comum` está nos dois schemas: roda no `public` (conta principal) e em cada empresa (subcontas).
A regra é a de `integracoes.pagamentos.base.aviso_sem_cartao`, copiada aqui para a migração não
depender do código de hoje.
"""

from typing import Any

from django.db import migrations


def _sem_cartao(corpo: Any) -> Any:
    if not isinstance(corpo, dict) or not isinstance(corpo.get("payment"), dict):
        return corpo
    return {**corpo, "payment": {k: v for k, v in corpo["payment"].items() if k != "creditCard"}}


def limpar(apps: Any, schema_editor: Any) -> None:
    webhook_recebido = apps.get_model("comum", "WebhookRecebido")
    for aviso in webhook_recebido.objects.filter(corpo__bruto__payment__has_key="creditCard"):
        aviso.corpo = {**aviso.corpo, "bruto": _sem_cartao(aviso.corpo["bruto"])}
        aviso.save(update_fields=["corpo"])


class Migration(migrations.Migration):
    dependencies = [("comum", "0002_webhook_recebido")]

    operations = [migrations.RunPython(limpar, migrations.RunPython.noop)]
