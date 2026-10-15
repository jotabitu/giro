"""T-204 · Seed das decisões de 14 out 2026: horas dos pedidos aprovados (`APR-12`).

Caso "Números da tela Aprovações em 07 out" (CA-APR-01): aluguel do ponto pedido por Lúcia em
05 out 08:30 e aprovado por Rodrigo às 09:10 (40 min); rastreadores pedidos em 02 out 10:00 e
aprovados às 12:20 (140 min); média (40 + 140) ÷ 2 = 90 min. Pendentes: pneus e LOC-2812.
"""

from datetime import timedelta
from typing import Any

from apps.aprovacoes.models import PedidoAprovacao
from apps.financeiro.models import Despesa

from .test_t019_seed_completo import _sp
from .test_t019_seed_completo import seed as seed
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures


def _pedido_da_despesa(descricao: str) -> PedidoAprovacao:
    despesa = Despesa.objects.get(descricao=descricao)
    return PedidoAprovacao.objects.get(pk=despesa.pedido_aprovacao_id or 0)


def test_apr_12_seed_horas_dos_pedidos_aprovados(seed: Any):
    aluguel = _pedido_da_despesa("Aluguel do ponto")
    rastreadores = _pedido_da_despesa("Rastreadores (86)")
    assert (
        aluguel.status,
        aluguel.solicitante.nome,
        (aluguel.aprovador and aluguel.aprovador.nome),
    ) == (
        "aprovado",
        "Lúcia Freitas",
        "Rodrigo Pinheiro",
    )
    assert (_sp(aluguel.criado_em), _sp(aluguel.decidido_em)) == (
        "2026-10-05 08:30",
        "2026-10-05 09:10",
    )
    assert rastreadores.aprovador and rastreadores.aprovador.nome == "Rodrigo Pinheiro"
    assert (_sp(rastreadores.criado_em), _sp(rastreadores.decidido_em)) == (
        "2026-10-02 10:00",
        "2026-10-02 12:20",
    )


def test_apr_12_seed_tempo_medio_de_90_minutos(seed: Any):
    aprovados = PedidoAprovacao.objects.filter(status="aprovado", decidido_em__isnull=False)
    assert aprovados.count() == 2
    espera = [p.decidido_em - p.criado_em for p in aprovados]
    assert sorted(espera) == [timedelta(minutes=40), timedelta(minutes=140)]
    assert sum(espera, timedelta()) / len(espera) == timedelta(minutes=90)


def test_apr_12_seed_pendentes_sao_pneus_e_loc_2812(seed: Any):
    pendentes = PedidoAprovacao.objects.filter(status="pendente")
    assert sorted(p.solicitante.nome for p in pendentes) == ["Bruna Alves", "João Silva"]
    assert PedidoAprovacao.objects.exclude(status__in=["aprovado", "pendente"]).count() == 0
    # O pedido não é recriado nem muda de hora ao ser decidido: `criado_em` fica no pedido.
    pneus = _pedido_da_despesa("Pneus (2)")
    assert _sp(pneus.criado_em) == "2026-10-07 09:00"
