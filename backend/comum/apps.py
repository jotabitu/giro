from django.apps import AppConfig


class ComumConfig(AppConfig):
    name = "comum"
    label = "comum"

    def ready(self) -> None:
        # Sinais do Celery: só disparam no worker (e nas tarefas eager dos testes).
        from comum.worker import conectar

        conectar()
