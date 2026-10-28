"""S-11: nada de uma tarefa passa para a próxima no mesmo processo, e o cache é por empresa."""

from typing import Any

import pytest
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import connection

from apps.plataforma.models import Empresa
from comum.auditoria import Ator, TipoAtor, _ator, ator_atual
from comum.conexao import conexao


@pytest.fixture(autouse=True)
def _ator_limpo():
    yield
    _ator.set(None)


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


class _TarefaFalsa:
    """Só o que o sinal lê: `request.is_eager`."""

    def __init__(self, eager: bool) -> None:
        self.request = type("Pedido", (), {"is_eager": eager})()


def _rodar_sinais(eager: bool, id_tarefa: str) -> None:
    from celery.signals import task_postrun, task_prerun

    tarefa = _TarefaFalsa(eager)
    task_prerun.send(sender=tarefa, task_id=id_tarefa)
    # A tarefa mal escrita deixa rastro.
    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    _ator.set(Ator(tipo=TipoAtor.USUARIO, id=9, nome="Carla Menezes"))
    task_postrun.send(sender=tarefa, task_id=id_tarefa)


def test_worker_real_limpa_e_nao_devolve_o_contexto(empresa_a):
    """S-11: tarefa do worker (não eager) termina no public e como Sistema, como sempre."""
    _ator.set(Ator(tipo=TipoAtor.USUARIO, id=1, nome="Quem chamou"))
    _rodar_sinais(eager=False, id_tarefa="worker-real")
    assert connection.schema_name == "public"
    assert ator_atual().nome == "Sistema"


def test_tarefa_eager_comeca_limpa_e_devolve_o_contexto_de_quem_chamou(empresa_a):
    """T-281: eager roda na conexão do chamador. Começa limpa, o rastro dela não vaza, e o schema
    e o ator de quem chamou voltam no fim."""
    from celery.signals import task_prerun

    _ator.set(Ator(tipo=TipoAtor.USUARIO, id=1, nome="Quem chamou"))
    task_prerun.send(sender=_TarefaFalsa(True), task_id="eager-1")
    assert connection.schema_name == "public"
    assert ator_atual().nome == "Sistema"
    # termina como a tarefa mal escrita do teste acima
    from celery.signals import task_postrun

    conexao().set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    task_postrun.send(sender=_TarefaFalsa(True), task_id="eager-1")
    assert connection.schema_name == "empresa_a"
    assert ator_atual().nome == "Quem chamou"


def test_tarefa_eager_que_troca_de_schema_nao_vaza_para_o_chamador(empresa_a):
    _rodar_sinais(eager=True, id_tarefa="eager-2")
    assert connection.schema_name == "empresa_a"
    assert ator_atual().nome == "Sistema"
