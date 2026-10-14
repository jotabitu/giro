"""T-018 · Tela e consulta da auditoria (docs/qa/criterios/T-018.md, docs/api/auditoria.md).

Roda na `empresa_a` com as pessoas da Moto Rápida e a Filial Centro, relógio em 07 out 2026.
A gravação vem de cada módulo; aqui se testa a consulta e as garantias. Os eventos do caixa e das
despesas entram direto na tabela, nas horas do CA-018-09, com a ação e os campos do contrato; o
resto passa pelos serviços de verdade.
"""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.db import DatabaseError, connection, transaction
from django_tenants.utils import schema_context

from apps.auditoria import services as exportacao
from apps.auditoria.models import EventoAuditoria, EventoImutavel, Exportacao
from apps.contas.models import Usuario
from apps.plataforma.models import AcessoSuporte, Empresa
from apps.plataforma.services import abrir_acesso_suporte, sair_do_suporte
from comum import arquivos, relogio
from comum.auditoria import (
    ATOR_SISTEMA,
    Ator,
    Categoria,
    TipoAtor,
    registrar_evento,
    retrato,
    usar_ator,
)
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from comum.estados import transicionar

from .conftest import HOST_PLATAFORMA, entrar
from .conftest import cliente as cliente_http
from .test_t012_filiais import HOST, MotoRapida
from .test_t014_clientes import JULIANA, _criar, _patch

SP = ZoneInfo("America/Sao_Paulo")
EVENTOS = "/api/auditoria/eventos/"
PLATAFORMA = "/api/plataforma/auditoria/eventos/"
EXPORTACOES = "/api/exportacoes/"


def _em(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=SP)


