"""T-522 B1 · O tipo (moto ou carro) é do próprio veículo e o tipo de plano sai (ADR 0043).

Regras: VEI-01, VEI-11, VEI-12, VEI-15, CLI-02, VIS-01, FIL-04 (PR #692). O veículo de categoria
nula, como o cadastrado depois da ADR, passa pela Frota, pela Nova locação, pela CNH e pela
vistoria de saída; as migrações `veiculos 0014` e `0015` preenchem o tipo pela categoria nas
empresas que já existem e não fazem nada na empresa nova. A frota dos testes (`frota.py`) já nasce
sem categoria, então os testes da T-013, T-015, T-016 e T-288 também a cobrem.
"""

import importlib
from types import SimpleNamespace
from typing import Any

import pytest
from django.apps import apps as django_apps
from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.veiculos import services
from apps.veiculos.models import (
    Categoria,
    CustosVeiculo,
    HistoricoPrecoVeiculo,
    PlanoVeiculo,
    RegrasVeiculo,
    Veiculo,
)
from apps.vistorias import services as vistorias_services
from comum import relogio as relogio_do_giro
from comum.erros import ErroDeValidacao
from seed.ator import como

from .frota import CARRO, Frota, criar_veiculo, montar_frota
from .test_t012_filiais import MotoRapida
from .test_t014_clientes import ANA
from .test_t015_locacoes import Cenario, _recusada, cenario  # noqa: F401

VEICULOS = "/api/veiculos/"
SEM_PRECO = "Sem preço · ligue um plano"


@pytest.fixture
def moto(empresa_a, planos, relogio) -> MotoRapida:
    return MotoRapida(empresa_a, planos["Profissional"])


@pytest.fixture
def frota(moto) -> Frota:
    return montar_frota(moto)


def _novo(frota: Frota, **campos: Any) -> dict[str, Any]:
    return {
        "placa": "QAB1C23",
        "chassi": "9C2JC4820TR000123",
        "marca": "Renault",
        "modelo": "Kwid",
        "ano_fabricacao": 2026,
        "ano_modelo": 2026,
        "cor": "branca",
        "km_atual": 0,
        "tipo_veiculo": "carro",
        "filial_id": frota.centro.pk,
        **campos,
    }


def _cadastrar(moto: MotoRapida, corpo: dict[str, Any]) -> Any:
    return moto.api("Rodrigo").post(VEICULOS, corpo, format="json")


# --- O tipo é do veículo (VEI-11) ---


def test_vei_11_tipo_e_do_veiculo(moto, frota) -> None:
    """A Frota filtra e conta Moto e Carro pelo tipo do veículo, com todos de categoria nula."""
    assert not Veiculo.objects.filter(categoria__isnull=False).exists()
    api = moto.api("Rodrigo")
    carros = api.get(VEICULOS, {"tipo_veiculo": "carro", "tamanho": 100}).json()
    assert {v["tipo_veiculo"] for v in carros["resultados"]} == {"carro"}
    assert len(carros["resultados"]) == 6
    assert (carros["contagens"]["motos"], carros["contagens"]["carros"]) == (0, 6)
    todos = api.get(VEICULOS).json()["contagens"]
    assert (todos["motos"], todos["carros"]) == (80, 6)
    ficha = api.get(f"{VEICULOS}{frota.veiculos['RHT9F02'].pk}/").json()
    assert ficha["tipo_veiculo"] == "carro"
    assert "categoria" not in ficha and "preco_vigente" not in ficha


def test_vei_11_categoria_antiga_nao_decide_o_tipo(moto, frota) -> None:
    """Dado antigo: um veículo com categoria de carro e tipo moto é moto em tudo (a categoria
    não é mais lida)."""
    carro_antigo = Categoria.objects.create(nome="Carro antigo", tipo_veiculo="carro")
    sak = frota.veiculos["SAK1D39"]
    Veiculo.objects.filter(pk=sak.pk).update(categoria=carro_antigo)
    api = moto.api("Rodrigo")
    assert api.get(f"{VEICULOS}{sak.pk}/").json()["tipo_veiculo"] == "moto"
    placas = {
        v["placa"]
        for v in api.get(VEICULOS, {"tipo_veiculo": "moto", "tamanho": 100}).json()["resultados"]
    }
    assert "SAK1D39" in placas


# --- Cadastro (VEI-01, VEI-11) ---


