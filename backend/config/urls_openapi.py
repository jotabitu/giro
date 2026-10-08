"""Só para gerar o contrato (`spectacular --urlconf config.urls_openapi`): as rotas da empresa e
as da plataforma num arquivo só. Não é servido em nenhum host.
"""

from django.urls import URLPattern, URLResolver

from config import urls, urls_publico

urlpatterns: list[URLPattern | URLResolver] = [*urls.urlpatterns, *urls_publico.urlpatterns]