class Auditoria:
    """A Moto Rápida com os eventos de 06 e 07 out do CA-018-09."""

    def __init__(self, moto: MotoRapida, relogio_: Any) -> None:
        # O schema de teste guarda eventos de execuções anteriores (a auditoria não se apaga):
        # as consultas daqui só olham os eventos que este teste gravou.
        self.desde = EventoAuditoria.objects.order_by("-id").values_list("id", flat=True).first()
        self.moto = moto
        self.relogio = relogio_
        relogio_.em("2026-06-01 09:00")  # a filial nasce fora dos 90 dias da consulta
        self.centro = moto.centro()
        moto._tokens.clear()  # o token de junho já venceu em outubro
        p = moto.pessoas
        Usuario.objects.filter(pk=p["Bruna"].pk).update(nome="Bruna Alves")
        Usuario.objects.filter(pk=p["João"].pk).update(nome="João Silva")
        Usuario.objects.filter(pk=p["Mariana"].pk).update(nome="Mariana Costa")
        self.bruna = Ator(TipoAtor.USUARIO, "Bruna Alves", p["Bruna"].pk, "177.84.10.22", "Chrome")
        self.joao = Ator(TipoAtor.USUARIO, "João Silva", p["João"].pk, "177.84.10.30", "Android")
        self.mariana = Ator(TipoAtor.USUARIO, "Mariana Costa", p["Mariana"].pk)

    def financeiro(self, quando: str, ator: Ator, acao: str, **campos: Any) -> EventoAuditoria:
        """Evento do caixa ou da despesa, como o serviço da T-017 grava."""
        return EventoAuditoria.objects.create(
            ocorrido_em=_em(quando),
            ator_tipo=ator.tipo,
            ator_id=ator.id,
            ator_nome=ator.nome,
            acao=acao,
            categoria=Categoria.FINANCEIRO,
            filial_id=self.centro.pk,
            ip=ator.ip,
            aparelho=ator.aparelho,
            **campos,
        )

    def semear(self) -> None:
        r, p = self.relogio, self.moto.pessoas
        # Antes do período de 7 dias (29 set): não entra na lista.
        r.em("2026-09-29 10:00")
        with usar_ator(self.mariana):
            registrar_evento("usuario.editar", Categoria.SEGURANCA, objeto=p["Lúcia"])
        r.em("2026-10-06 18:10")
        with usar_ator(self.mariana):
            joao = Usuario.objects.get(pk=p["João"].pk)
            registrar_evento(
                "usuario.convidar",
                Categoria.SEGURANCA,
                objeto=joao,
                depois=retrato(joao),
                regra="USR-01",
            )
        self.financeiro(
            "2026-10-07 07:55",
            self.bruna,
            "caixa.abrir",
            objeto_tipo="caixa",
            objeto_id=240,
            depois={"troco_centavos": 20000, "status": "aberto"},
            regra="FIN-07",
        )
        r.em("2026-10-07 08:02")
        with usar_ator(ATOR_SISTEMA):
            registrar_evento(
                "usuario.bloqueado",
                Categoria.SEGURANCA,
                objeto=p["Rodrigo"],
                depois={"bloqueado_ate": _em("2026-10-07 08:17")},
                motivo="5 tentativas erradas",
                regra="USR-06",
            )
        self.financeiro(
            "2026-10-07 08:55",
            self.joao,
            "despesa.lancar",
            objeto_tipo="despesa",
            objeto_id=91,
            depois={
                "valor_centavos": 120000,
                "descricao": "Pneus PMZ-3E17",
                "status": "aguardando_aprovacao",
            },
            regra="FIN-05",
        )
        EventoAuditoria.objects.create(
            ocorrido_em=_em("2026-10-07 09:15"),
            ator_tipo=TipoAtor.USUARIO,
            ator_id=p["Bruna"].pk,
            ator_nome="Bruna Alves",
            acao="locacao.criar",
            categoria=Categoria.OPERACAO,
            objeto_tipo="locacao",
            objeto_id=2856,
            objeto_codigo="LOC-2856",
            filial_id=self.centro.pk,
        )
        self.sangria = self.financeiro(
            "2026-10-07 10:30",
            self.bruna,
            "caixa.sangria",
            objeto_tipo="caixa",
            objeto_id=240,
            depois={"valor_centavos": 50000, "tipo": "sangria"},
            regra="FIN-07",
        )
        self.financeiro(
            "2026-10-07 11:20",
            self.bruna,
            "despesa.lancar",
            objeto_tipo="despesa",
            objeto_id=92,
            depois={"valor_centavos": 4800, "descricao": "Óleo QXA-4B21", "status": "paga"},
            regra="FIN-05",
        )
        r.em("2026-10-07 13:40")
        self.acesso = abrir_suporte(self.moto, "ver")
        r.em("2026-10-07 13:52")
        sair_do_suporte(self.acesso.pk)
        connection.set_tenant(self.moto.empresa)
        r.em("2026-10-07 14:00")

    def lista(self, consulta: str = "", quem: str = "Mariana") -> list[dict[str, Any]]:
        separador = "&" if "?" in consulta else "?"
        resposta = self.moto.api(quem).get(f"{EVENTOS}{consulta}{separador}tamanho=100")
        assert resposta.status_code == 200, resposta.json()
        return [e for e in resposta.json()["resultados"] if e["id"] > (self.desde or 0)]


def diego() -> Usuario:
    with schema_context("public"):
        pessoa = Usuario.objects.filter(email="diego@girolocadoras.com.br").first()
        if pessoa is None:
            pessoa = Usuario.objects.create_user(
                "diego@girolocadoras.com.br",
                "senha-forte-123",
                nome="Diego Santos",
                funcao_plataforma="suporte",
            )
        return pessoa


def abrir_suporte(moto: MotoRapida, permissao: str) -> AcessoSuporte:
    acesso, _ = abrir_acesso_suporte(
        Empresa.objects.get(pk=moto.empresa.pk),
        diego(),
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao=permissao,
    )
    connection.set_tenant(moto.empresa)
    return acesso


def token_de_suporte(moto: MotoRapida, permissao: str) -> Any:
    _, token = abrir_acesso_suporte(
        Empresa.objects.get(pk=moto.empresa.pk),
        diego(),
        motivo="Chamado #1042",
        duracao_minutos=30,
        permissao=permissao,
    )
    connection.set_tenant(moto.empresa)
    return cliente_http(HOST, str(token))


@pytest.fixture
def moto(empresa_a, planos, relogio_jwt) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def aud(moto, relogio_jwt) -> Auditoria:
    auditoria = Auditoria(moto, relogio_jwt)
    auditoria.semear()
    return auditoria