def test_vei_01_cadastro_sem_tipo_veiculo_400(moto, frota) -> None:
    for corpo in (
        {k: v for k, v in _novo(frota).items() if k != "tipo_veiculo"},
        _novo(frota, tipo_veiculo=None),
        _novo(frota, tipo_veiculo="caminhao"),
    ):
        resposta = _cadastrar(moto, corpo)
        assert resposta.status_code == 400, resposta.json()
        assert resposta.json()["campos"]["tipo_veiculo"] == ["Escolha moto ou carro."]
    assert not Veiculo.objects.filter(placa="QAB1C23").exists()
    # O serviço (importação, troca na venda) confere o mesmo, com a mesma frase.
    with pytest.raises(ErroDeValidacao) as erro:
        services.cadastrar({k: v for k, v in _novo(frota).items() if k != "tipo_veiculo"})
    assert erro.value.campos["tipo_veiculo"] == ["Escolha moto ou carro."]


def test_vei_01_cadastro_ignora_categoria_id(moto, frota) -> None:
    antiga = Categoria.objects.create(nome="Compacto antigo", tipo_veiculo="moto")
    resposta = _cadastrar(moto, _novo(frota, categoria_id=antiga.pk))
    assert resposta.status_code == 201, resposta.json()
    assert resposta.json()["tipo_veiculo"] == "carro"
    veiculo = Veiculo.objects.get(placa="QAB1C23")
    assert (veiculo.tipo_veiculo, veiculo.categoria_id) == ("carro", None)
    evento = EventoAuditoria.objects.get(acao="veiculo.cadastrar", objeto_id=veiculo.pk)
    assert evento.depois["tipo_veiculo"] == "carro"
    assert "categoria_id" not in evento.depois


def test_vei_11_receber_na_troca_exige_o_tipo(moto, frota) -> None:
    """A troca na venda (VEI-07) cria o veículo pelo mesmo cadastro: sem tipo, 400."""
    dados = {k: v for k, v in _novo(frota).items() if k not in ("chassi", "tipo_veiculo")}
    with pytest.raises(ErroDeValidacao) as erro:
        services.receber_na_troca("9C2TROCA000000009", {**dados, "venda_id": 181})
    assert "tipo_veiculo" in erro.value.campos
    nova = services.receber_na_troca(
        "9C2TROCA000000009", {**dados, "tipo_veiculo": "carro", "venda_id": 181}
    )
    assert (nova.status, nova.tipo_veiculo, nova.categoria_id) == ("indisponivel", "carro", None)


# --- Nascimento "sem preço" (VEI-12, VEI-15, ADR 0043 item 5, ponto T-522 · 1 padrão A) ---


def test_vei_12_vei_15_cadastro_nasce_sem_preco(moto, frota) -> None:
    resposta = _cadastrar(moto, _novo(frota))
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    assert (corpo["status"], corpo["motivo_status"]) == ("indisponivel", SEM_PRECO)
    assert corpo["aviso_preco"] is not None
    veiculo = Veiculo.objects.get(pk=corpo["id"])
    planos = {p.tipo: p for p in PlanoVeiculo.ativos.filter(veiculo=veiculo)}
    assert set(planos) == {"diaria", "semanal", "mensal"}
    for tipo, como_paga in (
        ("diaria", "tudo_na_retirada"),
        ("semanal", "semana_adiantado"),
        ("mensal", "mes_uma_parcela"),
    ):
        plano = planos[tipo]
        assert (plano.valor_centavos, plano.ligado, plano.caucao_centavos) == (0, False, None)
        assert plano.como_paga == como_paga
        assert plano.formas_aceitas == ["pix", "boleto", "cartao", "dinheiro"]
        assert plano.agendado_para is None
    regras = RegrasVeiculo.objects.get(veiculo=veiculo)
    assert (
        regras.dia_atraso_centavos,
        regras.multa_minima_centavos,
        regras.km_excedente_centavos,
        str(regras.desconto_sem_aprovacao_pct),
        regras.prazo_devolucao_caucao_dias,
    ) == (0, 0, 0, "5.00", None)
    assert CustosVeiculo.objects.filter(veiculo=veiculo).exists()
    assert set(
        HistoricoPrecoVeiculo.objects.filter(veiculo=veiculo).values_list("origem", flat=True)
    ) == {"cadastro"}
    assert list(veiculo.historico.values_list("de", "para")) == [("", "indisponivel")]

    # O primeiro plano ligado na tela de preços leva a `disponivel` (VEI-15).
    semanal = {
        "tipo": "semanal",
        "valor_centavos": 64900,
        "caucao_centavos": 80000,
        "ligado": True,
        "agendado": None,
    }
    with como(moto.pessoas["Mariana"]):
        services.salvar_precos(veiculo, {"planos": [semanal]})
    veiculo.refresh_from_db()
    assert (veiculo.status, veiculo.motivo_status) == ("disponivel", "")


