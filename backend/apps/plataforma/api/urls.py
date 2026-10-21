"""Rotas da plataforma. `urls_plataforma` no host admin (public); `urls_empresa` no da empresa."""

from django.urls import URLPattern, path

from . import assinatura, auditoria, suporte
from .views import AssinaturaView, EmpresaDetalheView, EmpresasView, PlanosView

urls_plataforma: list[URLPattern] = [
    path("planos/", PlanosView.as_view(), name="plataforma-planos"),
    path("empresas/", EmpresasView.as_view(), name="plataforma-empresas"),
    path("empresas/<int:pk>/", EmpresaDetalheView.as_view(), name="plataforma-empresa"),
    path(
        "empresas/<int:pk>/acessos-suporte/",
        suporte.AbrirAcessoSuporteView.as_view(),
        name="plataforma-empresa-acessos-suporte",
    ),
    path(
        "auditoria/eventos/",
        auditoria.EventosDaPlataformaView.as_view(),
        name="plataforma-auditoria-eventos",
    ),
    path(
        "auditoria/eventos/<int:pk>/",
        auditoria.EventoDaPlataformaView.as_view(),
        name="plataforma-auditoria-evento",
    ),
]

urls_empresa: list[URLPattern] = [
    path("assinatura/", AssinaturaView.as_view(), name="assinatura"),
    path("implantacao/", assinatura.ImplantacaoView.as_view(), name="implantacao"),
    path(
        "assinatura/planos/",
        assinatura.PlanosDaAssinaturaView.as_view(),
        name="assinatura-planos",
    ),
    path(
        "assinatura/mudanca-plano/simular/",
        assinatura.SimularMudancaPlanoView.as_view(),
        name="assinatura-mudanca-plano-simular",
    ),
    path(
        "assinatura/mudanca-plano/",
        assinatura.MudancaPlanoView.as_view(),
        name="assinatura-mudanca-plano",
    ),
    path(
        "assinatura/forma-pagamento/",
        assinatura.FormaPagamentoView.as_view(),
        name="assinatura-forma-pagamento",
    ),
    path("assinatura/faturas/", assinatura.FaturasView.as_view(), name="assinatura-faturas"),
    path(
        "assinatura/faturas/<str:codigo>/",
        assinatura.FaturaView.as_view(),
        name="assinatura-fatura",
    ),
    path(
        "assinatura/faturas/<str:codigo>/pagar/",
        assinatura.PagarFaturaView.as_view(),
        name="assinatura-fatura-pagar",
    ),
    path(
        "assinatura/dados-fiscais/",
        assinatura.DadosFiscaisView.as_view(),
        name="assinatura-dados-fiscais",
    ),
    path(
        "assinatura/cancelamento/",
        assinatura.CancelamentoView.as_view(),
        name="assinatura-cancelamento",
    ),
    path("assinatura/pausa/", assinatura.PausaView.as_view(), name="assinatura-pausa"),
    path("suporte/", suporte.SuporteView.as_view(), name="suporte"),
    path("suporte/bloquear/", suporte.BloquearSuporteView.as_view(), name="suporte-bloquear"),
    path("suporte/liberar/", suporte.LiberarSuporteView.as_view(), name="suporte-liberar"),
    path(
        "suporte/acessos/<int:pk>/revogar/",
        suporte.RevogarAcessoSuporteView.as_view(),
        name="suporte-acesso-revogar",
    ),
]
