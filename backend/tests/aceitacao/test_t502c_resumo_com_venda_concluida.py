"""T-502 · Fase 1c com a 1b dentro: o resumo, o ticket médio e a meta leem a venda concluída
pelo serviço da 1b (assinatura e entrada, `VEN-06`), não só as gravadas direto no banco.

Cenário da T-015: Moto Rápida, Filial Centro, 07 out 2026, 10:00. A VEN-0177 (CB 300F, R$
22.900,00 com 8% aprovado pelo Rodrigo = R$ 21.068,00; `dados-de-teste.md`) é assinada pelo
Diego e a entrada é paga: vira `vendida`. A Bruna tem meta de R$ 50.000,00 em outubro.
"""

from datetime import date

import pytest

from apps.relatorios import selectors as relatorios_selectors
from apps.vendas.models import MetaVenda

from .test_t015_locacoes import Cenario, cenario  # noqa: F401
from .test_t502_fase_1c import _resumo
from .test_t502b_assinatura_e_vendida import (
    _assinar,
    _pagar_entrada,
    _preparada,
    modelo_de_venda,  # noqa: F401
)

pytestmark = pytest.mark.usefixtures("modelo_de_venda")


def _concluida(cenario: Cenario):  # noqa: F811
    venda = _preparada(cenario)
    _assinar(venda)
    _pagar_entrada(venda)
    venda.refresh_from_db()
    assert venda.status == "vendida"
    return venda


def test_ven_12_resumo_conta_a_venda_concluida_pela_assinatura(cenario):  # noqa: F811
    antes = _resumo(cenario, "Bruna")
    assert antes["vendido"]["quantidade"] == 0
    assert antes["em_negociacao"]["quantidade"] == 0
    venda = _concluida(cenario)
    corpo = _resumo(cenario, "Bruna")
    vendido = corpo["vendido"]
    assert (vendido["quantidade"], vendido["soma_centavos"], vendido["ticket_centavos"]) == (
        1,
        2106800,
        2106800,
    )
    assert corpo["funil"]["vendido"] == 1  # VEN-08
    assert corpo["conversao"]["vendidas"] == 1
    assert corpo["em_negociacao"]["quantidade"] == 0  # saiu de `proposta`
    assert corpo["transferencias_pendentes"] >= 1  # VEN-17
    assert all(p["venda_id"] != venda.pk for p in corpo["propostas_para_retornar"])  # VEN-16


def test_ven_12_ticket_medio_do_inicio_com_a_venda_concluida(cenario):  # noqa: F811
    _concluida(cenario)
    escopo = relatorios_selectors.Escopo(filiais=frozenset({cenario.frota.centro.pk}), todas=False)
    bloco = relatorios_selectors._ticket_medio(escopo)
    assert (bloco["vendas"], bloco["soma_centavos"], bloco["ticket_centavos"]) == (
        1,
        2106800,
        2106800,
    )
    assert bloco["resumo"] == "1 venda · R$ 21.068,00"


def test_ven_09_meta_com_a_venda_concluida(cenario):  # noqa: F811
    _concluida(cenario)
    MetaVenda.objects.create(
        vendedor=cenario.pessoas["Bruna"],
        filial=cenario.frota.centro,
        mes=date(2026, 10, 1),
        valor_centavos=5000000,
        definida_por=cenario.pessoas["Rodrigo"],
    )
    meta = _resumo(cenario, "Bruna")["meta"]
    assert (meta["vendido_centavos"], meta["pct"], meta["faltam_dias"]) == (2106800, 42, 24)
    assert meta["texto"] == "42% de R$ 50.000,00 · faltam 24 dias"
