from django.apps import AppConfig


class LocacoesConfig(AppConfig):
    name = "apps.locacoes"
    label = "locacoes"

    def ready(self) -> None:
        from . import eventos, leituras  # noqa: F401 - eventos registra os assinantes

        leituras.registrar()