# --- Imutável (AUD-01, ADR 0010) ---


ALTERAR = "UPDATE auditoria_eventoauditoria SET acao = 'x' WHERE id = %s"
APAGAR = "DELETE FROM auditoria_eventoauditoria WHERE id = %s"


def _falha_no_banco(sql: str, params: list[Any], papel: str = "") -> None:
    with pytest.raises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
        if papel:
            cursor.execute(f"SET ROLE {papel}")
        cursor.execute(sql, params)


def test_aud_01_ca_018_01_ninguem_edita_nem_apaga(aud):
    evento = aud.sangria
    evento.acao = "caixa.outra"
    with pytest.raises(EventoImutavel):
        evento.save()
    with pytest.raises(EventoImutavel):
        evento.delete()
    with pytest.raises(EventoImutavel):
        EventoAuditoria.objects.filter(pk=evento.pk).update(acao="x")
    with pytest.raises(EventoImutavel):
        EventoAuditoria.objects.filter(pk=evento.pk).delete()

    for papel in ("", "giro_app"):
        _falha_no_banco(ALTERAR, [evento.pk], papel)
        _falha_no_banco(APAGAR, [evento.pk], papel)
    with schema_context("public"):
        publico = EventoAuditoria.objects.filter(acao="suporte.entrar").first()
        assert publico is not None
        for papel in ("", "giro_app"):
            _falha_no_banco(ALTERAR, [publico.pk], papel)
            _falha_no_banco(APAGAR, [publico.pk], papel)
    connection.set_tenant(aud.moto.empresa)
    assert EventoAuditoria.objects.get(pk=evento.pk).acao == "caixa.sangria"

    api = aud.moto.api()
    for rota in (EVENTOS, f"{EVENTOS}{evento.pk}/"):
        assert api.post(rota, {}, format="json").status_code == 405
        assert api.put(rota, {}, format="json").status_code == 405
        assert api.patch(rota, {}, format="json").status_code == 405
        assert api.delete(rota).status_code == 405


def test_aud_01_ca_018_01_nem_o_dono_da_plataforma_escreve(publico, equipe, relogio_jwt):
    dono = cliente_http(HOST_PLATAFORMA, entrar(*equipe["Você"]))
    evento = registrar_evento("plano.editar", Categoria.CONFIGURACOES)
    for rota in (PLATAFORMA, f"{PLATAFORMA}{evento.pk}/"):
        assert dono.post(rota, {}, format="json").status_code == 405
        assert dono.put(rota, {}, format="json").status_code == 405
        assert dono.patch(rota, {}, format="json").status_code == 405
        assert dono.delete(rota).status_code == 405


def test_aud_02_ca_018_02_expurgo_de_5_anos(empresa_a):
    """O banco usa o relógio de verdade: o limite é o de 07 out 2026 menos 5 anos."""
    antigo = EventoAuditoria.objects.create(
        ocorrido_em=_em("2021-10-06 10:00"),
        ator_tipo="sistema",
        ator_nome="Sistema",
        acao="teste.antigo",
        categoria=Categoria.SEGURANCA,
    )
    fica = EventoAuditoria.objects.create(
        ocorrido_em=_em("2021-10-08 10:00"),
        ator_tipo="sistema",
        ator_nome="Sistema",
        acao="teste.antigo",
        categoria=Categoria.SEGURANCA,
    )
    limite = date(2021, 10, 7)  # 07 out 2026 menos 5 anos
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET ROLE giro_app")
        cursor.execute("SELECT auditoria_expurgar(%s)", [limite])
        assert cursor.fetchone() == (1,)
        cursor.execute("RESET ROLE")
    assert not EventoAuditoria.objects.filter(pk=antigo.pk).exists()
    assert EventoAuditoria.objects.filter(pk=fica.pk).exists()
    _falha_no_banco(APAGAR, [fica.pk], "giro_app")


# --- O que cada evento guarda (AUD-01) ---


