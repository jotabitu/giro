from django.apps import AppConfig


class ContasConfig(AppConfig):
    name = "apps.contas"
    label = "contas"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_contador

        from . import eventos

        registrar_contador("usuarios", eventos.contar_usuarios)
