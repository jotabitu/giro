"""T-477 · Criação do schema de empresa com os papéis de banco separados (ADR 0040; PLT-01, AUD-02).

Como em homologação e produção: o `default` atende como `giro_app` (`SET ROLE`, sem DDL) e o alias
`migracao` é uma conexão própria do `giro_migracao` (login, sem superusuário), como o
`infra/postgres/01-papeis.sh` monta. O schema criado pelo `giro_migracao` é confirmado na hora
(DDL em outra conexão), então ele é apagado no fim do módulo; as linhas do `public` voltam com a
transação do teste.

Moto Rápida dos dados de referência: compra em 07 out 2026, administradora Mariana Costa.
"""

import contextlib
import copy
import logging
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, connections, transaction
from django_tenants.utils import schema_context, tenant_context

from apps.auditoria.banco import PAPEL_APP, PAPEL_EXPURGO, PAPEL_MIGRACAO, TABELA
from apps.contas.models import Usuario
from apps.empresas.models import ConfiguracaoEmpresa
from apps.plataforma import banco, compra, privilegios
from apps.plataforma.models import Dominio, Empresa, Origem, PedidoCompra, StatusPedidoCompra
from apps.plataforma.services import RESERVADO, Administrador, reservar_empresa
from comum.estados import transicionar
from comum.tarefas import EmpresaIndisponivel, conferir_empresa_para_tarefa, schemas_das_empresas

from .conftest import CNPJ_MOTO_RAPIDA, HOST_PLATAFORMA, cliente, entrar

SENHA_MIGRACAO = "t477-so-para-o-teste"
SCHEMAS = (
    "t477_papeis",
    "t477_convite",
    "t477_auditoria",
    "t477_futura",
    "t477_conferir",
    "t477_desfaz",
    "t477_semdireito",
    "t477_donofuncao",
    "t477_alheio",
)


def _papeis(cursor: Any, banco_de_teste: str) -> None:
    """Os papéis e as concessões do `01-papeis.sh` no banco de teste (o `public` do teste é do
    superusuário, então o `giro_migracao` recebe DML nele como receberia por ser o dono)."""
    for papel, atributos in (
        (PAPEL_MIGRACAO, f"LOGIN NOSUPERUSER PASSWORD '{SENHA_MIGRACAO}'"),
        (PAPEL_APP, "NOLOGIN NOSUPERUSER"),
        (PAPEL_EXPURGO, "NOLOGIN NOSUPERUSER"),
    ):
        # Papel é global do cluster; dois workers do xdist podem criar ao mesmo tempo (T-429).
        cursor.execute(
            f"DO $$ BEGIN CREATE ROLE {papel} {atributos}; "
            "EXCEPTION WHEN duplicate_object OR unique_violation THEN NULL; END $$"
        )
    with contextlib.suppress(DatabaseError):
        cursor.execute(f"ALTER ROLE {PAPEL_MIGRACAO} LOGIN NOSUPERUSER PASSWORD '{SENHA_MIGRACAO}'")
    cursor.execute(f"GRANT {PAPEL_EXPURGO} TO {PAPEL_MIGRACAO}")
    cursor.execute(f'GRANT CONNECT, CREATE ON DATABASE "{banco_de_teste}" TO {PAPEL_MIGRACAO}')
    cursor.execute(f"GRANT USAGE ON SCHEMA public TO {PAPEL_MIGRACAO}")
    cursor.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {PAPEL_MIGRACAO}"
    )
    cursor.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {PAPEL_MIGRACAO}")


def _apagar_schemas() -> None:
    with connection.cursor() as cursor:
        for nome in SCHEMAS:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{nome}" CASCADE')


@pytest.fixture(scope="module")
def papeis_separados(django_db_setup, django_db_blocker) -> Iterator[None]:
    with django_db_blocker.unblock():
        _apagar_schemas()
        with connection.cursor() as cursor:
            _papeis(cursor, connection.settings_dict["NAME"])
    yield
    with django_db_blocker.unblock():
        _apagar_schemas()


