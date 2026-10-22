"""T-347 · Reconfirmar as 2 etapas sem sair do sistema (`docs/api/contas.md`, "Reconfirmar as 2
etapas"; ADR 0032). `POST /api/auth/2fa/reconfirmar/` devolve só um access novo, com `auth_time`,
na mesma sessão. USR-02, USR-06, PLT-06, PLT-07."""

from typing import Any

from django.db import connection
from django_tenants.utils import tenant_context
from rest_framework_simplejwt.tokens import AccessToken

from apps.auditoria import textos
from apps.auditoria.models import EventoAuditoria
from apps.contas import dois_fatores
from apps.contas.models import Sessao
from comum.autenticacao import AMR_SENHA_E_CODIGO, COOKIE_REFRESH, emitir_tokens

from .conftest import autenticador_confirmado, codigo_atual, liberar_codigo
from .conftest import cliente as cliente_http
from .test_t195_cancelar_pausar import (
    CANCELAMENTO,
    HOST,
    MARIANA,
    _cancelar,
    _em,
    _erro,
    moto,  # noqa: F401 - fixture
)

RECONFIRMAR = "/api/auth/2fa/reconfirmar/"
RENOVAR = "/api/auth/renovar/"
ENTRAR = "/api/auth/entrar/"
SENHA = "senha-forte-123"
CODIGO_ERRADO = "Código incorreto. Confira o horário do celular e tente de novo."
PEDE_2_ETAPAS = {
    "codigo": "2fa_recente",
    "mensagem": "Confirme o código do autenticador para cancelar a assinatura.",
}


class Logada:
    """Mariana logada com as 2 etapas: o access no cabeçalho e o refresh no cookie."""

    def __init__(self, moto: Any) -> None:  # noqa: F811
        self.moto = moto
        self.mariana = moto.pessoas["Mariana"]
        with tenant_context(moto.empresa):
            self.mariana.set_password(SENHA)
            self.mariana.save()
            self.autenticador = autenticador_confirmado(self.mariana)
            refresh = emitir_tokens(self.mariana, AMR_SENHA_E_CODIGO)
        connection.set_schema_to_public()
        self.refresh = refresh
        self.api = cliente_http(HOST, str(refresh.access_token))
        self.api.cookies[COOKIE_REFRESH] = str(refresh)

    def usar(self, access: str) -> None:
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def codigo(self) -> str:
        with tenant_context(self.moto.empresa):
            liberar_codigo(self.autenticador)
            codigo = codigo_atual(self.autenticador)  # a semente é cifrada com o schema
        connection.set_schema_to_public()
        return codigo

    def codigo_errado(self) -> str:
        return f"{(int(self.codigo()) + 1) % 1_000_000:06d}"

    def reconfirmar(self, **corpo: str) -> Any:
        resposta = self.api.post(RECONFIRMAR, corpo, format="json")
        connection.set_schema_to_public()
        return resposta

    def renovar(self) -> Any:
        resposta = self.api.post(RENOVAR, HTTP_X_REQUESTED_WITH="giro")
        connection.set_schema_to_public()
        return resposta

    def entrar(self, senha: str = SENHA) -> Any:
        resposta = cliente_http(HOST).post(
            ENTRAR, {"email": MARIANA, "senha": senha}, format="json"
        )
        connection.set_schema_to_public()
        return resposta

    def sessoes(self) -> int:
        with tenant_context(self.moto.empresa):
            return int(Sessao.objects.filter(usuario=self.mariana).count())

    def eventos(self, *acoes: str) -> list[EventoAuditoria]:
        with tenant_context(self.moto.empresa):
            return list(EventoAuditoria.objects.filter(acao__in=acoes).order_by("pk"))


def _claims(access: str) -> dict[str, Any]:
    return dict(AccessToken(access).payload)  # type: ignore[arg-type]


