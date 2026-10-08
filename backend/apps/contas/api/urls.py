"""Rotas de `contas`.

`urls_plataforma`: login e convite da equipe, no host admin (public).
`urls_empresa`: login, 2 etapas, sessões, `eu` e senha, no host da empresa (T-011).
"""

from django.urls import URLPattern, path

from . import acesso, plataforma

urls_empresa: list[URLPattern] = [
    path("auth/entrar/", acesso.EntrarView.as_view(), name="entrar"),
    path("auth/2fa/verificar/", acesso.Verificar2FAView.as_view(), name="2fa-verificar"),
    path("auth/2fa/configurar/", acesso.Configurar2FAView.as_view(), name="2fa-configurar"),
    path("auth/2fa/ativar/", acesso.Ativar2FAView.as_view(), name="2fa-ativar"),
    path("auth/2fa/desativar/", acesso.Desativar2FAView.as_view(), name="2fa-desativar"),
    path(
        "auth/2fa/codigos-recuperacao/",
        acesso.CodigosRecuperacaoView.as_view(),
        name="2fa-codigos-recuperacao",
    ),
    path("auth/renovar/", acesso.RenovarView.as_view(), name="renovar"),
    path("auth/sair/", acesso.SairView.as_view(), name="sair"),
    path("auth/eu/", acesso.EuView.as_view(), name="eu"),
    path("auth/sessoes/", acesso.SessoesView.as_view(), name="sessoes"),
    path(
        "auth/sessoes/encerrar-outras/",
        acesso.EncerrarOutrasSessoesView.as_view(),
        name="sessoes-encerrar-outras",
    ),
    path(
        "auth/sessoes/<int:id>/encerrar/",
        acesso.EncerrarSessaoView.as_view(),
        name="sessao-encerrar",
    ),
    path("auth/senha/trocar/", acesso.TrocarSenhaView.as_view(), name="senha-trocar"),
    path("auth/senha/esqueci/", acesso.EsqueciSenhaView.as_view(), name="senha-esqueci"),
    path("auth/senha/redefinir/", acesso.RedefinirSenhaView.as_view(), name="senha-redefinir"),
]

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