@pytest.fixture
def como_app(papeis_separados, publico) -> Iterator[None]:
    """A conexão `default` como `giro_app` até o fim do teste (a transação do teste desfaz)."""
    with connection.cursor() as cursor:
        cursor.execute(f"SET ROLE {PAPEL_APP}")
    try:
        yield
    finally:
        with contextlib.suppress(DatabaseError), connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


@pytest.fixture
def com_migracao(como_app) -> Iterator[Any]:
    """O alias `migracao` como no worker-banco: outra conexão, logada como `giro_migracao`."""
    from django.conf import settings

    config = copy.deepcopy(connection.settings_dict)
    config.update(USER=PAPEL_MIGRACAO, PASSWORD=SENHA_MIGRACAO)
    config["OPTIONS"] = {**config.get("OPTIONS", {}), "options": "-c lock_timeout=15000"}
    settings.DATABASES["migracao"] = config
    connections.settings["migracao"] = config
    migracao = connections["migracao"]
    # O TestCase do Django recusa abrir conexão de alias que não declarou; aberta aqui, ela segue
    # como a do worker-banco (fora da transação do teste, cada comando confirmado na hora).
    migracao.connect()
    try:
        yield migracao
    finally:
        migracao.close()
        del connections["migracao"]
        connections.settings.pop("migracao", None)
        settings.DATABASES.pop("migracao", None)


def _pedido(planos: Any, relogio: Any, subdominio: str, **campos: Any) -> PedidoCompra:
    """Pedido da compra já confirmado pelo código e em `criando`, como o `confirmar` deixa."""
    agora = relogio.agora
    pedido = PedidoCompra.objects.create(
        status=StatusPedidoCompra.CONFIRMADO,
        plano=planos["Profissional"],
        ciclo="mensal",
        administrador_nome="Mariana Costa",
        administrador_email="mariana@motorapida.com.br",
        cnpj="12345678000195",
        razao_social="Moto Rápida Locações Ltda",
        nome_exibicao="Moto Rápida",
        cidade="Fortaleza",
        uf="CE",
        subdominio=subdominio,
        codigo_enviado_em=agora,
        expira_em=agora + timedelta(hours=24),
        **campos,
    )
    transicionar(pedido, StatusPedidoCompra.CRIANDO, acao="compra.criar_empresa")
    return pedido


def _executar(pedido: PedidoCompra) -> PedidoCompra:
    resultado = compra.executar_pedido_compra(pedido.pk)
    connection.set_schema_to_public()
    pedido.refresh_from_db()
    assert pedido.status == resultado
    return pedido


def _dono_do_schema(nome: str) -> str | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = %s", [nome]
        )
        linha = cursor.fetchone()
    return None if linha is None else str(linha[0])


def _pode(papel: str, consulta: str, *args: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {consulta}", [papel, *args])
        return bool(cursor.fetchone()[0])


def _sqlstate_ao_executar(sql: str) -> str:
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql)
    except DatabaseError as erro:
        return banco.sqlstate(erro)
    return ""


# --- Os 8 testes da ADR 0040 ---


def test_plt_01_cria_empresa_com_papeis_separados(com_migracao, planos, relogio):
    pedido = _executar(_pedido(planos, relogio, "t477-papeis"))
    assert pedido.status == StatusPedidoCompra.PRONTO, pedido.mensagem_falha
    empresa = Empresa.objects.get(subdominio="t477-papeis")
    assert empresa.schema_pronto_em is not None and pedido.empresa_id == empresa.pk
    assert _dono_do_schema("t477_papeis") == PAPEL_MIGRACAO
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        assert cursor.fetchone()[0] == PAPEL_APP  # tudo acima rodou como giro_app
        cursor.execute(
            "SELECT DISTINCT pg_get_userbyid(c.relowner) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 't477_papeis' "
            "AND c.relkind IN ('r', 'S')"
        )
        assert {linha[0] for linha in cursor.fetchall()} == {PAPEL_MIGRACAO}
    with tenant_context(empresa):
        mariana = Usuario.objects.get(email="mariana@motorapida.com.br")
        assert (mariana.perfil, mariana.status) == ("administrador", "convite_pendente")
        configuracao, _ = ConfiguracaoEmpresa.objects.get_or_create(unica=1)  # grava
        ConfiguracaoEmpresa.objects.filter(pk=configuracao.pk).update(exige_2fa_todos=True)
        assert ConfiguracaoEmpresa.objects.get(pk=configuracao.pk).exige_2fa_todos is True
    assert privilegios.problemas("t477_papeis") == []


