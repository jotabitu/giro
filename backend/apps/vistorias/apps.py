from django.apps import AppConfig


class VistoriasConfig(AppConfig):
    name = "apps.vistorias"
    label = "vistorias"

    def ready(self) -> None:
        from . import leituras

        leituras.registrar()
