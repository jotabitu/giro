from django.apps import AppConfig


class ContasConfig(AppConfig):
    name = "apps.contas"
    label = "contas"

    def ready(self) -> None:
        from apps.plataforma.services import registrar_contador
        from comum.auditoria import registrar_consulta
        from comum.permissoes import registrar_pode

        from . import eventos, selectors, sessoes

        registrar_contador("usuarios", eventos.contar_usuarios)
        registrar_pode(selectors.pode)  # USR-03, USR-05
        sessoes.registrar()  # ADR 0014, item 1
        registrar_consulta("emails_de_usuarios", selectors.emails_de_usuarios)  # T-018
