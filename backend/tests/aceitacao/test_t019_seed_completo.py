"""T-019 · Seed Moto Rápida completo: os casos da tabela "Dados de referência para testes".

Roda sobre o banco que o `seed_moto_rapida` deixa (uma vez por módulo, ver T-149), sem montar
cenário: cada teste pede à API ou ao serviço o número da tabela e compara. Casos que dependem de
módulo que ainda não existe (vendas, comissões de venda, DRE, conciliação) ou de código da T-148
ficam `xfail(strict)` com a tarefa que os destrava; quando passarem, o `strict` avisa.
"""

from datetime import date
from typing import Any

import pytest
from django_tenants.utils import tenant_context

from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.financeiro import leituras as financeiro_leituras
from apps.financeiro.models import Caixa, ContaReceber, Reembolso
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens

from .conftest import cliente as cliente_http
from .test_t016_vistorias import (
    DEVOLUCOES,
    LISTA,
    _abrir_devolucao,
    _aprovar_encerramento,
    _chegada,
    _conta_do_saldo,
    _encerrar,
    _forma,
    _item,
    _km_de_volta,
    _parcelas_do_acerto,
    _valor_do_item,
)
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures

CONTAS = "/api/financeiro/contas-receber/"
CAIXAS = "/api/financeiro/caixas/"
HOST = "motorapida.localhost"
EMAILS = {
    "Mariana": "mariana@motorapida.com.br",
    "Rodrigo": "rodrigo@motorapida.com.br",
    "Bruna": "bruna@motorapida.com.br",
    "João": "joao@motorapida.com.br",
    "Lúcia": "lucia@motorapida.com.br",
}


