from django.apps import AppConfig


class AppExemploConfig(AppConfig):
    """Instalado só em config.settings.test, como app de empresa."""

    name = "tests.app_exemplo"
    label = "exemplo"
