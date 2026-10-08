"""T-058: correções dos achados P-01 a P-04 da revisão de segurança da T-010 (T-057).

Relatório: docs/seguranca/2026-10-08-codigo-t010.md. Cada teste reproduz o achado.
"""

import threading
import time
from typing import Any

import pytest
from django.db import connection, connections
from django.test import Client

from apps.auditoria.models import EventoAuditoria
from apps.contas import dois_fatores
from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from comum.erros import ErroDeValidacao, MuitasTentativas

from .conftest import (
    HOST_PLATAFORMA,
    SENHA,
    autenticador_confirmado,
    cliente,
    codigo_atual,
    liberar_codigo,
)

ENTRAR = "/api/plataforma/auth/entrar/"
LOGIN_ADMIN = "/admin/login/"
OUTRO_CNPJ = "11.222.333/0001-81"


def _admin_login(email: str, senha: str, codigo: str) -> Any:
    navegador = Client(HTTP_HOST=HOST_PLATAFORMA, REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="pytest")
    resposta = navegador.post(
        LOGIN_ADMIN,
        {"username": email, "password": senha, "otp_token": codigo, "next": "/admin/"},
    )
    connection.set_schema_to_public()
    return navegador, resposta


def _eventos(acao: str, usuario: Any) -> int:
    return int(EventoAuditoria.objects.filter(acao=acao, objeto_id=usuario.pk).count())


# --- P-01: login do Django Admin com o bloqueio e a auditoria do PLT-08 ---


@pytest.fixture
def dono_do_admin(equipe):
    """O dono com acesso ao Admin, como o criado por `createsuperuser`."""
    dono, dispositivo = equipe["Você"]
    Usuario.objects.filter(pk=dono.pk).update(is_staff=True, is_superuser=True)
    dono.refresh_from_db()
    return dono, dispositivo


def test_plt_08_admin_entra_com_codigo_certo_e_audita(dono_do_admin):
    dono, dispositivo = dono_do_admin
    navegador, resposta = _admin_login(dono.email, SENHA, codigo_atual(dispositivo))

    assert resposta.status_code == 302
    assert resposta["Location"] == "/admin/"
    painel = navegador.get("/admin/")
    connection.set_schema_to_public()
    assert painel.status_code == 200  # sessão verificada pelo django-otp
    evento = EventoAuditoria.objects.get(acao="usuario.entrar", objeto_id=dono.pk)
    assert (evento.categoria, evento.regra) == ("seguranca", "PLT-08")
    assert (evento.ip, evento.aparelho) == ("10.0.0.5", "pytest")


def test_plt_08_admin_bloqueia_depois_de_3_codigos_errados(dono_do_admin, relogio):
    dono, _ = dono_do_admin
    relogio.em("2026-10-07 10:00")
    for _ in range(2):
        _, resposta = _admin_login(dono.email, SENHA, "000000")
        assert resposta.status_code == 200
        assert "E-mail, senha ou código incorretos" in resposta.content.decode()
    _, terceira = _admin_login(dono.email, SENHA, "000000")
    assert "Acesso bloqueado por 15 minutos depois de 3 códigos errados" in (
        terceira.content.decode()
    )

    dono.refresh_from_db()
    assert dono.bloqueado_ate == relogio.agora.replace(minute=15)
    assert _eventos("usuario.entrar_falhou", dono) == 3
    bloqueio = EventoAuditoria.objects.get(acao="usuario.bloqueado", objeto_id=dono.pk)
    assert (bloqueio.categoria, bloqueio.regra) == ("seguranca", "PLT-08")


def test_plt_08_admin_bloqueado_recusa_codigo_certo(dono_do_admin, relogio):
    dono, dispositivo = dono_do_admin
    relogio.em("2026-10-07 10:00")
    for _ in range(3):
        _admin_login(dono.email, SENHA, "000000")

    relogio.em("2026-10-07 10:14")
    _, resposta = _admin_login(dono.email, SENHA, codigo_atual(dispositivo))
    assert resposta.status_code == 200
    assert "Acesso bloqueado por 15 minutos" in resposta.content.decode()

    relogio.em("2026-10-07 10:15")
    liberar_codigo(dispositivo)
    _, resposta = _admin_login(dono.email, SENHA, codigo_atual(dispositivo))
    assert resposta.status_code == 302