class _Moto:
    """O que os apoios da T-016 pedem de `cenario.moto`: `api(nome)` e `_tokens`. O token sai a
    cada chamada, com o relógio do momento (não vence ao mudar de dia)."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def api(self, nome: str = "Mariana", **cabecalhos: str) -> Any:
        usuario = Usuario.objects.get(email=EMAILS[nome])
        token = str(emitir_tokens(usuario, AMR_SENHA_E_CODIGO).access_token)
        api = cliente_http(HOST, token)
        if cabecalhos:
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", **cabecalhos)
        return api


class _Cenario:
    def __init__(self) -> None:
        self.moto = _Moto()


@pytest.fixture
def seed(semeado, relogio):  # noqa: F811
    """O seed pronto, o relógio em 07 out 10:00 e o schema da Moto Rápida."""
    relogio.em("2026-10-07 10:00")
    with tenant_context(Empresa.objects.get(subdominio="motorapida")):
        yield _Cenario()


def _api(seed: _Cenario, nome: str = "Mariana", **cabecalhos: str) -> Any:
    return seed.moto.api(nome, **cabecalhos)


# --- Contas a receber (FIN-15, FIN-01) ---


def _contas_das_reservas() -> Any:
    """Parcelas das locações `aguardando_retirada` (D-01 da T-138), que a tabela não conta."""
    codigos = Locacao.objects.filter(status="aguardando_retirada").values_list("codigo", flat=True)
    return ContaReceber.objects.filter(
        origem_codigo__in=list(codigos), tipo="parcela", vencimento__year=2026, vencimento__month=10
    )


def test_fin_15_t019_recebido_vence_hoje_e_atraso_em_07_out(seed):
    """Recebido R$ 13.401,70 em 30 (25,77%), vence hoje R$ 2.625,80 em 6, em atraso R$ 1.646,40
    (2 clientes, 2 parcelas) e as abas Em atraso 2, Vencem hoje 6, Pagas 30."""
    corpo = _api(seed, "Lúcia").get(CONTAS, {"periodo": "mes"}).json()
    i = corpo["indicadores"]
    assert i["recebido_mes_centavos"] == 1340170
    assert (i["vence_hoje_centavos"], i["vence_hoje_parcelas"]) == (262580, 6)
    assert (i["em_atraso_centavos"], i["em_atraso_clientes"], i["em_atraso_parcelas"]) == (
        164640,
        2,
        2,
    )
    contagens = corpo["contagens"]
    assert (contagens["atrasadas"], contagens["vencem_hoje"], contagens["pagas"]) == (2, 6, 30)


def test_fin_15_t019_previsto_e_a_vencer_sem_as_reservas(seed):
    """Previsto R$ 52.002,10 em 128 parcelas e A vencer 92: as 42 locações abertas. As reservas
    (D-01) somam 17 parcelas de outubro; tirando-as, o seed fecha na tabela."""
    reservas = _contas_das_reservas()
    corpo = _api(seed, "Lúcia").get(CONTAS, {"periodo": "mes"}).json()
    i = corpo["indicadores"]
    assert i["previsto_mes_centavos"] - sum(c.valor_centavos for c in reservas) == 5200210
    assert i["previsto_mes_parcelas"] - reservas.count() == 128
    assert corpo["contagens"]["a_vencer"] - reservas.count() == 92


@pytest.mark.xfail(
    strict=True,
    reason="[decisão] reservas D-01 (T-138) entram em Previsto e A vencer: 145 parcelas, não 128",
)
def test_fin_15_t019_previsto_exato_da_tabela(seed):
    """A linha 'Contas a receber de outubro em 07 out' sem tirar nada: 128 parcelas, 130 abas."""
    corpo = _api(seed, "Lúcia").get(CONTAS, {"periodo": "mes"}).json()
    i = corpo["indicadores"]
    assert (i["previsto_mes_centavos"], i["previsto_mes_parcelas"]) == (5200210, 128)
    assert corpo["contagens"]["todas"] == 130


def test_fin_01_t019_em_aberto_dos_clientes(seed):
    """Carlos R$ 299,40 + Rafael R$ 1.347,00 = R$ 1.646,40 em 2 clientes."""
    corpo = _api(seed, "Rodrigo").get("/api/clientes/").json()
    assert corpo["indicadores"]["em_aberto_total_centavos"] == 164640
    assert corpo["contagens"]["em_aberto"] == 2
    em_aberto = {
        c.nome: financeiro_leituras.em_aberto_centavos(c.pk)
        for c in Cliente.objects.filter(nome__in=("Carlos Menezes", "Rafael Sousa"))
    }
    assert em_aberto == {"Carlos Menezes": 29940, "Rafael Sousa": 134700}


@pytest.mark.xfail(strict=True, reason="T-148: filtro ?periodo=semana (FIN-15, T-147)")
def test_fin_15_semana_de_segunda_a_domingo(seed):
    """Contas a receber da semana em 07 out (05 a 11 out): 36 / 2 / 6 / 13 / 15."""
    corpo = _api(seed, "Lúcia").get(CONTAS, {"periodo": "semana"}).json()
    assert corpo["contagens"] == {
        "todas": 36,
        "atrasadas": 2,
        "vencem_hoje": 6,
        "a_vencer": 13,
        "pagas": 15,
    }
    i = corpo["indicadores"]
    assert (i["previsto_mes_centavos"], i["previsto_mes_parcelas"]) == (1424750, 34)
    assert (i["recebido_mes_centavos"], i["recebido_pct"]) == (588250, "41.29")


def test_fin_15_fin_05_t019_contadores_do_menu_da_mariana(seed):
    contadores = _api(seed, "Mariana").get("/api/painel/contadores/").json()["contadores"]
    assert (contadores["receber"], contadores["despesas"]) == (2, 1)


# --- Caixa e despesas (FIN-07, FIN-05) ---


def test_fin_07_t019_caixa_de_07_out(seed):
    """Gaveta R$ 281,00 e R$ 1.111,90 em 5 entradas (Pix 329,00 + 44,90, cartão 109,00,
    dinheiro 629,00)."""
    corpo = _api(seed, "Bruna").get(f"{CAIXAS}hoje/").json()
    resumo = corpo["resumo"]
    assert (resumo["entrou_hoje_centavos"], resumo["recebimentos"]) == (111190, 5)
    assert resumo["por_forma"]["pix"] == {"centavos": 37390, "quantidade": 2}
    assert resumo["por_forma"]["cartao"]["centavos"] == 10900
    assert resumo["por_forma"]["dinheiro"] == {"centavos": 62900, "quantidade": 2}
    assert resumo["gaveta"] == {
        "troco_centavos": 20000,
        "entradas_dinheiro_centavos": 62900,
        "saidas_dinheiro_centavos": 54800,  # sangria 500,00 + óleo 48,00
        "esperado_centavos": 28100,
    }
    assert (corpo["status"], corpo["aberto_por"]["nome"]) == ("aberto", "Bruna Alves")
    assert Caixa.objects.count() == 1


def test_fin_07_t019_entradas_do_caixa_apontam_para_as_contas(seed):
    """Todo pagamento aponta para uma conta (decisão de 08 out): Juliana, a diária Urbana
    (LOC-2826), Diego (LOC-2848, renovação de 1 diária) e Lucas (1ª semana e caução)."""
    pagas = ContaReceber.objects.filter(movimento_caixa__isnull=False).order_by("pago_em")
    assert [(c.origem_codigo, c.tipo, c.valor_centavos) for c in pagas] == [
        ("LOC-2836", "parcela", 32900),
        ("LOC-2848", "parcela", 10900),
        ("LOC-2856", "parcela", 32900),
        ("LOC-2856", "caucao", 30000),
        ("LOC-2826", "parcela", 4490),
    ]
    assert Locacao.objects.get(codigo="LOC-2856").cliente.nome == "Lucas Ferreira"
    assert Locacao.objects.get(codigo="LOC-2848").cliente.nome == "Diego Martins"


def test_fin_05_t019_despesas_de_outubro(seed):
    """6 lançamentos, R$ 7.066,70; só os pneus (R$ 1.200,00) aguardam o gerente."""
    corpo = _api(seed, "Lúcia").get("/api/financeiro/despesas/", {"mes": "2026-10"}).json()
    i = corpo["indicadores"]
    assert i["gasto_mes_centavos"] == 706670
    assert (i["aguardando_aprovacao_centavos"], i["aguardando_aprovacao_quantidade"]) == (120000, 1)
    assert i["por_categoria"] == {
        "fixas": 391230,
        "rastreamento": 172000,
        "manutencao": 124800,
        "impostos": 18640,
    }
    assert corpo["contagens"] == {"aguardando_aprovacao": 1, "a_pagar": 2, "paga": 3, "recusada": 0}
    ipva = next(d for d in corpo["resultados"] if d["descricao"].startswith("IPVA"))
    assert ipva["status"] == "a_pagar"  # abaixo de R$ 500 não vai para aprovação


# --- Locações do seed: totais e preços (LOC-05, LOC-15) ---


def test_loc_05_t019_caucoes_pagas_do_seed(seed):
    """Caução paga na retirada: LOC-2841 e LOC-2856 R$ 300,00, LOC-2812 R$ 500,00."""
    caucoes = {
        c.origem_codigo: c.valor_centavos
        for c in ContaReceber.objects.filter(tipo="caucao", status="paga")
    }
    assert caucoes == {"LOC-2836": 30000, "LOC-2841": 30000, "LOC-2812": 50000, "LOC-2856": 30000}


# --- Devoluções (DEV-02, LOC-12, DEV-07) ---


def test_dev_02_t019_acerto_da_loc_2836_devolve_183(seed, relogio):
    """Caução 300,00; combustível 32,00 (3/4 do tanque); retrovisor 85,00 → devolver R$ 183,00."""
    relogio.em("2026-10-14 17:40")
    juliana = Locacao.objects.get(codigo="LOC-2836")
    assert juliana.km_saida is not None
    assert juliana.fim_previsto.isoformat() == "2026-10-14T21:00:00+00:00"
    devolucao = _abrir_devolucao(seed, juliana.pk)
    km = juliana.km_saida + 1228
    corpo = _chegada(
        seed, devolucao, km, "tres_quartos", avarias=(("Retrovisor esquerdo riscado", {}),)
    )
    retrovisor = _item(corpo, "avaria")
    assert _valor_do_item(seed, devolucao["id"], retrovisor["id"], 8500).status_code == 200
    assert _forma(seed, devolucao["id"]).status_code == 200
    acerto = _api(seed, "Bruna").get(f"{DEVOLUCOES}{devolucao['id']}/").json()["acerto"]
    assert {i["tipo"]: i["valor_centavos"] for i in acerto["itens"]} == {
        "combustivel": 3200,
        "avaria": 8500,
        "atraso": 0,
        "km_excedente": 0,
    }
    assert (acerto["total_cobrancas_centavos"], acerto["caucao_centavos"]) == (11700, 30000)
    assert acerto["resultado"]["valor_centavos"] == 18300
    assert acerto["resultado"]["botao"] == "Encerrar e devolver R$ 183,00"


def test_dev_07_t019_devolucao_antecipada_do_carlos_cobra_365_37(seed):
    """LOC-2841 em 07 out 10:00: parcela 2 R$ 306,09 + parcela 3 R$ 299,40 + multa R$ 59,88,
    menos a caução de R$ 300,00 → cobrar R$ 365,37."""
    carlos = Locacao.objects.get(codigo="LOC-2841")
    _aprovar_encerramento(seed, carlos)
    p2, p3 = (
        ContaReceber.objects.get(origem_codigo="LOC-2841", tipo="parcela", numero_parcela=n)
        for n in (2, 3)
    )
    devolucao = _abrir_devolucao(seed, carlos.pk)
    corpo = _chegada(seed, devolucao, _km_de_volta(carlos))
    acerto = corpo["acerto"]
    assert _parcelas_do_acerto(corpo) == [(30609, p2.pk), (29940, p3.pk)]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 5988
    assert (acerto["caucao_centavos"], acerto["saldo_centavos"]) == (30000, -36537)
    assert acerto["resultado"]["botao"] == "Encerrar e cobrar R$ 365,37"
    assert _encerrar(seed, devolucao["id"]).status_code == 200
    assert _conta_do_saldo(devolucao["id"]).valor_centavos == 36537


def test_loc_12_t019_encerramento_antecipado_da_loc_2812(seed):
    """NMax mensal R$ 1.590,00, pedido em 07 out, fim 15 out: multa R$ 84,80 e devolve R$ 286,20
    além da caução."""
    patricia = Locacao.objects.get(codigo="LOC-2812")
    resposta = _api(seed, "Rodrigo").post(
        f"{LISTA}{patricia.pk}/cancelar/", {"motivo": "Cliente vai mudar de cidade"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    devolucao = _abrir_devolucao(seed, patricia.pk)
    corpo = _chegada(seed, devolucao, _km_de_volta(patricia))
    acerto = corpo["acerto"]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 8480
    assert acerto["saldo_centavos"] == 78620
    assert acerto["resultado"]["texto"] == "Devolve a caução de R$ 500,00 e mais R$ 286,20"
    assert _encerrar(seed, devolucao["id"]).status_code == 200
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=devolucao["id"])
    assert reembolso.valor_centavos == 78620


# --- Cliente: bloqueio e histórico (CLI-04, CLI-05) ---


def test_cli_05_t019_bloqueio_do_rafael(seed):
    assert Cliente.objects.get(nome="Rafael Sousa").status == "bloqueado"
    assert Locacao.objects.get(codigo="LOC-2790").status == "devolucao_atrasada"
    conta = ContaReceber.objects.get(origem_codigo="LOC-2790", tipo="parcela")
    assert (conta.vencimento, conta.valor_centavos) == (date(2026, 9, 12), 134700)


@pytest.mark.xfail(strict=True, reason="T-148: histórico pela FIN-03 e 'Cliente novo na empresa'")
def test_cli_04_historico_da_analise_em_07_out(seed):
    """Juliana e Lucas `ok`, Carlos e Rafael `problema`, cliente novo `ok`."""

    def situacao(nome: str) -> str:
        historico = financeiro_leituras.montar_historico(Cliente.objects.get(nome=nome))
        assert historico is not None
        return f"{historico['situacao']}: {historico['rotulo']}"

    assert situacao("Juliana Rocha") == "ok: Sem atraso na empresa"
    assert situacao("Lucas Ferreira") == "ok: Sem atraso na empresa"
    assert situacao("Carlos Menezes") == "problema: Conta em atraso na empresa"
    assert situacao("Rafael Sousa") == "problema: Conta em atraso na empresa"
    com_conta = ContaReceber.objects.values("cliente_id")
    novo = Cliente.objects.exclude(pk__in=com_conta).first()
    assert novo is not None
    assert financeiro_leituras.montar_historico(novo) == {
        "situacao": "ok",
        "rotulo": "Cliente novo na empresa",
    }


# --- Casos sem módulo no backend (vendas, comissões, DRE, conciliação) ---

SEM_VENDAS = "módulo de vendas ainda não existe (apps/vendas é só README; VEN-02, VEN-04)"


@pytest.mark.xfail(strict=True, raises=ImportError, reason=SEM_VENDAS)
def test_ven_02_t019_venda_ven_0177():
    """Tabela 22.900,00, desconto 8%, entrada 5.000,00, 12 parcelas: final 21.068,00,
    12 × 1.339,00 e vai para aprovação."""
    from apps.vendas import services  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason=SEM_VENDAS)
def test_fin_09_t019_comissao_da_venda_ven_0177():
    """3% de 21.068,00 = R$ 632,04 pendente; comissões de outubro da Bruna R$ 968,00 e de
    setembro R$ 1.240,00 + R$ 650,00 (FIN-09, FIN-10)."""
    from apps.vendas import services  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason="sem módulo de conciliação (FIN-12)")
def test_fin_12_t019_conciliacao_diferenca_de_137_10():
    """Pix sem par +150,00 e tarifa −12,90: diferença R$ 137,10."""
    from apps.financeiro import conciliacao  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason="sem selector da DRE (FIN-13)")
def test_fin_13_t019_dre_de_setembro_34231_30():
    """Locações 56.420,00 + extras 2.310,00 + taxas 1.128,40 − despesas 21.480,30 − comissões
    1.890,00 = R$ 34.231,30 (margem 58%)."""
    from apps.relatorios.selectors import dre  # noqa: F401
