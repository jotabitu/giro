"""Rotas de `contas`. `urls_plataforma`: login e convite da equipe, no host admin (public)."""

from django.urls import URLPattern, path

from . import plataforma

urls_plataforma: list[URLPattern] = [
    path("auth/entrar/", plataforma.EntrarView.as_view(), name="plataforma-entrar"),
    path(
        "auth/2fa/configurar/",
        plataforma.Configurar2FAView.as_view(),
        name="plataforma-2fa-configurar",
    ),
    path(
        "auth/2fa/verificar/",
        plataforma.Verificar2FAView.as_view(),
        name="plataforma-2fa-verificar",
    ),
    path("auth/renovar/", plataforma.RenovarView.as_view(), name="plataforma-renovar"),
    path("auth/sair/", plataforma.SairView.as_view(), name="plataforma-sair"),
    path("auth/eu/", plataforma.EuView.as_view(), name="plataforma-eu"),
    path("convites/<str:token>/", plataforma.ConviteView.as_view(), name="plataforma-convite"),
    path(
        "convites/<str:token>/aceitar/",
        plataforma.AceitarConviteView.as_view(),
        name="plataforma-convite-aceitar",
    ),
]
