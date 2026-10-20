"""T-204 · Seed e critérios das decisões de 14 out 2026: horas e números da tela Aprovações
(`APR-12`, `APR-01`, `APR-02`, `APR-03`, `APR-04`, CA-APR-01 a 05, 10 e 11) e o evento da troca
da tabela de preço em 01 out às 17:42 por Mariana (`AUD-02`, `LOC-15`, CA-018-09).

Caso "Números da tela Aprovações em 07 out" (CA-APR-01): aluguel do ponto pedido por Lúcia em
05 out 08:30 e aprovado por Rodrigo às 09:10 (40 min); rastreadores pedidos em 02 out 10:00 e
aprovados às 12:20 (140 min); média (40 + 140) ÷ 2 = 90 min. Pendentes: pneus e LOC-2812.
"""

from datetime import timedelta
from typing import Any

import pytest

from apps.aprovacoes.models import PedidoAprovacao
from apps.clientes.models import Cliente
from apps.financeiro.models import Caixa, Despesa
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo
from comum import relogio as comum_relogio

from .test_t019_seed_completo import _api, _sp
from .test_t019_seed_completo import seed as seed
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures

APROVACOES = "/api/aprovacoes/"
LOCACOES = "/api/locacoes/"


def _pedido_da_despesa(descricao: str) -> PedidoAprovacao:
    despesa = Despesa.objects.get(descricao=descricao)
    return PedidoAprovacao.objects.get(pk=despesa.pedido_aprovacao_id or 0)


def _desconto_street_de_8(seed: Any, relogio: Any, quando: str = "2026-10-08 09:00") -> int:
    """Bruna pede 8% de desconto numa locação semanal Street (tabela R$ 329,00, com desconto
    R$ 302,68; CA-APR-02 e CA-APR-10)."""
    relogio.em(quando)
    juliana = Cliente.objects.get(nome="Juliana Rocha")
    moto = (
        Veiculo.objects.filter(categoria__nome="Street 150–160", status="disponivel")
        .order_by("placa")
        .first()
    )
    assert moto is not None
    api = _api(seed, "Bruna")
    criada = api.post(
        LOCACOES,
        {
            "cliente_id": juliana.pk,
            "veiculo_id": moto.pk,
            "periodicidade": "semanal",
            "plano_especial_id": None,
            "inicio": "2026-10-08T12:00:00Z",
            "periodos": 1,
            "extras": [],
            "desconto_pct": "8.00",
            "forma_pagamento": "pix",
        },
        format="json",
    )
    assert criada.status_code == 201, criada.json()
    confirmada = api.post(f"{LOCACOES}{criada.json()['id']}/confirmar/", {}, format="json")
    assert confirmada.status_code == 200, confirmada.json()
    pedido_id = int(confirmada.json()["desconto"]["pedido_aprovacao_id"])
    PedidoAprovacao.objects.filter(pk=pedido_id).update(criado_em=comum_relogio.agora())
    return pedido_id


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


def test_aud_02_loc_15_seed_evento_de_01_out_17_42_por_mariana_na_lista(seed: Any):
    """Evento da troca da Street em 01 out às 17:42 por Mariana Costa na consulta de 7 dias."""
    corpo = (
        _api(seed, "Mariana")
        .get(
            "/api/auditoria/eventos/",
            {"periodo": "7d", "categoria": "configuracoes", "tamanho": 100},
        )
        .json()
    )
    trocas = [
        e
        for e in corpo["resultados"]
        if e["acao"] == "categoria.definir_preco" and e["resumo"] == "Mudou a tabela de preço"
    ]
    assert len(trocas) == 1
    item = trocas[0]
    assert item["ocorrido_em"] == "2026-10-01T20:42:00Z"  # 01 out 17:42 em São Paulo
    assert item["ator"]["nome"] == "Mariana Costa" and item["ator"]["iniciais"] == "MC"
    assert (item["categoria"], item["regra"], item["tom"], item["suporte"]) == (
        "configuracoes",
        "LOC-15",
        "info",
        None,
    )
    assert item["detalhe"] == "Street 150–160 · semanal R$ 299,40 → R$ 329,00"
    # O preço inicial de 01 set fica fora dos últimos 7 dias em 07 out.
    assert not [e for e in corpo["resultados"] if e["ocorrido_em"].startswith("2026-09-")]


