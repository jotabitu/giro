"""T-011 · Achados de segurança que entraram com as sessões e as 2 etapas da empresa.

P-05, P-07 e P-08 da revisão da T-010 (`docs/seguranca/2026-10-08-codigo-t010.md`), R-06 da
revisão da T-033 (`docs/seguranca/2026-10-08-codigo-t033.md`) e os testes obrigatórios da
ADR 0014 que dependem de sessão.
"""

import re
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import tenant_context
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.auditoria.models import EventoAuditoria
from apps.contas import dois_fatores, sessoes
from apps.contas.models import Autenticador, CodigoRecuperacao, MotivoRevogacao, Sessao, Usuario
from apps.empresas.models import ConfiguracaoEmpresa
from comum import cripto
from comum.auditoria import Categoria, registrar_evento

from .conftest import HOST_PLATAFORMA, cliente, codigo_atual
from .test_t011_contas import EU, FRONTEND, RENOVAR, SENHA, Moto, _get, _post


@pytest.fixture
def moto(empresa_a, relogio_jwt) -> Moto:
    return Moto(empresa_a)


# --- P-05: primeiro autenticador só no prazo do convite ---


def test_plt_08_configurar_2fa_recusado_depois_da_validade_do_convite(publico, relogio):
    relogio.em("2026-10-07 10:00")
    saida = StringIO()
    call_command(
        "convidar_equipe_plataforma",
        "larissa@girolocadoras.com.br",
        "suporte",
        "--nome",
        "Larissa Melo",
        stdout=saida,
    )
    token = re.search(r"/convite#(\S+)", saida.getvalue()).group(1)  # type: ignore[union-attr]
    api = cliente(HOST_PLATAFORMA)
    relogio.em("2026-10-13 10:00")
    aceito = api.post(
        "/api/plataforma/convites/aceitar/", {"token": token, "senha": SENHA}, format="json"
    )
    pre = cliente(HOST_PLATAFORMA, aceito.json()["token_pre_2fa"])

    # Meses depois a senha sozinha não cadastra mais um autenticador: precisa de convite novo.
    relogio.em("2026-10-15 10:00")
    entrar = api.post(
        "/api/plataforma/auth/entrar/",
        {"email": "larissa@girolocadoras.com.br", "senha": SENHA},
        format="json",
    )
    assert entrar.status_code == 403
    assert entrar.json()["codigo"] == "convite_expirado"
    configurar = pre.post("/api/plataforma/auth/2fa/configurar/")
    assert configurar.status_code == 403
    assert not Autenticador.objects.filter(user__email="larissa@girolocadoras.com.br").exists()


def test_usr_02_configurar_2fa_recusado_depois_da_validade_do_convite(moto, relogio):
    relogio.em("2026-10-15 10:00")  # o convite de Lúcia venceu em 14 out
    resposta = moto.entrar("Lúcia")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "convite_expirado"


# --- P-07: refresh reusado derruba a sessão ---


def test_usr_04_refresh_reusado_revoga_a_sessao(moto):
    api = moto.logar("Bruna")
    roubado = api.cookies["__Host-giro_refresh"].value
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 200
    vigente = api.cookies["__Host-giro_refresh"].value

    api.cookies["__Host-giro_refresh"] = roubado
    reuso = _post(api, RENOVAR, moto.empresa, **FRONTEND)
    assert reuso.status_code == 401
    assert reuso.json()["codigo"] == "sessao_encerrada"
    sessao = Sessao.objects.get(usuario=moto.pessoas["Bruna"])
    assert sessao.motivo_revogacao == MotivoRevogacao.REFRESH_REUSADO
    # A família inteira cai: o refresh vigente e o access também.
    api.cookies["__Host-giro_refresh"] = vigente
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 401
    assert _get(api, EU, moto.empresa).json()["codigo"] == "sessao_encerrada"
    evento = EventoAuditoria.objects.get(acao="sessao.encerrar")
    assert evento.categoria == "seguranca"


def test_renovar_com_cookie_invalido_responde_401(moto):
    api = moto.cliente()
    api.cookies["__Host-giro_refresh"] = "isto-nao-e-um-jwt"
    resposta = _post(api, RENOVAR, moto.empresa, **FRONTEND)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


# --- ADR 0014: revogar derruba o access na requisição seguinte ---