# --- Leitores do tipo: CNH (CLI-02) e vistoria (VIS-01) ---


def test_cli_02_cnh_pelo_tipo_do_veiculo(cenario) -> None:  # noqa: F811
    """O carro de categoria nula pede CNH B: Ana, só com A, é recusada; Diego (AB) aluga."""
    kwid = cenario.veiculo(CARRO)
    assert (kwid.tipo_veiculo, kwid.categoria_id) == ("carro", None)
    cenario.clientes["Ana"] = clientes_services.cadastrar(
        {**ANA, "cnh": {**ANA["cnh"], "categoria": "A"}}
    )
    corpo = _recusada(cenario, "CLI-02", cliente="Ana", veiculo=kwid)
    assert corpo["mensagem"] == "A CNH do cliente não tem a categoria B."
    confirmada = cenario.confirmada(cliente="Diego", veiculo=kwid)
    assert confirmada["status"] == "aguardando_retirada"


def test_vis_01_itens_pelo_tipo_do_veiculo(cenario) -> None:  # noqa: F811
    """A vistoria de saída do carro de categoria nula traz os itens do carro."""
    kwid = cenario.veiculo(CARRO)
    confirmada = cenario.confirmada(cliente="Diego", veiculo=kwid)
    locacao = Locacao.objects.get(pk=confirmada["id"])
    codigos = [i["codigo"] for i in vistorias_services.itens_iniciais(locacao, kwid)]
    assert codigos == [c for c, _ in vistorias_services.ITENS_PADRAO["carro"]]
    sak = cenario.sak
    moto = cenario.confirmada(cliente="Lucas", veiculo=sak)
    locacao_moto = Locacao.objects.get(pk=moto["id"])
    codigos_moto = [i["codigo"] for i in vistorias_services.itens_iniciais(locacao_moto, sak)]
    assert codigos_moto == [c for c, _ in vistorias_services.ITENS_PADRAO["moto"]]


# --- Migrações (ADR 0043, item 2) ---


def _migracao() -> Any:
    return importlib.import_module("apps.veiculos.migrations.0015_tipo_pela_categoria")


def test_t522_migracao_preenche_tipo_pela_categoria(moto, frota) -> None:
    """Todos nasceram `moto` na 0014; a 0015 passa a `carro` os de categoria de carro, o
    excluído (VEI-22) e o vendido incluídos, e deixa os outros como estão. Rodar de novo não
    muda nada."""
    carro = Categoria.objects.create(nome="Carro compacto", tipo_veiculo="carro")
    moto_antiga = Categoria.objects.create(nome="Urbana", tipo_veiculo="moto")
    kwid = criar_veiculo(910, CARRO, frota.centro, tipo_veiculo="moto", categoria=carro)
    excluido = criar_veiculo(
        911,
        CARRO,
        frota.centro,
        tipo_veiculo="moto",
        categoria=carro,
        excluido_em=relogio_do_giro.agora(),
    )
    vendido = criar_veiculo(
        912, CARRO, frota.centro, "vendido", tipo_veiculo="moto", categoria=carro
    )
    pop = criar_veiculo(913, "Urbana 110–125", frota.centro, categoria=moto_antiga)
    for _ in range(2):
        _migracao().preencher(django_apps, None)
        tipos = dict(
            Veiculo.todos.filter(pk__in=[kwid.pk, excluido.pk, vendido.pk, pop.pk]).values_list(
                "placa", "tipo_veiculo"
            )
        )
        assert tipos == {
            kwid.placa: "carro",
            excluido.placa: "carro",
            vendido.placa: "carro",
            pop.placa: "moto",
        }
    # Os sem categoria (a frota de hoje) ficam com o tipo que já têm.
    assert Veiculo.objects.filter(categoria__isnull=True, tipo_veiculo="carro").count() == 6


def test_t522_migracao_na_empresa_nova(moto, frota) -> None:
    """Na empresa nova (schema sem veículos), pela conexão da migração, nada é alterado e nada
    quebra. A criação de schema de verdade, pelo papel de migração, roda todas as migrações nos
    testes da T-477."""
    empresa_b = Empresa.objects.get(schema_name="empresa_b")
    connection.set_tenant(empresa_b)
    try:
        assert not Veiculo.todos.exists()
        editor = SimpleNamespace(connection=SimpleNamespace(alias=connection.alias))
        _migracao().preencher(django_apps, editor)
        assert not Veiculo.todos.exists()
    finally:
        connection.set_tenant(moto.empresa)
    # Na empresa A, nada mudou por isso.
    assert Veiculo.objects.filter(tipo_veiculo="carro").count() == 6
