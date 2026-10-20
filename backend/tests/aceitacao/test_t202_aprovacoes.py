"""T-202 · Os números da tela Aprovações (`APR-12`, CA-APR-02 a 08) e o `resumo` do desconto
(`aprovacoes.md`, T-201; CA-APR-10). Os números do seed (CA-APR-01) e o `resumo` dos pneus
(CA-APR-11) estão em `test_t202_seed_aprovacoes.py`.

Roda no cenário da T-015 (Moto Rápida, Filial Centro, Street semanal R$ 329,00, 07 out 2026).
"""

from itertools import count
from typing import Any

from apps.aprovacoes import services as aprovacoes_services
from apps.aprovacoes.models import PedidoAprovacao
from apps.filiais import services as filiais_services
from comum import relogio as comum_relogio

from .test_t012_filiais import CENTRO
from .test_t015_locacoes import cenario  # noqa: F401 - fixture

LISTA = "/api/aprovacoes/"
_origens = count(9000)


def _lista(cenario, quem: str = "Rodrigo", **parametros: Any) -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem, **parametros.pop("cabecalhos", {})).get(LISTA, parametros)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _na_hora(pedido_id: int) -> PedidoAprovacao:
    """`criado_em` é `auto_now_add` (hora real): o pedido leva a hora do relógio do teste, como
    o seed faz com o `RelogioDoSeed`."""
    PedidoAprovacao.objects.filter(pk=pedido_id).update(criado_em=comum_relogio.agora())
    return PedidoAprovacao.objects.get(pk=pedido_id)


def _despesa(cenario, quem: str = "João", filial_id: int | None = None) -> PedidoAprovacao:  # noqa: F811
    """Um pedido APR-03 pela porta, como a despesa faz, na hora do relógio."""
    ref = aprovacoes_services.pedir(
        tipo="APR-03",
        origem_tipo="despesa",
        origem_id=next(_origens),
        origem_codigo=None,
        filial_id=filial_id or cenario.frota.centro.pk,
        solicitante=cenario.pessoas[quem],
        titulo="Despesa de R$ 1.200,00",
        detalhe="Pneus · Manutenção",
        valor_centavos=120000,
    )
    return _na_hora(ref.id)


def _desconto_de_8(cenario, relogio) -> PedidoAprovacao:  # noqa: F811
    relogio.em("2026-10-08 09:00")
    criada = cenario.confirmada(desconto_pct="8.00")
    return _na_hora(criada["desconto"]["pedido_aprovacao_id"])


def test_apr_01_resumo_do_desconto(cenario, relogio):  # noqa: F811
    pedido = _desconto_de_8(cenario, relogio)
    assert pedido.valor_centavos == 2632  # o desconto de um período: 32900 − 30268
    [item] = _lista(cenario)["resultados"]
    assert item["resumo"] == {
        "celulas": [
            {"rotulo": "Preço de tabela", "valor": "R$ 329,00"},
            {"rotulo": "Com desconto", "valor": "R$ 302,68"},
            {"rotulo": "Desconto", "valor": "R$ 26,32 · 8%"},
        ],
        "nota": "O limite de Bruna é 5%.",
    }


def test_apr_12_desconto_aprovado(cenario, relogio):  # noqa: F811
    pedido = _desconto_de_8(cenario, relogio)
    relogio.em("2026-10-08 09:40")
    aprovacoes_services.aprovar(pedido, cenario.pessoas["Rodrigo"], "")
    corpo = _lista(cenario)
    indicadores = corpo["indicadores"]
    assert indicadores["mes"] == "2026-10"
    assert indicadores["aprovadas"] == {
        "titulo": "Aprovadas em outubro",
        "quantidade": 1,
        "tempo_medio_min": 40,
        "contexto": "tempo médio de 40 min",
    }
    assert indicadores["descontos"] == {
        "titulo": "Descontos aprovados",
        "valor_centavos": 2632,
        "quantidade": 1,
        "contexto": "em 1 pedido",
    }
    assert corpo["contagens"] == {
        "pendente": 0,
        "aprovado": 1,
        "recusado": 0,
        "minhas_pendentes": 0,
    }
    aprovadas = _lista(cenario, status="aprovado")["resultados"]
    assert [p["id"] for p in aprovadas] == [pedido.pk]

    # Um segundo aprovado em 2 h 20 min: (40 + 140) ÷ 2 = 90 → "1 h 30 min".
    relogio.em("2026-10-08 10:00")
    outro = _despesa(cenario)
    relogio.em("2026-10-08 12:20")
    aprovacoes_services.aprovar(outro, cenario.pessoas["Rodrigo"], "")
    aprovadas = _lista(cenario)["indicadores"]["aprovadas"]
    assert (aprovadas["tempo_medio_min"], aprovadas["contexto"]) == (
        90,
        "tempo médio de 1 h 30 min",
    )