def test_usr_02_reconfirmar_devolve_access_na_mesma_sessao(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    antes = _claims(str(logada.refresh.access_token))
    _em(relogio, "2026-10-10", "10:03")
    resposta = logada.reconfirmar(codigo=logada.codigo())
    assert resposta.status_code == 200, resposta.json()
    assert set(resposta.json()) == {"access"}
    assert resposta["Cache-Control"] == "no-store"
    assert not resposta.cookies  # sem refresh novo
    novo = _claims(resposta.json()["access"])
    for claim in ("sid", "schema", "empresa_id", "amr", "user_id"):
        assert novo[claim] == antes[claim], claim
    assert novo["amr"] == ["pwd", "otp"]
    assert novo["auth_time"] == antes["auth_time"] + 3 * 60  # agora, 3 min depois do login
    assert novo["token_type"] == "access"
    assert logada.sessoes() == 1  # nenhuma sessão nova


def test_usr_02_reconfirmar_libera_o_cancelamento(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    _em(relogio, "2026-10-10", "10:16")
    renovada = logada.renovar()
    assert renovada.status_code == 200
    logada.usar(renovada.json()["access"])
    recusa = logada.api.post(
        CANCELAMENTO, {"motivo": "preco_alto", "nome_confirmacao": "Moto Rápida"}, format="json"
    )
    assert recusa.status_code == 403
    assert _erro(recusa) == PEDE_2_ETAPAS
    connection.set_schema_to_public()

    resposta = logada.reconfirmar(codigo=logada.codigo())
    assert resposta.status_code == 200
    logada.usar(resposta.json()["access"])
    assert _cancelar(logada.api).status_code == 200


def test_usr_02_renovar_depois_de_reconfirmar_continua_sem_auth_time(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    _em(relogio, "2026-10-10", "10:03")
    reconfirmado = logada.reconfirmar(codigo=logada.codigo()).json()["access"]
    # O refresh do cookie continua valendo: a reconfirmação não mexe nele (outra aba).
    renovada = logada.renovar()
    assert renovada.status_code == 200
    access = _claims(renovada.json()["access"])
    assert "auth_time" not in access
    assert access["sid"] == _claims(reconfirmado)["sid"]
    assert logada.sessoes() == 1


def test_usr_06_reconfirmar_conta_tentativas_e_bloqueia(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    # Soma com a senha: 2 senhas erradas no login e 3 códigos errados aqui.
    for _ in range(2):
        assert logada.entrar("senha-errada").status_code == 401
    for _ in range(2):
        resposta = logada.reconfirmar(codigo=logada.codigo_errado())
        assert resposta.status_code == 400
        assert resposta.json()["codigo"] == "validacao"
        assert resposta.json()["campos"] == {"codigo": [CODIGO_ERRADO]}
    bloqueou = logada.reconfirmar(codigo=logada.codigo_errado())
    assert bloqueou.status_code == 429
    assert bloqueou.json()["codigo"] == "USR-06"
    assert bloqueou.json()["detalhes"]["tentar_de_novo_em"]
    assert len(logada.eventos("usuario.bloqueado")) == 1
    # Durante o bloqueio, nem o código certo passa, e o bloqueio vale no login.
    assert logada.reconfirmar(codigo=logada.codigo()).status_code == 429
    assert logada.entrar().status_code == 429
    # A sessão aberta continua.
    assert logada.api.get("/api/auth/eu/").status_code == 200
    connection.set_schema_to_public()
    # Passado o bloqueio, o acerto zera a contagem.
    _em(relogio, "2026-10-10", "10:16")
    logada.usar(logada.renovar().json()["access"])
    assert logada.reconfirmar(codigo=logada.codigo()).status_code == 200
    with tenant_context(moto.empresa):
        logada.mariana.refresh_from_db()
        assert (logada.mariana.senhas_erradas, logada.mariana.tentativas_erradas) == (0, 0)
    connection.set_schema_to_public()


def test_usr_02_reconfirmar_com_codigo_de_recuperacao(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    with tenant_context(moto.empresa):
        codigos = dois_fatores.gerar_codigos_recuperacao(logada.mariana)
    connection.set_schema_to_public()

    resposta = logada.reconfirmar(codigo_recuperacao=codigos[0])
    assert resposta.status_code == 200
    assert "auth_time" in _claims(resposta.json()["access"])
    with tenant_context(moto.empresa):
        assert dois_fatores.codigos_restantes(logada.mariana) == 7
    connection.set_schema_to_public()
    assert len(logada.eventos("usuario.usar_codigo_recuperacao")) == 1

    # O mesmo código não vale de novo.
    repetido = logada.reconfirmar(codigo_recuperacao=codigos[0])
    assert repetido.status_code == 400
    assert repetido.json()["campos"] == {"codigo_recuperacao": [CODIGO_ERRADO]}
    falhou = logada.eventos("usuario.reconfirmar_2fa_falhou")
    assert [e.motivo for e in falhou] == ["código de recuperação"]
    # Os dois campos juntos, ou nenhum, também são 400.
    for corpo in ({}, {"codigo": logada.codigo(), "codigo_recuperacao": codigos[1]}):
        assert logada.reconfirmar(**corpo).status_code == 400


def test_usr_02_reconfirmar_sem_autenticador(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    api = moto.api("Rodrigo")
    resposta = api.post(RECONFIRMAR, {"codigo": "123456"}, format="json")
    connection.set_schema_to_public()
    assert resposta.status_code == 409
    assert _erro(resposta) == {
        "codigo": "2fa_inativo",
        "mensagem": "Ative a verificação em 2 etapas primeiro.",
    }
    with tenant_context(moto.empresa):
        rodrigo = type(moto.pessoas["Rodrigo"]).objects.get(pk=moto.pessoas["Rodrigo"].pk)
        assert rodrigo.tentativas_erradas == 0  # antes de contar tentativa
    connection.set_schema_to_public()


def test_plt_07_reconfirmar_recusa_suporte(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    for permissao in ("ver", "ver_editar"):
        resposta = moto.suporte(permissao).post(RECONFIRMAR, {"codigo": "123456"}, format="json")
        connection.set_schema_to_public()
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "PLT-07"


def test_usr_02_reconfirmar_evento_sem_o_codigo(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    logada = Logada(moto)
    errado = logada.codigo_errado()
    assert logada.reconfirmar(codigo=errado).status_code == 400
    certo = logada.codigo()
    assert logada.reconfirmar(codigo=certo).status_code == 200

    falhou, confirmou = logada.eventos("usuario.reconfirmar_2fa_falhou", "usuario.reconfirmar_2fa")
    assert (falhou.acao, confirmou.acao) == (
        "usuario.reconfirmar_2fa_falhou",
        "usuario.reconfirmar_2fa",
    )
    for evento in (falhou, confirmou):
        assert (evento.categoria, evento.regra) == ("seguranca", "USR-02")
        assert evento.objeto_id == logada.mariana.pk
        gravado = f"{evento.antes} {evento.depois} {evento.motivo}"
        assert errado not in gravado and certo not in gravado
    assert falhou.motivo == "código"
    with tenant_context(moto.empresa):
        assert textos.texto(falhou, {}) == textos.Texto("Errou o código do autenticador", "código")
        assert textos.texto(confirmou, {}).resumo == "Confirmou o código do autenticador"
    connection.set_schema_to_public()
