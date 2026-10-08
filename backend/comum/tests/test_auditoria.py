import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError, connection, transaction
from django.test import RequestFactory

from apps.auditoria.models import EventoAuditoria, EventoImutavel
from comum.auditoria import (
    Ator,
    Categoria,
    TipoAtor,
    ator_atual,
    auditar,
    registrar_evento,
    usar_ator,
)
from comum.classificacao import mascarar_documento
from comum.middleware import ator_da_requisicao
from tests.app_exemplo.models import Pedido


def _evento(empresa_a):
    return registrar_evento("sessao.entrar", Categoria.SEGURANCA)


def test_aud_01_evento_guarda_ator_acao_objeto_antes_depois_ip_aparelho(empresa_a):
    ator = Ator(tipo=TipoAtor.USUARIO, id=7, nome="Carla Menezes", ip="10.0.0.5", aparelho="UA")
    pedido = Pedido.objects.create(cliente="Larissa", valor_centavos=10_000)

    with usar_ator(ator), auditar(pedido, "pedido.editar", Categoria.OPERACAO, motivo="Ajuste"):
        pedido.valor_centavos = 12_000
        pedido.save()

    evento = EventoAuditoria.objects.get(acao="pedido.editar")
    assert evento.ator_tipo == "usuario"
    assert evento.ator_id == 7
    assert evento.ator_nome == "Carla Menezes"
    assert evento.objeto_tipo == "pedido"
    assert evento.objeto_id == pedido.pk
    assert evento.objeto_codigo == pedido.codigo
    assert evento.antes == {"valor_centavos": 10_000}
    assert evento.depois == {"valor_centavos": 12_000}
    assert evento.ip == "10.0.0.5"
    assert evento.aparelho == "UA"
    assert evento.categoria == "operacao"
    assert evento.motivo == "Ajuste"


def test_aud_01_sem_requisicao_o_ator_e_o_sistema(empresa_a):
    evento = _evento(empresa_a)
    assert evento.ator_tipo == "sistema"
    assert evento.ator_nome == "Sistema"


def test_aud_01_dados_pessoais_gravados_mascarados(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    with auditar(pedido, "pedido.editar", Categoria.OPERACAO):
        pedido.cpf_cliente = "123.218.330-45"
        pedido.save()
    evento = EventoAuditoria.objects.get(acao="pedido.editar")
    assert evento.depois == {"cpf_cliente": "***.218.330-**"}


def test_mascara_de_cpf_aud_04():
    assert mascarar_documento("123.218.330-45") == "***.218.330-**"
    assert mascarar_documento("12321833045") == "***.218.330-**"


def test_aud_01_auditar_volta_junto_com_a_transacao(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    with pytest.raises(RuntimeError), auditar(pedido, "pedido.editar", Categoria.OPERACAO):
        pedido.cliente = "Outra"
        pedido.save()
        raise RuntimeError
    assert not EventoAuditoria.objects.filter(acao="pedido.editar").exists()


def test_aud_01_model_recusa_alterar_e_apagar(empresa_a):
    evento = _evento(empresa_a)
    evento.acao = "outra.coisa"
    with pytest.raises(EventoImutavel):
        evento.save()
    with pytest.raises(EventoImutavel):
        evento.delete()


def test_aud_01_queryset_recusa_update_e_delete(empresa_a):
    _evento(empresa_a)
    with pytest.raises(EventoImutavel):
        EventoAuditoria.objects.all().update(acao="x")
    with pytest.raises(EventoImutavel):
        EventoAuditoria.objects.all().delete()


def test_aud_01_update_direto_no_banco_falha(empresa_a):
    evento = _evento(empresa_a)
    with (
        pytest.raises(DatabaseError, match="imutável"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("UPDATE auditoria_eventoauditoria SET acao = 'x' WHERE id = %s", [evento.pk])


def test_aud_01_delete_direto_no_banco_falha(empresa_a):
    evento = _evento(empresa_a)
    with (
        pytest.raises(DatabaseError, match="imutável"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("DELETE FROM auditoria_eventoauditoria WHERE id = %s", [evento.pk])


def test_aud_01_ligar_expurgo_nao_libera_evento_recente(empresa_a):
    evento = _evento(empresa_a)
    with (
        pytest.raises(DatabaseError, match="imutável"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("SET LOCAL giro.expurgo_auditoria = 'on'")
        cursor.execute("DELETE FROM auditoria_eventoauditoria WHERE id = %s", [evento.pk])


def test_aud_02_expurgo_so_apaga_eventos_com_mais_de_5_anos(empresa_a):
    _evento(empresa_a)
    with connection.cursor() as cursor:
        cursor.execute("SELECT auditoria_expurgar_vencidos()")
        assert cursor.fetchone() == (0,)
    assert EventoAuditoria.objects.count() >= 1


def test_trigger_existe_no_schema_da_empresa_e_no_public(empresa_a):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT event_object_schema FROM information_schema.triggers "
            "WHERE trigger_name = 'auditoria_evento_imutavel' GROUP BY event_object_schema"
        )
        schemas = {linha[0] for linha in cursor.fetchall()}
    assert {"public", "empresa_a", "empresa_b"} <= schemas


def test_ator_da_requisicao_le_usuario_ip_e_aparelho():
    class UsuarioFalso:
        pk = 3
        nome = "Rafael Lima"
        is_authenticated = True

    request = RequestFactory().get("/", HTTP_USER_AGENT="x" * 300, REMOTE_ADDR="10.1.2.3")
    request.user = UsuarioFalso()  # type: ignore[assignment]
    ator = ator_da_requisicao(request)
    assert (ator.tipo, ator.id, ator.nome, ator.ip) == ("usuario", 3, "Rafael Lima", "10.1.2.3")
    assert len(ator.aparelho) == 200

    request.user = AnonymousUser()
    assert ator_da_requisicao(request).tipo == "sistema"


def test_usar_ator_restaura_o_anterior():
    with usar_ator(Ator(tipo=TipoAtor.USUARIO, nome="A")):
        assert ator_atual().nome == "A"
    assert ator_atual().nome == "Sistema"


def test_aud_01_troca_de_cpf_com_mesma_mascara_gera_evento(empresa_a):
    # Achado 1 da T-039: o diff usa os valores reais; a máscara só vale na saída.
    pedido = Pedido.objects.create(cliente="Larissa", cpf_cliente="123.218.330-45")
    with auditar(pedido, "pedido.editar", Categoria.OPERACAO):
        pedido.cpf_cliente = "999.218.330-11"
        pedido.save()
    evento = EventoAuditoria.objects.get(acao="pedido.editar")
    assert evento.antes == {"cpf_cliente": "***.218.330-**"}
    assert evento.depois == {"cpf_cliente": "***.218.330-**"}
