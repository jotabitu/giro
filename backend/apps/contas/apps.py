from django.apps import AppConfig


class ContasConfig(AppConfig):
    name = "apps.contas"
    label = "contas"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_contador
        from comum.permissoes import registrar_pode

        from . import eventos, selectors, sessoes

        registrar_contador("usuarios", eventos.contar_usuarios)
        registrar_pode(selectors.pode)  # USR-03, USR-05
        sessoes.registrar()  # ADR 0014, item 1
