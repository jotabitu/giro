from typing import Any

import pytest
from django.db import connection

from apps.plataforma.models import Empresa
from comum.auditoria import ator_atual
from comum.tarefas import para_cada_empresa, regra_da_tarefa, tarefa_de_empresa


class TarefaFalsa:
    def __init__(self) -> None:
        self.chamadas: list[tuple[Any, ...]] = []

    def delay(self, *args: Any, **kwargs: Any) -> None:
        self.chamadas.append(args)


def test_regra_vem_do_nome_da_tarefa():
    assert regra_da_tarefa("aut_02_marcar_devolucao_atrasada") == "AUT-02"
    assert regra_da_tarefa("limpar_cache") == ""


def test_tarefa_de_empresa_entra_no_schema_com_ator_sistema(publico):
    visto: dict[str, Any] = {}

    @tarefa_de_empresa
    def aut_02_marcar_devolucao_atrasada(schema_name: str) -> None:
        visto["schema"] = connection.schema_name
        visto["ator"] = ator_atual()

    aut_02_marcar_devolucao_atrasada("empresa_b")

    assert visto["schema"] == "empresa_b"
    assert visto["ator"].tipo == "sistema"
    assert visto["ator"].regra == "AUT-02"
    assert connection.schema_name == "public"


def test_tarefa_de_empresa_sem_schema_e_erro(publico):
    @tarefa_de_empresa
    def aut_99_qualquer(schema_name: str) -> None:
        pass

    with pytest.raises(TypeError):
        aut_99_qualquer("public")


def test_para_cada_empresa_enfileira_so_as_que_operam(publico):
    tarefa = TarefaFalsa()
    assert para_cada_empresa(tarefa, 1) == 2
    assert tarefa.chamadas == [("empresa_a", 1), ("empresa_b", 1)]

    Empresa.objects.filter(schema_name="empresa_b").update(status=Empresa.Status.SUSPENSA)
    tarefa = TarefaFalsa()
    para_cada_empresa(tarefa)
    assert tarefa.chamadas == [("empresa_a",)]

    tarefa = TarefaFalsa()
    para_cada_empresa(tarefa, inclui_suspensas=True)
    assert tarefa.chamadas == [("empresa_a",), ("empresa_b",)]
