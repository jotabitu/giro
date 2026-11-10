"""T-417 · Despesas do veículo na ficha, com categorias próprias (docs/qa/criterios/T-417.md,
CA-417-01 a 13; `FIN-06`, `FIN-16`, `FIN-17`, `VEI-05`).

Cenário da T-178: Moto Rápida em 07 out 2026, Filial Centro, com as 6 despesas de outubro (o óleo
de R$ 48,00 no QXA-4B21, pago no caixa; os pneus de R$ 1.200,00 no PMZ-3E17, aguardando o
gerente).
"""

from typing import Any

from apps.financeiro.models import CategoriaDespesa, ContaReceber, Despesa
from apps.veiculos.models import Veiculo

from .test_t013_veiculos import _caucaia
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _jpg
from .test_t017_financeiro import (  # noqa: F401 - fixtures
    _decidir,
    _despesa,
    caixa_do_seed,
    lucas,
    recebimentos,
)
from .test_t178_despesas import frota_com_historico, outubro  # noqa: F401 - fixtures
from .test_t317_varredura_suporte import _suporte

DESPESAS = "/api/financeiro/despesas/"


def _rota(veiculo: Veiculo) -> str:
    return f"{DESPESAS}veiculo/{veiculo.pk}/"


def _veiculo(cenario, placa: str) -> Veiculo:  # noqa: F811
    return cenario.frota.veiculos[placa]


def _ficha(cenario, placa: str, quem: str = "Rodrigo") -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(f"/api/veiculos/{_veiculo(cenario, placa).pk}/")
    assert resposta.status_code == 200, resposta.json()
    return resposta.json()


def _lancar_pela_ficha(cenario, placa: str, quem: str = "Rodrigo", **campos: Any) -> Any:  # noqa: F811
    corpo = {
        "descricao": "IPVA 2026",
        "valor_centavos": 21000,
        "data": "2026-10-07",
        "vencimento": "2026-10-07",
        "categoria": "ipva",
        "nota": _jpg("nota.jpg"),
        **campos,
    }
    corpo = {k: v for k, v in corpo.items() if v is not None}
    return cenario.moto.api(quem).post(_rota(_veiculo(cenario, placa)), corpo, format="multipart")


# --- Categorias (FIN-06) ---


def test_fin_06_ca_417_01_categorias_em_dois_grupos():
    assert CategoriaDespesa.values == [
        "ipva",
        "seguro",
        "multa_transito",
        "pecas",
        "combustivel",
        "manutencao",
        "rastreamento",
        "fixas",
        "impostos",
        "pessoal",
        "outros",
    ]
    assert CategoriaDespesa.IPVA.label == "IPVA e licenciamento"