def test_aud_01_ca_018_03_campos_do_evento(aud):
    evento = aud.sangria
    assert evento.ocorrido_em == datetime(2026, 10, 7, 13, 30, tzinfo=ZoneInfo("UTC"))
    item = next(e for e in aud.lista() if e["id"] == evento.pk)
    assert item["ocorrido_em"] == "2026-10-07T13:30:00Z"  # 10:30 em São Paulo
    assert item["ator"] == {
        "tipo": "usuario",
        "id": aud.moto.pessoas["Bruna"].pk,
        "nome": "Bruna Alves",
        "iniciais": "BA",
    }
    assert item["acao"] == "caixa.sangria"
    assert item["categoria"] == "financeiro"
    assert item["resumo"] == "Fez sangria de R$ 500,00"
    assert item["objeto"] == {"tipo": "caixa", "id": 240, "codigo": None, "filial": "Filial Centro"}
    assert item["suporte"] is None

    detalhe = aud.moto.api().get(f"{EVENTOS}{evento.pk}/").json()
    assert detalhe["depois"] == {"valor_centavos": 50000, "tipo": "sangria"}
    assert detalhe["antes"] == {}
    assert (detalhe["ip"], detalhe["aparelho"]) == ("177.84.10.22", "Chrome")


def test_aud_01_ca_018_04_nome_do_ator_nao_muda(aud):
    Usuario.objects.filter(pk=aud.moto.pessoas["Bruna"].pk).update(nome="Bruna Alves Lima")
    nomes = {e["ator"]["nome"] for e in aud.lista("?categoria=financeiro") if e["ator"]["id"]}
    assert "Bruna Alves" in nomes
    assert "Bruna Alves Lima" not in nomes


def test_aud_01_ca_018_05_ator_sistema_e_suporte(moto, relogio, django_capture_on_commit_callbacks):
    moto.centro()
    # Fechamento automático do caixa (AUT-08): tarefa do Celery entra como Sistema com a regra.
    from comum.tarefas import _montar_ator

    with usar_ator(_montar_ator(None, "AUT-08")):
        fechamento = registrar_evento("caixa.fechar_sem_conferencia", Categoria.FINANCEIRO)
    assert (fechamento.ator_tipo, fechamento.ator_nome, fechamento.regra) == (
        "sistema",
        "Sistema",
        "AUT-08",
    )

    # 5 senhas erradas de Rodrigo pela API: o bloqueio é do Sistema, na categoria segurança.
    with django_capture_on_commit_callbacks(execute=True):
        for _ in range(5):
            cliente_http(HOST).post(
                "/api/auth/entrar/",
                {"email": "rodrigo@motorapida.com.br", "senha": "senha-errada-1"},
                format="json",
            )
    connection.set_tenant(moto.empresa)
    bloqueio = EventoAuditoria.objects.get(acao="usuario.bloqueado")
    assert (bloqueio.ator_tipo, bloqueio.ator_nome, bloqueio.categoria) == (
        "sistema",
        "Sistema",
        "seguranca",
    )
    item = next(e for e in moto_lista(moto) if e["acao"] == "usuario.bloqueado")
    assert item["ator"]["nome"] == "Sistema"
    assert item["resumo"] == (
        "Login bloqueado após 5 tentativas erradas de rodrigo@motorapida.com.br"
    )

    # Escrita com o token de suporte "ver e editar": ator Suporte Giro com o acesso.
    suporte = token_de_suporte(moto, "ver_editar")
    criado = suporte.post("/api/clientes/", {**JULIANA}, format="json")
    assert criado.status_code == 201, criado.json()
    connection.set_tenant(moto.empresa)
    escrita = EventoAuditoria.objects.filter(objeto_tipo="cliente").latest("id")
    acesso = AcessoSuporte.objects.latest("id")
    assert (escrita.ator_tipo, escrita.ator_nome) == ("suporte", "Diego Santos")
    assert escrita.acesso_suporte_id == acesso.pk


def moto_lista(moto: MotoRapida, consulta: str = "") -> list[dict[str, Any]]:
    resposta = moto.api().get(f"{EVENTOS}{consulta}")
    assert resposta.status_code == 200, resposta.json()
    return list(resposta.json()["resultados"])


