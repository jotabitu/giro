import pytest

from comum.documentos import cnpj_valido, cpf_valido, so_digitos


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


@pytest.mark.parametrize("cpf", ["123.456.789-09", "05221833018", "052.218.330-18"])
def test_cli_01_cpf_valido(cpf):
    assert cpf_valido(cpf)


@pytest.mark.parametrize("cpf", ["123.456.789-00", "111.111.111-11", "1234567890", "", "abc"])
def test_cli_01_cpf_invalido(cpf):
    assert not cpf_valido(cpf)
