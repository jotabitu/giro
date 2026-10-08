from typing import Any

import pytest
from django.db import connection

from apps.plataforma.models import Empresa
from comum.auditoria import ator_atual
from comum.tarefas import (
    EmpresaIndisponivel,
    na_empresa,
    para_cada_empresa,
    regra_da_tarefa,
    tarefa_de_empresa,
)


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

    Empresa._base_manager.filter(schema_name="empresa_b").update(status=Empresa.Status.SUSPENSA)
    tarefa = TarefaFalsa()
    para_cada_empresa(tarefa)
    assert tarefa.chamadas == [("empresa_a",)]

    tarefa = TarefaFalsa()
    para_cada_empresa(tarefa, inclui_suspensas=True)
    assert tarefa.chamadas == [("empresa_a",), ("empresa_b",)]


def test_tarefa_de_empresa_suspensa_nao_roda_e_nao_falha(publico):
    rodou: list[str] = []

    @tarefa_de_empresa
    def aut_02_marcar(schema_name: str) -> str:
        rodou.append(schema_name)
        return "feito"

    Empresa._base_manager.filter(schema_name="empresa_b").update(status=Empresa.Status.SUSPENSA)
    assert aut_02_marcar("empresa_b") is None
    assert rodou == []


def test_tarefa_de_leitura_roda_em_empresa_suspensa(publico):
    @tarefa_de_empresa(inclui_suspensas=True)
    def aut_07_cobrar(schema_name: str) -> str:
        return connection.schema_name

    Empresa._base_manager.filter(schema_name="empresa_b").update(status=Empresa.Status.SUSPENSA)
    assert aut_07_cobrar("empresa_b") == "empresa_b"


def test_tarefa_de_empresa_inexistente_nao_cai_no_public(publico):
    rodou: list[str] = []

    @tarefa_de_empresa
    def aut_02_marcar(schema_name: str) -> None:
        rodou.append(connection.schema_name)

    assert aut_02_marcar("empresa_que_nao_existe") is None
    assert rodou == []


def test_tarefa_de_empresa_com_schema_apagado_nao_cai_no_public(publico):
    # Linha em Empresa sem schema no banco (situação do AUD-08 com tarefa ainda na fila).
    Empresa.objects.bulk_create([Empresa(schema_name="empresa_apagada", nome_exibicao="Apagada")])
    rodou: list[str] = []

    @tarefa_de_empresa
    def aut_02_marcar(schema_name: str) -> None:
        rodou.append(connection.schema_name)

    assert aut_02_marcar("empresa_apagada") is None
    assert rodou == []


def test_na_empresa_recusa_empresa_indisponivel(publico):
    with pytest.raises(EmpresaIndisponivel), na_empresa("empresa_que_nao_existe"):
        pass


def test_tarefa_pedida_por_pessoa_age_em_nome_dela(publico):
    from apps.contas.models import Usuario
    from comum.auditoria import Ator, TipoAtor, usar_ator
    from comum.tarefas import ator_para_fila

    with na_empresa("empresa_a"):
        carla = Usuario.objects.create_user(
            "carla@a.com", "x", nome="Carla Menezes", perfil="gerente"
        )

    with usar_ator(Ator(tipo=TipoAtor.USUARIO, id=carla.pk, nome="Carla Menezes")):
        ator = ator_para_fila()
    # Na fila vai só tipo e id, sem nome.
    assert ator == {"tipo": "usuario", "id": carla.pk, "acesso_suporte_id": None}

    visto: dict[str, Any] = {}

    @tarefa_de_empresa
    def importar_planilha(schema_name: str) -> None:
        visto["ator"] = ator_atual()

    importar_planilha("empresa_a", ator=ator)
    assert visto["ator"].tipo == "usuario"
    assert visto["ator"].id == carla.pk
    assert visto["ator"].nome == "Carla Menezes"
    assert visto["ator"].regra == ""


def test_tarefa_sem_ator_e_do_sistema_e_sistema_nao_vai_para_a_fila(publico):
    from comum.tarefas import ator_para_fila

    assert ator_para_fila() is None


def test_cli_01_cifra_e_hash_dentro_de_tarefa_de_empresa(publico):
    """R-01 da T-050: dentro da tarefa a conexão tem a empresa real, com id."""
    from comum import cripto
    from comum.conexao import conexao
    from tests.app_exemplo.models import Pessoa

    empresa_a = Empresa.objects.get(schema_name="empresa_a")
    visto: dict[str, Any] = {}

    @tarefa_de_empresa
    def importar_clientes(schema_name: str) -> None:
        pessoa = Pessoa(nome="Larissa Souza")
        pessoa.definir_documento("123.218.330-45")
        pessoa.save()
        visto["hash"] = pessoa.documento_hash
        visto["claro"] = Pessoa.objects.get(pk=pessoa.pk).documento_claro()

    importar_clientes("empresa_a")

    # O mesmo hash que a requisição da empresa A calcularia.
    conexao().set_tenant(empresa_a)
    assert visto["hash"] == cripto.hash_busca("12321833045")
    assert visto["claro"] == "123.218.330-45"
    with na_empresa("empresa_a"):
        assert Pessoa.objects.get(documento_hash=visto["hash"]).nome == "Larissa Souza"


def test_ator_do_suporte_sem_acesso_e_recusado(publico):
    """R-04 da T-050: ação do suporte sempre com o acesso que a justifica (AUD-03, PLT-07)."""

    @tarefa_de_empresa
    def exportar(schema_name: str) -> None:
        pass

    with pytest.raises(ValueError, match="acesso_suporte_id"):
        exportar("empresa_a", ator={"tipo": "suporte", "id": 1, "acesso_suporte_id": None})
