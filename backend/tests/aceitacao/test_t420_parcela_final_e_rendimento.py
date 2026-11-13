"""T-420 · Achados A4 e A8 da conferência de 13 nov 2026 (`docs/qa/conferencia-13-nov-t420.md`),
com a regra do produto no #575.

- A4 (`LOC-16`, CA-420-14): a última parcela de R$ 0,00 (caução maior que a parcela) não vira
  conta a receber, mas aparece na ficha da locação ("Parcela 104 de 104 · R$ 0,00 · paga com a
  caução") e conta como paga desde que a caução está paga. Em `Receber`, "Parcela 1 de 104". A
  última parcela com valor leva a observação "caução abatida" (D2 da revisão do Design System).
- A8 (`VEI-05`): o veículo vendido pela quitação continua mostrando o que rendeu no ano: as
  parcelas da compra são receita, a caução fica fora.

Cenário de `test_t420_locacao_com_compra`: Moto Rápida, Filial Centro, 10 nov 2026; plano da
Street (caução R$ 300,00) e o Lucas no SAK-1D39.
"""

from typing import Any

from apps.financeiro.models import ContaReceber
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo
from apps.vendas import leituras as vendas_leituras

from .test_t015_locacoes import Cenario
from .test_t420_locacao_com_compra import (  # noqa: F401
    _compra,
    _confirmada,
    _contas,
    _criar_plano,
    _pagar,
    _retirada,
    ativa,
    cenario,
    compra,
    plano,
)

RECEBER = "/api/financeiro/contas-receber/"


def _semanal(cen: Cenario) -> dict[str, Any]:
    return _criar_plano(
        cen,
        nome="Compra Street 104 semanas",
        periodicidade="semanal",
        parcelas=104,
        valor_parcela_centavos=19900,
    )


def _linhas(cen: Cenario, locacao: Locacao, quem: str = "Bruna") -> list[dict[str, Any]]:
    return list(cen.detalhe(locacao.pk, quem)["parcelas"])


def _ultima(cen: Cenario, locacao: Locacao) -> dict[str, Any]:
    [linha] = [p for p in _linhas(cen, locacao) if p["tipo"] == "parcela" and p["numero"] == 104]
    return linha


def test_loc_16_ca_420_14_parcela_de_zero_na_ficha_antes_da_caucao(compra: Cenario) -> None:  # noqa: F811
    """Confirmada e não retirada: a 104ª aparece na ficha, R$ 0,00, "será paga com a caução",
    sem conta e sem botão; ainda não conta como paga."""
    locacao = _confirmada(compra, _semanal(compra)["id"])
    assert len(_contas(locacao)) == 103
    linha = _ultima(compra, locacao)
    assert linha["id"] is None and linha["conta_id"] is None
    assert (linha["valor_centavos"], linha["valor_hoje_centavos"]) == (0, 0)
    assert linha["total_parcelas"] == 104
    assert linha["rotulo"] == "Parcela 104"
    assert linha["status"] == "aberta"
    assert linha["observacao"] == "será paga com a caução"
    assert linha["paga_com_caucao"] is True
    assert linha["acoes"] == {"receber": False}
    assert linha["pago_em"] is None
    # O calendário da LOC-05: semanal desde 10 nov 2026, a 104ª 103 semanas depois.
    assert linha["vencimento"] == "2028-10-31"
    # A ordem: as parcelas pelo número, a 104ª depois da 103ª, e a caução no fim.
    linhas = _linhas(compra, locacao)
    assert [p["rotulo"] for p in linhas[-3:]] == ["Parcela 103", "Parcela 104", "Caução"]
    assert _compra(compra, locacao)["parcelas_pagas"] == 0


def test_loc_16_ca_420_14_parcela_de_zero_paga_com_a_caucao(compra: Cenario) -> None:  # noqa: F811
    """Com a caução e a parcela 1 pagas na retirada: "Parcela 2 de 104 · faltam 102"; com 102
    pagas, "Parcela 103 de 104 · falta 1"; paga a 103ª, quita."""
    locacao = _retirada(_confirmada(compra, _semanal(compra)["id"]))
    [caucao] = _contas(locacao, "caucao")
    linha = _ultima(compra, locacao)
    assert (linha["status"], linha["observacao"]) == ("paga", "paga com a caução")
    assert (
        linha["pago_em"] is not None
        and linha["pago_em"] == compra.detalhe(locacao.pk)["parcelas"][-1]["pago_em"]
    )
    assert caucao.status == "paga"
    bloco = _compra(compra, locacao)
    assert bloco["parcelas_pagas"] == 2
    assert bloco["andamento"] == "Parcela 2 de 104 · faltam 102 para a transferência"

    _pagar(locacao, *range(2, 103))
    assert _compra(compra, locacao)["andamento"] == (
        "Parcela 103 de 104 · falta 1 para a transferência"
    )
    _pagar(locacao, 103)
    locacao.refresh_from_db()
    assert locacao.status == "encerrada" and locacao.quitada_em is not None
    assert _ultima(compra, locacao)["status"] == "paga"


