"""Dado criado na empresa A não aparece na empresa B (ADR 0002)."""

from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.plataforma.models import Empresa
from comum.auditoria import Categoria, registrar_evento
from tests.app_exemplo.models import Pedido


def test_pedido_da_empresa_a_nao_aparece_na_b(empresa_a):
    Pedido.objects.create(cliente="Só da A")
    assert Pedido.objects.filter(cliente="Só da A").count() == 1

    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Pedido.objects.filter(cliente="Só da A").exists()


def test_auditoria_da_empresa_a_nao_aparece_na_b_nem_no_public(empresa_a):
    registrar_evento("teste.isolamento", Categoria.OPERACAO)

    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not EventoAuditoria.objects.filter(acao="teste.isolamento").exists()
    connection.set_schema_to_public()
    assert not EventoAuditoria.objects.filter(acao="teste.isolamento").exists()


def test_usuario_da_empresa_a_nao_existe_na_b(empresa_a):
    Usuario.objects.create_user("carla@motorapida.com.br", "x", nome="Carla", perfil="gerente")

    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Usuario.objects.filter(email="carla@motorapida.com.br").exists()
