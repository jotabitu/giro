from django.apps import AppConfig


class AprovacoesConfig(AppConfig):
    name = "apps.aprovacoes"
    label = "aprovacoes"

    def ready(self) -> None:
        from comum import aprovacoes

        from . import selectors, services

        # Os outros apps abrem pedidos só pela porta em `comum` (ADR 0019).
        aprovacoes.registrar(
            pedir=services.pedir,
            pendente=selectors.pendente,
            cancelar_pendentes=services.cancelar_pendentes,
        )