def test_loc_16_ca_420_14_receber_numera_de_104(compra: Cenario) -> None:  # noqa: F811
    """Em `Receber`, a numeração segue o plano: "Parcela 1 de 104", e não "de 103"."""
    locacao = _confirmada(compra, _semanal(compra)["id"])
    primeira = ContaReceber.objects.get(
        origem_tipo="locacao", origem_id=locacao.pk, tipo="parcela", numero_parcela=1
    )
    conta = compra.moto.api("Lúcia").get(f"{RECEBER}{primeira.pk}/").json()
    assert (conta["rotulo"], conta["total_parcelas"]) == ("Parcela 1 de 104", 104)
    assert conta["parcela_de"] == "1 de 104 parcelas"


def test_loc_16_d2_ultima_parcela_com_a_caucao_abatida(compra: Cenario, ativa: Locacao) -> None:  # noqa: F811
    """Plano de 24 × R$ 1.190,00: a 24ª (R$ 890,00) leva a observação "caução abatida"; as
    outras, nenhuma. Sem a 25ª: a última com valor não tem a linha de R$ 0,00."""
    linhas = [p for p in _linhas(compra, ativa) if p["tipo"] == "parcela"]
    assert len(linhas) == 24
    assert (linhas[-1]["valor_centavos"], linhas[-1]["observacao"]) == (89000, "caução abatida")
    assert linhas[-1]["paga_com_caucao"] is False
    assert {p["observacao"] for p in linhas[:-1]} == {None}


def test_vei_05_veiculo_vendido_pela_quitacao_mantem_o_rendimento(
    compra: Cenario,  # noqa: F811
    ativa: Locacao,  # noqa: F811
    django_capture_on_commit_callbacks: Any,
) -> None:
    """Exemplo da VEI-05: quitado com 23 × R$ 1.190,00 + R$ 890,00 pagos no ano, o veículo
    vendido rendeu R$ 28.260,00 (menos as despesas do ano, nenhuma aqui), e não R$ 0,00. A
    caução fica fora."""
    vendas_leituras.registrar()
    rota = f"/api/veiculos/{compra.sak.pk}/"
    # Na retirada, só a parcela 1 (a caução, também paga, fica fora).
    antes = compra.moto.api("Rodrigo").get(rota).json()["indicadores_financeiros"]
    assert antes["rendeu_no_ano_centavos"] == 119000
    with django_capture_on_commit_callbacks(execute=True):
        _pagar(ativa, *range(2, 25))
    assert Veiculo.objects.get(pk=compra.sak.pk).status == "vendido"
    for quem in ("Rodrigo", "Mariana", "Lúcia"):
        ficha = compra.moto.api(quem).get(rota)
        assert ficha.status_code == 200, ficha.json()
        fin = ficha.json()["indicadores_financeiros"]
        assert fin["despesas_ano_centavos"] == 0
        assert fin["rendeu_no_ano_centavos"] == 23 * 119000 + 89000 == 2826000, quem


def test_vei_05_rendimento_so_das_locacoes_do_veiculo(compra: Cenario, ativa: Locacao) -> None:  # noqa: F811
    """O que rendeu é das locações do próprio veículo: os outros da frota não recebem as
    parcelas do SAK-1D39 (o filtro antigo comparava o veículo da locação com o `id` da conta)."""
    rendeu = {
        v.pk: v.loc_rendeu_ano for v in locacoes_leituras.anotar_rendimento(Veiculo.objects.all())
    }
    assert rendeu[compra.sak.pk] == 119000
    pagas_no_ano = ContaReceber.objects.filter(
        origem_tipo="locacao", status="paga", pago_em__year=2026
    ).exclude(tipo="caucao")
    for veiculo_id, valor in rendeu.items():
        das_locacoes = sum(
            c.valor_centavos
            for c in pagas_no_ano
            if Locacao.objects.filter(pk=c.origem_id, veiculo_id=veiculo_id).exists()
        )
        assert valor == das_locacoes, veiculo_id