def test_aud_09_ca_018_06_dados_pessoais_mascarados(moto):
    moto.centro()
    juliana = _criar(moto, JULIANA)
    novo_endereco = {**JULIANA["endereco"], "logradouro": "Rua Barão do Rio Branco"}
    editado = _patch(
        moto,
        juliana["id"],
        {"documento": "741.552.016-58", "endereco": novo_endereco},
        quem="Mariana",
    )
    assert editado.status_code == 200, editado.json()
    evento = EventoAuditoria.objects.filter(objeto_tipo="cliente", acao="cliente.editar").get()
    detalhe = moto.api().get(f"{EVENTOS}{evento.pk}/").json()
    # ADR 0014 (item 3): o CPF é cifrado e sai omitido, mais restrito que a máscara do critério
    # ([divergência] no backlog para o produto).
    assert detalhe["depois"]["documento"] == {"alterado": True}
    assert detalhe["antes"]["logradouro"] == "***" and detalhe["depois"]["logradouro"] == "***"
    assert "Barão" not in str(detalhe["depois"]) and "Mororó" not in str(detalhe["antes"])
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM auditoria_eventoauditoria WHERE "
            "concat_ws(' ', antes::text, depois::text, motivo, objeto_codigo) LIKE %s "
            "OR concat_ws(' ', antes::text, depois::text) LIKE %s",
            ["%05221833018%", "%04512345678%"],
        )
        assert cursor.fetchone() == (0,)


def test_aud_01_ca_018_07_uma_transicao_um_evento(aud):
    exportado = Exportacao.objects.create(itens=["auditoria"], formato="csv")
    antes = EventoAuditoria.objects.count()
    transicionar(exportado, "falhou", acao="exportacao.falhar")
    assert EventoAuditoria.objects.count() == antes + 1
    assert (
        EventoAuditoria.objects.filter(acao="exportacao.falhar", objeto_id=exportado.pk).count()
        == 1
    )

    outro = Exportacao.objects.create(itens=["auditoria"], formato="csv")
    with pytest.raises(RuntimeError), transaction.atomic():
        transicionar(outro, "pronta", acao="exportacao.concluir")
        raise RuntimeError("falhou depois da transição")
    outro.refresh_from_db()
    assert outro.status == "na_fila"
    assert not EventoAuditoria.objects.filter(acao="exportacao.concluir").exists()


# --- Consulta na empresa (Admin-Auditoria) ---


def test_aud_02_ca_018_08_so_o_administrador(aud):
    assert aud.moto.api("Mariana").get(EVENTOS).status_code == 200
    for nome in ("Rodrigo", "Bruna", "João", "Lúcia"):
        assert aud.moto.api(nome).get(EVENTOS).status_code == 403
        assert aud.moto.api(nome).get("/api/auditoria/pessoas/").status_code == 403
        # O financeiro vê as exportações das despesas (decisão do dono de 13 out 2026, T-177).
        esperado = 200 if nome == "Lúcia" else 403
        assert aud.moto.api(nome).get(EXPORTACOES).status_code == esperado
    suporte = token_de_suporte(aud.moto, "ver_editar")
    for rota in (EVENTOS, "/api/auditoria/pessoas/", EXPORTACOES):
        recusa = suporte.get(rota)
        assert recusa.status_code == 403
        assert recusa.json()["codigo"] == "PLT-07"


SEED = [
    ("2026-10-07T16:52:00Z", "Suporte Giro", "Saiu do modo suporte", "suporte"),
    ("2026-10-07T16:40:00Z", "Suporte Giro", "Entrou como suporte", "suporte"),
    ("2026-10-07T14:20:00Z", "Bruna Alves", "Lançou despesa de R$ 48,00", "financeiro"),
    ("2026-10-07T13:30:00Z", "Bruna Alves", "Fez sangria de R$ 500,00", "financeiro"),
    ("2026-10-07T12:15:00Z", "Bruna Alves", "Criou a locação LOC-2856", "operacao"),
    ("2026-10-07T11:55:00Z", "João Silva", "Lançou despesa de R$ 1.200,00", "financeiro"),
    (
        "2026-10-07T11:02:00Z",
        "Sistema",
        "Login bloqueado após 5 tentativas erradas de rodrigo@motorapida.com.br",
        "seguranca",
    ),
    ("2026-10-07T10:55:00Z", "Bruna Alves", "Abriu o caixa com troco de R$ 200,00", "financeiro"),
    ("2026-10-06T21:10:00Z", "Mariana Costa", "Convidou João Silva", "seguranca"),
]


