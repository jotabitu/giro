"""T-505 · Preço do veículo sem valor de compra e desvalorização nunca negativa (VEI-13, VEI-16).

Padrão A de 22 nov 2026 (PR #636): sem valor de compra, o pago na moto fica vazio, a
desvalorização sai da conta e a margem vem marcada `sem_custo_compra`, sem a faixa amarela; na
locação com compra, o lucro e a margem sobre o pago vêm nulos. A revenda acima do pago dá
desvalorização R$ 0,00. A Biz ADJ-4T71 é o caso achado na conferência da T-496.
"""

from decimal import Decimal
from typing import Any

import pytest

from apps.empresas import selectors as empresas_selectors
from apps.empresas.models import ConfiguracaoEmpresa
from apps.veiculos import services
from apps.veiculos.models import Veiculo

from .frota import Frota, criar_veiculo
from .test_t012_filiais import MotoRapida
from .test_t494_precos_veiculo import COMPRA_POP, VEICULOS, _pop, _precos
from .test_t494_precos_veiculo import frota as frota
from .test_t494_precos_veiculo import moto as moto

CUSTOS_BIZ = {
    "manutencao_mes_centavos": 10000,
    "seguro_mes_centavos": 8000,
    "rastreador_mes_centavos": 5000,
    "ipva_ano_centavos": 120000,
    "revenda_estimada_centavos": 900000,
    "ocupacao_esperada_pct": "85.00",
}


def _biz(frota: Frota) -> Veiculo:
    """A Biz 125 ADJ-4T71, Urbana, sem valor de compra (semanal R$ 299,40)."""
    biz = criar_veiculo(
        901,
        frota.categorias["Urbana 110–125"],
        frota.centro,
        placa="ADJ4T71",
        chassi="9C2JC4110RR000901",
        modelo="Biz 125",
    )
    services.aplicar_modelo_de_preco([biz], "cadastro")
    return biz


def _simular(moto: MotoRapida, veiculo: Veiculo, corpo: dict[str, Any]) -> Any:
    resposta = moto.api("Mariana").post(
        f"{VEICULOS}{veiculo.pk}/precos/simular/", corpo, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()


def _semanal(dados: dict[str, Any]) -> dict[str, Any]:
    plano: dict[str, Any] = next(p for p in dados["planos"] if p["tipo"] == "semanal")
    return plano


def test_vei_13_sem_valor_de_compra_sem_desvalorizacao(moto, frota) -> None:
    """Biz: o custo era −R$ 45,00 e as margens passavam de 100%. Sem a compra, R$ 330,00 por mês,
    margem semanal 70,08% com a marca, e sem a faixa amarela mesmo abaixo da mínima de 80%."""
    biz = _biz(frota)
    ConfiguracaoEmpresa.objects.update(margem_minima_pct=Decimal("80.00"))
    assert empresas_selectors.margem_minima_pct() == Decimal("80.00")
    dados = _simular(moto, biz, {"custos": CUSTOS_BIZ})
    assert dados["pago_na_moto"]["total_centavos"] is None
    assert dados["custos"]["custo_mes_centavos"] == 33000
    assert dados["custos"]["sem_custo_compra"] is True
    assert dados["custos"]["revenda_acima_do_pago"] is False
    margem = _semanal(dados)["margem"]
    assert margem["margem_pct"] == "70.08"
    assert margem["sem_custo_compra"] is True
    assert margem["abaixo_da_minima"] is False

    salvo = moto.api("Mariana").put(
        f"{VEICULOS}{biz.pk}/precos/", {"custos": CUSTOS_BIZ}, format="json"
    )
    assert salvo.status_code == 200, salvo.json()
    lido = _precos(moto, biz).json()
    assert lido["custos"]["custo_mes_centavos"] == 33000
    assert lido["custos"]["sem_custo_compra"] is True
    assert _semanal(lido)["margem"]["sem_custo_compra"] is True


def test_vei_16_sem_valor_de_compra_sem_lucro_nem_margem_sobre_o_pago(moto, frota) -> None:
    """A compra da Biz sem valor de compra: a parcela e os juros aparecem; o lucro e a margem
    sobre o pago vêm nulos, com a marca. O vendedor não recebe as chaves de custo."""
    biz = _biz(frota)
    corpo = {"valor_venda_centavos": 1590000, "plano_compra": COMPRA_POP}
    resultado = _simular(moto, biz, corpo)["plano_compra"]["resultado"]
    assert resultado["parcela_cliente_centavos"] == 19101
    assert resultado["recebe_pela_moto_centavos"] == 1776896
    assert resultado["lucro_centavos"] is None
    assert resultado["margem_sobre_pago_pct"] is None
    assert resultado["sem_custo_compra"] is True
    salvo = moto.api("Mariana").put(f"{VEICULOS}{biz.pk}/precos/", corpo, format="json")
    assert salvo.status_code == 200, salvo.json()
    vendedor = _precos(moto, biz, "Bruna").json()
    assert "custos" not in vendedor
    assert "sem_custo_compra" not in vendedor["plano_compra"]["resultado"]
    assert "margem" not in _semanal(vendedor)


def test_vei_13_desvalorizacao_nunca_negativa(moto, frota) -> None:
    """Pop TBC-5H21 (pago R$ 13.800,00) com revenda R$ 15.000,00: desvalorização R$ 0,00."""
    pop = _pop(moto, frota)
    custos = {**CUSTOS_BIZ, "revenda_estimada_centavos": 1500000}
    dados = _simular(moto, pop, {"custos": custos})
    assert dados["pago_na_moto"]["total_centavos"] == 1380000
    assert dados["custos"]["custo_mes_centavos"] == 33000
    assert dados["custos"]["revenda_acima_do_pago"] is True
    assert dados["custos"]["sem_custo_compra"] is False
    assert _semanal(dados)["margem"]["sem_custo_compra"] is False


@pytest.mark.parametrize(("revenda", "custo"), [(900000, 53000), (890000, 53417)])
def test_vei_13_pop_com_compra_continua_igual(moto, frota, revenda, custo) -> None:
    """Pop TBC-5H21 de dados-de-teste.md: revenda R$ 9.000,00, custo R$ 530,00 (exemplo da API);
    R$ 8.900,00, R$ 534,17. A compra continua com o lucro e a margem sobre o pago."""
    pop = _pop(moto, frota)
    corpo = {
        "valor_venda_centavos": 1590000,
        "custos": {**CUSTOS_BIZ, "revenda_estimada_centavos": revenda},
        "plano_compra": COMPRA_POP,
    }
    dados = _simular(moto, pop, corpo)
    assert dados["custos"]["custo_mes_centavos"] == custo
    assert dados["custos"]["revenda_acima_do_pago"] is False
    resultado = dados["plano_compra"]["resultado"]
    assert (resultado["lucro_centavos"], resultado["margem_sobre_pago_pct"]) == (396896, "28.76")
    assert resultado["sem_custo_compra"] is False