def test_fin_06_ca_417_02_nenhuma_categoria_exige_veiculo(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    seguro = _despesa(
        cenario, "Lúcia", descricao="Seguro da frota", valor_centavos=38000, categoria="seguro"
    )
    assert seguro.status_code == 201, seguro.json()
    assert (seguro.json()["status"], seguro.json()["veiculo"]) == ("a_pagar", None)
    pmz = _veiculo(cenario, "PMZ3E17").pk
    diesel = _despesa(cenario, "Lúcia", descricao="Diesel", categoria="combustivel", veiculo_id=pmz)
    assert diesel.status_code == 201, diesel.json()
    assert diesel.json()["veiculo"]["placa"] == "PMZ3E17"


def test_fin_06_ca_417_03_o_que_ja_foi_lancado_nao_muda(cenario, outubro):  # noqa: F811
    assert Despesa.objects.get(descricao="IPVA ROE-2A88").categoria == "impostos"
    indicadores = cenario.moto.api("Lúcia").get(DESPESAS, {"mes": "2026-10"}).json()["indicadores"]
    assert indicadores["gasto_mes_centavos"] == 706670
    assert indicadores["por_categoria"] == {
        "fixas": 391230,
        "rastreamento": 172000,
        "manutencao": 124800,
        "impostos": 18640,
    }


def test_fin_06_ca_417_04_vistoriador_lanca_manutencao_e_pecas(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    pneu = _despesa(cenario, "João", descricao="Pneu dianteiro", categoria="pecas")
    assert pneu.status_code == 201, pneu.json()
    antes = Despesa.objects.count()
    for categoria in ("combustivel", "ipva"):
        recusada = _despesa(cenario, "João", categoria=categoria)
        assert recusada.status_code == 403
        assert recusada.json()["codigo"] == "FIN-06"
        assert recusada.json()["mensagem"] == "Seu perfil lança só despesas de manutenção e peças."
    # Pela ficha também (FIN-17).
    pela_ficha = _lancar_pela_ficha(cenario, "QXA4B21", "João", categoria="combustivel")
    assert pela_ficha.status_code == 403
    assert pela_ficha.json()["codigo"] == "FIN-06"
    assert Despesa.objects.count() == antes


def test_fin_06_ca_417_05_multa_de_transito_nao_cobra_o_cliente(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    contas = ContaReceber.objects.count()
    multa = _despesa(
        cenario,
        "Lúcia",
        descricao="Multa QXA-4B21 · 12/09",
        valor_centavos=19523,
        categoria="multa_transito",
        veiculo_id=_veiculo(cenario, "QXA4B21").pk,
    )
    assert multa.status_code == 201, multa.json()
    assert ContaReceber.objects.count() == contas


# --- Filtro por veículo (FIN-16) ---


def test_fin_16_ca_417_06_filtro_por_veiculo(cenario, outubro):  # noqa: F811
    lucia = cenario.moto.api("Lúcia")
    todas = lucia.get(DESPESAS, {"mes": "2026-10"}).json()
    pmz = lucia.get(DESPESAS, {"mes": "2026-10", "veiculo": _veiculo(cenario, "PMZ3E17").pk}).json()
    assert [d["descricao"] for d in pmz["resultados"]] == ["Pneus (2 unidades)"]
    assert (pmz["indicadores"], pmz["contagens"]) == (todas["indicadores"], todas["contagens"])
    assert pmz["indicadores"]["despesa_por_veiculo_centavos"] == 8217
    qxa = lucia.get(DESPESAS, {"mes": "2026-10", "veiculo": _veiculo(cenario, "QXA4B21").pk}).json()
    assert [d["descricao"] for d in qxa["resultados"]] == ["Óleo 1 litro"]


# --- Ficha (FIN-17, VEI-05) ---


def test_fin_17_vei_05_ca_417_07_lista_no_qxa(cenario, outubro):  # noqa: F811
    lista = cenario.moto.api("Rodrigo").get(_rota(_veiculo(cenario, "QXA4B21")))
    assert lista.status_code == 200, lista.json()
    corpo = lista.json()
    assert (corpo["ano"], corpo["total_ano_centavos"]) == (2026, 4800)
    assert [
        (d["data"], d["descricao"], d["categoria"], d["valor_centavos"], d["status"])
        for d in corpo["resultados"]
    ] == [("2026-10-07", "Óleo 1 litro", "manutencao", 4800, "paga")]
    ficha = _ficha(cenario, "QXA4B21")
    assert ficha["indicadores_financeiros"]["custo_manutencao_ano_centavos"] == 4800
    assert ficha["indicadores_financeiros"]["despesas_ano_centavos"] == 4800
    # Outro ano: nada.
    vazio = (
        cenario.moto.api("Rodrigo").get(_rota(_veiculo(cenario, "QXA4B21")), {"ano": "2025"}).json()
    )
    assert (vazio["ano"], vazio["total_ano_centavos"], vazio["resultados"]) == (2025, 0, [])


def test_fin_17_ca_417_08_aguardando_e_recusada(cenario, outubro):  # noqa: F811
    rota = _rota(_veiculo(cenario, "PMZ3E17"))
    rodrigo = cenario.moto.api("Rodrigo")
    corpo = rodrigo.get(rota).json()
    assert [(d["status"], d["valor_centavos"]) for d in corpo["resultados"]] == [
        ("aguardando_aprovacao", 120000)
    ]
    assert corpo["total_ano_centavos"] == 120000
    assert _decidir(cenario, outubro["pneus"], "recusar").status_code == 200
    corpo = rodrigo.get(rota).json()
    assert [d["status"] for d in corpo["resultados"]] == ["recusada"]
    assert corpo["total_ano_centavos"] == 0
    assert _ficha(cenario, "PMZ3E17")["indicadores_financeiros"]["despesas_ano_centavos"] == 0


def test_fin_17_ca_417_09_quem_ve_a_lista(cenario, outubro):  # noqa: F811
    rota = _rota(_veiculo(cenario, "QXA4B21"))
    for quem in ("Mariana", "Rodrigo", "Lúcia"):
        assert cenario.moto.api(quem).get(rota).status_code == 200, quem
        assert (
            "despesas_ano_centavos" in _ficha(cenario, "QXA4B21", quem)["indicadores_financeiros"]
        )
    for quem in ("Bruna", "João"):
        assert cenario.moto.api(quem).get(rota).status_code == 403, quem
        assert "indicadores_financeiros" not in _ficha(cenario, "QXA4B21", quem)


def test_fin_17_vei_05_ca_417_10_lancar_pela_ficha(cenario, outubro):  # noqa: F811
    rendeu_antes = _ficha(cenario, "QXA4B21")["indicadores_financeiros"]["rendeu_no_ano_centavos"]
    lancada = _lancar_pela_ficha(
        cenario, "QXA4B21", veiculo_id=str(_veiculo(cenario, "PMZ3E17").pk)
    )
    assert lancada.status_code == 201, lancada.json()
    despesa = lancada.json()
    # O veículo é o da rota, não o do corpo; a filial é a do veículo.
    assert despesa["veiculo"]["placa"] == "QXA4B21"
    assert despesa["filial"]["nome"] == "Filial Centro"
    assert (despesa["status"], despesa["categoria"]) == ("a_pagar", "ipva")
    fin = _ficha(cenario, "QXA4B21")["indicadores_financeiros"]
    assert fin["despesas_ano_centavos"] == 25800
    assert fin["custo_manutencao_ano_centavos"] == 4800
    assert fin["rendeu_no_ano_centavos"] == rendeu_antes - 21000
    gasto = cenario.moto.api("Lúcia").get(DESPESAS, {"mes": "2026-10"}).json()["indicadores"]
    assert gasto["gasto_mes_centavos"] == 727670


def test_fin_17_ca_417_11_regras_de_sempre_pela_ficha(cenario, outubro):  # noqa: F811
    antes = Despesa.objects.count()
    sem_nota = _lancar_pela_ficha(cenario, "QXA4B21", nota=None)
    assert sem_nota.status_code == 400
    assert sem_nota.json()["campos"]["nota"] == ["Envie a foto da nota."]
    revisao: dict[str, Any] = {
        "descricao": "Revisão completa",
        "valor_centavos": 65000,
        "categoria": "manutencao",
    }
    pago = _lancar_pela_ficha(cenario, "QXA4B21", pago_no_caixa="true", **revisao)
    assert pago.status_code == 422
    assert pago.json()["codigo"] == "APR-03"
    assert Despesa.objects.count() == antes
    acima = _lancar_pela_ficha(cenario, "QXA4B21", **revisao)
    assert acima.status_code == 201, acima.json()
    assert acima.json()["status"] == "aguardando_aprovacao"
    # O caixa é o da filial do veículo: a Caucaia não tem caixa aberto.
    caucaia = _caucaia(cenario.moto)
    Veiculo.objects.filter(pk=_veiculo(cenario, "QXA4B21").pk).update(filial=caucaia)
    sem_caixa = _lancar_pela_ficha(
        cenario, "QXA4B21", "Mariana", pago_no_caixa="true", valor_centavos=4800
    )
    assert sem_caixa.status_code == 422, sem_caixa.json()
    assert sem_caixa.json()["mensagem"] == "Abra o caixa do dia para pagar por ele"
    assert Despesa.objects.count() == antes + 1


def test_fin_17_ca_417_12_botao_para_quem_lanca(cenario, outubro):  # noqa: F811
    for quem in ("Mariana", "Rodrigo", "Lúcia", "Bruna", "João"):
        assert _ficha(cenario, "QXA4B21", quem)["acoes"]["lancar_despesa"] is True, quem
    bruna = _lancar_pela_ficha(
        cenario, "QXA4B21", "Bruna", descricao="Gasolina", categoria="combustivel"
    )
    assert bruna.status_code == 201, bruna.json()
    joao = _lancar_pela_ficha(cenario, "QXA4B21", "João", descricao="Vela", categoria="pecas")
    assert joao.status_code == 201, joao.json()
    antes = Despesa.objects.count()
    suporte = _suporte(cenario).post(
        _rota(_veiculo(cenario, "QXA4B21")),
        {"descricao": "x", "valor_centavos": 100, "categoria": "ipva"},
        format="multipart",
    )
    assert suporte.status_code == 403
    assert suporte.json()["codigo"] == "PLT-07"
    assert Despesa.objects.count() == antes


def test_fin_17_ca_417_13_veiculo_transferido(cenario, outubro):  # noqa: F811
    qxa = _veiculo(cenario, "QXA4B21")
    caucaia = _caucaia(cenario.moto)
    Veiculo.objects.filter(pk=qxa.pk).update(filial=caucaia)
    mariana = cenario.moto.api("Mariana")
    corpo = mariana.get(_rota(qxa)).json()
    assert [(d["descricao"], d["filial"]["nome"]) for d in corpo["resultados"]] == [
        ("Óleo 1 litro", "Filial Centro")
    ]
    lancada = _lancar_pela_ficha(cenario, "QXA4B21", "Mariana")
    assert lancada.status_code == 201, lancada.json()
    assert lancada.json()["filial"]["nome"] == "Filial Caucaia"


def test_fin_17_veiculo_fora_das_filiais_responde_404(cenario, outubro):  # noqa: F811
    qxa = _veiculo(cenario, "QXA4B21")
    Veiculo.objects.filter(pk=qxa.pk).update(filial=_caucaia(cenario.moto))
    # O Rodrigo é só da Filial Centro.
    assert cenario.moto.api("Rodrigo").get(_rota(qxa)).status_code == 404
    assert _lancar_pela_ficha(cenario, "QXA4B21").status_code == 404