def test_plt_08_admin_bloqueia_depois_de_5_senhas_erradas(dono_do_admin, relogio):
    dono, dispositivo = dono_do_admin
    relogio.em("2026-10-07 10:00")
    for _ in range(4):
        _, resposta = _admin_login(dono.email, "errada", codigo_atual(dispositivo))
        assert "E-mail, senha ou código incorretos" in resposta.content.decode()
    _, quinta = _admin_login(dono.email, "errada", codigo_atual(dispositivo))
    assert "Acesso bloqueado por 15 minutos depois de 5 senhas erradas" in quinta.content.decode()
    _, certa = _admin_login(dono.email, SENHA, codigo_atual(dispositivo))
    assert "Acesso bloqueado" in certa.content.decode()


def test_plt_08_admin_recusa_quem_nao_e_da_equipe_do_admin(equipe):
    """Senha e código certos de quem não tem `is_staff`: recusado e auditado."""
    diego, dispositivo = equipe["Diego Santos"]
    _, resposta = _admin_login(diego.email, SENHA, codigo_atual(dispositivo))
    assert resposta.status_code == 200
    assert "Esta conta não tem acesso ao Admin." in resposta.content.decode()
    assert _eventos("usuario.entrar_falhou", diego) == 1


# --- P-02: bloqueio, verificação e contagem com a linha do usuário travada ---