def test_plt_01_giro_app_nao_cria_schema(como_app, planos, relogio, caplog):
    assert banco.alias_de_migracao() == "default"  # sem a DATABASE_URL_MIGRACAO
    pedido = _pedido(planos, relogio, "t477-semdireito")
    with caplog.at_level(logging.ERROR, logger="apps.plataforma.compra"):
        pedido = _executar(pedido)
    assert pedido.status == StatusPedidoCompra.FALHOU
    assert pedido.mensagem_falha == compra.MENSAGEM_FALHA  # não RESERVADO
    assert "42501" in caplog.text  # InsufficientPrivilege, no log e no Sentry
    assert not Empresa.objects.filter(subdominio="t477-semdireito").exists()
    assert not Dominio.objects.filter(domain__startswith="t477-semdireito.").exists()
    assert _dono_do_schema("t477_semdireito") is None


def test_plt_01_schema_existente_e_reservado(como_app, planos, relogio, monkeypatch):
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
        cursor.execute("CREATE SCHEMA t477_existe")  # de extensão ou ferramenta
        cursor.execute(f"SET ROLE {PAPEL_APP}")

    def sem_ddl(_: int) -> str:
        raise AssertionError("nenhum DDL antes da recusa")

    monkeypatch.setattr(banco, "criar_schema", sem_ddl)
    pedido = _executar(_pedido(planos, relogio, "t477-existe"))
    assert pedido.status == StatusPedidoCompra.FALHOU
    assert pedido.mensagem_falha == RESERVADO
    assert not Empresa.objects.filter(subdominio="t477-existe").exists()


def test_plt_01_falha_desfaz_reserva(com_migracao, planos, relogio, monkeypatch):
    def quebra(_: Any) -> None:
        raise RuntimeError("falha no passo 3")

    monkeypatch.setattr("apps.plataforma.services.criar_primeira_fatura", quebra)
    pedido = _executar(_pedido(planos, relogio, "t477-desfaz"))
    assert pedido.status == StatusPedidoCompra.FALHOU
    assert pedido.mensagem_falha == compra.MENSAGEM_FALHA and pedido.empresa_id is None
    assert not Empresa.objects.filter(subdominio="t477-desfaz").exists()
    assert not Dominio.objects.filter(domain__startswith="t477-desfaz.").exists()
    assert _dono_do_schema("t477_desfaz") is None  # o DROP foi pela conexão de migração


def test_plt_01_convite_depois_do_schema(
    com_migracao, planos, relogio, monkeypatch, django_capture_on_commit_callbacks
):
    vistos: list[tuple[Any, bool]] = []
    from apps.contas import tasks as tarefas_de_contas

    original = tarefas_de_contas.host_da_empresa

    def conferir(schema_name: str) -> str:
        with schema_context("public"):
            pronta = Empresa.objects.get(schema_name=schema_name).schema_pronto_em
        with schema_context(schema_name):
            le = Usuario.objects.filter(email="mariana@motorapida.com.br").exists()
        vistos.append((pronta, le))
        return original(schema_name)

    monkeypatch.setattr(tarefas_de_contas, "host_da_empresa", conferir)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        pedido = _executar(_pedido(planos, relogio, "t477-convite"))
    assert pedido.status == StatusPedidoCompra.PRONTO
    assert callbacks  # o convite saiu no on_commit do passo 3
    assert vistos and all(pronta is not None and le for pronta, le in vistos)


