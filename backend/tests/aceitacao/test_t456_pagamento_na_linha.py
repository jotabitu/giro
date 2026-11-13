"""T-456 · Pagamento e caução na linha da locação (LOC-17, FIN-01, FIN-18).

A lista de locações e a seção Locações do cliente (`GET /api/locacoes/?cliente=`) usam a mesma
linha. Cenário da T-090: Moto Rápida, Filial Centro. Os exemplos são os da LOC-17: a semanal
Street de R$ 329,00 por Pix do Lucas, com caução de R$ 300,00.
"""

from typing import Any

from apps.financeiro.models import ContaReceber
from apps.locacoes.models import Locacao
from comum.dinheiro import formatar_reais

from .test_t015_locacoes import LISTA, Cenario, _vistoriar
from .test_t016_vistorias import _completar
from .test_t017_financeiro import CONTAS, _abrir, _receber
from .test_t090_contratos import moto as cenario  # noqa: F401 - fixture
from .test_t451_retirada_e_caucao import _conta, _no_dia, _registrar, locacao  # noqa: F401


def _linha(cenario: Cenario, locacao: Locacao, **filtro: Any) -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api("Rodrigo").get(LISTA, filtro)
    assert resposta.status_code == 200, resposta.json()
    linha: dict[str, Any] = next(x for x in resposta.json()["resultados"] if x["id"] == locacao.pk)
    return linha


def _pagamento(cenario: Cenario, locacao: Locacao) -> tuple[str, str, str | None]:  # noqa: F811
    p = _linha(cenario, locacao)["pagamento"]
    return p["rotulo"], p["tom"], p["caucao"]["rotulo"] if p["caucao"] else None


def test_loc_17_antes_da_retirada_o_que_falta_e_a_caucao(cenario, locacao) -> None:  # noqa: F811
    """O exemplo da LOC-17: a vendedora recebe só a 1ª semana, e a linha passa de "Falta
    R$ 629,00 · 1ª semana e caução" para "Falta R$ 300,00 · caução"."""
    assert _pagamento(cenario, locacao) == (
        "Falta R$ 629,00 · 1ª semana e caução",
        "alerta",
        "Caução R$ 300,00 · em aberto",
    )
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _pagamento(cenario, locacao) == (
        "Falta R$ 300,00 · caução",
        "alerta",
        "Caução R$ 300,00 · em aberto",
    )
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    assert _pagamento(cenario, locacao) == (
        "1º pagamento feito · R$ 629,00",
        "info",
        "Caução R$ 300,00 · paga",
    )
    # A seção Locações do cliente lê a mesma linha.
    do_cliente = _linha(cenario, locacao, cliente=locacao.cliente_id)["pagamento"]
    assert (do_cliente["rotulo"], do_cliente["caucao"]["rotulo"]) == (
        "1º pagamento feito · R$ 629,00",
        "Caução R$ 300,00 · paga",
    )
    assert (do_cliente["caucao"]["valor_centavos"], do_cliente["caucao"]["paga"]) == (30000, True)


def _valor_hoje(cenario: Cenario, conta: ContaReceber) -> int:  # noqa: F811
    """O valor de hoje que a API cobra (FIN-03), com a multa e os juros que o contrato prevê."""
    resposta = cenario.moto.api("Rodrigo").get(f"{CONTAS}{conta.pk}/")
    return int(resposta.json()["valor_hoje"]["total_centavos"])


def _de_05_nov(cenario: Cenario, relogio: Any) -> Locacao:  # noqa: F811
    """Semanal Street de 05 nov 10:00 a 19 nov 10:00, com a vistoria de saída feita."""
    _completar(cenario.clientes["Lucas"])
    _no_dia(cenario, relogio, "2026-11-05 09:00")
    criada = cenario.confirmada(inicio="2026-11-05T13:00:00Z", periodos=2)
    nova = Locacao.objects.get(pk=criada["id"])
    _vistoriar(nova.pk)
    return nova


def test_loc_17_retirada_a_mao_so_com_a_caucao_paga(cenario, relogio, relogio_jwt) -> None:  # noqa: F811
    """Ex. da LOC-17: retirada em 07 nov com a caução paga e a 1ª semana em aberto. Nunca
    "R$ 300,00 pago": a caução tem o texto dela. Em 08 nov, o valor de hoje da parcela 1."""
    nova = _de_05_nov(cenario, relogio)
    _no_dia(cenario, relogio, "2026-11-07 09:00")
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(nova, "caucao"), 30000).status_code == 200
    assert _registrar(cenario, nova).status_code == 200
    linha = _linha(cenario, nova)
    assert linha["situacao"]["rotulo"] == "Faltam assinatura e pagamento"
    assert _pagamento(cenario, nova) == (
        "Falta R$ 329,00 · 1ª semana",
        "alerta",
        "Caução R$ 300,00 · paga",
    )
    # 08 nov: atrasada, com a multa (e os juros, se o contrato prevê) a partir de 08 nov (FIN-03).
    _no_dia(cenario, relogio, "2026-11-08 09:00")
    parcela = cenario.moto.api("Rodrigo").get(f"{CONTAS}{_conta(nova).pk}/").json()
    assert parcela["status"] == "atrasada"
    hoje = int(parcela["valor_hoje"]["total_centavos"])
    assert _pagamento(cenario, nova) == (
        f"Falta {formatar_reais(hoje)} · 1ª semana",
        "alerta",
        "Caução R$ 300,00 · paga",
    )


def test_loc_17_fin_01_da_retirada_em_diante_a_ordem_dos_textos(
    cenario,  # noqa: F811
    relogio,
    relogio_jwt,
) -> None:
    """Ex. da LOC-17: parcela 1 paga, parcela 2 vence em 12 nov. Em 11 nov, "Pix"; em 12 nov,
    "R$ 329,00 vence hoje"; em 13 nov, atrasada; paga a última, "Pago". Nunca "Pago" antes."""
    nova = _de_05_nov(cenario, relogio)
    _no_dia(cenario, relogio, "2026-11-07 09:00")
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(nova), 32900).status_code == 200
    assert _receber(cenario, _conta(nova, "caucao"), 30000).status_code == 200
    assert _registrar(cenario, nova).status_code == 200  # falta só a assinatura

    _no_dia(cenario, relogio, "2026-11-11 09:00")
    assert _pagamento(cenario, nova) == ("Pix", "info", "Caução R$ 300,00 · paga")
    _no_dia(cenario, relogio, "2026-11-12 09:00")
    assert _pagamento(cenario, nova)[:2] == ("R$ 329,00 vence hoje", "alerta")
    _no_dia(cenario, relogio, "2026-11-13 09:00")
    assert _pagamento(cenario, nova)[:2] == ("R$ 329,00 em aberto", "perigo")
    assert _linha(cenario, nova)["situacao"]["rotulo"] == "Parcela 2 atrasada"

    assert _abrir(cenario).status_code == 201
    assert (
        _receber(
            cenario,
            _conta(nova, "parcela", 2),
            _valor_hoje(cenario, _conta(nova, "parcela", 2)),
        ).status_code
        == 200
    )
    assert _pagamento(cenario, nova) == ("Pago", "sucesso", "Caução R$ 300,00 · paga")