def _em_paralelo(funcao, quantas: int) -> list[BaseException]:
    """Threads com conexão própria em autocommit, fora da transação do teste."""
    erros: list[BaseException] = []
    largada = threading.Barrier(quantas)

    def rodar() -> None:
        try:
            connection.set_schema_to_public()
            largada.wait(timeout=10)
            funcao()
        except BaseException as erro:  # devolvido ao teste
            erros.append(erro)
        finally:
            connections.close_all()

    threads = [threading.Thread(target=rodar) for _ in range(quantas)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return erros


EMAIL_PARALELO = "paralelo@girolocadoras.com.br"


def _apagar_conta_paralela() -> None:
    """SQL direto: o `delete` do ORM segue relações que só existem no schema da empresa."""
    with connection.cursor() as cursor:
        for tabela, coluna in (
            ("contas_autenticador", "user_id"),
            ("contas_codigorecuperacao", "usuario_id"),
            ("contas_sessao", "usuario_id"),
            ("token_blacklist_outstandingtoken", "user_id"),
        ):
            cursor.execute(
                f"DELETE FROM {tabela} WHERE {coluna} IN "  # noqa: S608 - nomes fixos acima
                "(SELECT id FROM contas_usuario WHERE email = %s)",
                [EMAIL_PARALELO],
            )
        cursor.execute("DELETE FROM contas_usuario WHERE email = %s", [EMAIL_PARALELO])


@pytest.fixture
def conta_commitada(db):
    """Conta da equipe gravada de verdade (as threads não enxergam a transação do teste)."""
    criada: dict[str, Any] = {}

    def criar() -> None:
        _apagar_conta_paralela()
        usuario = Usuario.objects.create_user(
            EMAIL_PARALELO, SENHA, nome="Paralelo", funcao_plataforma="suporte"
        )
        criada["usuario"] = usuario
        criada["dispositivo"] = autenticador_confirmado(usuario)

    assert not _em_paralelo(criar, 1)
    yield criada["usuario"], criada["dispositivo"]
    assert not _em_paralelo(_apagar_conta_paralela, 1)  # os eventos de auditoria ficam


def test_plt_08_codigos_em_paralelo_nao_passam_do_limite(conta_commitada, monkeypatch):
    usuario, _ = conta_commitada
    original = dois_fatores.conferir_codigo
    verificados: list[str] = []
    resultados: list[str] = []

    def conferir_devagar(*args: Any, **kwargs: Any) -> Any:
        verificados.append(kwargs.get("codigo", ""))
        time.sleep(0.05)  # alarga a janela, como o Argon2 da senha
        return original(*args, **kwargs)

    monkeypatch.setattr(dois_fatores, "conferir_codigo", conferir_devagar)

    def tentar() -> None:
        try:
            tentativa = dois_fatores.tentar_entrar(usuario, senha=SENHA, codigo="000000")
            resultados.append("bloqueou" if tentativa.bloqueio else "errou")
        except MuitasTentativas:
            resultados.append("429")

    assert not _em_paralelo(tentar, 12)
    assert len(verificados) == 3
    assert sorted(resultados) == ["429"] * 9 + ["bloqueou", "errou", "errou"]
    assert Usuario.objects.get(pk=usuario.pk).bloqueado_ate is not None


def test_plt_08_mesmo_codigo_em_paralelo_aceito_uma_vez(conta_commitada):
    usuario, dispositivo = conta_commitada
    codigo = codigo_atual(dispositivo)
    aceitos: list[bool] = []

    def tentar() -> None:
        tentativa = dois_fatores.tentar_entrar(usuario, senha=SENHA, codigo=codigo)
        aceitos.append(tentativa.falha is None)

    assert not _em_paralelo(tentar, 3)
    assert sorted(aceitos) == [False, False, True]  # os outros dois viram replay do código


# --- P-03: senha errada e senha certa sem código respondem igual; 5 senhas bloqueiam ---


def test_plt_08_senha_certa_sem_codigo_responde_como_senha_errada(equipe):
    diego, _ = equipe["Diego Santos"]
    api = cliente(HOST_PLATAFORMA)

    errada = api.post(ENTRAR, {"email": diego.email, "senha": "palpite"}, format="json")
    certa = api.post(ENTRAR, {"email": diego.email, "senha": SENHA}, format="json")
    inexistente = api.post(
        ENTRAR, {"email": "ninguem@girolocadoras.com.br", "senha": SENHA}, format="json"
    )
    assert errada.status_code == certa.status_code == inexistente.status_code == 401
    assert errada.json() == certa.json() == inexistente.json()
    assert certa.json()["codigo"] == "credenciais_invalidas"


def test_plt_08_bloqueio_por_senha_tem_mensagem_propria(equipe, relogio):
    """O caso completo é o CA-010-18 (test_t010_plataforma); aqui, a mensagem e o motivo."""
    diego, _ = equipe["Diego Santos"]
    api = cliente(HOST_PLATAFORMA)
    relogio.em("2026-10-07 10:00")
    for _ in range(4):
        api.post(ENTRAR, {"email": diego.email, "senha": "palpite"}, format="json")
    quinta = api.post(ENTRAR, {"email": diego.email, "senha": "palpite"}, format="json")
    assert quinta.status_code == 429
    assert quinta.json()["mensagem"] == "Acesso bloqueado por 15 minutos depois de 5 senhas erradas"
    evento = EventoAuditoria.objects.get(acao="usuario.bloqueado", objeto_id=diego.pk)
    assert evento.motivo == "5 senhas erradas"
    assert _eventos("usuario.entrar_falhou", diego) == 5


def test_plt_08_senha_certa_com_codigo_errado_nao_zera_as_senhas(equipe, relogio):
    """Acertar só a senha não muda a contagem: a resposta não revela a senha certa."""
    diego, _ = equipe["Diego Santos"]
    api = cliente(HOST_PLATAFORMA)
    relogio.em("2026-10-07 10:00")
    for _ in range(2):
        api.post(ENTRAR, {"email": diego.email, "senha": "palpite"}, format="json")
    api.post(ENTRAR, {"email": diego.email, "senha": SENHA, "codigo": "000000"}, format="json")
    diego.refresh_from_db()
    assert (diego.senhas_erradas, diego.tentativas_erradas) == (2, 1)


def test_plt_08_entrar_com_limite_por_ip_e_por_email(db):
    """Throttle do DRF (comum.limites): 10 por minuto por IP e por e-mail, exista ele ou não."""
    por_ip = cliente(HOST_PLATAFORMA)
    for numero in range(10):
        resposta = por_ip.post(
            ENTRAR, {"email": f"palpite{numero}@girolocadoras.com.br", "senha": "x"}, format="json"
        )
        assert resposta.status_code == 401
    estourou = por_ip.post(ENTRAR, {"email": "outro@girolocadoras.com.br", "senha": "x"})
    assert estourou.status_code == 429
    assert estourou.json()["codigo"] == "muitas_requisicoes"
    assert estourou.json()["detalhes"]["tentar_de_novo_em_segundos"] > 0
    assert int(estourou["Retry-After"]) > 0

    corpo = {"email": "alvo@girolocadoras.com.br", "senha": "x"}
    for numero in range(10):
        api = cliente(HOST_PLATAFORMA)
        api.defaults["REMOTE_ADDR"] = f"200.1.1.{numero}"
        assert api.post(ENTRAR, corpo, format="json").status_code == 401
    outro_ip = cliente(HOST_PLATAFORMA)
    outro_ip.defaults["REMOTE_ADDR"] = "200.1.1.99"
    assert outro_ip.post(ENTRAR, corpo, format="json").status_code == 429


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        pytest.param(
            "post",
            "/api/plataforma/convites/consultar/",
            marks=pytest.mark.xfail(strict=False, reason="T-069: rota nova do convite (T-072)"),
        ),
        pytest.param(
            "post",
            "/api/plataforma/convites/aceitar/",
            marks=pytest.mark.xfail(strict=False, reason="T-069: rota nova do convite (T-072)"),
        ),
        ("post", "/api/plataforma/auth/renovar/"),
    ],
)
def test_plt_08_convite_e_renovar_com_limite_por_ip(db, metodo, caminho):
    api = cliente(HOST_PLATAFORMA)
    for _ in range(30):
        assert getattr(api, metodo)(caminho, HTTP_X_REQUESTED_WITH="giro").status_code != 429
    estourou = getattr(api, metodo)(caminho, HTTP_X_REQUESTED_WITH="giro")
    assert estourou.status_code == 429
    assert estourou.json()["codigo"] == "muitas_requisicoes"


