from django.apps import AppConfig


class VendasConfig(AppConfig):
    name = "apps.vendas"
    label = "vendas"

    def ready(self) -> None:
        from apps.veiculos import services as veiculos_services
        from comum.auditoria import registrar_formatador

        from . import eventos, leituras, services, textos  # noqa: F401 (eventos assina no import)

        leituras.registrar()
        # ADR 0042, item 1: o veículo com venda aberta não volta para a frota (VEN-10).
        veiculos_services.registrar_trava_do_estoque(services.trava_do_estoque)
        # Textos da auditoria (VEN-11, T-420; VEN-13, T-502)
        registrar_formatador("venda.criar_da_quitacao", textos.criar_da_quitacao)
        registrar_formatador("venda.registrar_transferencia", textos.registrar_transferencia)
        for acao, funcao in textos.DO_FLUXO.items():
            registrar_formatador(acao, funcao)
