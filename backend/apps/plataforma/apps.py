from django.apps import AppConfig


class PlataformaConfig(AppConfig):
    name = "apps.plataforma"
    label = "plataforma"

    def ready(self) -> None:
        # O token de suporte é conferido no `public` a cada requisição (ADR 0013, item 2).
        from comum.autenticacao import registrar_suporte

        from .services import conferir_acesso_suporte

        registrar_suporte(conferir_acesso_suporte)
