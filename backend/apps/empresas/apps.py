from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    name = "apps.empresas"
    label = "empresas"

    def ready(self) -> None:
        from comum.empresa import registrar_exige_2fa_todos, registrar_marca

        from . import eventos, selectors  # noqa: F401 - eventos registra os assinantes

        registrar_exige_2fa_todos(selectors.exige_2fa_todos)  # USR-02
        registrar_marca(selectors.marca)  # docs/api/empresas.md