def test_aud_02_auditoria_so_select_insert_em_empresa_nova(com_migracao, planos, relogio):
    _executar(_pedido(planos, relogio, "t477-auditoria"))
    tabela = f"t477_auditoria.{TABELA}"
    assert _pode(PAPEL_APP, "has_table_privilege(%s, %s, 'SELECT')", tabela)
    assert _pode(PAPEL_APP, "has_table_privilege(%s, %s, 'INSERT')", tabela)
    for comando in (
        "UPDATE t477_auditoria.auditoria_eventoauditoria SET acao = 'x'",
        "DELETE FROM t477_auditoria.auditoria_eventoauditoria",
        "TRUNCATE t477_auditoria.auditoria_eventoauditoria",
    ):
        assert _sqlstate_ao_executar(comando) == "42501", comando


def test_aud_02_migracao_futura_mantem_privilegios(com_migracao, planos, relogio):
    _executar(_pedido(planos, relogio, "t477-futura"))
    # Uma migração depois da criação, pelo giro_migracao (a regra padrão do FOR ROLE vale).
    with transaction.atomic(using="migracao"), com_migracao.cursor() as cursor:
        cursor.execute("CREATE TABLE t477_futura.t477_nova (id bigserial PRIMARY KEY, x int)")
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO t477_futura.t477_nova (x) VALUES (1)")
        cursor.execute("UPDATE t477_futura.t477_nova SET x = 2")
    # O `post_migrate` (ou o `conceder_privilegios` do deploy) reaplica; a auditoria segue igual.
    assert privilegios.conceder("t477_futura") is False  # nada a mudar
    tabela = f"t477_futura.{TABELA}"
    assert not _pode(PAPEL_APP, "has_table_privilege(%s, %s, 'UPDATE')", tabela)
    assert privilegios.problemas("t477_futura") == []


def test_conferir_privilegios_acusa_schema_sem_concessao(com_migracao, planos, relogio):
    _executar(_pedido(planos, relogio, "t477-conferir"))
    call_command("conferir_privilegios", "--schema", "t477_conferir")  # passa
    with transaction.atomic(using="migracao"), com_migracao.cursor() as cursor:
        cursor.execute(f"REVOKE INSERT ON ALL TABLES IN SCHEMA t477_conferir FROM {PAPEL_APP}")
        cursor.execute(f"GRANT UPDATE ON t477_conferir.{TABELA} TO {PAPEL_APP}")
        cursor.execute(f"GRANT SELECT ON t477_conferir.{TABELA} TO PUBLIC")
    erros = privilegios.problemas("t477_conferir")
    assert f"t477_conferir.{TABELA}: {PAPEL_APP} com UPDATE" in erros
    assert f"t477_conferir.{TABELA}: PUBLIC com privilégio" in erros
    assert any(e.endswith(f"{PAPEL_APP} sem INSERT") for e in erros)
    with pytest.raises(CommandError, match="problema"):
        call_command("conferir_privilegios", "--schema", "t477_conferir")
    # Regularizar: o conceder devolve o que falta e tira o UPDATE da auditoria (por último).
    with transaction.atomic(using="migracao"), com_migracao.cursor() as cursor:
        cursor.execute("REVOKE SELECT ON t477_conferir.auditoria_eventoauditoria FROM PUBLIC")
    call_command("conceder_privilegios", "--schema", "t477_conferir")
    assert privilegios.problemas("t477_conferir") == []


# --- Item 7 da ADR: a reserva é inalcançável ---


