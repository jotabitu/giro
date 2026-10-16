"""T-011 · Contas, perfis, 2 etapas, convite (critérios em docs/qa/criterios/T-011.md).

A T-011 entregou login, sessões, 2 etapas, `eu` e senha; a T-069, usuários e convite; a T-070, o
modo suporte (divisão combinada com o Orquestrador em 09/10).

Roda na `empresa_a` (host `empresa-a.localhost`), com o nome de exibição "Moto Rápida" e as
pessoas do seed.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.auditoria.models import EventoAuditoria
from apps.contas import selectors, services
from apps.contas.models import Autenticador, Convite, PermissaoExtra, StatusUsuario, Usuario
from apps.empresas.services import definir_exige_2fa_todos
from apps.filiais.models import UsuarioFilial
from apps.plataforma.models import AcessoSuporte, UsoEmpresa
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from integracoes.whatsapp.falso import caixa_de_saida

from .conftest import (
    HOST_PLATAFORMA,
    autenticador_confirmado,
    cliente,
    codigo_atual,
    entrar,
    liberar_codigo,
)

HOST = "empresa-a.localhost"
SENHA = "girafa-azul-2026"
FRONTEND = {"HTTP_X_REQUESTED_WITH": "giro"}
IP_DE_CASA = "177.12.34.56"

ENTRAR = "/api/auth/entrar/"
VERIFICAR = "/api/auth/2fa/verificar/"
CONFIGURAR = "/api/auth/2fa/configurar/"
RENOVAR = "/api/auth/renovar/"
SAIR = "/api/auth/sair/"
EU = "/api/auth/eu/"
SESSOES = "/api/auth/sessoes/"

PESSOAS = {
    # nome: (e-mail, perfil, status)
    "Mariana": ("mariana@motorapida.com.br", "administrador", StatusUsuario.ATIVO),
    "Rodrigo": ("rodrigo@motorapida.com.br", "gerente", StatusUsuario.ATIVO),
    "Bruna": ("bruna@motorapida.com.br", "vendedor", StatusUsuario.ATIVO),
    "João": ("joao@motorapida.com.br", "vistoriador", StatusUsuario.CONVITE_PENDENTE),
    "Lúcia": ("lucia@motorapida.com.br", "financeiro", StatusUsuario.CONVITE_PENDENTE),
    "Felipe": ("felipe@motorapida.com.br", "vendedor", StatusUsuario.DESATIVADO),
}


def _em_sp(texto: str) -> datetime:
    return datetime.fromisoformat(texto).astimezone(UTC)


class Moto:
    """A Moto Rápida com as 6 pessoas do seed (tela `Admin-Usuarios`)."""

    def __init__(self, empresa: Any) -> None:
        empresa.nome_exibicao = "Moto Rápida"
        empresa.save(update_fields=["nome_exibicao"])
        self.empresa = empresa
        self.pessoas: dict[str, Usuario] = {}
        for nome, (email, perfil, status) in PESSOAS.items():
            usuario = Usuario.objects.create_user(
                email, SENHA, nome=nome, perfil=perfil, status=status
            )
            self.pessoas[nome] = usuario
        # João ainda não aceitou: sem senha. Lúcia aceitou em 07 out e falta o código.
        self.pessoas["João"].set_unusable_password()
        self.pessoas["João"].save()
        Convite.objects.create(
            usuario=self.pessoas["João"],
            token_hash="a" * 64,
            expira_em=_em_sp("2026-10-14T23:59:59-03:00"),
        )
        Convite.objects.create(
            usuario=self.pessoas["Lúcia"],
            token_hash="b" * 64,
            expira_em=_em_sp("2026-10-14T23:59:59-03:00"),
            aceito_em=_em_sp("2026-10-07T09:00:00-03:00"),
        )
        self.autenticador = {
            "Mariana": autenticador_confirmado(self.pessoas["Mariana"]),
            "Rodrigo": autenticador_confirmado(self.pessoas["Rodrigo"]),
        }

    @staticmethod
    def cliente(ip: str = IP_DE_CASA) -> APIClient:
        return APIClient(
            HTTP_HOST=HOST,
            REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR=ip,
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 Safari/537.36",
        )

    def email(self, nome: str) -> str:
        return PESSOAS[nome][0]

    def entrar(self, nome: str, senha: str = SENHA, api: APIClient | None = None, **corpo: Any):
        api = api or self.cliente()
        resposta = api.post(
            ENTRAR, {"email": self.email(nome), "senha": senha, **corpo}, format="json"
        )
        connection.set_tenant(self.empresa)
        return resposta

    def codigo(self, nome: str) -> str:
        liberar_codigo(self.autenticador[nome])
        return codigo_atual(self.autenticador[nome])

    def logar(self, nome: str, aparelho: str = "desktop", ip: str = IP_DE_CASA) -> APIClient:
        """Login completo pela API. Devolve o cliente com o access e o cookie do refresh."""
        api = self.cliente(ip)
        resposta = self.entrar(nome, api=api, aparelho=aparelho)
        assert resposta.status_code == 200, resposta.json()
        corpo = resposta.json()
        if corpo["etapa"] == "verificar_2fa":
            pre = corpo["token_pre_2fa"]
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {pre}")
            resposta = api.post(VERIFICAR, {"codigo": self.codigo(nome)}, format="json")
            assert resposta.status_code == 200, resposta.json()
            corpo = resposta.json()
        assert corpo["etapa"] == "pronto"
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {corpo['access']}")
        connection.set_tenant(self.empresa)
        return api

    def eventos(self, acao: str) -> Any:
        return EventoAuditoria.objects.filter(acao=acao).order_by("id")


@pytest.fixture
def moto(empresa_a, relogio_jwt) -> Moto:
    return Moto(empresa_a)


USUARIOS = "/api/usuarios/"
CONSULTAR = "/api/convites/consultar/"
ACEITAR = "/api/convites/aceitar/"


@pytest.fixture
def adm(moto, planos) -> Moto:
    """A Moto Rápida da tela `Admin-Usuarios`: plano Profissional (5 de 10 usuários) e a Filial
    Centro com Rodrigo, Bruna, João e Felipe. Mariana e Lúcia veem todas as filiais."""
    from apps.filiais.services import criar_filial, definir_filiais_do_usuario

    from .test_t012_filiais import CENTRO

    moto.empresa.plano = planos["Profissional"]
    moto.empresa.save(update_fields=["plano"])
    UsoEmpresa.objects.update_or_create(
        empresa=moto.empresa, defaults={"usuarios": 5, "filiais": 0}
    )
    moto.centro = criar_filial(CENTRO, moto.pessoas["Mariana"])
    for nome in ("Rodrigo", "Bruna", "João", "Felipe"):
        definir_filiais_do_usuario(moto.pessoas[nome].pk, [moto.centro.pk])
    caixa_de_saida.clear()
    return moto


def _uso_de_usuarios(moto: Moto) -> int:
    return int(UsoEmpresa.objects.get(empresa=moto.empresa).usuarios)


def _token_do_convite(mensagem: Any) -> str:
    achado = re.search(r"/convite#(\S+)", mensagem.body)
    assert achado, mensagem.body
    return achado.group(1)


def _api_de(moto: Moto, nome: str) -> APIClient:
    """Token de quem já passou pelas 2 etapas, mesmo sem login pela API (João e Lúcia)."""
    from comum.estados import transicionar

    usuario = Usuario.objects.get(pk=moto.pessoas[nome].pk)
    transicionar(usuario, StatusUsuario.ATIVO)
    refresh = emitir_tokens(usuario, AMR_SENHA_E_CODIGO)
    api = moto.cliente()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api


def _get(api: APIClient, rota: str, empresa: Any) -> Any:
    resposta = api.get(rota)
    connection.set_tenant(empresa)
    return resposta


def _post(api: APIClient, rota: str, empresa: Any, corpo: Any = None, **extra: Any) -> Any:
    resposta = api.post(rota, corpo or {}, format="json", **extra)
    connection.set_tenant(empresa)
    return resposta


# --- Lista e plano (T-069) ---


def test_usr_01_ca_011_01_contagens_do_seed(adm):
    api = adm.logar("Mariana")
    corpo = _get(api, USUARIOS, adm.empresa).json()
    assert corpo["contagens"] == {"todos": 6, "ativos": 3, "convites": 2, "desativados": 1}
    assert corpo["plano"] == {"usado": 5, "limite": 10, "aviso": False, "bloqueado": False}
    pessoas = {item["nome"]: item for item in corpo["resultados"]}
    assert set(pessoas) == set(PESSOAS)
    assert (pessoas["Mariana"]["eu"], pessoas["Mariana"]["todas_filiais"]) == (True, True)
    assert pessoas["Lúcia"]["todas_filiais"] is True
    assert pessoas["Rodrigo"]["filiais"] == [{"id": adm.centro.pk, "nome": "Filial Centro"}]
    assert pessoas["Rodrigo"]["dois_fatores_ativo"] is True
    assert pessoas["Bruna"]["dois_fatores_ativo"] is False
    assert pessoas["João"]["convite_expira_em"] == "2026-10-15T02:59:59Z"  # 14 out, 23:59:59
    assert pessoas["Lúcia"]["convite_expira_em"] is None  # já aceitou
    assert pessoas["Mariana"]["ultimo_acesso_em"] is not None
    assert "proximo" in corpo and "anterior" in corpo

    desativados = _get(api, f"{USUARIOS}?situacao=desativados", adm.empresa).json()
    assert [u["nome"] for u in desativados["resultados"]] == ["Felipe"]
    assert desativados["plano"]["usado"] == 5  # Felipe não conta no plano
    vendedores = _get(api, f"{USUARIOS}?perfil=vendedor&busca=bru", adm.empresa).json()
    assert [u["nome"] for u in vendedores["resultados"]] == ["Bruna"]
    da_centro = _get(api, f"{USUARIOS}?filial={adm.centro.pk}", adm.empresa).json()
    assert len(da_centro["resultados"]) == 6  # 4 ligados e quem vê todas


def test_usr_01_ca_011_02_so_o_administrador_administra_usuarios(adm):
    rodrigo = adm.pessoas["Rodrigo"].pk
    rotas = [
        ("get", USUARIOS, None),
        ("get", f"{USUARIOS}{rodrigo}/", None),
        ("get", f"{USUARIOS}{rodrigo}/sessoes/", None),
        ("post", f"{USUARIOS}convites/", {"email": "x@motorapida.com.br", "perfil": "vendedor"}),
        ("patch", f"{USUARIOS}{rodrigo}/", {"perfil": "vendedor"}),
        ("post", f"{USUARIOS}{rodrigo}/desativar/", {}),
        ("post", f"{USUARIOS}{rodrigo}/reativar/", {}),
        ("post", f"{USUARIOS}{rodrigo}/reenviar-convite/", {}),
        ("post", f"{USUARIOS}{rodrigo}/cancelar-convite/", {}),
        ("post", f"{USUARIOS}{rodrigo}/redefinir-2fa/", {"motivo": "x"}),
    ]
    apis = {
        "Rodrigo": adm.logar("Rodrigo"),
        "Bruna": adm.logar("Bruna"),
        "João": _api_de(adm, "João"),
        "Lúcia": _api_de(adm, "Lúcia"),
    }
    for nome, api in apis.items():
        for metodo, rota, corpo in rotas:
            resposta = getattr(api, metodo)(rota, corpo, format="json")
            connection.set_tenant(adm.empresa)
            assert resposta.status_code == 403, (nome, metodo, rota)


# --- Login e sessão (USR-06) ---


def test_usr_06_ca_011_03_login_sem_duas_etapas(moto):
    api = moto.cliente()
    resposta = moto.entrar("Bruna", api=api, aparelho="desktop", manter_conectado=True)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["etapa"] == "pronto"
    assert corpo["access"]
    assert corpo["usuario"]["nome"] == "Bruna"
    assert "refresh" not in corpo
    cookie = resposta.cookies["__Host-giro_refresh"]
    assert cookie["httponly"] and cookie["secure"] and cookie["samesite"] == "Strict"
    assert cookie["path"] == "/" and not cookie["domain"]
    # "manter conectado" não existe: a sessão é de desktop, 12 h sem uso.
    sessao = moto.pessoas["Bruna"].sessoes.get()
    assert sessao.tipo == "desktop"
    assert sessao.expira_em - sessao.ultimo_uso == timedelta(hours=12)


def test_usr_02_ca_011_04_login_com_duas_etapas(moto, relogio):
    for nome in ("Mariana", "Rodrigo"):  # Rodrigo ativou por conta própria
        corpo = moto.entrar(nome).json()
        assert corpo["etapa"] == "verificar_2fa"
        assert "access" not in corpo
        assert corpo["token_pre_2fa"]

    relogio.em("2026-10-07 09:00")
    api = moto.cliente()
    pre = moto.entrar("Mariana", api=api).json()["token_pre_2fa"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pre}")
    relogio.em("2026-10-07 09:04:59")
    certo = _post(api, VERIFICAR, moto.empresa, {"codigo": moto.codigo("Mariana")})
    assert certo.status_code == 200
    assert certo.json()["etapa"] == "pronto"

    relogio.em("2026-10-07 09:00")
    api = moto.cliente()
    pre = moto.entrar("Mariana", api=api).json()["token_pre_2fa"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pre}")
    relogio.em("2026-10-07 09:05:01")
    vencido = _post(api, VERIFICAR, moto.empresa, {"codigo": moto.codigo("Mariana")})
    assert vencido.status_code == 401


def test_usr_06_ca_011_05_cinco_tentativas_erradas_bloqueiam_por_15_minutos(
    moto, relogio, django_capture_on_commit_callbacks
):
    relogio.em("2026-10-07 09:00")
    with django_capture_on_commit_callbacks(execute=True):
        respostas = [moto.entrar("Bruna", "senha-errada-1") for _ in range(5)]
    connection.set_tenant(moto.empresa)  # a tarefa do aviso volta a conexão ao public
    assert [r.status_code for r in respostas] == [401, 401, 401, 401, 429]
    quinta = respostas[-1].json()
    assert quinta["codigo"] == "USR-06"
    assert quinta["mensagem"] == "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas"
    assert quinta["detalhes"]["tentar_de_novo_em"] == "2026-10-07T12:15:00Z"  # 09:15 em SP
    bloqueio = moto.eventos("usuario.bloqueado").get()
    assert bloqueio.categoria == "seguranca" and bloqueio.regra == "USR-06"
    aviso = [m for m in mail.outbox if "bloqueado" in m.subject]
    assert len(aviso) == 1 and aviso[0].to == ["mariana@motorapida.com.br"]
    assert "Moto Rápida" in aviso[0].subject

    relogio.em("2026-10-07 09:14")
    assert moto.entrar("Bruna").status_code == 429
    relogio.em("2026-10-07 09:15")
    assert moto.entrar("Bruna").json()["etapa"] == "pronto"

    # Mariana: 3 senhas e 2 códigos errados também somam 5 (de outro IP, fora do limite de
    # 10 entradas por minuto por IP).
    api = moto.cliente(ip="189.40.1.2")
    for _ in range(3):
        assert moto.entrar("Mariana", "senha-errada-1", api=api).status_code == 401
    pre = moto.entrar("Mariana", api=api).json()["token_pre_2fa"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pre}")
    assert _post(api, VERIFICAR, moto.empresa, {"codigo": "000000"}).status_code == 401
    segundo = _post(api, VERIFICAR, moto.empresa, {"codigo": "000001"})
    assert segundo.status_code == 429 and segundo.json()["codigo"] == "USR-06"

    # Com 4 erros e depois o acerto, entra, e a contagem zera. O limite de requisições conta no
    # relógio de verdade: limpar o cache faz o papel do minuto seguinte (10 entradas por e-mail).
    cache.clear()
    api = moto.cliente(ip="189.40.1.3")
    for _ in range(4):
        assert moto.entrar("Bruna", "senha-errada-1", api=api).status_code == 401
    assert moto.entrar("Bruna", api=api).json()["etapa"] == "pronto"
    bruna = Usuario.objects.get(pk=moto.pessoas["Bruna"].pk)
    assert (bruna.senhas_erradas, bruna.tentativas_erradas, bruna.bloqueado_ate) == (0, 0, None)


def test_usr_06_ca_011_06_mensagem_de_erro_nao_revela_o_que_errou(moto):
    inexistente = moto.cliente().post(
        ENTRAR, {"email": "ninguem@motorapida.com.br", "senha": SENHA}, format="json"
    )
    connection.set_tenant(moto.empresa)
    senha_errada = moto.entrar("Bruna", "senha-errada-1")
    for resposta in (inexistente, senha_errada):
        assert resposta.status_code == 401
        assert resposta.json()["codigo"] == "credenciais_invalidas"
        assert resposta.json()["mensagem"] == "E-mail ou senha incorretos"


def test_usr_04_ca_011_07_quem_nao_pode_entrar(moto):
    felipe = moto.entrar("Felipe")
    assert felipe.status_code == 403
    assert felipe.json()["codigo"] == "usuario_inativo"
    assert felipe.json()["mensagem"] == "Seu acesso foi desativado. Fale com o administrador."
    joao = moto.entrar("João")
    assert joao.status_code == 403
    assert joao.json()["codigo"] == "convite_pendente"
    assert joao.json()["mensagem"] == "Use o link do convite para criar seu acesso"


def test_usr_06_ca_011_08_duracao_da_sessao(moto, relogio):
    # Desktop: 12 h sem uso.
    relogio.em("2026-10-07 08:00")
    usada = moto.logar("Bruna", "desktop")
    parada = moto.logar("Bruna", "desktop")
    relogio.em("2026-10-07 19:59")
    assert _post(usada, RENOVAR, moto.empresa, **FRONTEND).status_code == 200
    relogio.em("2026-10-07 20:01")
    encerrada = _post(parada, RENOVAR, moto.empresa, **FRONTEND)
    assert encerrada.status_code == 401
    assert encerrada.json()["codigo"] == "sessao_encerrada"

    # Celular: 30 dias sem uso.
    relogio.em("2026-10-07 10:00")
    celular = moto.logar("Bruna", "celular")
    outro_celular = moto.logar("Bruna", "celular")
    relogio.em("2026-11-06 09:59")
    assert _post(celular, RENOVAR, moto.empresa, **FRONTEND).status_code == 200
    relogio.em("2026-11-06 10:01")
    encerrada = _post(outro_celular, RENOVAR, moto.empresa, **FRONTEND)
    assert encerrada.status_code == 401
    assert encerrada.json()["codigo"] == "sessao_encerrada"

    # Renovar gira o refresh: o anterior, usado de novo, responde 401.
    api = moto.logar("Bruna")
    anterior = api.cookies["__Host-giro_refresh"].value
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 200
    assert api.cookies["__Host-giro_refresh"].value != anterior
    api.cookies["__Host-giro_refresh"] = anterior
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 401

    # Sem o cabeçalho do frontend: 403.
    api = moto.logar("Bruna")
    assert _post(api, RENOVAR, moto.empresa).status_code == 403
    assert _post(api, SAIR, moto.empresa).status_code == 403


def test_usr_06_ca_011_09_sair_e_sessoes(moto):
    api = moto.logar("Bruna")
    assert _post(api, SAIR, moto.empresa, **FRONTEND).status_code == 204
    assert _post(api, RENOVAR, moto.empresa, **FRONTEND).status_code == 401

    no_celular = moto.logar("Bruna", "celular", ip="200.10.20.30")
    no_desktop = moto.logar("Bruna", "desktop")
    lista = _get(no_desktop, SESSOES, moto.empresa).json()["resultados"]
    assert {s["tipo"] for s in lista} == {"celular", "desktop"}
    atual = next(s for s in lista if s["atual"])
    assert atual["tipo"] == "desktop"
    assert atual["ip"] == "177.12.34.0/24"
    assert atual["aparelho"] == "Chrome no Windows"
    assert next(s for s in lista if not s["atual"])["ip"] == "200.10.20.0/24"

    assert _post(no_desktop, f"{SESSOES}encerrar-outras/", moto.empresa).status_code == 204
    lista = _get(no_desktop, SESSOES, moto.empresa).json()["resultados"]
    assert [s["atual"] for s in lista] == [True]
    # O access da sessão encerrada cai já na requisição seguinte (antes dos 5 min do token).
    caiu = _get(no_celular, EU, moto.empresa)
    assert caiu.status_code == 401
    assert caiu.json()["codigo"] == "sessao_encerrada"


# --- Verificação em 2 etapas (USR-02) ---


def test_usr_02_ca_011_10_quem_e_obrigado(moto):
    obrigatorio = {}
    for nome in ("Mariana", "Rodrigo", "Bruna"):
        eu = _get(moto.logar(nome), EU, moto.empresa).json()
        obrigatorio[nome] = eu["dois_fatores"]["obrigatorio"]
    assert obrigatorio == {"Mariana": True, "Rodrigo": False, "Bruna": False}
    assert moto.pessoas["Lúcia"].exige_2fa_pela_regra is True

    mariana = moto.logar("Mariana")
    recusado = _post(mariana, "/api/auth/2fa/desativar/", moto.empresa, {"senha": SENHA})
    assert recusado.status_code == 422
    assert recusado.json()["codigo"] == "USR-02"

    rodrigo = moto.logar("Rodrigo")
    desativou = _post(rodrigo, "/api/auth/2fa/desativar/", moto.empresa, {"senha": SENHA})
    assert desativou.status_code == 204
    assert moto.entrar("Rodrigo").json()["etapa"] == "pronto"
    assert moto.eventos("usuario.desativar_2fa").get().categoria == "seguranca"


def test_usr_02_ca_011_11_exigir_para_todos(moto):
    bruna = moto.logar("Bruna")
    assert _get(bruna, EU, moto.empresa).status_code == 200

    definir_exige_2fa_todos(True)

    sem_otp = _get(bruna, EU, moto.empresa)
    assert sem_otp.status_code == 401
    assert sem_otp.json()["codigo"] == "2fa_obrigatorio"
    assert moto.entrar("Bruna").json()["etapa"] == "configurar_2fa"
    evento = moto.eventos("empresa.exigir_2fa_todos").get()
    assert evento.categoria == "seguranca"
    assert (evento.antes, evento.depois) == ({"exige_2fa_todos": False}, {"exige_2fa_todos": True})
    # Quem é obrigado não desliga.
    assert moto.pessoas["Bruna"].exige_2fa_pela_regra is True


def test_usr_02_ca_011_12_mudar_de_perfil(adm):
    rodrigo = adm.pessoas["Rodrigo"]
    adm.autenticador["Rodrigo"].delete()  # Rodrigo sem autenticador, entra só com senha
    api = adm.logar("Rodrigo")
    mariana = adm.logar("Mariana")
    resposta = mariana.patch(f"{USUARIOS}{rodrigo.pk}/", {"perfil": "financeiro"}, format="json")
    connection.set_tenant(adm.empresa)
    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "financeiro"

    seguinte = _get(api, EU, adm.empresa)
    assert seguinte.status_code == 401
    assert seguinte.json()["codigo"] == "2fa_obrigatorio"
    evento = adm.eventos("usuario.alterar_perfil").get()
    assert (evento.categoria, evento.objeto_id) == ("seguranca", rodrigo.pk)
    assert (evento.antes, evento.depois) == ({"perfil": "gerente"}, {"perfil": "financeiro"})
    assert evento.ator_id == adm.pessoas["Mariana"].pk


def test_usr_02_ca_011_13_configurar_autenticador_com_a_marca_da_locadora(moto):
    from apps.contas.models import Autenticador

    api = moto.cliente()
    etapa = moto.entrar("Lúcia", api=api).json()
    assert etapa["etapa"] == "configurar_2fa"
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {etapa['token_pre_2fa']}")
    configurar = _post(api, CONFIGURAR, moto.empresa).json()
    assert "issuer=Moto%20R%C3%A1pida" in configurar["otpauth_uri"]
    assert configurar["otpauth_uri"].startswith("otpauth://totp/Moto%20R%C3%A1pida%3A")
    assert "giro" not in configurar["otpauth_uri"].lower()
    assert re.fullmatch(r"[A-Z2-7]{4}( [A-Z2-7]{4})+", configurar["chave"])

    dispositivo = Autenticador.objects.get(user=moto.pessoas["Lúcia"], confirmed=False)
    confirmado = _post(api, VERIFICAR, moto.empresa, {"codigo": codigo_atual(dispositivo)})
    assert confirmado.status_code == 200
    codigos = confirmado.json()["codigos_recuperacao"]
    assert len(codigos) == 8 and len(set(codigos)) == 8
    assert Usuario.objects.get(pk=moto.pessoas["Lúcia"].pk).status == StatusUsuario.ATIVO

    def entrar_com_codigo_de_recuperacao(codigo: str) -> Any:
        api = moto.cliente()
        etapa = moto.entrar("Lúcia", api=api).json()
        assert etapa["etapa"] == "verificar_2fa"
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {etapa['token_pre_2fa']}")
        return _post(api, VERIFICAR, moto.empresa, {"codigo_recuperacao": codigo})

    entrou = entrar_com_codigo_de_recuperacao(codigos[0])
    assert entrou.status_code == 200
    assert entrou.json()["usuario"]["dois_fatores"]["codigos_recuperacao_restantes"] == 7
    de_novo = entrar_com_codigo_de_recuperacao(codigos[0])
    assert de_novo.status_code == 401
    assert de_novo.json()["codigo"] == "codigo_invalido"


# --- Convite (T-069) ---


def _convidar(api: APIClient, moto: Moto, capturar: Any, **corpo: Any) -> Any:
    with capturar(execute=True):
        resposta = api.post(f"{USUARIOS}convites/", corpo, format="json")
    connection.set_tenant(moto.empresa)  # a tarefa do envio volta a conexão ao public
    return resposta


def test_usr_01_ca_011_14_convidar(adm, relogio, django_capture_on_commit_callbacks):
    # O João do seed sai para ser convidado pela tela; o plano continua em 5, como na tela.
    Usuario.objects.filter(pk=adm.pessoas["João"].pk).delete()
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    joao = {
        "email": "joao@motorapida.com.br",
        "nome": "João Silva",
        "perfil": "vistoriador",
        "filiais": [adm.centro.pk],
        "celular": "(85) 99654-2210",
    }
    resposta = _convidar(api, adm, django_capture_on_commit_callbacks, **joao)
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    assert corpo["status"] == "convite_pendente"
    assert corpo["convite_expira_em"].startswith("2026-10-14")
    assert corpo["filiais"] == [{"id": adm.centro.pk, "nome": "Filial Centro"}]
    assert corpo["celular"] == "85996542210"
    assert _uso_de_usuarios(adm) == 6
    # Depois do commit, por e-mail e por WhatsApp, com a marca da locadora.
    assert [m.to for m in mail.outbox] == [["joao@motorapida.com.br"]]
    assert "Moto Rápida" in mail.outbox[0].subject
    assert "/convite#" in mail.outbox[0].body
    assert [m.celular for m in caixa_de_saida] == ["85996542210"]
    assert "Moto Rápida" in caixa_de_saida[0].texto
    assert "giro" not in caixa_de_saida[0].texto.lower()
    assert Convite.objects.get(usuario_id=corpo["id"]).enviado_whatsapp is True

    sem_email = _convidar(api, adm, django_capture_on_commit_callbacks, perfil="vendedor")
    assert (sem_email.status_code, sem_email.json()["codigo"]) == (400, "validacao")

    sem_celular = _convidar(
        api,
        adm,
        django_capture_on_commit_callbacks,
        email="ana@motorapida.com.br",
        perfil="vendedor",
        filiais=[adm.centro.pk],
    )
    assert sem_celular.status_code == 201
    assert len(mail.outbox) == 2 and len(caixa_de_saida) == 1  # só e-mail

    em_uso = _convidar(
        api,
        adm,
        django_capture_on_commit_callbacks,
        email="Bruna@MotoRapida.com.br",  # o mesmo e-mail, com maiúsculas
        perfil="vendedor",
        filiais=[adm.centro.pk],
    )
    assert em_uso.status_code == 409
    assert em_uso.json()["codigo"] == "email_em_uso"
    assert em_uso.json()["mensagem"] == "Já existe um usuário com este e-mail"

    sem_filial = _convidar(
        api,
        adm,
        django_capture_on_commit_callbacks,
        email="pedro@motorapida.com.br",
        perfil="vistoriador",
    )
    assert (sem_filial.status_code, sem_filial.json()["codigo"]) == (400, "validacao")
    assert "filiais" in sem_filial.json()["campos"]
    assert _uso_de_usuarios(adm) == 7  # João e Ana


def test_usr_01_ca_011_15_convite_vence_em_7_dias(adm, relogio):
    relogio.em("2026-10-07 10:00")
    _, token = services.criar_convite(adm.pessoas["João"])
    publica = adm.cliente()

    relogio.em("2026-10-14 09:00")
    em_dia = _post(publica, CONSULTAR, adm.empresa, {"token": token})
    assert em_dia.status_code == 200
    assert (em_dia.json()["nome"], em_dia.json()["perfil"]) == ("João", "vistoriador")
    assert em_dia.json()["empresa"] == "Moto Rápida"
    assert em_dia.json()["exige_2fa"] is False

    relogio.em("2026-10-15 10:00")
    for rota, corpo in ((CONSULTAR, {}), (ACEITAR, {"senha": SENHA})):
        vencido = _post(publica, rota, adm.empresa, {"token": token, **corpo})
        assert vencido.status_code == 410
        assert vencido.json()["codigo"] == "convite_expirado"
    joao = Usuario.objects.get(pk=adm.pessoas["João"].pk)
    assert joao.status == StatusUsuario.CONVITE_PENDENTE
    lista = _get(adm.logar("Mariana"), USUARIOS, adm.empresa).json()
    assert lista["plano"]["usado"] == 5  # o vencido continua contando


def test_usr_01_ca_011_16_reenviar_e_cancelar(adm, relogio, django_capture_on_commit_callbacks):
    relogio.em("2026-10-07 10:00")
    joao = adm.pessoas["João"]
    _, antigo = services.criar_convite(joao)
    relogio.em("2026-10-15 10:00")
    api = adm.logar("Mariana")
    with django_capture_on_commit_callbacks(execute=True):
        reenviado = api.post(f"{USUARIOS}{joao.pk}/reenviar-convite/", format="json")
    connection.set_tenant(adm.empresa)
    assert reenviado.status_code == 200
    assert reenviado.json()["convite_expira_em"].startswith("2026-10-22")
    publica = adm.cliente()
    assert _post(publica, CONSULTAR, adm.empresa, {"token": antigo}).status_code in (404, 410)
    novo = _token_do_convite(mail.outbox[-1])
    assert _post(publica, CONSULTAR, adm.empresa, {"token": novo}).status_code == 200

    cancelado = _post(api, f"{USUARIOS}{joao.pk}/cancelar-convite/", adm.empresa)
    assert cancelado.status_code == 200
    assert cancelado.json()["status"] == "desativado"
    assert _uso_de_usuarios(adm) == 4
    assert _post(publica, CONSULTAR, adm.empresa, {"token": novo}).status_code in (404, 410)

    bruna = adm.pessoas["Bruna"].pk
    ativo = _post(api, f"{USUARIOS}{bruna}/reenviar-convite/", adm.empresa)
    assert (ativo.status_code, ativo.json()["codigo"]) == (409, "transicao_usuario")


def test_plt_03_ca_011_17_limite_do_plano_conta_convites(adm, django_capture_on_commit_callbacks):
    UsoEmpresa.objects.filter(empresa=adm.empresa).update(usuarios=10)  # 8 ativos e 2 convites
    api = adm.logar("Mariana")
    pedro = {"email": "pedro@motorapida.com.br", "perfil": "vendedor", "filiais": [adm.centro.pk]}
    cheio = _convidar(api, adm, django_capture_on_commit_callbacks, **pedro)
    assert (cheio.status_code, cheio.json()["codigo"]) == (422, "PLT-03")
    assert not Usuario.objects.filter(email="pedro@motorapida.com.br").exists()

    joao = adm.pessoas["João"].pk
    assert _post(api, f"{USUARIOS}{joao}/cancelar-convite/", adm.empresa).status_code == 200
    assert _convidar(api, adm, django_capture_on_commit_callbacks, **pedro).status_code == 201
    assert _uso_de_usuarios(adm) == 10


def test_usr_01_ca_011_18_aceitar_o_convite(adm, relogio):
    from apps.contas.services import convidar_administrador, renovar_token

    relogio.em("2026-10-07 10:00")
    publica = adm.cliente()

    # João, vistoriador: entra na hora e fica ativo.
    _, token = services.criar_convite(adm.pessoas["João"])
    fraca = _post(publica, ACEITAR, adm.empresa, {"token": token, "senha": "abc123"})
    assert (fraca.status_code, fraca.json()["codigo"]) == (400, "validacao")
    aceito = _post(
        publica,
        ACEITAR,
        adm.empresa,
        {"token": token, "nome": "João Silva", "senha": SENHA, "aparelho": "celular"},
    )
    assert aceito.status_code == 200, aceito.json()
    assert aceito.json()["etapa"] == "pronto"
    assert aceito.json()["usuario"]["nome"] == "João Silva"
    assert aceito.cookies["__Host-giro_refresh"].value
    joao = Usuario.objects.get(pk=adm.pessoas["João"].pk)
    assert joao.status == StatusUsuario.ATIVO
    assert joao.sessoes.get().tipo == "celular"
    assert _post(publica, ACEITAR, adm.empresa, {"token": token, "senha": SENHA}).status_code == 404

    # Lúcia, financeiro: configura as 2 etapas e só fica ativa ao confirmar o código.
    _, token = services.criar_convite(adm.pessoas["Lúcia"])
    etapa = _post(publica, ACEITAR, adm.empresa, {"token": token, "senha": SENHA}).json()
    assert etapa["etapa"] == "configurar_2fa" and "access" not in etapa
    assert Usuario.objects.get(pk=adm.pessoas["Lúcia"].pk).status == "convite_pendente"
    api = adm.cliente()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {etapa['token_pre_2fa']}")
    _post(api, CONFIGURAR, adm.empresa)
    dispositivo = Autenticador.objects.get(user=adm.pessoas["Lúcia"], confirmed=False)
    pronto = _post(api, VERIFICAR, adm.empresa, {"codigo": codigo_atual(dispositivo)})
    assert pronto.json()["etapa"] == "pronto"
    assert Usuario.objects.get(pk=adm.pessoas["Lúcia"].pk).status == "ativo"
    uso = UsoEmpresa.objects.get(empresa=adm.empresa)
    assert "conta" not in uso.passos_implantacao  # Lúcia não é a administradora da compra

    # A administradora da compra: o `pronto` marca o passo `conta` da implantação.
    convite = convidar_administrador("Carla Dias", "carla@motorapida.com.br")
    token = renovar_token(convite)
    etapa = _post(publica, ACEITAR, adm.empresa, {"token": token, "senha": SENHA}).json()
    assert etapa["etapa"] == "configurar_2fa"
    api = adm.cliente()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {etapa['token_pre_2fa']}")
    _post(api, CONFIGURAR, adm.empresa)
    carla = Usuario.objects.get(email="carla@motorapida.com.br")
    dispositivo = Autenticador.objects.get(user=carla, confirmed=False)
    assert (
        _post(api, VERIFICAR, adm.empresa, {"codigo": codigo_atual(dispositivo)}).json()["etapa"]
        == "pronto"
    )
    uso.refresh_from_db()
    assert uso.passos_implantacao["conta"] == "2026-10-07"


def test_usr_01_convite_novo_invalida_o_anterior(adm, relogio):
    """P-06 da T-057: só o convite mais novo vale; aceitar um invalida os outros."""
    relogio.em("2026-10-07 10:00")
    joao = adm.pessoas["João"]
    _, primeiro = services.criar_convite(joao)
    _, segundo = services.criar_convite(joao)
    publica = adm.cliente()
    assert _post(publica, CONSULTAR, adm.empresa, {"token": primeiro}).status_code == 410
    assert (
        _post(publica, ACEITAR, adm.empresa, {"token": primeiro, "senha": SENHA}).status_code == 410
    )
    aceito = _post(publica, ACEITAR, adm.empresa, {"token": segundo, "senha": SENHA})
    assert aceito.json()["etapa"] == "pronto"
    abertos = Convite.objects.filter(
        usuario=joao, aceito_em__isnull=True, expira_em__gt=relogio.agora
    )
    assert not abertos.exists()


def test_usr_01_convite_com_limite_por_ip(adm):
    """30 por minuto por IP nas duas rotas públicas do convite (contrato de contas)."""
    for rota in (CONSULTAR, ACEITAR):
        api = adm.cliente(ip=f"189.1.1.{len(rota)}")
        for _ in range(30):
            assert _post(api, rota, adm.empresa, {"token": "x"}).status_code != 429
        estourou = _post(api, rota, adm.empresa, {"token": "x"})
        assert (estourou.status_code, estourou.json()["codigo"]) == (429, "muitas_requisicoes")


def test_usr_06_ca_011_19_senha(moto):
    api = moto.logar("Bruna")

    def trocar(nova: str) -> Any:
        return _post(
            api, "/api/auth/senha/trocar/", moto.empresa, {"senha_atual": SENHA, "senha_nova": nova}
        )

    recusadas = {
        "abc123": "Use 12 caracteres ou mais.",
        "senhasemnumero": "Use letras e números.",
        "123456789012": "Use letras e números.",
        "bruna@motorapida.com.br": "A senha não pode ser o seu e-mail.",
        "password1234": "Esta senha é muito comum. Escolha outra.",
    }
    for senha, texto in recusadas.items():
        resposta = trocar(senha)
        assert resposta.status_code == 400, senha
        assert resposta.json()["codigo"] == "validacao"
        assert texto in resposta.json()["campos"]["senha_nova"], senha
    nome_da_empresa = trocar("Moto Rápida").json()["campos"]["senha_nova"]
    assert "A senha não pode ser o nome da empresa." in nome_da_empresa
    assert trocar("girafa-azul-2027").status_code == 204


# --- Permissões (USR-03, USR-05) ---


def test_usr_03_ca_011_20_pode_por_perfil(moto):
    def pode(nome: str) -> dict[str, Any]:
        return selectors.calcular_pode(moto.pessoas[nome].perfil, [])

    assert _get(moto.logar("Rodrigo"), EU, moto.empresa).json()["pode"] == pode("Rodrigo")
    assert pode("Rodrigo")["painel"] == "filial"
    assert pode("Rodrigo")["locacoes_cancelar"] == "aprova"
    bruna = _get(moto.logar("Bruna"), EU, moto.empresa).json()["pode"]
    assert (bruna["painel"], bruna["locacoes_cancelar"], bruna["despesas_aprovar"]) == (
        "proprios",
        "pede",
        False,
    )
    assert pode("João")["veiculos"] == "km_e_avarias"
    assert pode("João")["despesas_lancar"] == "manutencao"
    assert pode("Lúcia")["financeiro_pagar"] is True
    assert pode("Lúcia")["veiculos"] == "ver"  # T-287
    mariana = _get(moto.logar("Mariana"), EU, moto.empresa).json()
    assert mariana["pode"]["administracao"] is True
    assert mariana["empresa"] == {
        "nome_exibicao": "Moto Rápida",
        "status": "ativa",
        "somente_leitura": False,
    }
    assert mariana["suporte"] is None


def test_usr_05_ca_011_21_permissoes_extras_so_somam(moto):
    bruna = moto.pessoas["Bruna"]
    bruna.permissoes_extras = [PermissaoExtra.APROVAR_DESCONTO]
    bruna.save()
    pode = _get(moto.logar("Bruna"), EU, moto.empresa).json()["pode"]
    assert pode["desconto_acima_limite"] == "aprova"

    com_relatorios = selectors.calcular_pode("vendedor", ["relatorios_todas_filiais"])
    assert com_relatorios["painel"] == "todas_filiais"
    assert selectors.extra_e_padrao_do_perfil("gerente", "aprovar_desconto") is True
    assert selectors.extra_e_padrao_do_perfil("vendedor", "aprovar_desconto") is False
    # Nenhuma extra reduz: o administrador com todas continua com "sim" e "todas_filiais".
    todas = selectors.calcular_pode("administrador", list(PermissaoExtra.values))
    assert todas == selectors.pode_do_perfil("administrador")


# --- Desativar e administradores (T-069) ---


def test_usr_04_ca_011_22_desativar_encerra_na_hora(adm):
    bruna = adm.pessoas["Bruna"]
    sessao_da_bruna = adm.logar("Bruna")
    api = adm.logar("Mariana")
    desativada = _post(
        api, f"{USUARIOS}{bruna.pk}/desativar/", adm.empresa, {"motivo": "Saiu da empresa"}
    )
    assert desativada.status_code == 200
    assert desativada.json()["status"] == "desativado"

    caiu = _get(sessao_da_bruna, EU, adm.empresa)
    assert (caiu.status_code, caiu.json()["codigo"]) == (401, "sessao_encerrada")
    assert _post(sessao_da_bruna, RENOVAR, adm.empresa, **FRONTEND).status_code == 401
    assert _uso_de_usuarios(adm) == 4
    evento = adm.eventos("usuario.desativar").get()
    assert (evento.objeto_id, evento.motivo, evento.regra) == (
        bruna.pk,
        "Saiu da empresa",
        "USR-04",
    )
    assert adm.eventos("usuario.entrar").filter(objeto_id=bruna.pk).exists()  # histórico fica
    assert Usuario.objects.filter(pk=bruna.pk).exists()

    reativada = _post(api, f"{USUARIOS}{bruna.pk}/reativar/", adm.empresa)
    assert (reativada.status_code, reativada.json()["status"]) == (200, "ativo")
    assert _uso_de_usuarios(adm) == 5
    assert adm.entrar("Bruna").json()["etapa"] == "pronto"

    _post(api, f"{USUARIOS}{bruna.pk}/desativar/", adm.empresa)
    UsoEmpresa.objects.filter(empresa=adm.empresa).update(usuarios=10)
    cheio = _post(api, f"{USUARIOS}{bruna.pk}/reativar/", adm.empresa)
    assert (cheio.status_code, cheio.json()["codigo"]) == (422, "PLT-03")
    convite = _post(api, f"{USUARIOS}{adm.pessoas['João'].pk}/reativar/", adm.empresa)
    assert (convite.status_code, convite.json()["codigo"]) == (409, "transicao_usuario")


def test_usr_04_ca_011_22_reativar_depende_de_ja_ter_sido_ativo(
    adm, relogio, django_capture_on_commit_callbacks
):
    publica = adm.cliente()

    # Felipe já foi ativo: volta ativo, sem convite, e o plano sobe de 5 para 6.
    relogio.em("2026-10-08 10:00")
    api = adm.logar("Mariana")
    felipe = adm.pessoas["Felipe"]
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        reativado = api.post(f"{USUARIOS}{felipe.pk}/reativar/", format="json")
    connection.set_tenant(adm.empresa)
    assert (reativado.status_code, reativado.json()["status"]) == (200, "ativo")
    assert reativado.json()["convite_expira_em"] is None
    assert mail.outbox == []
    assert _uso_de_usuarios(adm) == 6
    assert _post(api, f"{USUARIOS}{felipe.pk}/desativar/", adm.empresa).status_code == 200

    # Lúcia nunca chegou a ativo, e já tinha criado a senha. Mariana cancela o convite em 08 out.
    lucia = adm.pessoas["Lúcia"]
    _, antigo = services.criar_convite(lucia)
    cancelado = _post(api, f"{USUARIOS}{lucia.pk}/cancelar-convite/", adm.empresa)
    assert (cancelado.status_code, cancelado.json()["status"]) == (200, "desativado")
    assert _uso_de_usuarios(adm) == 4

    # Em 09 out, com o plano em 10 de 10: 422 PLT-03, ela continua desativada e nada sai.
    relogio.em("2026-10-09 10:00")
    api = adm.logar("Mariana")
    UsoEmpresa.objects.filter(empresa=adm.empresa).update(usuarios=10)
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        cheio = api.post(f"{USUARIOS}{lucia.pk}/reativar/", format="json")
    connection.set_tenant(adm.empresa)
    assert (cheio.status_code, cheio.json()["codigo"]) == (422, "PLT-03")
    assert Usuario.objects.get(pk=lucia.pk).status == StatusUsuario.DESATIVADO
    assert mail.outbox == []
    assert not adm.eventos("usuario.reativar_convite").exists()

    # Com vaga: volta para convite pendente, com convite novo até 16 out, e o plano volta a 5.
    UsoEmpresa.objects.filter(empresa=adm.empresa).update(usuarios=4)
    with django_capture_on_commit_callbacks(execute=True):
        reativada = api.post(f"{USUARIOS}{lucia.pk}/reativar/", format="json")
    connection.set_tenant(adm.empresa)
    assert reativada.status_code == 200, reativada.json()
    assert reativada.json()["status"] == "convite_pendente"
    assert reativada.json()["convite_expira_em"].startswith("2026-10-16")
    assert _uso_de_usuarios(adm) == 5
    assert [m.to for m in mail.outbox] == [["lucia@motorapida.com.br"]]
    evento = adm.eventos("usuario.reativar_convite").get()
    assert (evento.objeto_id, evento.regra) == (lucia.pk, "USR-04")

    # O link antigo não vale; a senha anterior também não: o link novo cria a senha.
    assert _post(publica, CONSULTAR, adm.empresa, {"token": antigo}).status_code in (404, 410)
    senha_velha = adm.entrar("Lúcia")
    assert (senha_velha.status_code, senha_velha.json()["codigo"]) == (403, "convite_pendente")
    novo = _token_do_convite(mail.outbox[-1])
    etapa = _post(publica, ACEITAR, adm.empresa, {"token": novo, "senha": SENHA}).json()
    assert etapa["etapa"] == "configurar_2fa"
    assert Usuario.objects.get(pk=lucia.pk).status == StatusUsuario.CONVITE_PENDENTE
    duas_etapas = adm.cliente()
    duas_etapas.credentials(HTTP_AUTHORIZATION=f"Bearer {etapa['token_pre_2fa']}")
    _post(duas_etapas, CONFIGURAR, adm.empresa)
    dispositivo = Autenticador.objects.get(user=lucia, confirmed=False)
    pronto = _post(duas_etapas, VERIFICAR, adm.empresa, {"codigo": codigo_atual(dispositivo)})
    assert pronto.json()["etapa"] == "pronto"
    assert Usuario.objects.get(pk=lucia.pk).status == StatusUsuario.ATIVO
    assert services.ja_foi_ativo(lucia) is True


def test_usr_04_ca_011_23_sempre_um_administrador(adm):
    mariana = adm.pessoas["Mariana"].pk
    api = adm.logar("Mariana")
    rebaixar = api.patch(
        f"{USUARIOS}{mariana}/",
        {"perfil": "gerente", "filiais": [adm.centro.pk]},
        format="json",
    )
    connection.set_tenant(adm.empresa)
    assert rebaixar.status_code == 422
    assert rebaixar.json()["codigo"] == "ultimo_administrador"
    assert rebaixar.json()["mensagem"] == "A empresa precisa de ao menos um administrador ativo"
    a_si_mesma = _post(api, f"{USUARIOS}{mariana}/desativar/", adm.empresa)
    assert a_si_mesma.status_code == 422
    assert a_si_mesma.json()["codigo"] == "desativar_a_si_mesmo"
    assert a_si_mesma.json()["mensagem"] == "Peça a outro administrador para desativar seu acesso"
    assert Usuario.objects.get(pk=mariana).perfil == "administrador"

    # Com outro administrador ativo, Mariana pode deixar de ser administradora.
    rodrigo = adm.pessoas["Rodrigo"].pk
    promovido = api.patch(f"{USUARIOS}{rodrigo}/", {"perfil": "administrador"}, format="json")
    connection.set_tenant(adm.empresa)
    assert promovido.status_code == 200
    sem_filial = api.patch(f"{USUARIOS}{mariana}/", {"perfil": "gerente"}, format="json")
    connection.set_tenant(adm.empresa)
    assert (sem_filial.status_code, sem_filial.json()["codigo"]) == (400, "validacao")
    rebaixada = api.patch(
        f"{USUARIOS}{mariana}/", {"perfil": "gerente", "filiais": [adm.centro.pk]}, format="json"
    )
    connection.set_tenant(adm.empresa)
    assert rebaixada.status_code == 200
    assert rebaixada.json()["filiais"] == [{"id": adm.centro.pk, "nome": "Filial Centro"}]


def test_usr_02_ca_011_24_redefinir_duas_etapas(adm):
    rodrigo = adm.pessoas["Rodrigo"]
    sessao_do_rodrigo = adm.logar("Rodrigo")
    api = adm.logar("Mariana")
    sem_motivo = _post(api, f"{USUARIOS}{rodrigo.pk}/redefinir-2fa/", adm.empresa)
    assert (sem_motivo.status_code, sem_motivo.json()["codigo"]) == (400, "validacao")
    redefinida = _post(
        api, f"{USUARIOS}{rodrigo.pk}/redefinir-2fa/", adm.empresa, {"motivo": "Perdeu o celular"}
    )
    assert redefinida.status_code == 200
    assert redefinida.json()["dois_fatores_ativo"] is False

    caiu = _get(sessao_do_rodrigo, EU, adm.empresa)
    assert (caiu.status_code, caiu.json()["codigo"]) == (401, "sessao_encerrada")
    assert not Autenticador.objects.filter(user=rodrigo).exists()
    assert adm.entrar("Rodrigo").json()["etapa"] == "pronto"  # gerente: só a senha
    evento = adm.eventos("usuario.redefinir_2fa").get()
    assert (evento.categoria, evento.motivo, evento.objeto_id) == (
        "seguranca",
        "Perdeu o celular",
        rodrigo.pk,
    )

    # Perfil que exige: o próximo login configura de novo.
    api.patch(f"{USUARIOS}{rodrigo.pk}/", {"perfil": "financeiro"}, format="json")
    connection.set_tenant(adm.empresa)
    assert adm.entrar("Rodrigo").json()["etapa"] == "configurar_2fa"


def test_usr_04_administrador_ve_e_encerra_sessoes_de_outro(adm):
    sessao_da_bruna = adm.logar("Bruna")
    api = adm.logar("Mariana")
    bruna = adm.pessoas["Bruna"].pk
    lista = _get(api, f"{USUARIOS}{bruna}/sessoes/", adm.empresa).json()["resultados"]
    assert len(lista) == 1 and lista[0]["ip"] == "177.12.34.0/24" and lista[0]["atual"] is False
    encerrar = f"{USUARIOS}{bruna}/sessoes/{lista[0]['id']}/encerrar/"
    assert _post(api, encerrar, adm.empresa).status_code == 204
    assert _get(sessao_da_bruna, EU, adm.empresa).status_code == 401
    sessao = adm.pessoas["Bruna"].sessoes.get()
    assert sessao.motivo_revogacao == "revogada_pelo_administrador"


def test_usr_03_ca_011_21_detalhe_com_permissoes_extras(adm):
    api = adm.logar("Mariana")
    rodrigo = adm.pessoas["Rodrigo"].pk
    detalhe = _get(api, f"{USUARIOS}{rodrigo}/", adm.empresa).json()
    extras = {e["chave"]: e for e in detalhe["permissoes_extras"]}
    assert extras["aprovar_desconto"] == {
        "chave": "aprovar_desconto",
        "marcada": True,
        "padrao_do_perfil": True,
    }
    assert extras["relatorios_todas_filiais"]["marcada"] is False
    assert detalhe["entrou_em"] is not None

    alterado = api.patch(
        f"{USUARIOS}{rodrigo}/", {"permissoes_extras": ["relatorios_todas_filiais"]}, format="json"
    )
    connection.set_tenant(adm.empresa)
    extras = {e["chave"]: e for e in alterado.json()["permissoes_extras"]}
    assert extras["relatorios_todas_filiais"] == {
        "chave": "relatorios_todas_filiais",
        "marcada": True,
        "padrao_do_perfil": False,
    }
    evento = adm.eventos("usuario.alterar_permissoes").get()
    assert (evento.antes, evento.depois) == (
        {"permissoes_extras": []},
        {"permissoes_extras": ["relatorios_todas_filiais"]},
    )


# --- Filiais da pessoa (USR-07, F-03 da T-064) ---


def test_usr_07_troca_de_filiais_da_pessoa_vai_para_a_auditoria(adm):
    from apps.filiais.models import Filial
    from apps.filiais.services import criar_filial, desativar

    from .test_t012_filiais import _filial

    norte = criar_filial(_filial("Filial Norte"), adm.pessoas["Mariana"])
    bruna = adm.pessoas["Bruna"]
    api = adm.logar("Mariana")
    trocou = api.patch(f"{USUARIOS}{bruna.pk}/", {"filiais": [norte.pk]}, format="json")
    connection.set_tenant(adm.empresa)
    assert trocou.status_code == 200
    assert trocou.json()["filiais"] == [{"id": norte.pk, "nome": "Filial Norte"}]
    # O vínculo com a Centro é desativado, não apagado.
    vinculo = UsuarioFilial.objects.get(usuario=bruna, filial=adm.centro)
    assert vinculo.ativo is False
    evento = adm.eventos("usuario.alterar_filiais").filter(objeto_id=bruna.pk).last()
    assert evento.categoria == "seguranca"
    assert evento.antes == {"filiais": [{"id": adm.centro.pk, "nome": "Filial Centro"}]}
    assert evento.depois == {"filiais": [{"id": norte.pk, "nome": "Filial Norte"}]}
    assert evento.ator_id == adm.pessoas["Mariana"].pk

    # Volta para a Centro: a mesma linha é reativada.
    api.patch(f"{USUARIOS}{bruna.pk}/", {"filiais": [adm.centro.pk]}, format="json")
    connection.set_tenant(adm.empresa)
    vinculo.refresh_from_db()
    assert vinculo.ativo is True

    # Filial inativa ou inexistente: 422 e nada muda.
    sul = criar_filial(_filial("Filial Sul"), adm.pessoas["Mariana"])
    desativar(Filial.objects.get(pk=sul.pk), motivo="Fechou")
    for filial in (sul.pk, 999999):
        recusada = api.patch(f"{USUARIOS}{bruna.pk}/", {"filiais": [filial]}, format="json")
        connection.set_tenant(adm.empresa)
        assert (recusada.status_code, recusada.json()["codigo"]) == (422, "filial_invalida")
    assert list(UsuarioFilial.ativos.filter(usuario=bruna).values_list("filial_id", flat=True)) == [
        adm.centro.pk
    ]


def test_usr_07_financeiro_escolhe_todas_as_filiais(adm):
    """USR-07 (T-067): o financeiro vê todas as filiais ativas e pode escolher "Todas"."""
    lucia = _api_de(adm, "Lúcia")
    minhas = _get(lucia, "/api/filiais/minhas/", adm.empresa).json()
    assert minhas["pode_escolher_todas"] is True
    assert [f["id"] for f in minhas["resultados"]] == [adm.centro.pk]
    lucia.credentials(
        HTTP_AUTHORIZATION=lucia._credentials["HTTP_AUTHORIZATION"], HTTP_X_FILIAL="todas"
    )
    assert _get(lucia, "/api/filiais/minhas/", adm.empresa).status_code == 200


def test_usr_03_relatorios_todas_filiais_so_em_painel_e_relatorios(adm, rf):
    """USR-03: a extra libera `X-Filial: todas` só nas views de painel e relatórios."""
    from rest_framework.response import Response
    from rest_framework.test import force_authenticate
    from rest_framework.views import APIView

    class Relatorio(APIView):
        escopo_de_relatorio = True

        def get(self, request: Any) -> Response:
            return Response({"ok": True})

    class Operacao(Relatorio):
        escopo_de_relatorio = False

    bruna = adm.pessoas["Bruna"]

    def chamar(view: type[APIView]) -> Any:
        requisicao = rf.get("/", HTTP_X_FILIAL="todas")
        requisicao.tenant = adm.empresa
        force_authenticate(requisicao, user=Usuario.objects.get(pk=bruna.pk))
        return view.as_view()(requisicao)

    assert chamar(Relatorio).status_code == 403  # sem a extra
    Usuario.objects.filter(pk=bruna.pk).update(permissoes_extras=["relatorios_todas_filiais"])
    assert chamar(Relatorio).status_code == 200
    operacao = chamar(Operacao)
    assert operacao.status_code == 403
    assert operacao.data["codigo"] == "USR-07"


def test_usr_01_usuario_da_empresa_a_nao_aparece_na_b(adm, empresa_b):
    from django.db import connection as conexao

    conexao.set_tenant(empresa_b)
    dona_b = Usuario.objects.create_user(
        "dona@empresab.com.br", SENHA, nome="Dona B", perfil="administrador"
    )
    refresh = emitir_tokens(dona_b, AMR_SENHA_E_CODIGO)
    api = APIClient(HTTP_HOST="empresa-b.localhost", REMOTE_ADDR="10.0.0.5")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    lista = api.get(USUARIOS).json()
    conexao.set_tenant(adm.empresa)
    assert [u["email"] for u in lista["resultados"]] == ["dona@empresab.com.br"]
    assert lista["contagens"]["todos"] == 1


# --- Esqueci a senha ---


def _token_do_email(mensagem: Any) -> str:
    achado = re.search(r"/entrar/redefinir#(\S+)", mensagem.body)
    assert achado, mensagem.body
    return achado.group(1)


def test_usr_06_ca_011_25_recuperacao_sem_revelar_contas(
    moto, relogio, django_capture_on_commit_callbacks
):
    publica = moto.cliente()

    def esqueci(email: str) -> Any:
        with django_capture_on_commit_callbacks(execute=True):
            resposta = _post(publica, "/api/auth/senha/esqueci/", moto.empresa, {"email": email})
        connection.set_tenant(moto.empresa)  # a tarefa do e-mail volta a conexão ao public
        return resposta

    def redefinir(token: str, senha: str = "girafa-verde-2026") -> Any:
        return _post(
            publica,
            "/api/auth/senha/redefinir/",
            moto.empresa,
            {"token": token, "senha_nova": senha},
        )

    relogio.em("2026-10-07 10:00")
    existe = esqueci("bruna@motorapida.com.br")
    nao_existe = esqueci("ninguem@motorapida.com.br")
    assert existe.status_code == nao_existe.status_code == 202
    assert existe.json() == nao_existe.json()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["bruna@motorapida.com.br"]

    # Vale 1 hora.
    relogio.em("2026-10-07 11:00:01")
    resposta = redefinir(_token_do_email(mail.outbox[0]))
    assert resposta.status_code == 410
    assert resposta.json()["codigo"] == "link_expirado"

    # O 4º pedido na mesma hora não envia nada.
    relogio.em("2026-10-07 12:00")
    for _ in range(4):
        assert esqueci("bruna@motorapida.com.br").status_code == 202
    assert len(mail.outbox) == 4  # 1 + 3

    # Uso único; encerra todas as sessões da pessoa.
    sessao = moto.logar("Bruna")
    token = _token_do_email(mail.outbox[-1])
    assert redefinir(token).status_code == 204
    assert redefinir(token).status_code == 410
    caiu = _get(sessao, EU, moto.empresa)
    assert caiu.status_code == 401 and caiu.json()["codigo"] == "sessao_encerrada"
    assert moto.entrar("Bruna", "girafa-verde-2026").json()["etapa"] == "pronto"

    # Quem tem autenticador continua precisando do código.
    esqueci("mariana@motorapida.com.br")
    assert redefinir(_token_do_email(mail.outbox[-1])).status_code == 204
    assert moto.entrar("Mariana", "girafa-verde-2026").json()["etapa"] == "verificar_2fa"


# --- Modo suporte (T-070; PLT-07, AUD-03; ADR 0013, item 2) ---


def _token_do_diego(moto: Moto, equipe: Any) -> str:
    """Login de verdade na plataforma (no `public`), uma vez por teste."""
    if not hasattr(moto, "token_do_diego"):
        connection.set_schema_to_public()
        moto.token_do_diego = entrar(*equipe["Diego Santos"])
        connection.set_tenant(moto.empresa)
    return str(moto.token_do_diego)


def _abrir_suporte(
    moto: Moto,
    equipe: Any,
    *,
    permissao: str = "ver",
    duracao: int = 30,
    motivo: str = "Chamado #1042",
) -> tuple[APIClient, dict[str, Any]]:
    """Diego abre o acesso pela plataforma; devolve o cliente com o token do fragmento."""
    plataforma = cliente(HOST_PLATAFORMA, _token_do_diego(moto, equipe))
    resposta = plataforma.post(
        f"/api/plataforma/empresas/{moto.empresa.pk}/acessos-suporte/",
        {"motivo": motivo, "duracao_minutos": duracao, "permissao": permissao},
        format="json",
    )
    connection.set_tenant(moto.empresa)
    assert resposta.status_code == 201, resposta.json()
    url = resposta.json()["url_entrada"]
    assert url.startswith("https://empresa-a.localhost/suporte/entrar#")
    api = moto.cliente()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {url.split('#', 1)[1]}")
    return api, resposta.json()


def _acesso(pk: int) -> AcessoSuporte:
    with schema_context("public"):
        return AcessoSuporte.objects.get(pk=pk)


def _codigo_e_mensagem(resposta: Any) -> tuple[int, str, str]:
    corpo = resposta.json()
    return resposta.status_code, corpo["codigo"], corpo["mensagem"]


def test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte(
    equipe, adm, relogio, django_capture_on_commit_callbacks
):
    relogio.em("2026-10-07 15:00")
    with django_capture_on_commit_callbacks(execute=True):
        diego, aberto = _abrir_suporte(adm, equipe)
    connection.set_tenant(adm.empresa)  # a tarefa do aviso volta a conexão ao public
    assert aberto["fim"] == "2026-10-07T18:30:00Z"  # 15:30 em São Paulo
    aviso = [m for m in mail.outbox if "suporte" in m.subject]
    assert len(aviso) == 1 and aviso[0].to == ["mariana@motorapida.com.br"]
    assert "Moto Rápida" in aviso[0].subject
    assert "Chamado #1042" in aviso[0].body and "Diego Santos" in aviso[0].body

    eu = _get(diego, EU, adm.empresa)
    assert eu.status_code == 200
    corpo = eu.json()
    assert corpo["suporte"] == {
        "acesso_suporte_id": aberto["acesso_suporte_id"],
        "nome": "Diego Santos",
        "permissao": "ver",
        "fim": "2026-10-07T18:30:00Z",
        "motivo": "Chamado #1042",
    }
    assert (corpo["perfil"], corpo["id"]) == ("administrador", None)
    assert corpo["filiais"] == [{"id": adm.centro.pk, "nome": "Filial Centro"}]
    assert corpo["pode"]["administracao"] is True
    assert corpo["pode"]["locacoes_criar"] is False  # "só ver": sem as chaves de escrita

    # Leitura marcada para o suporte responde.
    for rota in (USUARIOS, "/api/filiais/", f"/api/filiais/{adm.centro.pk}/", "/api/assinatura/"):
        assert _get(diego, rota, adm.empresa).status_code == 200, rota

    # Escrita no modo "só ver".
    patch = diego.patch(f"/api/filiais/{adm.centro.pk}/", {"nome": "X"}, format="json")
    connection.set_tenant(adm.empresa)
    assert _codigo_e_mensagem(patch) == (403, "PLT-07", "No modo só ver você não pode fazer isto")

    # Rotas que o suporte nunca usa, em qualquer modo.
    editar, _ = _abrir_suporte(adm, equipe, permissao="ver_editar")
    bruna = adm.pessoas["Bruna"].pk
    for api in (diego, editar):
        proibidas = [
            _post(api, ENTRAR, adm.empresa, {"email": "x@y.com", "senha": "x"}),
            _post(api, RENOVAR, adm.empresa, **FRONTEND),
            _post(api, CONSULTAR, adm.empresa, {"token": "x"}),
            _get(api, SESSOES, adm.empresa),
            _post(api, f"{USUARIOS}convites/", adm.empresa, {"email": "a@b.com"}),
            _post(api, f"{USUARIOS}{bruna}/desativar/", adm.empresa),
            _post(api, "/api/auth/senha/trocar/", adm.empresa, {}),
        ]
        for resposta in proibidas:
            assert resposta.status_code == 403, resposta.json()
            assert resposta.json()["codigo"] == "PLT-07"
        alterar = api.patch(f"{USUARIOS}{bruna}/", {"perfil": "gerente"}, format="json")
        connection.set_tenant(adm.empresa)
        assert (alterar.status_code, alterar.json()["codigo"]) == (403, "PLT-07")
    plataforma = cliente(HOST_PLATAFORMA)
    plataforma.credentials(HTTP_AUTHORIZATION=diego._credentials["HTTP_AUTHORIZATION"])
    na_plataforma = plataforma.get("/api/plataforma/empresas/")
    connection.set_tenant(adm.empresa)
    assert (na_plataforma.status_code, na_plataforma.json()["codigo"]) == (403, "PLT-07")

    # "Ver e editar" escreve fora de usuários, e a auditoria mostra o suporte com o acesso.
    editado = editar.patch(
        f"/api/filiais/{adm.centro.pk}/", {"nome": "Filial Centro Fortaleza"}, format="json"
    )
    connection.set_tenant(adm.empresa)
    assert editado.status_code == 200
    evento = adm.eventos("filial.editar").last()
    assert (evento.ator_tipo, evento.ator_nome) == ("suporte", "Diego Santos")
    assert evento.acesso_suporte_id is not None and evento.ator_id is None

    # O token de uma empresa não vale em outra.
    outra = APIClient(HTTP_HOST="empresa-b.localhost", REMOTE_ADDR="10.0.0.5")
    outra.credentials(HTTP_AUTHORIZATION=diego._credentials["HTTP_AUTHORIZATION"])
    em_b = outra.get(EU)
    connection.set_tenant(adm.empresa)
    assert (em_b.status_code, em_b.json()["codigo"]) == (401, "PLT-07")

    # No `fim`, a requisição seguinte cai.
    relogio.em("2026-10-07 15:30:01")
    acabou = _get(diego, EU, adm.empresa)
    assert _codigo_e_mensagem(acabou) == (401, "PLT-07", "O acesso de suporte terminou")


def test_plt_07_ca_011_27_administrador_controla_o_suporte(equipe, adm, relogio):
    relogio.em("2026-10-07 15:00")
    diego, aberto = _abrir_suporte(adm, equipe)
    mariana = adm.logar("Mariana")
    lista = _get(mariana, "/api/suporte/", adm.empresa).json()
    assert lista["bloqueado"] is False
    assert [(a["nome"], a["status"], a["motivo"]) for a in lista["acessos"]] == [
        ("Diego Santos", "ativo", "Chamado #1042")
    ]
    # Só o administrador controla, e o suporte não se libera.
    assert _get(adm.logar("Bruna"), "/api/suporte/", adm.empresa).status_code == 403
    proprio = _post(diego, "/api/suporte/liberar/", adm.empresa)
    assert (proprio.status_code, proprio.json()["codigo"]) == (403, "PLT-07")

    # Bloquear com Diego dentro: o acesso vira `revogado` e a requisição seguinte falha.
    bloqueio = _post(mariana, "/api/suporte/bloquear/", adm.empresa, {"motivo": "Sem chamado"})
    assert bloqueio.json() == {"bloqueado": True}
    assert _acesso(aberto["acesso_suporte_id"]).status == "revogado"
    caiu = _get(diego, EU, adm.empresa)
    assert (caiu.status_code, caiu.json()["codigo"]) == (401, "PLT-07")
    plataforma = cliente(HOST_PLATAFORMA, _token_do_diego(adm, equipe))
    recusado = plataforma.post(
        f"/api/plataforma/empresas/{adm.empresa.pk}/acessos-suporte/",
        {"motivo": "Chamado #1043", "duracao_minutos": 15, "permissao": "ver"},
        format="json",
    )
    connection.set_tenant(adm.empresa)
    assert _codigo_e_mensagem(recusado) == (
        422,
        "PLT-07",
        "O administrador da empresa bloqueou o acesso do suporte",
    )
    assert _post(mariana, "/api/suporte/liberar/", adm.empresa).json() == {"bloqueado": False}

    # O suporte sai: `encerrado`.
    saindo, saida = _abrir_suporte(adm, equipe, motivo="Chamado #1044")
    assert _post(saindo, "/api/auth/suporte/sair/", adm.empresa).status_code == 204
    assert _acesso(saida["acesso_suporte_id"]).status == "encerrado"
    assert _get(saindo, EU, adm.empresa).status_code == 401
    assert _post(mariana, "/api/auth/suporte/sair/", adm.empresa).status_code == 403

    # O administrador revoga um acesso.
    revogado, outro = _abrir_suporte(adm, equipe, motivo="Chamado #1045")
    rota = f"/api/suporte/acessos/{outro['acesso_suporte_id']}/revogar/"
    resposta = _post(mariana, rota, adm.empresa, {"motivo": "Já resolvido"})
    assert (resposta.status_code, resposta.json()["status"]) == (200, "revogado")
    assert _get(revogado, EU, adm.empresa).status_code == 401

    # Auditoria da empresa: entrada, saída e revogação, com destaque (ator suporte) e motivo.
    entrada = adm.eventos("suporte.entrar").first()
    assert (entrada.categoria, entrada.ator_tipo, entrada.ator_nome) == (
        "suporte",
        "suporte",
        "Diego Santos",
    )
    assert (entrada.motivo, entrada.acesso_suporte_id) == (
        "Chamado #1042",
        aberto["acesso_suporte_id"],
    )
    sair = adm.eventos("suporte.sair").get()
    assert (sair.ator_tipo, sair.acesso_suporte_id) == ("suporte", saida["acesso_suporte_id"])
    revogacoes = adm.eventos("suporte.revogar")
    assert {e.motivo for e in revogacoes} == {"Sem chamado", "Já resolvido"}
    assert all(e.ator_nome == "Mariana" and e.categoria == "suporte" for e in revogacoes)
    assert adm.eventos("suporte.bloquear").get().depois == {"suporte_bloqueado": True}
    # E na auditoria da plataforma.
    with schema_context("public"):
        acoes = set(EventoAuditoria.objects.values_list("acao", flat=True))
    assert {"suporte.entrar", "suporte.sair", "suporte.revogar", "suporte.bloquear"} <= acoes


def test_aut_15_encerra_acessos_de_suporte_vencidos(equipe, adm, relogio):
    from apps.plataforma.tasks import aut_15_encerrar_acessos_de_suporte_vencidos

    relogio.em("2026-10-07 15:00")
    _, aberto = _abrir_suporte(adm, equipe, duracao=15)
    relogio.em("2026-10-07 15:14")
    assert aut_15_encerrar_acessos_de_suporte_vencidos() == 0
    relogio.em("2026-10-07 15:15")
    assert aut_15_encerrar_acessos_de_suporte_vencidos() == 1
    connection.set_tenant(adm.empresa)
    acesso = _acesso(aberto["acesso_suporte_id"])
    assert (acesso.status, acesso.encerrado_em is not None) == ("encerrado", True)
    assert aut_15_encerrar_acessos_de_suporte_vencidos() == 0  # idempotente
    connection.set_tenant(adm.empresa)
    assert adm.eventos("suporte.encerrar").get().motivo == "O prazo do acesso acabou"


def test_plt_07_lista_de_rotas_que_o_suporte_le():
    """ADR 0013, item 2: "só ver" é uma lista de views marcadas. Uma view nova só entra aqui de
    propósito (sem exportação, URL assinada nem dado pessoal completo)."""
    from config import urls

    def views(padroes: Any, prefixo: str = "") -> Any:
        for padrao in padroes:
            if hasattr(padrao, "url_patterns"):
                yield from views(padrao.url_patterns, prefixo + str(padrao.pattern))
            else:
                classe = getattr(padrao.callback, "view_class", None)
                if classe is not None:
                    yield prefixo + str(padrao.pattern), classe

    marcadas = {
        rota
        for rota, classe in views(urls.urlpatterns)
        if getattr(classe, "suporte_somente_leitura", False)
    }
    assert marcadas == {
        "api/auth/eu/",
        # T-027: a importação, com linha de cliente resumida para o suporte (AUD-09).
        "api/importacoes/",
        "api/importacoes/modelo/",
        "api/importacoes/<int:pk>/",
        "api/importacoes/<int:pk>/linhas/",
        "api/usuarios/",
        "api/usuarios/<int:pk>/",
        "api/assinatura/",
        # T-185: Mudar e Comparar planos; o suporte lê e nunca escreve na assinatura.
        "api/assinatura/planos/",
        "api/assinatura/faturas/",
        "api/assinatura/faturas/<str:codigo>/",
        "api/filiais/minhas/",
        "api/filiais/",
        "api/filiais/<int:pk>/",
        "api/filiais/<int:pk>/feriados/",
        "api/filiais/<int:pk>/feriados/sugestoes/",
        "api/enderecos/cep/<str:cep>/",
        "api/veiculos/",
        "api/veiculos/<int:pk>/",
        "api/veiculos/<int:pk>/documentos/",
        "api/veiculos/<int:pk>/documentos/historico/",
        "api/categorias/",
        "api/categorias/<int:pk>/precos/",
        "api/precos/historico/",
        "api/extras/",
        "api/clientes/",
        "api/clientes/<int:pk>/",
        # Painel (T-129): números agregados, sem dado pessoal completo.
        "api/painel/contadores/",
        "api/painel/inicio/",
        # T-181: Configurações, só contagens e textos (sem auditoria e exportar para o suporte).
        "api/configuracoes/",
    }


# --- Auditoria (AUD-01) ---


def test_aud_01_ca_011_28_eventos_de_seguranca(moto, relogio):
    """Login, falha, bloqueio e troca de senha. Perfil, filiais, permissões, desativação e
    redefinição das 2 etapas entram com as rotas da T-069."""
    relogio.em("2026-10-07 09:00")
    for _ in range(5):
        moto.entrar("Bruna", "senha-errada-1")
    relogio.em("2026-10-07 09:15")
    api = moto.logar("Bruna")
    moto.logar("Mariana")
    codigo = codigo_atual(moto.autenticador["Mariana"])
    _post(
        api,
        "/api/auth/senha/trocar/",
        moto.empresa,
        {"senha_atual": SENHA, "senha_nova": "girafa-azul-2027"},
    )

    bruna = moto.pessoas["Bruna"]
    for acao in ("usuario.entrar", "usuario.entrar_falhou", "usuario.bloqueado"):
        evento = moto.eventos(acao).filter(objeto_id=bruna.pk).last()
        assert evento is not None, acao
        assert evento.categoria == "seguranca"
        assert evento.objeto_tipo == "usuario"
    login = moto.eventos("usuario.entrar").filter(objeto_id=bruna.pk).last()
    assert (login.ator_id, login.ip) == (bruna.pk, IP_DE_CASA)
    assert "Chrome" in login.aparelho
    troca = moto.eventos("usuario.trocar_senha").get()
    assert troca.ator_id == bruna.pk
    assert troca.depois == {"password": {"alterado": True}}

    tudo = json.dumps(
        list(EventoAuditoria.objects.values("antes", "depois", "motivo")), default=str
    )
    for segredo in (SENHA, "senha-errada-1", "girafa-azul-2027", codigo, "md5$", "argon2"):
        assert segredo not in tudo
    assert api.cookies["__Host-giro_refresh"].value not in tudo


def test_aud_01_ca_011_28_eventos_da_administracao_de_usuarios(adm):
    """Mudança de perfil, filiais e permissões, desativação e redefinição das 2 etapas: quem,
    quando, ação, objeto, antes e depois, IP e aparelho, sem segredo nenhum."""
    from apps.filiais.services import criar_filial

    from .test_t012_filiais import _filial

    norte = criar_filial(_filial("Filial Norte"), adm.pessoas["Mariana"])
    api = adm.logar("Mariana")
    rodrigo, bruna = adm.pessoas["Rodrigo"].pk, adm.pessoas["Bruna"].pk

    def patch(pk: int, corpo: dict[str, Any]) -> None:
        resposta = api.patch(f"{USUARIOS}{pk}/", corpo, format="json")
        connection.set_tenant(adm.empresa)
        assert resposta.status_code == 200, resposta.json()

    patch(rodrigo, {"perfil": "vendedor"})
    patch(rodrigo, {"filiais": [adm.centro.pk, norte.pk]})
    patch(bruna, {"permissoes_extras": ["aprovar_desconto"]})
    _post(api, f"{USUARIOS}{bruna}/desativar/", adm.empresa, {"motivo": "Saiu"})
    _post(api, f"{USUARIOS}{rodrigo}/redefinir-2fa/", adm.empresa, {"motivo": "Perdeu o celular"})

    mariana = adm.pessoas["Mariana"].pk
    esperados = {
        "usuario.alterar_perfil": rodrigo,
        "usuario.alterar_filiais": rodrigo,
        "usuario.alterar_permissoes": bruna,
        "usuario.desativar": bruna,
        "usuario.redefinir_2fa": rodrigo,
    }
    for acao, objeto in esperados.items():
        evento = adm.eventos(acao).filter(objeto_id=objeto).last()
        assert evento is not None, acao
        assert evento.categoria == "seguranca", acao
        assert (evento.ator_id, evento.objeto_tipo) == (mariana, "usuario"), acao
        assert evento.ip == IP_DE_CASA and "Chrome" in evento.aparelho, acao
        assert evento.ocorrido_em is not None
    filiais = adm.eventos("usuario.alterar_filiais").filter(objeto_id=rodrigo).last()
    assert [f["nome"] for f in filiais.depois["filiais"]] == ["Filial Centro", "Filial Norte"]
    assert adm.eventos("usuario.desativar").get().antes == {"status": "ativo"}

    tudo = json.dumps(
        list(EventoAuditoria.objects.values("antes", "depois", "motivo")), default=str
    )
    for segredo in (SENHA, "md5$", "argon2", "token_hash", "chave"):
        assert segredo not in tudo


# --- Navegação do eu (T-071) ---

TODOS_OS_MODULOS = [
    "aprovacoes",
    "auditoria",
    "clientes",
    "conciliacao",  # fase 2: a conciliação tem o próprio módulo (T-017)
    "configuracoes",
    "contas",
    "empresas",
    "filiais",
    "financeiro",
    "locacoes",
    "manutencao",
    "plataforma",
    "relatorios",
    "veiculos",
    "vendas",
    "vistorias",
]
ADMINISTRACAO = ["config", "marca", "filiais", "usuarios", "assinatura", "auditoria"]


def _chaves(menu: list[dict[str, Any]]) -> list[tuple[str | None, list[str]]]:
    return [(grupo["grupo"], [item["chave"] for item in grupo["itens"]]) for grupo in menu]


def _navegacao(adm: Moto, nome: str) -> dict[str, Any]:
    api = adm.logar(nome) if nome in ("Mariana", "Rodrigo", "Bruna") else _api_de(adm, nome)
    resposta = _get(api, EU, adm.empresa)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json()["navegacao"])


def test_usr_05_usr_08_navegacao_por_perfil(adm, settings):
    settings.GIRO_MODULOS_ATIVOS = TODOS_OS_MODULOS  # plano Profissional, aluga e vende

    # Mariana, administradora antes da 1ª locação: implantação, com o menu completo no início.
    mariana = _navegacao(adm, "Mariana")
    assert mariana["inicio"] == {"rota": "/inicio", "variante": "implantacao"}
    assert _chaves(mariana["menu_completo"]) == [
        (None, ["inicio", "aprovacoes", "veiculos"]),
        ("Operação", ["locacoes", "vendas", "clientes", "manutencoes"]),
        ("Financeiro", ["caixa", "receber", "despesas", "comissoes", "conciliacao", "relatorios"]),
        ("Administração", ADMINISTRACAO),
    ]
    assert mariana["menu_inicio"] == mariana["menu_completo"]
    assert mariana["menu_completo"][0]["itens"][0] == {
        "chave": "inicio",
        "rotulo": "Visão geral",
        "contador": None,
    }
    assert mariana["barra_celular"] == ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]

    # Rodrigo, gerente: o menu da tela Gerente; sem pagar contas nem administração.
    rodrigo = _navegacao(adm, "Rodrigo")
    assert rodrigo["inicio"]["variante"] == "gerente"
    assert _chaves(rodrigo["menu_inicio"]) == [
        (None, ["inicio", "aprovacoes", "veiculos"]),
        ("Operação", ["locacoes", "vendas", "clientes", "manutencoes"]),
        ("Filial", ["caixa", "relatorios"]),
    ]
    assert rodrigo["menu_inicio"][0]["itens"][0]["rotulo"] == "Visão da filial"
    assert rodrigo["menu_inicio"][2]["itens"][0]["rotulo"] == "Caixa da filial"
    assert _chaves(rodrigo["menu_completo"]) == [
        (None, ["inicio", "aprovacoes", "veiculos"]),
        ("Operação", ["locacoes", "vendas", "clientes", "manutencoes"]),
        ("Financeiro", ["caixa", "receber", "despesas", "relatorios"]),
    ]
    assert rodrigo["menu_completo"][2]["itens"][2]["contador"] == "despesas"  # aprova despesas
    assert rodrigo["menu_completo"][0]["itens"][0]["rotulo"] == "Visão da filial"

    # Bruna, vendedora: só o que é dela; sem aprovações nem relatórios. Veículos só para ler
    # (T-287).
    bruna = _navegacao(adm, "Bruna")
    assert bruna["inicio"]["variante"] == "vendedor"
    assert _chaves(bruna["menu_inicio"]) == [
        (None, ["inicio"]),
        ("Operação", ["locacoes", "veiculos", "clientes"]),
        ("Vendas", ["propostas", "minhas_vendas", "veiculos_a_venda", "minhas_comissoes"]),
    ]
    assert _chaves(bruna["menu_completo"]) == [
        (None, ["inicio", "veiculos"]),
        ("Operação", ["locacoes", "vendas", "clientes"]),
        ("Financeiro", ["caixa", "receber", "despesas"]),
    ]
    assert bruna["menu_completo"][2]["itens"][2]["contador"] is None  # lança, não aprova
    assert bruna["menu_completo"][0]["itens"][0]["rotulo"] == "Início"
    assert bruna["barra_celular"] == ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]

    # João, vistoriador: um menu só, o da agenda (test_usr_05_menu_completo_do_vistoriador).
    joao = _navegacao(adm, "João")
    assert joao["inicio"]["variante"] == "vistoriador"
    assert joao["menu_completo"] == joao["menu_inicio"]

    # Lúcia, financeiro: o menu da tela Financeiro; sem locações. Veículos só para ler (T-287).
    lucia = _navegacao(adm, "Lúcia")
    assert lucia["inicio"]["variante"] == "financeiro"
    assert _chaves(lucia["menu_inicio"]) == [
        (
            None,
            ["inicio", "receber", "contas_a_pagar", "caixa_e_bancos", "veiculos", "comissoes"],
        ),
    ]
    assert _chaves(lucia["menu_completo"]) == [
        (None, ["inicio", "veiculos"]),
        ("Operação", ["clientes"]),
        ("Financeiro", ["caixa", "receber", "despesas", "comissoes", "conciliacao", "relatorios"]),
    ]
    assert lucia["menu_completo"][0]["itens"][0]["rotulo"] == "Início"
    assert lucia["barra_celular"] == ["inicio", "veiculos", "mais"]

    # A permissão extra de aprovar desconto traz Aprovações para a vendedora (USR-03).
    vendedora = adm.pessoas["Bruna"]
    vendedora.permissoes_extras = ["aprovar_desconto"]
    vendedora.save()
    assert _chaves(_navegacao(adm, "Bruna")["menu_completo"])[0] == (
        None,
        ["inicio", "aprovacoes", "veiculos"],
    )


def test_usr_05_menu_completo_do_vistoriador(adm, settings):
    """USR-05 (T-141): João tem um menu só, sem "Visão geral" (não vê painel) e sem
    "Locações" (chega à vistoria pela agenda); a barra do celular leva a Consultar veículo."""
    settings.GIRO_MODULOS_ATIVOS = TODOS_OS_MODULOS
    joao = _navegacao(adm, "João")
    esperado = [(None, ["agenda", "consultar_veiculo", "avarias"])]
    assert _chaves(joao["menu_inicio"]) == esperado
    assert _chaves(joao["menu_completo"]) == esperado
    rotulos = [item["rotulo"] for grupo in joao["menu_completo"] for item in grupo["itens"]]
    assert rotulos == ["Vistorias de hoje", "Consultar veículo", "Avarias abertas"]
    assert "Visão geral" not in rotulos and "Locações" not in rotulos
    assert joao["barra_celular"] == ["inicio", "veiculos", "mais"]


def test_usr_05_menu_do_administrador_tem_auditoria(adm):
    """T-180: com os módulos padrão, a Mariana vê "Auditoria" na Administração (a tela da
    T-171). Configurações vem pela chave `configuracoes` (T-181); Empresa e marca fica fora
    até a tela existir (`empresas`)."""
    from django.conf import settings as configuracao

    assert "auditoria" in configuracao.GIRO_MODULOS_ATIVOS
    mariana = _navegacao(adm, "Mariana")
    administracao = dict(_chaves(mariana["menu_completo"]))["Administração"]
    assert administracao == ["config", "filiais", "usuarios", "assinatura", "auditoria"]
    item = mariana["menu_completo"][-1]["itens"][-1]
    assert (item["chave"], item["rotulo"]) == ("auditoria", "Auditoria")
    # Só o administrador: o gerente e o financeiro não veem.
    for nome in ("Rodrigo", "Lúcia"):
        chaves = [c for _, itens in _chaves(_navegacao(adm, nome)["menu_completo"]) for c in itens]
        assert "auditoria" not in chaves


def test_usr_05_plano_atividade_e_modulos_escondem_itens(adm, settings, planos):
    from apps.contas import navegacao, selectors

    # Só os módulos entregues: o menu nunca leva a uma tela que não existe.
    settings.GIRO_MODULOS_ATIVOS = ["contas", "filiais", "plataforma"]
    mariana = _navegacao(adm, "Mariana")
    assert _chaves(mariana["menu_completo"]) == [
        (None, ["inicio"]),
        ("Administração", ["filiais", "usuarios", "assinatura"]),
    ]
    assert mariana["barra_celular"] == ["inicio", "mais"]

    # Plano Essencial: sem vendas, manutenção e despesas, comissões nem relatórios.
    settings.GIRO_MODULOS_ATIVOS = TODOS_OS_MODULOS
    adm.empresa.plano = planos["Essencial"]
    adm.empresa.save(update_fields=["plano"])
    assert _chaves(_navegacao(adm, "Mariana")["menu_completo"]) == [
        (None, ["inicio", "aprovacoes", "veiculos"]),
        ("Operação", ["locacoes", "clientes"]),
        ("Financeiro", ["caixa", "receber", "conciliacao"]),
        ("Administração", ADMINISTRACAO),
    ]

    # Atividade da empresa: quem só aluga não vê vendas; quem só vende não vê locações.
    pode = selectors.pode_do_perfil("gerente")
    recursos = list(navegacao.Recurso.values)
    comum: dict[str, Any] = {"perfil": "gerente", "pode": pode, "recursos": recursos}
    so_aluga = navegacao.montar(
        **comum, implantacao_concluida=True, atividade="aluga", modulos=TODOS_OS_MODULOS
    )
    assert _chaves(so_aluga["menu_inicio"])[1] == (
        "Operação",
        ["locacoes", "clientes", "manutencoes"],
    )
    so_vende = navegacao.montar(
        **comum, implantacao_concluida=True, atividade="vende", modulos=TODOS_OS_MODULOS
    )
    assert _chaves(so_vende["menu_inicio"])[1] == (
        "Operação",
        ["vendas", "clientes", "manutencoes"],
    )
    assert so_vende["barra_celular"] == ["inicio", "veiculos", "mais"]


def test_usr_08_administrador_ve_o_geral_depois_da_primeira_locacao(adm, settings):
    from apps.contas import navegacao, selectors

    settings.GIRO_MODULOS_ATIVOS = TODOS_OS_MODULOS
    uso = UsoEmpresa.objects.get(empresa=adm.empresa)
    uso.passos_implantacao = {**uso.passos_implantacao, "primeira_locacao": "2026-10-08"}
    uso.save(update_fields=["passos_implantacao"])
    mariana = _navegacao(adm, "Mariana")
    assert mariana["inicio"]["variante"] == "geral"
    assert mariana["menu_inicio"] == mariana["menu_completo"]

    # No modo suporte, a variante é a do administrador; com "ver", o menu segue o `pode`.
    suporte = navegacao.da_empresa(adm.empresa, "administrador", selectors.pode_do_suporte("ver"))
    assert suporte["inicio"]["variante"] == "geral"
    assert _chaves(suporte["menu_completo"]) == [
        (None, ["inicio", "veiculos"]),
        ("Financeiro", ["relatorios"]),
        ("Administração", ADMINISTRACAO),
    ]
