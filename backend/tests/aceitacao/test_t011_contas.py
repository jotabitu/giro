"""T-011 · Contas, perfis, 2 etapas, convite (critérios em docs/qa/criterios/T-011.md).

A T-011 entrega login, sessões, 2 etapas, `eu` e senha. Os critérios de usuários e convite são da
T-069 e os do modo suporte, da T-070 (divisão combinada com o Orquestrador em 09/10).

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
from rest_framework.test import APIClient

from apps.auditoria.models import EventoAuditoria
from apps.contas import selectors
from apps.contas.models import Convite, PermissaoExtra, StatusUsuario, Usuario
from apps.empresas.services import definir_exige_2fa_todos

from .apoio import USUARIOS_SEED, aguarda, pendente
from .conftest import autenticador_confirmado, codigo_atual, liberar_codigo

T_USUARIOS = "T-069"
T_SUPORTE = "T-070"

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


def _get(api: APIClient, rota: str, empresa: Any) -> Any:
    resposta = api.get(rota)
    connection.set_tenant(empresa)
    return resposta


def _post(api: APIClient, rota: str, empresa: Any, corpo: Any = None, **extra: Any) -> Any:
    resposta = api.post(rota, corpo or {}, format="json", **extra)
    connection.set_tenant(empresa)
    return resposta


# --- Lista e plano (T-069) ---


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_01_contagens_do_seed():
    pendente(
        contagens={"todos": 6, "ativos": 3, "convites": 2, "desativados": 1},
        plano={"usado": 5, "limite": 10, "aviso": False, "bloqueado": False},
        usuarios=USUARIOS_SEED,
        felipe_conta_no_plano=False,
    )


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_02_so_o_administrador_administra_usuarios():
    pendente(
        recebem_403=["Rodrigo", "Bruna", "João", "Lúcia"], rotas=["GET /api/usuarios/", "escritas"]
    )


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


def test_usr_02_ca_011_12_mudar_de_perfil(moto):
    """O mecanismo (perfil novo derruba o token sem `otp`). A rota e a auditoria
    `usuario.alterar_perfil` são da T-069."""
    rodrigo = moto.pessoas["Rodrigo"]
    moto.autenticador["Rodrigo"].delete()  # Rodrigo sem autenticador, entra só com senha
    api = moto.logar("Rodrigo")
    Usuario.objects.filter(pk=rodrigo.pk).update(perfil="financeiro")
    resposta = _get(api, EU, moto.empresa)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "2fa_obrigatorio"


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


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_14_convidar():
    pendente(
        email="joao@motorapida.com.br",
        perfil="vistoriador",
        filial="Filial Centro",
        celular="(85) 99654-2210",
        status=201,
        convite_expira_em="2026-10-14",
        canais=["email", "whatsapp"],
        apos_commit=True,
        plano=(5, 6),
        sem_email=(400, "validacao"),
        sem_celular="só e-mail",
        email_em_uso=(409, "email_em_uso"),
        vistoriador_sem_filial=(400, "validacao"),
    )


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_15_convite_vence_em_7_dias():
    pendente(
        em_14_out=200,
        em_15_out=(410, "convite_expirado"),
        vencido_continua="convite_pendente",
        conta_no_plano=True,
    )


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_16_reenviar_e_cancelar():
    pendente(
        reenviar_em_15_out="expira em 22 out",
        link_antigo=[404, 410],
        cancelar="desativado",
        plano_cai=1,
        reenviar_ativo=(409, "transicao_usuario"),
    )


@aguarda(T_USUARIOS)
def test_plt_03_ca_011_17_limite_do_plano_conta_convites():
    pendente(ativos=8, convites=2, convidar_mais=(422, "PLT-03"), apos_cancelar_um="passa")


@aguarda(T_USUARIOS)
def test_usr_01_ca_011_18_aceitar_o_convite():
    pendente(
        joao="pronto e ativo",
        lucia="configurar_2fa, ativa só após confirmar o código",
        mariana="marca o passo conta da implantação",
    )


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
    assert pode("Lúcia")["veiculos"] == "nao"
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


@aguarda(T_USUARIOS)
def test_usr_04_ca_011_22_desativar_encerra_na_hora():
    pendente(
        access_atual=(401, "sessao_encerrada"),
        refresh_renova=False,
        plano=(5, 4),
        historico_na_auditoria=True,
        reativar="ativo",
        reativar_com_10_de_10=(422, "PLT-03"),
    )


@aguarda(T_USUARIOS)
def test_usr_04_ca_011_23_sempre_um_administrador():
    pendente(
        tirar_proprio_perfil_sendo_unica=(422, "ultimo_administrador"),
        desativar_a_si_mesma=(422, "desativar_a_si_mesmo"),
    )


@aguarda(T_USUARIOS)
def test_usr_02_ca_011_24_redefinir_duas_etapas():
    pendente(
        motivo="Perdeu o celular",
        sessoes_caem=True,
        proximo_login="configurar_2fa se o perfil exigir",
        auditoria="seguranca com motivo",
    )


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


# --- Modo suporte (T-070) ---


@aguarda(T_SUPORTE)
def test_plt_07_ca_011_26_faixa_e_permissoes_do_suporte():
    pendente(
        suporte={
            "nome": "Diego Santos",
            "permissao": "ver",
            "duracao_min": 30,
            "motivo": "Chamado #1042",
        },
        escrita=(403, "PLT-07", "No modo só ver você não pode fazer isto"),
        apos_fim=(401, "PLT-07"),
        rotas_proibidas=["auth/entrar", "renovar", "sessoes", "escrita de usuarios"],
        proibidas_status=(403, "PLT-07"),
    )


@aguarda(T_SUPORTE)
def test_plt_07_ca_011_27_administrador_controla_o_suporte():
    pendente(
        bloquear="acesso vira revogado",
        proxima_requisicao="falha",
        auditoria="entrada, saída e revogação com destaque e motivo (AUD-03)",
    )


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