def test_plt_01_empresa_sem_schema_pronto_e_inalcancavel(como_app, planos, relogio, equipe):
    reserva = reservar_empresa(
        razao_social="Moto Rápida Locações Ltda",
        nome_exibicao="Moto Rápida",
        cnpj=CNPJ_MOTO_RAPIDA,
        subdominio="t477-reserva",
        plano=planos["Profissional"],
        administrador=Administrador(nome="Mariana Costa", email="mariana@motorapida.com.br"),
        origem=Origem.COMPRA,
    )
    assert reserva.schema_pronto_em is None
    assert Dominio.objects.filter(tenant=reserva).exists()  # o domínio já existe
    # Subdomínio, login, refresh e convite: 404, como um host desconhecido.
    empresa = cliente("t477-reserva.localhost")
    for rota in ("/api/auth/entrar/", "/api/auth/renovar/", "/api/usuarios/1/reenviar-convite/"):
        assert empresa.post(rota, {}, format="json").status_code == 404, rota
    assert empresa.get("/api/assinatura/").status_code == 404
    connection.set_schema_to_public()
    # Painel da plataforma, busca e suporte.
    token = entrar(*equipe["Você"])
    painel = cliente(HOST_PLATAFORMA, token)
    lista = painel.get("/api/plataforma/empresas/", {"busca": "t477"})
    assert lista.status_code == 200
    assert reserva.pk not in [item["id"] for item in lista.json()["resultados"]]
    assert painel.get(f"/api/plataforma/empresas/{reserva.pk}/").status_code == 404
    suporte = painel.post(
        f"/api/plataforma/empresas/{reserva.pk}/acessos-suporte/",
        {"motivo": "Conferir a reserva", "duracao_minutos": 30, "permissao": "ver"},
        format="json",
    )
    assert suporte.status_code == 404
    connection.set_schema_to_public()
    # As tarefas do beat não a tocam.
    assert "t477_reserva" not in schemas_das_empresas(inclui_suspensas=True)
    with pytest.raises(EmpresaIndisponivel):
        conferir_empresa_para_tarefa("t477_reserva")
    assert reserva.pk not in Empresa.objects.prontas().values_list("pk", flat=True)


# --- Itens 6 e 10 da ADR: o Admin só enfileira; o worker-banco aceita a lista fechada ---


def test_plt_01_admin_so_enfileira_a_criacao(
    publico, planos, relogio, equipe, monkeypatch, django_capture_on_commit_callbacks
):
    from apps.auditoria.models import EventoAuditoria
    from apps.plataforma import tasks
    from comum.erros import Conflito

    enfileirados: list[int] = []
    monkeypatch.setattr(tasks.plataforma_criar_empresa, "delay", enfileirados.append)
    usuario, _ = equipe["Você"]
    usuario.is_staff = True
    dados: dict[str, Any] = {
        "razao_social": "Moto Rápida Locações Ltda",
        "nome_exibicao": "Moto Rápida",
        "cnpj": CNPJ_MOTO_RAPIDA,
        "subdominio": "t477-admin",
        "plano": planos["Profissional"],
        "administrador_nome": "Mariana Costa",
        "administrador_email": "mariana@motorapida.com.br",
    }
    usuario.is_verified = lambda: False  # sessão sem as 2 etapas
    with pytest.raises(Conflito):
        compra.solicitar_criacao_pelo_admin(usuario=usuario, **dados)
    usuario.is_verified = lambda: True
    with django_capture_on_commit_callbacks(execute=True):
        pedido = compra.solicitar_criacao_pelo_admin(usuario=usuario, **dados)
    assert (pedido.origem, pedido.status) == (Origem.ADMIN, StatusPedidoCompra.CRIANDO)
    assert pedido.solicitado_por_id == usuario.pk and enfileirados == [pedido.pk]
    assert pedido.solicitado_verificado_em is not None
    assert not Empresa.objects.filter(subdominio="t477-admin").exists()  # nada na requisição
    assert EventoAuditoria.objects.filter(acao="empresa.solicitar_criacao").exists()


def test_plt_01_worker_banco_recusa_tarefa_fora_da_lista(monkeypatch, settings):
    from comum.worker import TarefaRecusada, conferir_tarefa_do_worker

    conferir_tarefa_do_worker("plataforma_recalcular_uso_de_todas")  # outro worker: passa
    monkeypatch.setenv("GIRO_WORKER", "banco")
    for nome in settings.TAREFAS_DA_FILA_BANCO:
        conferir_tarefa_do_worker(nome)
    with pytest.raises(TarefaRecusada):
        conferir_tarefa_do_worker("plataforma_recalcular_uso_de_todas")
    assert set(settings.CELERY_TASK_ROUTES) == set(settings.TAREFAS_DA_FILA_BANCO)


