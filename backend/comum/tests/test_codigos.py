import threading
import uuid

import pytest
from django.db import connection, transaction

from comum.codigos import ajustar_sequencia, formatar_codigo, proximo_numero
from comum.models import Sequencia
from tests.app_exemplo.models import Pedido


def test_formato_dos_codigos_por_prefixo():
    assert formatar_codigo("LOC", 2856) == "LOC-2856"
    assert formatar_codigo("VEN", 177) == "VEN-0177"
    assert formatar_codigo("OS", 118) == "OS-118"
    assert formatar_codigo("FAT", 2209) == "FAT-2209"
    assert formatar_codigo("LOC", 12345) == "LOC-12345"


def test_codigo_sequencial_no_primeiro_save(empresa_a):
    primeiro = Pedido.objects.create(cliente="Larissa")
    segundo = Pedido.objects.create(cliente="Rafael")
    assert segundo.numero == primeiro.numero + 1
    assert segundo.codigo == formatar_codigo("LOC", segundo.numero)


def test_codigo_nao_muda_em_saves_seguintes(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    codigo = pedido.codigo
    pedido.cliente = "Larissa Souza"
    pedido.save()
    pedido.refresh_from_db()
    assert pedido.codigo == codigo


def test_seed_ajusta_sequencia_para_os_numeros_de_referencia(empresa_a):
    ajustar_sequencia("LOC", 2855)
    assert Pedido.objects.create(cliente="Larissa").codigo == "LOC-2856"


def test_rollback_devolve_o_numero(empresa_a):
    ajustar_sequencia("LOC", 100)
    with pytest.raises(RuntimeError), transaction.atomic():
        Pedido.objects.create(cliente="Vai voltar")
        raise RuntimeError
    assert Pedido.objects.create(cliente="Fica").codigo == "LOC-0101"


def test_sequencia_e_por_empresa(empresa_a):
    from apps.plataforma.models import Empresa

    ajustar_sequencia("LOC", 500)
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    ajustar_sequencia("LOC", 0)
    assert Pedido.objects.create(cliente="B").codigo == "LOC-0001"


def test_sequencia_sem_buracos_sob_concorrencia(django_db_setup, django_db_blocker):
    """Várias transações ao mesmo tempo: números de 1 a N, sem repetir nem pular."""
    from apps.plataforma.models import Empresa

    chave = f"T{uuid.uuid4().hex[:8]}"
    threads_n, por_thread = 6, 10
    obtidos: list[int] = []
    trava = threading.Lock()
    erros: list[BaseException] = []

    with django_db_blocker.unblock():
        empresa = Empresa.objects.get(schema_name="empresa_a")

        def trabalhar() -> None:
            try:
                connection.set_tenant(empresa)
                for _ in range(por_thread):
                    with transaction.atomic():
                        numero = proximo_numero(chave)
                    with trava:
                        obtidos.append(numero)
            except BaseException as erro:  # pragma: no cover - só aparece se falhar
                erros.append(erro)
            finally:
                connection.close()

        threads = [threading.Thread(target=trabalhar) for _ in range(threads_n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not erros
        assert sorted(obtidos) == list(range(1, threads_n * por_thread + 1))
        connection.set_tenant(empresa)
        assert Sequencia.objects.get(chave=chave).ultimo_numero == threads_n * por_thread
        connection.set_schema_to_public()
