"""T-288 parte 2: a lavagem do CA-246-02 nas despesas de outubro do seed (FIN-05, FIN-16).

Cenário da T-178: as 6 despesas de outubro da Filial Centro (R$ 7.066,70) e os 86 veículos com o
histórico do cadastro. A lavagem de R$ 35,00 da MOV-0001 entra no mês e na despesa por veículo.
"""

import pytest

from apps.locacoes.models import ABERTAS, Locacao
from apps.movimentacoes import leituras as movimentacoes_leituras
from apps.veiculos.models import Veiculo

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t017_financeiro import caixa_do_seed, lucas, recebimentos  # noqa: F401 - fixtures
from .test_t178_despesas import _lista, frota_com_historico, outubro  # noqa: F401 - fixtures
from .test_t288_movimentacoes import _criada, _lavagem, _passar_pela_parada


@pytest.fixture
def lavagem(cenario, outubro) -> int:  # noqa: F811
    """O CA-246-02: o João passa no lava-jato e confirma R$ 35,00. O SAK1D39 está reservado
    para o Lucas neste cenário, então vai outro veículo livre (o total não depende dele)."""
    movimentacoes_leituras.registrar()
    abertas = Locacao.objects.filter(status__in=ABERTAS).values("veiculo_id")
    livre = (
        Veiculo.objects.filter(status="disponivel", filial=cenario.frota.centro)
        .exclude(pk__in=abertas)
        .order_by("id")[0]
    )
    mov = _criada(cenario, placa=livre.placa, paradas=_lavagem(cenario))
    saiu = _passar_pela_parada(cenario, mov, 3500)
    return int(saiu["paradas"][0]["despesa"]["id"])


def test_mov_04_fin_16_ca_246_02_despesas_de_outubro_com_a_lavagem(cenario, outubro, lavagem):  # noqa: F811
    indicadores = _lista(cenario).json()["indicadores"]
    # R$ 7.066,70 + R$ 35,00 = R$ 7.101,70.
    assert indicadores["gasto_mes_centavos"] == 710170
    # 7.101,70 ÷ 86 = 82,5779... → R$ 82,58 (FIN-16).
    assert indicadores["despesa_por_veiculo_centavos"] == 8258
    resultados = _lista(cenario).json()["resultados"]
    assert lavagem in [d["id"] for d in resultados]
