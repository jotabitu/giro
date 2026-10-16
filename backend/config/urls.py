"""Rotas do schema da empresa (<subdominio>.<DOMINIO_BASE>).

Sem Django Admin aqui: o admin só existe no schema público, com 2FA (achado 4 da T-032).
"""

from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.contas.api.urls import urls_empresa as urls_contas
from apps.plataforma.api.urls import urls_empresa as urls_assinatura
from comum.ambiente import AmbienteView
from comum.arquivos_dev import servir as servir_arquivo_falso

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/", include(urls_contas)),
    path("api/", include(urls_assinatura)),
    path("api/", include("apps.filiais.api.urls")),
    path("api/", include("apps.veiculos.api.urls")),
    path("api/", include("apps.clientes.api.urls")),
    path("api/", include("apps.aprovacoes.api.urls")),
    path("api/", include("apps.locacoes.api.urls")),
    path("api/", include("apps.contratos.api.urls")),
    path("api/", include("apps.vistorias.api.urls")),
    path("api/", include("apps.movimentacoes.api.urls")),
    path("api/", include("apps.financeiro.api.urls")),
    path("api/", include("apps.relatorios.api.urls")),
    path("api/", include("apps.empresas.api.urls")),
    path("api/", include("apps.auditoria.api.urls")),
    path("api/", include("apps.importacao.api.urls")),
    path("api/ambiente/", AmbienteView.as_view(), name="ambiente"),
]

# Documentação da API só onde EXPOR_DOCUMENTACAO_DA_API permite (fechada em produção).
if settings.EXPOR_DOCUMENTACAO_DA_API:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]

# Só no desenvolvimento (T-210): as fotos do armazenamento "falso" abrem na mesma origem da tela.
if settings.GIRO_ARQUIVOS_FALSOS_BASE.startswith("/"):
    urlpatterns += [path("api/arquivos-dev/<path:caminho>", servir_arquivo_falso)]