def test_apr_12_ca_apr_01_mariana_e_rodrigo_veem_os_mesmos_numeros_e_abas(seed: Any):
    rodrigo = _api(seed, "Rodrigo").get(APROVACOES).json()
    mariana = _api(seed, "Mariana").get(APROVACOES).json()
    assert rodrigo["indicadores"] == mariana["indicadores"]
    assert (
        rodrigo["contagens"]
        == mariana["contagens"]
        == {
            "pendente": 2,
            "aprovado": 2,
            "recusado": 0,
            "minhas_pendentes": 0,
        }
    )
    pneus = _pedido_da_despesa("Pneus (2)")
    patricia = Locacao.objects.get(codigo="LOC-2812")
    encerramento = PedidoAprovacao.objects.get(tipo="APR-02", origem_id=patricia.pk)
    assert [p["id"] for p in rodrigo["resultados"]] == [pneus.pk, encerramento.pk]
    assert rodrigo["resultados"][1]["resumo"] == {
        "celulas": [
            {"rotulo": "Plano", "valor": "NMax 160 · mensal R$ 1.590,00"},
            {"rotulo": "Dias restantes", "valor": "8 de 30 · até 15 out"},
            {"rotulo": "Multa (20%)", "valor": "R$ 84,80"},
            {"rotulo": "A devolver", "valor": "R$ 286,20"},
        ],
        "nota": (
            "Valores estimados para 07 out; o acerto final é feito no dia da devolução. Ao "
            "aprovar, a locação vai para a devolução: vistoria, acerto e devolução da caução."
        ),
    }
    aluguel = _pedido_da_despesa("Aluguel do ponto")
    rastreadores = _pedido_da_despesa("Rastreadores (86)")
    aprovadas = _api(seed, "Rodrigo").get(APROVACOES, {"status": "aprovado"}).json()["resultados"]
    assert [p["id"] for p in aprovadas] == [aluguel.pk, rastreadores.pk]
    recusadas = _api(seed, "Rodrigo").get(APROVACOES, {"status": "recusado"}).json()["resultados"]
    assert recusadas == []


def test_apr_12_apr_01_ca_apr_02_03_10_desconto_aprovado_e_pneus_recusados_no_seed(
    seed: Any, relogio: Any
):
    pedido_id = _desconto_street_de_8(seed, relogio)
    pendentes = _api(seed, "Rodrigo").get(APROVACOES).json()["resultados"]
    item = next(p for p in pendentes if p["id"] == pedido_id)
    assert item["valor_centavos"] == 2632
    assert item["resumo"] == {
        "celulas": [
            {"rotulo": "Preço de tabela", "valor": "R$ 329,00"},
            {"rotulo": "Com desconto", "valor": "R$ 302,68"},
            {"rotulo": "Desconto", "valor": "R$ 26,32 · 8%"},
        ],
        "nota": "O limite de Bruna é 5%.",
    }

    relogio.em("2026-10-08 09:40")
    aprovado = _api(seed, "Rodrigo").post(f"{APROVACOES}{pedido_id}/aprovar/", {}, format="json")
    assert aprovado.status_code == 200, aprovado.json()

    corpo = _api(seed, "Rodrigo").get(APROVACOES).json()
    assert corpo["indicadores"]["aprovadas"] == {
        "titulo": "Aprovadas em outubro",
        "quantidade": 3,
        "tempo_medio_min": 73,  # (40 + 140 + 40) / 3 = 73,3 -> 73
        "contexto": "tempo médio de 1 h 13 min",
    }
    assert corpo["indicadores"]["descontos"] == {
        "titulo": "Descontos aprovados",
        "valor_centavos": 2632,
        "quantidade": 1,
        "contexto": "em 1 pedido",
    }

    # CA-APR-03: em seguida, Rodrigo recusa os pneus com motivo; o tempo médio não muda.
    pneus = _pedido_da_despesa("Pneus (2)")
    recusado = _api(seed, "Rodrigo").post(
        f"{APROVACOES}{pneus.pk}/recusar/", {"motivo": "Cotar em outra loja"}, format="json"
    )
    assert recusado.status_code == 200, recusado.json()
    depois = _api(seed, "Rodrigo").get(APROVACOES).json()
    assert depois["indicadores"]["recusadas"] == {
        "titulo": "Recusadas em outubro",
        "quantidade": 1,
        "contexto": "sempre com motivo",
    }
    assert depois["indicadores"]["esperando"]["quantidade"] == 1
    assert depois["indicadores"]["aprovadas"]["tempo_medio_min"] == 73
    assert depois["indicadores"]["aprovadas"]["contexto"] == "tempo médio de 1 h 13 min"
    assert depois["contagens"] == {
        "pendente": 1,
        "aprovado": 3,
        "recusado": 1,
        "minhas_pendentes": 0,
    }
    aba_recusadas = (
        _api(seed, "Rodrigo").get(APROVACOES, {"status": "recusado"}).json()["resultados"]
    )
    assert [p["id"] for p in aba_recusadas] == [pneus.pk]


