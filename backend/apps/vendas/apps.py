from django.apps import AppConfig


class VendasConfig(AppConfig):
    name = "apps.vendas"
    label = "vendas"

    def ready(self) -> None:
        from . import eventos, leituras  # noqa: F401 (eventos assina no import)

        leituras.registrar()
