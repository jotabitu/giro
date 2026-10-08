"""Token preso à empresa (ADR 0008, item 5; ADR 0013, item 1)."""

import pytest
from django.db import connection
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from comum.autenticacao import (
    AMR_SENHA_E_CODIGO,
    COOKIE_REFRESH,
    JWTDaEmpresa,
    emitir_pre_2fa,
    emitir_tokens,
)
from comum.erros import NaoAutenticado
from comum.estados import transicionar


def _autenticar(token: str):
    request = APIRequestFactory().get("/api/", HTTP_AUTHORIZATION=f"Bearer {token}")
    return JWTDaEmpresa().authenticate(request)


def _criar(email: str, perfil: str = "vendedor") -> Usuario:
    return Usuario.objects.create_user(email, "senha-forte-123", nome=email, perfil=perfil)


def test_token_vale_na_propria_empresa(empresa_a):
    usuario = _criar("carla@a.com")
    token = str(emitir_tokens(usuario).access_token)
    resultado = _autenticar(token)
    assert resultado is not None
    assert resultado[0] == usuario


def test_token_leva_schema_e_empresa_id(empresa_a):
    usuario = _criar("carla@a.com")
    access = emitir_tokens(usuario).access_token
    assert access["schema"] == "empresa_a"
    assert access["empresa_id"] == empresa_a.pk


def test_token_da_empresa_a_recusado_na_b_mesmo_com_o_mesmo_user_id(empresa_a):
    usuario_a = _criar("carla@a.com")
    token_a = str(emitir_tokens(usuario_a).access_token)

    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    # Na B existe outra pessoa com o mesmo id: o token não pode virar essa pessoa.
    Usuario.objects.create_user(
        "outra@b.com", "x", nome="Outra", perfil="administrador", id=usuario_a.pk
    )

    with pytest.raises(AuthenticationFailed) as erro:
        _autenticar(token_a)
    assert erro.value.get_codes() == "nao_autenticado"


def test_token_sem_empresa_id_recusado(empresa_a):
    usuario = _criar("carla@a.com")
    access = AccessToken.for_user(usuario)
    access["schema"] = "empresa_a"
    with pytest.raises(AuthenticationFailed):
        _autenticar(str(access))


def test_token_sem_claim_de_empresa_recusado(empresa_a):
    usuario = _criar("carla@a.com")
    with pytest.raises(AuthenticationFailed):
        _autenticar(str(AccessToken.for_user(usuario)))


def test_usr_04_token_de_usuario_desativado_recusado(empresa_a):
    usuario = _criar("carla@a.com")
    token = str(emitir_tokens(usuario).access_token)
    transicionar(usuario, "desativado")
    with pytest.raises(AuthenticationFailed):
        _autenticar(token)


def test_refresh_nao_serve_como_access(empresa_a):
    usuario = _criar("carla@a.com")
    with pytest.raises(Exception):  # noqa: B017 - InvalidToken do simplejwt
        _autenticar(str(emitir_tokens(usuario)))


def test_sem_empresa_na_conexao_nao_emite_token(publico):
    connection.tenant = None
    usuario = Usuario(email="x@giro.com", nome="X", funcao_plataforma="dono")
    try:
        with pytest.raises(RuntimeError):
            emitir_tokens(usuario)
    finally:
        connection.set_schema_to_public()


# --- Plataforma: 2 etapas, cookie do refresh, renovar e sair (ADR 0013, itens 3 e 5) ---


@pytest.fixture
def plataforma(publico):
    """Conexão no public com a linha da plataforma, como no host admin (empresa_id dos tokens)."""
    connection.set_tenant(Empresa.objects.get(schema_name="public"))
    yield
    connection.set_schema_to_public()


def _dono_da_plataforma() -> Usuario:
    return Usuario.objects.create_user(
        "dono@giro.com", "senha-forte-123", nome="Dono", funcao_plataforma="dono"
    )


def test_plt_08_token_da_plataforma_sem_otp_recusado(plataforma):
    dono = _dono_da_plataforma()
    with pytest.raises(NaoAutenticado) as erro:
        _autenticar(str(emitir_tokens(dono).access_token))
    assert erro.value.codigo == "2fa_obrigatorio"
    resultado = _autenticar(str(emitir_tokens(dono, amr=AMR_SENHA_E_CODIGO).access_token))
    assert resultado is not None and resultado[0] == dono


def test_token_pre_2fa_nao_serve_como_access(plataforma):
    dono = _dono_da_plataforma()
    with pytest.raises(Exception):  # noqa: B017 - InvalidToken do simplejwt
        _autenticar(str(emitir_pre_2fa(dono)))


def _cliente_com_cookie(refresh: str) -> APIClient:
    api = APIClient(HTTP_HOST="admin.localhost", HTTP_X_REQUESTED_WITH="giro")
    api.cookies[COOKIE_REFRESH] = refresh
    return api


def test_renovar_troca_o_refresh_e_poe_o_anterior_na_blacklist(plataforma):
    refresh = str(emitir_tokens(_dono_da_plataforma(), amr=AMR_SENHA_E_CODIGO))
    api = _cliente_com_cookie(refresh)
    resposta = api.post("/api/plataforma/auth/renovar/")
    assert resposta.status_code == 200
    assert resposta.json()["access"]
    assert resposta.cookies[COOKIE_REFRESH].value != refresh
    de_novo = _cliente_com_cookie(refresh).post("/api/plataforma/auth/renovar/")
    assert de_novo.status_code == 401


def test_renovar_exige_o_cabecalho_do_frontend(plataforma):
    refresh = str(emitir_tokens(_dono_da_plataforma(), amr=AMR_SENHA_E_CODIGO))
    api = APIClient(HTTP_HOST="admin.localhost")
    api.cookies[COOKIE_REFRESH] = refresh
    assert api.post("/api/plataforma/auth/renovar/").status_code == 403


def test_refresh_da_empresa_recusado_na_plataforma_sem_gravar_nada(empresa_a):
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    refresh = str(emitir_tokens(_criar("carla@a.com")))
    connection.set_schema_to_public()
    antes = BlacklistedToken.objects.count()
    resposta = _cliente_com_cookie(refresh).post("/api/plataforma/auth/renovar/")
    connection.set_schema_to_public()
    assert resposta.status_code == 401
    assert BlacklistedToken.objects.count() == antes


def test_sair_apaga_o_cookie_e_bloqueia_o_refresh(plataforma):
    refresh = str(emitir_tokens(_dono_da_plataforma(), amr=AMR_SENHA_E_CODIGO))
    resposta = _cliente_com_cookie(refresh).post("/api/plataforma/auth/sair/")
    assert resposta.status_code == 204
    assert resposta.cookies[COOKIE_REFRESH].value == ""
    assert _cliente_com_cookie(refresh).post("/api/plataforma/auth/renovar/").status_code == 401