def test_usr_04_revogar_as_sessoes_derruba_o_access_na_proxima_requisicao(moto):
    api = moto.logar("Bruna")
    assert _get(api, EU, moto.empresa).status_code == 200  # a sessão fica no cache
    sessoes.revogar_todas(moto.pessoas["Bruna"], MotivoRevogacao.USUARIO_DESATIVADO)
    resposta = _get(api, EU, moto.empresa)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "sessao_encerrada"
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 401


def test_aud_01_troca_de_senha_nao_grava_hash(moto):
    api = moto.logar("Bruna")
    hash_antigo = Usuario.objects.get(pk=moto.pessoas["Bruna"].pk).password
    _post(
        api,
        "/api/auth/senha/trocar/",
        moto.empresa,
        {"senha_atual": SENHA, "senha_nova": "girafa-azul-2027"},
    )
    evento = EventoAuditoria.objects.get(acao="usuario.trocar_senha")
    assert evento.depois == {"password": {"alterado": True}}
    hash_novo = Usuario.objects.get(pk=moto.pessoas["Bruna"].pk).password
    assert hash_antigo not in str(evento.antes) + str(evento.depois)
    assert hash_novo not in str(evento.antes) + str(evento.depois)


def test_sessao_da_empresa_a_nao_vale_na_empresa_b(moto, empresa_b):
    api = moto.logar("Bruna")
    token = api._credentials["HTTP_AUTHORIZATION"]
    outra = cliente("empresa-b.localhost")
    outra.credentials(HTTP_AUTHORIZATION=token)
    resposta = outra.get(EU)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"
    connection.set_tenant(empresa_b)
    assert not Sessao.objects.exists()


# --- P-08: segredos das 2 etapas fora do banco em claro ---


def test_plt_08_semente_e_codigos_de_recuperacao_nao_ficam_em_claro(moto):
    mariana = moto.pessoas["Mariana"]
    dispositivo = moto.autenticador["Mariana"]
    semente = dispositivo.chave_claro()
    codigos = dois_fatores.gerar_codigos_recuperacao(mariana)
    with connection.cursor() as cursor:
        cursor.execute("SELECT chave FROM contas_autenticador WHERE id = %s", [dispositivo.pk])
        (gravada,) = cursor.fetchone()
        cursor.execute(
            "SELECT codigo_hash FROM contas_codigorecuperacao WHERE usuario_id = %s", [mariana.pk]
        )
        hashes = [linha[0] for linha in cursor.fetchall()]
    assert gravada.startswith("v1:") and semente not in gravada
    assert len(hashes) == 8
    for codigo in codigos:
        assert all(codigo not in h and codigo.replace("-", "") not in h for h in hashes)

    # O cifrado copiado para outro autenticador não decifra (dado associado com a linha).
    outro = Autenticador(user=moto.pessoas["Bruna"], name="autenticador", confirmed=True)
    outro.chave = gravada
    with pytest.raises(cripto.ErroDeCifra):
        outro.chave_claro()

    # Código de recuperação vale uma vez só, pelo hash.
    assert dois_fatores.conferir_codigo(mariana, codigo_recuperacao=codigos[0]) is not None
    assert dois_fatores.conferir_codigo(mariana, codigo_recuperacao=codigos[0]) is None
    assert CodigoRecuperacao.objects.filter(usuario=mariana, usado_em__isnull=True).count() == 7
    assert codigo_atual(dispositivo).isdigit()


# --- R-06: nada fora da classificação entra na auditoria ---


def test_aud_01_evento_sem_objeto_nao_leva_antes_nem_depois(empresa_a):
    with pytest.raises(ValueError, match="sem objeto"):
        registrar_evento("teste", Categoria.SEGURANCA, depois={"token": "segredo"})


def test_aud_01_model_de_terceiro_nao_entra_na_auditoria(moto):
    moto.logar("Bruna")
    token = OutstandingToken.objects.first()
    with pytest.raises(ValueError, match="não é model do Giro"):
        registrar_evento("teste", Categoria.SEGURANCA, objeto=token)


# --- ConfiguracaoEmpresa nasce com a empresa (USR-02) ---


def test_usr_02_configuracao_nasce_com_a_empresa(criar_empresa):
    empresa = criar_empresa()
    with tenant_context(empresa):
        configuracao = ConfiguracaoEmpresa.objects.get()
        assert configuracao.exige_2fa_todos is False
