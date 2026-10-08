"""Token preso à empresa (ADR 0008, item 5; ADR 0013, item 1)."""

import pytest
from django.db import connection
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from comum.autenticacao import JWTDaEmpresa, emitir_tokens


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
    Usuario.objects.filter(pk=usuario.pk).update(ativo=False)
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
