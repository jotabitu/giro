import pytest

from comum.documentos import cnpj_valido, so_digitos


@pytest.mark.parametrize("cnpj", ["12.345.678/0001-95", "12345678000195", "11.222.333/0001-81"])
def test_cnpj_valido(cnpj):
    assert cnpj_valido(cnpj)


@pytest.mark.parametrize(
    "cnpj", ["12.345.678/0001-10", "12.345.678/0001-11", "00000000000000", "1234567800019", ""]
)
def test_cnpj_invalido(cnpj):
    assert not cnpj_valido(cnpj)


def test_so_digitos():
    assert so_digitos("12.345.678/0001-95") == "12345678000195"