def test_aud_02_ca_018_09_lista_do_seed(aud):
    lista = aud.lista()
    assert [(e["ocorrido_em"], e["ator"]["nome"], e["resumo"], e["categoria"]) for e in lista] == (
        SEED
    )
    detalhes = [e["detalhe"] for e in lista]
    assert detalhes[0] == "12 min · só ver · nenhuma alteração"
    assert detalhes[1] == "Chamado #1042 · só ver"
    assert detalhes[2] == "Óleo QXA-4B21 · pago no caixa"
    assert detalhes[5] == "Pneus PMZ-3E17 · aguardando gerente"
    assert detalhes[8] == "Vistoriador"
    assert lista[0]["suporte"]["atendente"] == "Diego Santos"


def test_aud_02_ca_018_10_filtros(aud):
    def resumos(consulta: str) -> list[str]:
        return [e["resumo"] for e in aud.lista(consulta)]

    financeiro = resumos("?categoria=financeiro")
    assert len(financeiro) == 4
    assert len(resumos("?categoria=suporte")) == 2
    assert {e["ator"]["nome"] for e in aud.lista("?categoria=suporte")} == {"Suporte Giro"}
    assert sorted(resumos("?categoria=seguranca")) == [
        "Convidou João Silva",
        "Login bloqueado após 5 tentativas erradas de rodrigo@motorapida.com.br",
    ]
    bruna = aud.moto.pessoas["Bruna"].pk
    assert len(resumos(f"?ator={bruna}")) == 4
    assert len(resumos(f"?ator={bruna}&categoria=financeiro")) == 3  # os filtros combinam
    assert len(resumos("?ator_tipo=sistema")) == 1
    assert "Editou o usuário" not in " ".join(resumos("?periodo=7d"))  # 29 set fica de fora
    assert len(resumos("?de=2026-09-29&ate=2026-09-29")) == 1
    assert resumos("?objeto_codigo=LOC-2856") == ["Criou a locação LOC-2856"]
    assert resumos("?objeto_tipo=caixa&objeto_id=240") == [
        "Fez sangria de R$ 500,00",
        "Abriu o caixa com troco de R$ 200,00",
    ]
    assert len(resumos(f"?filial={aud.centro.pk}")) == 5
    invalido = aud.moto.api().get(f"{EVENTOS}?categoria=outra")
    assert invalido.status_code == 400 and "categoria" in invalido.json()["campos"]

    pessoas = aud.moto.api().get("/api/auditoria/pessoas/").json()["resultados"]
    nossas = {"Bruna Alves", "João Silva", "Mariana Costa", "Sistema", "Suporte Giro"}
    assert [p["nome"] for p in pessoas if p["nome"] in nossas] == [
        "Bruna Alves",
        "João Silva",
        "Mariana Costa",
        "Sistema",
        "Suporte Giro",
    ]


def test_aud_03_ca_018_11_suporte_em_destaque(aud):
    entrada, saida = (e for e in aud.lista("?categoria=suporte")[::-1])
    for item in (entrada, saida):
        assert item["suporte"] == {
            "atendente": "Diego Santos",
            "motivo": "Chamado #1042",
            "permissao": "ver",
            "acesso_suporte_id": aud.acesso.pk,
        }
    # Escrita durante um acesso "ver e editar": marcada, com o atendente.
    suporte = token_de_suporte(aud.moto, "ver_editar")
    assert suporte.post("/api/clientes/", {**JULIANA}, format="json").status_code == 201
    connection.set_tenant(aud.moto.empresa)
    escrita = next(e for e in aud.lista("?ator_tipo=suporte") if e["acao"] == "cliente.cadastrar")
    assert escrita["ator"]["nome"] == "Suporte Giro"
    assert escrita["suporte"]["atendente"] == "Diego Santos"
    assert escrita["suporte"]["permissao"] == "ver_editar"


