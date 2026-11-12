"""T-454 · A que se refere cada conta a receber (FIN-19).

Cenário da T-015 com a carteira de outubro: Moto Rápida em 07 out 2026, 10:00, Filial Centro.
Carlos, LOC-2841, semanal de 23 set a 28 out no QXA-4B21, 5 parcelas de R$ 299,40 (a de 30 set
atrasada). Lucas, LOC-2856 confirmada pela Bruna, com a caução de R$ 300,00.
"""

from datetime import date
from typing import Any

from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro.models import ContaReceber
from apps.locacoes.models import Locacao

from .test_t015_locacoes import (
    LISTA,
    cenario,  # noqa: F401 - fixture
)
from .test_t017_financeiro import (
    CONTAS,
    _avulsa,
    _carlos,
    _conta,
    com_carteira,  # noqa: F401 - fixture
    lucas,  # noqa: F401 - fixture
)


def _detalhe(cenario, conta: ContaReceber, quem: str = "Bruna") -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(f"{CONTAS}{conta.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _a_que_se_refere(dados: dict[str, Any]) -> tuple[Any, ...]:
    campos = ("tipo", "tipo_rotulo", "rotulo", "renegociacao", "numero", "total_parcelas")
    return (*(dados[c] for c in campos), dados["parcela_de"])


def test_fin_19_parcela_2_de_5_da_loc_2841(cenario, com_carteira):  # noqa: F811
    dados = _detalhe(cenario, _carlos(com_carteira))
    assert _a_que_se_refere(dados) == (
        "parcela",
        "Parcela",
        "Parcela 2 de 5",
        False,
        2,
        5,
        "2 de 5 parcelas",
    )
    assert (dados["origem"]["codigo"], dados["veiculo_placa"]) == ("LOC-2841", "QXA4B21")
    # A lista manda os mesmos textos.
    lista = cenario.moto.api("Bruna").get(
        CONTAS, {"origem_tipo": "locacao", "origem_id": com_carteira["LOC-2841"].pk}
    )
    rotulos = {c["vencimento"]: c["rotulo"] for c in lista.json()["resultados"]}
    assert rotulos["2026-09-30"] == "Parcela 2 de 5"


def test_fin_19_caucao_da_loc_2856(cenario, lucas):  # noqa: F811
    dados = _detalhe(cenario, _conta(lucas, "caucao"))
    assert _a_que_se_refere(dados) == ("caucao", "Caução", "Caução", False, None, None, None)
    parcela = _detalhe(cenario, _conta(lucas, "parcela", 1))
    # O total da parcela não conta a caução.
    assert (parcela["rotulo"], parcela["parcela_de"]) == ("Parcela 1 de 2", "1 de 2 parcelas")


def test_fin_19_renovacao_aumenta_o_total_e_cancelada_continua_contada(
    cenario,  # noqa: F811
    com_carteira,  # noqa: F811
):
    carlos: Locacao = com_carteira["LOC-2841"]
    renovar = cenario.moto.api("Bruna").post(
        f"{LISTA}{carlos.pk}/renovar/", {"periodos": 2}, format="json"
    )
    assert renovar.status_code == 200, renovar.json()
    dados = _detalhe(cenario, _carlos(com_carteira))
    assert (dados["rotulo"], dados["total_parcelas"], dados["parcela_de"]) == (
        "Parcela 2 de 7",
        7,
        "2 de 7 parcelas",
    )
    ultima = _conta(carlos, "parcela", 7)
    cancelada = cenario.moto.api("Rodrigo").post(
        f"{CONTAS}{ultima.pk}/cancelar/", {"motivo": "Encerramento antes do fim"}, format="json"
    )
    assert cancelada.status_code == 200, cancelada.json()
    assert _detalhe(cenario, _carlos(com_carteira))["rotulo"] == "Parcela 2 de 7"
    assert _detalhe(cenario, ultima)["rotulo"] == "Parcela 7 de 7"


def test_fin_19_outra_cobranca_e_renegociacao(cenario, com_carteira):  # noqa: F811
    avulsa = _detalhe(cenario, _avulsa(cenario, "Carlos", 5000))
    assert _a_que_se_refere(avulsa) == (
        "outro",
        "Outra cobrança",
        "Outra cobrança · Recebimento de Carlos",
        False,
        None,
        None,
        None,
    )
    renegociada = cenario.moto.api("Rodrigo").post(
        f"{CONTAS}renegociar/",
        {
            "contas": [_carlos(com_carteira).pk],
            "novas": [
                {"vencimento": "2026-10-15", "valor_centavos": 15000},
                {"vencimento": "2026-10-22", "valor_centavos": 15609},
            ],
            "motivo": "Combinado com o cliente",
        },
        format="json",
    )
    assert renegociada.status_code == 201, renegociada.json()
    novas = renegociada.json()["resultados"]
    assert [(n["tipo_rotulo"], n["rotulo"], n["renegociacao"]) for n in novas] == [
        ("Parcela", "Renegociação · 1 de 2", True),
        ("Parcela", "Renegociação · 2 de 2", True),
    ]
    assert {n["parcela_de"] for n in novas} == {None}


def test_fin_19_rotulos_de_cada_tipo():
    def rotulo(**campos: Any) -> tuple[str, str, str | None]:
        conta = ContaReceber(vencimento=date(2026, 10, 7), valor_centavos=1, **campos)
        dados = financeiro_selectors.a_que_se_refere(conta, campos.get("total_parcelas"))
        return dados["tipo_rotulo"], dados["rotulo"], dados["parcela_de"]

    assert rotulo(tipo="parcela", numero_parcela=1, total_parcelas=1) == (
        "Parcela",
        "Parcela única",
        None,
    )
    assert rotulo(tipo="parcela", numero_parcela=1, total_parcelas=128) == (
        "Parcela",
        "Parcela 1 de 128",
        "1 de 128 parcelas",
    )
    assert rotulo(tipo="multa", observacao="Encerramento antecipado") == (
        "Multa",
        "Multa · Encerramento antecipado",
        None,
    )
    assert rotulo(tipo="avaria", observacao="Retrovisor direito")[1] == (
        "Avaria · Retrovisor direito"
    )
    assert rotulo(tipo="acerto", observacao="3 diárias de atraso")[1] == (
        "Acerto da devolução · 3 diárias de atraso"
    )
    assert rotulo(tipo="acerto")[1] == "Acerto da devolução"
    assert rotulo(tipo="caucao", observacao="Devolver na entrega")[1] == "Caução"
