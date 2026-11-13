from django.apps import AppConfig


class VendasConfig(AppConfig):
    name = "apps.vendas"
    label = "vendas"

    def ready(self) -> None:
        from comum.auditoria import registrar_formatador

        from . import eventos, leituras, textos  # noqa: F401 (eventos assina no import)

        leituras.registrar()
        # Textos da auditoria (VEN-11, T-420)
        registrar_formatador("venda.criar_da_quitacao", textos.criar_da_quitacao)
        registrar_formatador("venda.registrar_transferencia", textos.registrar_transferencia)
