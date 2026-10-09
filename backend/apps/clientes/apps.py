from django.apps import AppConfig


class ClientesConfig(AppConfig):
    name = "apps.clientes"
    label = "clientes"

    def ready(self) -> None:
        from . import eventos  # noqa: F401 - registra os assinantes
