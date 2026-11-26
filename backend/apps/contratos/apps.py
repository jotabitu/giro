from django.apps import AppConfig


class ContratosConfig(AppConfig):
    name = "apps.contratos"
    label = "contratos"

    def ready(self) -> None:
        from comum import leituras

        from .models import Contrato

        def historico_do_cliente(cliente_id: int) -> int:
            """CLI-13: contrato em qualquer estado, inclusive o cancelado."""
            return int(Contrato.objects.filter(cliente_id=cliente_id).exists())

        leituras.registrar_contador("clientes.Cliente", "historico_contrato", historico_do_cliente)
