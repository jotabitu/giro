"""S-11: nada de uma tarefa passa para a próxima no mesmo processo, e o cache é por empresa."""

from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import connection

from apps.plataforma.models import Empresa
from comum.auditoria import Ator, TipoAtor, _ator, ator_atual
from comum.conexao import conexao


@shared_task(name="teste_deixa_rastro")
def deixa_rastro() -> None:
    # Tarefa mal escrita: entra no schema e define o ator sem restaurar.
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    _ator.set(Ator(tipo=TipoAtor.USUARIO, id=9, nome="Carla Menezes"))


@shared_task(name="teste_olha_contexto")
def olha_contexto() -> dict[str, Any]:
    return {"schema": connection.schema_name, "ator": ator_atual().nome}


def test_ator_nao_vaza_entre_tarefas(publico):
    deixa_rastro.apply()
    assert connection.schema_name == "public"
    assert ator_atual().nome == "Sistema"

    _ator.set(Ator(tipo=TipoAtor.USUARIO, id=9, nome="Carla Menezes"))
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    visto = olha_contexto.apply().get()
    assert visto == {"schema": "public", "ator": "Sistema"}


def test_cache_tem_o_schema_da_empresa_na_chave(empresa_a):
    cache.set("config_empresa", "da A")
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert cache.get("config_empresa") is None
    cache.set("config_empresa", "da B")
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert cache.get("config_empresa") == "da A"


def test_cache_de_producao_tambem_usa_o_schema_na_chave():
    from config.settings import base

    assert base.CACHES["default"]["KEY_FUNCTION"] == "django_tenants.cache.make_key"
    assert settings.CACHES["default"]["KEY_FUNCTION"] == "django_tenants.cache.make_key"


def test_resultado_das_tarefas_nao_e_guardado_por_padrao():
    assert settings.CELERY_TASK_IGNORE_RESULT is True