def test_apr_12_recusado(cenario, relogio):  # noqa: F811
    relogio.em("2026-10-07 08:00")
    pedido = _despesa(cenario)
    relogio.em("2026-10-07 10:30")
    esperando = _lista(cenario)["indicadores"]["esperando"]
    assert (esperando["quantidade"], esperando["contexto"]) == (1, "mais antigo há 2 h")
    aprovacoes_services.recusar(pedido, cenario.pessoas["Rodrigo"], "Sem orçamento")
    corpo = _lista(cenario)
    assert corpo["indicadores"]["recusadas"] == {
        "titulo": "Recusadas em outubro",
        "quantidade": 1,
        "contexto": "sempre com motivo",
    }
    assert corpo["indicadores"]["esperando"] == {
        "quantidade": 0,
        "mais_antigo_em": None,
        "contexto": None,
    }
    assert corpo["indicadores"]["aprovadas"]["tempo_medio_min"] is None  # recusado não entra
    assert len(_lista(cenario, status="recusado")["resultados"]) == 1


def test_apr_12_cancelado_nao_conta(cenario, relogio):  # noqa: F811
    pedido = _desconto_de_8(cenario, relogio)
    aprovacoes_services.cancelar(pedido, cenario.pessoas["Bruna"])
    corpo = _lista(cenario)
    assert corpo["contagens"] == {
        "pendente": 0,
        "aprovado": 0,
        "recusado": 0,
        "minhas_pendentes": 0,
    }
    assert corpo["indicadores"]["descontos"]["quantidade"] == 0
    minhas = _lista(cenario, "Bruna", minhas="true")["resultados"]
    assert [(p["id"], p["status"], p["pode_cancelar"]) for p in minhas] == [
        (pedido.pk, "cancelado", False)
    ]


def test_apr_12_sem_os_proprios(cenario, relogio):  # noqa: F811
    pedido = _despesa(cenario, quem="Rodrigo")
    assert _lista(cenario)["contagens"]["pendente"] == 0  # APR-09: não decide o próprio
    minhas = _lista(cenario, minhas="true")
    assert minhas["contagens"]["minhas_pendentes"] == 1
    assert [(p["id"], p["pode_cancelar"]) for p in minhas["resultados"]] == [(pedido.pk, True)]
    assert _lista(cenario, "Mariana")["contagens"]["pendente"] == 1
    relogio.em("2026-10-07 11:00")
    aprovacoes_services.aprovar(pedido, cenario.pessoas["Mariana"], "")
    assert _lista(cenario)["contagens"]["aprovado"] == 0
    assert _lista(cenario, "Mariana")["contagens"]["aprovado"] == 1


def test_apr_12_mes_pela_decisao(cenario, relogio):  # noqa: F811
    relogio.em("2026-09-29 10:00")
    aprovado_em_setembro = _despesa(cenario)
    pendente_de_setembro = _despesa(cenario)
    relogio.em("2026-09-30 10:00")
    aprovado_em_outubro = _despesa(cenario)
    aprovacoes_services.aprovar(aprovado_em_setembro, cenario.pessoas["Rodrigo"], "")
    relogio.em("2026-10-01 10:00")
    aprovacoes_services.aprovar(aprovado_em_outubro, cenario.pessoas["Rodrigo"], "")
    relogio.em("2026-10-07 10:00")
    corpo = _lista(cenario)
    assert corpo["contagens"]["aprovado"] == 1
    assert corpo["indicadores"]["aprovadas"]["tempo_medio_min"] == 24 * 60
    assert [p["id"] for p in _lista(cenario, status="aprovado")["resultados"]] == [
        aprovado_em_outubro.pk
    ]
    esperando = corpo["indicadores"]["esperando"]
    assert esperando["quantidade"] == 1
    assert esperando["contexto"] == "mais antigo há 8 dias"
    assert [p["id"] for p in corpo["resultados"]] == [pendente_de_setembro.pk]


def test_apr_12_sem_aprovados(cenario):  # noqa: F811
    aprovadas = _lista(cenario)["indicadores"]["aprovadas"]
    assert aprovadas["quantidade"] == 0
    assert aprovadas["tempo_medio_min"] is None and aprovadas["contexto"] is None
    descontos = _lista(cenario)["indicadores"]["descontos"]
    assert (descontos["valor_centavos"], descontos["contexto"]) == (0, "em 0 pedidos")


def test_apr_12_filial_do_seletor(cenario, relogio):  # noqa: F811
    messejana = filiais_services.criar_filial(
        {**CENTRO, "nome": "Filial Messejana", "cnpj": None}, cenario.pessoas["Mariana"]
    )
    _despesa(cenario)
    _despesa(cenario, filial_id=messejana.pk)
    todas = _lista(cenario, "Mariana", cabecalhos={"HTTP_X_FILIAL": "todas"})
    assert todas["indicadores"]["esperando"]["quantidade"] == 2
    centro = _lista(cenario, "Mariana", cabecalhos={"HTTP_X_FILIAL": str(cenario.frota.centro.pk)})
    assert centro["indicadores"]["esperando"]["quantidade"] == 1
    assert centro["contagens"]["pendente"] == 1
