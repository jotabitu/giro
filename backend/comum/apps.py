from django.apps import AppConfig


class ComumConfig(AppConfig):
    name = "comum"
    label = "comum"

    def ready(self) -> None:
        # Sinais do Celery: só disparam no worker (e nas tarefas eager dos testes).
        # Registra as autenticações no OpenAPI.
        from comum import openapi  # noqa: F401
        from comum.worker import conectar

        conectar()

        # ADR 0021: aviso no `check` e ao subir (backend, worker e beat passam por aqui).
        from django.core.checks import register

        from comum.ambiente import avisar_ao_subir, conferir_data_de_referencia

        register(conferir_data_de_referencia)
        avisar_ao_subir()