def test_aud_02_ca_018_12_escopo_da_empresa(aud, empresa_b):
    with usar_ator(ATOR_SISTEMA):
        registrar_evento("usuario.editar", Categoria.SEGURANCA)  # na empresa B
    with schema_context("public"):
        registrar_evento("plano.editar", Categoria.CONFIGURACOES)  # da plataforma
    connection.set_tenant(aud.moto.empresa)
    eventos = aud.lista("?periodo=90d")
    acoes = {e["acao"] for e in eventos}
    assert "plano.editar" not in acoes and "usuario.editar" in acoes
    assert acoes >= {"suporte.entrar", "suporte.sair"}
    assert len(eventos) == 10  # os 9 do seed e o de 29 set; nada da empresa B


def test_aud_07_ca_018_13_exportar(aud, django_capture_on_commit_callbacks):
    _criar(aud.moto, JULIANA)
    with usar_ator(aud.mariana):
        registrar_evento("usuario.editar", Categoria.SEGURANCA, motivo="=HYPERLINK(1)")
    corpo = {"itens": ["auditoria"], "formato": "csv", "periodo": None}
    for nome in ("Rodrigo", "Lúcia"):
        assert aud.moto.api(nome).post(EXPORTACOES, corpo, format="json").status_code == 403
    with django_capture_on_commit_callbacks(execute=True):
        pedido = aud.moto.api().post(EXPORTACOES, corpo, format="json")
    connection.set_tenant(aud.moto.empresa)
    assert pedido.status_code == 202, pedido.json()
    assert pedido.json()["status"] == "na_fila"
    feita = Exportacao.objects.get(pk=pedido.json()["id"])
    assert feita.status == "pronta"
    assert feita.expira_em == relogio.agora() + timedelta(days=7)
    conteudo = arquivos.guardados[feita.arquivo][0].decode("utf-8-sig")
    assert "Fez sangria de R$ 500,00" in conteudo
    assert "05221833018" not in conteudo and "04512345678" not in conteudo
    celulas = [c for linha in csv.reader(io.StringIO(conteudo), delimiter=";") for c in linha]
    assert "'=HYPERLINK(1)" in celulas
    assert not any(c.startswith(("=", "+", "-", "@")) for c in celulas)
    aviso = [m for m in mail.outbox if "exportação" in m.subject]
    assert aviso and aviso[-1].to == ["mariana@motorapida.com.br"]

    recentes = aud.moto.api().get(EXPORTACOES).json()["resultados"]
    assert recentes[0]["solicitada_por"] == "Mariana Costa"
    assert recentes[0]["status"] == "pronta"

    baixar = f"{EXPORTACOES}{feita.pk}/baixar/"
    assert aud.moto.api("Rodrigo").get(baixar).status_code == 403
    assert cliente_http(HOST).get(baixar).status_code == 401
    link = aud.moto.api().get(baixar)
    assert link.status_code == 302
    assert link["Location"].startswith("https://arquivos.invalid/")
    assert EventoAuditoria.objects.filter(acao="exportacao.baixar", objeto_id=feita.pk).count() == 1

    aud.relogio.em("2026-10-14 14:01")
    aud.moto._tokens.clear()  # novo login depois dos 7 dias
    vencida = aud.moto.api().get(baixar)
    assert vencida.status_code == 410
    assert vencida.json()["codigo"] == "exportacao_expirada"
    feita.refresh_from_db()
    assert feita.status == "expirada"


def test_aud_07_ca_018_13_backup_completo_pede_2_etapas_recentes(aud):
    corpo: dict[str, Any] = {"itens": [], "formato": "zip", "periodo": None}
    # Token renovado (rotação): as 2 etapas não são recentes, falta o `auth_time`.
    mariana = aud.moto.pessoas["Mariana"]
    login = emitir_tokens(mariana, AMR_SENHA_E_CODIGO)
    renovado = emitir_tokens(mariana, AMR_SENHA_E_CODIGO, sid=login["sid"]).access_token
    assert "auth_time" in login.access_token and "auth_time" not in renovado
    recusa = cliente_http(HOST, str(renovado)).post(EXPORTACOES, corpo, format="json")
    assert recusa.status_code == 403
    assert recusa.json()["codigo"] == "2fa_recente"
    # Com o código confirmado agora, passa da conferência (a geração do zip vem depois).
    assert aud.moto.api().post(EXPORTACOES, corpo, format="json").json()["codigo"] == (
        "exportacao_indisponivel"
    )
    agora = relogio.agora().timestamp()
    assert exportacao.dois_fatores_recente({"amr": ["pwd", "otp"], "auth_time": agora - 900})
    assert not exportacao.dois_fatores_recente({"amr": ["pwd", "otp"], "auth_time": agora - 901})
    assert not exportacao.dois_fatores_recente({"amr": ["pwd"], "auth_time": agora})


