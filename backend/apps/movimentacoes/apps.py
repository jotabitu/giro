from django.apps import AppConfig


class MovimentacoesConfig(AppConfig):
    name = "apps.movimentacoes"
    label = "movimentacoes"

    def ready(self) -> None:
        from . import eventos, leituras  # noqa: F401 (eventos assina no import)

        leituras.registrar()