# --- P-04: subdomínio que vira schema existente ou do Postgres ---


def _sem_empresa_nem_usuario(subdominio: str) -> None:
    assert not Empresa.objects.filter(subdominio=subdominio).exists()
    assert not Usuario.objects.filter(email="mariana@motorapida.com.br").exists()


@pytest.mark.parametrize(
    "subdominio", ["information-schema", "public", "pg-catalog", "pg-toast", "pg-temp-1"]
)
def test_plt_01_subdominio_de_schema_existente_recusado(criar_empresa, subdominio):
    with pytest.raises(ErroDeValidacao) as erro:
        criar_empresa(subdominio=subdominio, cnpj=OUTRO_CNPJ)
    assert (erro.value.status_http, erro.value.codigo) == (400, "validacao")
    assert erro.value.campos == {"subdominio": ["Este endereço é reservado. Escolha outro."]}
    _sem_empresa_nem_usuario(subdominio)


def test_plt_01_subdominio_de_schema_de_fora_do_giro_recusado(criar_empresa):
    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA "ferramenta_externa"')  # volta com a transação do teste
    with pytest.raises(ErroDeValidacao) as erro:
        criar_empresa(subdominio="ferramenta-externa", cnpj=OUTRO_CNPJ)
    assert erro.value.campos == {"subdominio": ["Este endereço é reservado. Escolha outro."]}
    _sem_empresa_nem_usuario("ferramenta-externa")


def test_plt_01_criar_empresa_nao_reaproveita_schema(criar_empresa, monkeypatch):
    """Se o schema aparece entre a validação e a criação, a criação falha e nada fica gravado."""
    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA "corrida_externa"')
    monkeypatch.setattr("apps.plataforma.services.schema_exists", lambda schema: False)
    with pytest.raises(ErroDeValidacao) as erro:
        criar_empresa(subdominio="corrida-externa", cnpj=OUTRO_CNPJ)
    assert erro.value.campos == {"subdominio": ["Este endereço é reservado. Escolha outro."]}
    _sem_empresa_nem_usuario("corrida-externa")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'corrida_externa'"
        )
        assert cursor.fetchone() == (0,)