def test_apr_12_ca_apr_04_cancelado_nao_muda_numeros_do_seed(seed: Any, relogio: Any):
    relogio.em("2026-10-08 09:00")
    antes = _api(seed, "Rodrigo").get(APROVACOES).json()
    pedido_id = _desconto_street_de_8(seed, relogio)
    cancelado = _api(seed, "Bruna").post(f"{APROVACOES}{pedido_id}/cancelar/", format="json")
    assert cancelado.status_code == 200, cancelado.json()

    depois = _api(seed, "Rodrigo").get(APROVACOES).json()
    assert depois["indicadores"] == antes["indicadores"]
    assert depois["contagens"] == antes["contagens"]

    minhas = _api(seed, "Bruna").get(APROVACOES, {"minhas": "true"}).json()
    assert minhas["contagens"]["minhas_pendentes"] == 1
    assert [(p["tipo"], p["status"], p["pode_cancelar"]) for p in minhas["resultados"]] == [
        ("APR-02", "pendente", True),
        ("APR-01", "cancelado", False),
    ]


def test_apr_12_apr_04_ca_apr_05_diferenca_de_caixa_do_rodrigo_aprovada_pela_mariana(
    seed: Any, relogio: Any
):
    relogio.em("2026-10-08 08:00")
    caixa = Caixa.objects.get()
    fechar = _api(seed, "Rodrigo").post(
        f"/api/financeiro/caixas/{caixa.pk}/fechar/",
        {"contado_centavos": 27000, "motivo_diferenca": "Faltou troco"},
        format="json",
    )
    assert fechar.status_code == 200, fechar.json()
    assert fechar.json()["status"] == "aguardando_aprovacao"
    caixa.refresh_from_db()
    pedido_id = int(caixa.pedido_aprovacao_id or 0)
    PedidoAprovacao.objects.filter(pk=pedido_id).update(criado_em=comum_relogio.agora())

    rodrigo_antes = _api(seed, "Rodrigo").get(APROVACOES).json()
    assert rodrigo_antes["indicadores"]["esperando"]["quantidade"] == 2
    assert rodrigo_antes["contagens"]["pendente"] == 2
    assert rodrigo_antes["contagens"]["minhas_pendentes"] == 1
    meus = _api(seed, "Rodrigo").get(APROVACOES, {"minhas": "true"}).json()["resultados"]
    assert len(meus) == 1 and meus[0]["id"] == pedido_id
    assert (meus[0]["pode_cancelar"], meus[0]["pode_decidir"]) == (True, False)
    assert meus[0]["resumo"] == {
        "celulas": [
            {"rotulo": "Esperado", "valor": "R$ 281,00"},
            {"rotulo": "Contado", "valor": "R$ 270,00"},
            {"rotulo": "Diferença", "valor": "falta de R$ 11,00"},
        ],
        "nota": "Aprovada, o caixa fecha com a diferença registrada.",
    }

    mariana_antes = _api(seed, "Mariana").get(APROVACOES).json()
    assert mariana_antes["indicadores"]["esperando"]["quantidade"] == 3

    relogio.em("2026-10-08 08:30")
    aprovado = _api(seed, "Mariana").post(f"{APROVACOES}{pedido_id}/aprovar/", {}, format="json")
    assert aprovado.status_code == 200, aprovado.json()

    rodrigo_depois = _api(seed, "Rodrigo").get(APROVACOES).json()
    mariana_depois = _api(seed, "Mariana").get(APROVACOES).json()
    assert rodrigo_depois["indicadores"]["aprovadas"]["quantidade"] == 2
    assert mariana_depois["indicadores"]["aprovadas"]["quantidade"] == 3
    meus_depois = _api(seed, "Rodrigo").get(APROVACOES, {"minhas": "true"}).json()["resultados"]
    assert [(p["id"], p["status"], p["pode_cancelar"]) for p in meus_depois] == [
        (pedido_id, "aprovado", False)
    ]


@pytest.mark.xfail(
    strict=True,
    reason="T-341: placa no resumo da despesa sai PMZ3E17 sem hífen (financeiro/services.py:1637)",
)
def test_apr_03_ca_apr_11_resumo_dos_pneus_com_placa_pmz_3e17(seed: Any):
    pneus = _pedido_da_despesa("Pneus (2)")
    corpo = _api(seed, "Rodrigo").get(APROVACOES).json()
    item = next(p for p in corpo["resultados"] if p["id"] == pneus.pk)
    assert item["resumo"] == {
        "celulas": [
            {"rotulo": "Categoria", "valor": "Manutenção"},
            {"rotulo": "Descrição", "valor": "Pneus (2)"},
            {"rotulo": "Veículo", "valor": "Honda Pop 110i · PMZ-3E17"},
            {"rotulo": "Valor", "valor": "R$ 1.200,00"},
            {"rotulo": "Vencimento", "valor": "07 out"},
        ],
        "nota": "Acima de R$ 500 precisa de aprovação. Aprovada, vai para o financeiro pagar.",
    }
