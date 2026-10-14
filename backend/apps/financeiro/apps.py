from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    name = "apps.financeiro"
    label = "financeiro"

    def ready(self) -> None:
        from . import eventos, exportacao, leituras  # noqa: F401 - registra os assinantes

        leituras.registrar()
        exportacao.registrar()  # item `despesas` da exportação (FIN-16, AUD-07)
