from rest_framework import exceptions

from comum.erros import (
    EmpresaSemOperacao,
    ErroDeRegra,
    LimiteDoPlano,
    TransicaoInvalida,
    tratar_excecao,
)


def test_erro_de_regra_vira_422_com_codigo_da_regra():
    resposta = tratar_excecao(
        ErroDeRegra("LOC-03", "Veículo indisponível no período", {"veiculo_id": 7}), {}
    )
    assert resposta is not None
    assert resposta.status_code == 422
    assert resposta.data == {
        "codigo": "LOC-03",
        "mensagem": "Veículo indisponível no período",
        "detalhes": {"veiculo_id": 7},
    }


def test_transicao_invalida_vira_409():
    resposta = tratar_excecao(TransicaoInvalida("LOC-05", "Não é possível."), {})
    assert resposta is not None
    assert resposta.status_code == 409
    assert resposta.data["codigo"] == "LOC-05"


def test_plt_03_limite_do_plano_vira_422():
    resposta = tratar_excecao(LimiteDoPlano("Limite de veículos do plano atingido."), {})
    assert resposta is not None
    assert resposta.status_code == 422
    assert resposta.data["codigo"] == "PLT-03"


def test_empresa_sem_operacao_vira_403():
    resposta = tratar_excecao(EmpresaSemOperacao("suspensa"), {})
    assert resposta is not None
    assert resposta.status_code == 403
    assert resposta.data["detalhes"] == {"status_empresa": "suspensa"}


def test_validacao_de_campo_vira_400_com_campos():
    erro = exceptions.ValidationError({"cnpj": ["CNPJ inválido"]})
    resposta = tratar_excecao(erro, {})
    assert resposta is not None
    assert resposta.status_code == 400
    assert resposta.data["codigo"] == "validacao"
    assert resposta.data["mensagem"] == "Confira os campos destacados"
    assert resposta.data["campos"] == {"cnpj": ["CNPJ inválido"]}


def test_codigos_fixos_de_401_403_404():
    casos = [
        (exceptions.NotAuthenticated(), 401, "nao_autenticado"),
        (exceptions.AuthenticationFailed(), 401, "nao_autenticado"),
        (exceptions.PermissionDenied(), 403, "permissao"),
        (exceptions.NotFound(), 404, "nao_encontrado"),
    ]
    for erro, status_http, codigo in casos:
        resposta = tratar_excecao(erro, {})
        assert resposta is not None
        assert resposta.status_code == status_http
        assert resposta.data["codigo"] == codigo
        assert set(resposta.data) == {"codigo", "mensagem", "detalhes"}


def test_excecao_desconhecida_nao_e_tratada():
    assert tratar_excecao(KeyError("x"), {}) is None