def test_plt_01_corrida_de_schema_nao_apaga_o_alheio(como_app, planos, relogio, monkeypatch):
    """O schema aparece entre a validação e o CREATE: RESERVADO, a reserva sai e o schema de fora
    fica (a compensação nunca apaga o que não criou)."""
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
        cursor.execute("CREATE SCHEMA t477_corrida")
        cursor.execute(f"SET ROLE {PAPEL_APP}")
    monkeypatch.setattr("apps.plataforma.services.schema_exists", lambda schema: False)
    pedido = _executar(_pedido(planos, relogio, "t477-corrida"))
    assert (pedido.status, pedido.mensagem_falha) == (StatusPedidoCompra.FALHOU, RESERVADO)
    assert not Empresa.objects.filter(subdominio="t477-corrida").exists()
    assert _dono_do_schema("t477_corrida") is not None


# --- Revisão da segurança do PR #600 ---


def test_plt_01_migrate_do_deploy_pula_reserva(como_app, planos, relogio, monkeypatch, caplog):
    """B-1: o migrate do deploy só passa pelas empresas prontas; a reserva vai ao log."""
    from apps.plataforma.management.commands import migrar_empresas

    reserva = reservar_empresa(
        razao_social="Moto Rápida Locações Ltda",
        nome_exibicao="Moto Rápida",
        cnpj=CNPJ_MOTO_RAPIDA,
        subdominio="t477-pulada",
        plano=planos["Profissional"],
        administrador=Administrador(nome="Mariana Costa", email="mariana@motorapida.com.br"),
        origem=Origem.COMPRA,
    )
    migrados: list[str] = []
    monkeypatch.setattr(
        migrar_empresas, "call_command", lambda *_, schema_name, **__: migrados.append(schema_name)
    )
    with caplog.at_level(logging.WARNING):
        call_command("migrar_empresas")
    assert reserva.schema_name not in migrados
    assert set(migrados) == set(
        Empresa.objects.prontas()
        .exclude(schema_name="public")
        .values_list("schema_name", flat=True)
    )
    assert f"schema={reserva.schema_name}" in caplog.text


def test_conferir_privilegios_aceita_o_dono_da_funcao(com_migracao, planos, relogio):
    """A-1: o dono de `auditoria_expurgar` aparece no acldefault e não é concessão a mais."""
    _executar(_pedido(planos, relogio, "t477-donofuncao"))
    funcao = "t477_donofuncao.auditoria_expurgar(date)"
    with connection.cursor() as cursor:
        cursor.execute("RESET ROLE")
        cursor.execute(f"ALTER FUNCTION {funcao} OWNER TO {PAPEL_MIGRACAO}")
        cursor.execute(f"SET ROLE {PAPEL_APP}")
    assert privilegios.problemas("t477_donofuncao") == []


def test_plt_01_retomada_nao_reaproveita_schema_alheio(com_migracao, planos, relogio):
    """A-2: na retomada, schema com o nome da reserva mas de outro dono é RESERVADO e fica."""
    pedido = _pedido(planos, relogio, "t477-alheio")
    reserva = reservar_empresa(
        razao_social="Moto Rápida Locações Ltda",
        nome_exibicao="Moto Rápida",
        cnpj=CNPJ_MOTO_RAPIDA,
        subdominio="t477-alheio",
        plano=planos["Profissional"],
        administrador=Administrador(nome="Mariana Costa", email="mariana@motorapida.com.br"),
        origem=Origem.COMPRA,
        pedido_id=pedido.pk,
    )
    # Confirmado numa conexão própria do superusuário (não da tarefa), visível ao alias migracao.
    import psycopg

    dados = connection.settings_dict
    with psycopg.connect(
        host=dados["HOST"],
        port=dados["PORT"] or 5432,
        dbname=dados["NAME"],
        user=dados["USER"],
        password=dados["PASSWORD"],
        autocommit=True,
    ) as superusuario:
        superusuario.execute(f"CREATE SCHEMA {reserva.schema_name}")
    pedido = _executar(pedido)
    assert (pedido.status, pedido.mensagem_falha) == (StatusPedidoCompra.FALHOU, RESERVADO)
    assert not Empresa.objects.filter(subdominio="t477-alheio").exists()
    assert _dono_do_schema(reserva.schema_name) not in (None, PAPEL_MIGRACAO)
