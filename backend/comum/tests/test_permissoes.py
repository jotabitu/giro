from types import SimpleNamespace

import pytest

from comum.erros import EmpresaSemOperacao
from comum.permissoes import EmpresaOperando, exige_perfil


def _request(metodo: str, status: str | None, perfil: str = "") -> SimpleNamespace:
    tenant = SimpleNamespace(schema_name="empresa_a", status=status) if status else None
    return SimpleNamespace(method=metodo, tenant=tenant, user=SimpleNamespace(perfil=perfil))


@pytest.mark.parametrize("status", ["em_teste", "ativa", "inadimplente"])
def test_empresa_que_opera_escreve(status):
    assert EmpresaOperando().has_permission(_request("POST", status), None)  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["suspensa", "pausada", "cancelada"])
def test_empresa_sem_operacao_so_le(status):
    permissao = EmpresaOperando()
    assert permissao.has_permission(_request("GET", status), None)  # type: ignore[arg-type]
    with pytest.raises(EmpresaSemOperacao):
        permissao.has_permission(_request("POST", status), None)  # type: ignore[arg-type]


def test_exige_perfil():
    permissao = exige_perfil("administrador", "gerente")()
    assert permissao.has_permission(_request("GET", "ativa", "gerente"), None)  # type: ignore[arg-type]
    assert not permissao.has_permission(_request("GET", "ativa", "vendedor"), None)  # type: ignore[arg-type]
