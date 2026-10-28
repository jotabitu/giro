"""T-405 · Token de suporte com a data simulada (ADR 0021; PLT-07).

Com `GIRO_DATA_REFERENCIA` ligada, o `fim` do acesso sai do relógio do Giro e o simplejwt confere
o `exp` pelo relógio real. O `exp` leva só o tempo que falta até o `fim`, como nos tokens do
login; a duração do acesso continua pelo relógio do Giro.
"""

from datetime import timedelta

from django.db import connection
from django.test import override_settings
from django.utils import timezone
from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import aware_utcnow

from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from apps.plataforma.services import abrir_acesso_suporte
from comum import relogio
from comum.autenticacao import TokenSuporte

HOST = "empresa-a.localhost"
EU = "/api/auth/eu/"


def _abrir(empresa_a, duracao_minutos: int = 30) -> tuple[str, int]:
    with schema_context("public"):
        diego = Usuario.objects.create_user(
            "diego@girolocadoras.com.br",
            "senha-forte-123",
            nome="Diego Santos",
            funcao_plataforma="suporte",
        )
        acesso, token = abrir_acesso_suporte(
            Empresa.objects.get(pk=empresa_a.pk),
            diego,
            motivo="Chamado #1042",
            duracao_minutos=duracao_minutos,
            permissao="ver",
        )
    connection.set_tenant(empresa_a)
    return token, acesso.pk


def _eu(empresa_a, token: str):
    api = APIClient(HTTP_HOST=HOST, REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="pytest")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    resposta = api.get(EU)
    connection.set_tenant(empresa_a)
    return resposta


def test_t405_plt_07_entra_com_o_token_de_suporte_com_a_data_simulada(empresa_a):
    simulada = timezone.localdate() - timedelta(days=21)
    with override_settings(GIRO_DATA_REFERENCIA=simulada):
        token, acesso_id = _abrir(empresa_a)
        resposta = _eu(empresa_a, token)
        assert resposta.status_code == 200, resposta.json()
        assert resposta.json()["suporte"]["acesso_suporte_id"] == acesso_id
        assert timezone.localdate(relogio.agora()) == simulada


def test_t405_plt_07_exp_leva_a_duracao_do_acesso(empresa_a):
    simulada = timezone.localdate() - timedelta(days=21)
    with override_settings(GIRO_DATA_REFERENCIA=simulada):
        token, _ = _abrir(empresa_a, duracao_minutos=15)
    exp = TokenSuporte(token)["exp"]  # type: ignore[arg-type]
    restante = exp - aware_utcnow().timestamp()
    assert 14 * 60 < restante <= 15 * 60