# --- Consulta na plataforma (Plat-Auditoria) ---


def test_aud_03_ca_018_14_auditoria_de_acessos(equipe, aud):
    with schema_context("public"):
        moto_id = aud.moto.empresa.pk
        bloqueado = EventoAuditoria.objects.create(
            ocorrido_em=_em("2026-10-07 08:02"),
            ator_tipo="sistema",
            ator_nome="Sistema",
            acao="usuario.bloqueado",
            categoria=Categoria.SEGURANCA,
            motivo="3 códigos errados",
            regra="PLT-08",
            ip="177.84.10.22",
        )
        EventoAuditoria.objects.create(
            ocorrido_em=_em("2026-10-06 09:00"),
            ator_tipo="usuario",
            ator_nome="Você",
            acao="usuario.convidar",
            categoria=Categoria.SEGURANCA,
            depois={"nome": "Larissa Melo", "funcao_plataforma": "sucesso"},
        )
    connection.set_schema_to_public()
    dono = cliente_http(HOST_PLATAFORMA, entrar(*equipe["Você"]))
    corpo = dono.get(PLATAFORMA).json()
    resumos = [e["resumo"] for e in corpo["resultados"]]
    assert "Entrou como suporte" in resumos and "Convidou Larissa Melo" in resumos
    bloqueio = next(e for e in corpo["resultados"] if e["id"] == bloqueado.pk)
    assert bloqueio["resumo"] == "Login bloqueado após 3 códigos errados"
    assert bloqueio["detalhe"] == "PLT-08 · 177.84.x.x"
    entrada = next(e for e in corpo["resultados"] if e["acao"] == "suporte.entrar")
    assert entrada["ocorrido_em"] == "2026-10-07T16:40:00Z"
    assert entrada["empresa"] == {"id": moto_id, "nome_exibicao": "Empresa A"}
    assert entrada["detalhe"] == "Chamado #1042 · só ver"
    assert corpo["indicadores"]["acessos_suporte_30d"] == 1

    suporte = dono.get(f"{PLATAFORMA}?categoria=suporte&empresa={moto_id}").json()["resultados"]
    assert [e["acao"] for e in suporte] == ["suporte.sair", "suporte.entrar"]
    assert dono.get(f"{PLATAFORMA}?empresa=999999").json()["resultados"] == []


def test_plt_09_ca_018_15_so_o_dono_ve(publico, equipe):
    for nome in ("Diego Santos", "Paula Andrade", "Caio Ribeiro"):
        api = cliente_http(HOST_PLATAFORMA, entrar(*equipe[nome]))
        recusa = api.get(PLATAFORMA)
        assert recusa.status_code == 403
        assert recusa.json()["codigo"] == "PLT-09"
    assert cliente_http(HOST_PLATAFORMA, entrar(*equipe["Você"])).get(PLATAFORMA).status_code == 200


def test_aud_03_ca_018_16_plataforma_nao_le_a_empresa(equipe, aud):
    connection.set_schema_to_public()
    dono = cliente_http(HOST_PLATAFORMA, entrar(*equipe["Você"]))
    acoes = {e["acao"] for e in dono.get(f"{PLATAFORMA}?periodo=30d").json()["resultados"]}
    assert {"suporte.entrar", "suporte.sair"} <= acoes
    assert not acoes & {"caixa.sangria", "caixa.abrir", "despesa.lancar", "locacao.criar"}
    with schema_context("public"):
        assert not EventoAuditoria.objects.filter(acao="caixa.sangria").exists()
