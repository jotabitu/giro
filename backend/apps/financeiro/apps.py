from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    name = "apps.financeiro"
    label = "financeiro"

    def ready(self) -> None:
        from . import eventos, leituras  # noqa: F401 - registra os assinantes

        leituras.registrar()
