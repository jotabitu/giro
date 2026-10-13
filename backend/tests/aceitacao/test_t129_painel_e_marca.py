"""T-129 · Rotas do painel e da marca da empresa (`docs/api/painel.md`, "Rotas, perfis e o que
entra no MVP"; `docs/api/empresas.md`; a linha de `docs/api/locacoes.md`).

Roda na `empresa_a` com as pessoas, a frota e a carteira de outubro da Moto Rápida (Filial
Centro) e o relógio em 07 out 2026, 10:00, como a T-015.
"""

from datetime import date
from typing import Any

import pytest
from django.core.cache import cache
from django.db import connection

from apps.empresas.models import ConfiguracaoEmpresa
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa, UsoEmpresa
from apps.relatorios.api import views as painel_views
from apps.veiculos import selectors as veiculos_selectors
from comum import aprovacoes

from . import carteira
from .test_t014_clientes import _suporte
from .test_t015_locacoes import LISTA, cenario  # noqa: F401 - fixture

CONTADORES = "/api/painel/contadores/"
INICIO = "/api/painel/inicio/"


@pytest.fixture
def com_carteira(cenario, relogio) -> dict[str, Locacao]:  # noqa: F811
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)


# --- Linha da lista de locações (ficha do cliente) ---


def _linha(corpo: dict[str, Any], codigo: str) -> dict[str, Any]:
    return next(item for item in corpo["resultados"] if item["codigo"] == codigo)


def test_fin_13_linha_da_locacao_com_pago_sem_caucao_e_tipo_do_veiculo(cenario, com_carteira):  # noqa: F811
    """LOC-2836: duas parcelas de R$ 329,00 pagas = 65800; a caução de R$ 300,00 fica de fora."""
    juliana = com_carteira["LOC-2836"]
    api = cenario.moto.api("Rodrigo")
    linha = _linha(api.get(LISTA, {"cliente": juliana.cliente_id}).json(), "LOC-2836")
    assert linha["pagamento"]["pago_centavos"] == 65800
    assert linha["veiculo"]["tipo"] == "moto"
    # O detalhe soma a caução no total pago (LOC-06); a linha não.
    detalhe = api.get(f"{LISTA}{juliana.pk}/").json()
    assert detalhe["total_pago_centavos"] == 95800
    assert detalhe["pagamento"]["pago_centavos"] == 65800


# --- Painel: um teste por variante com o seed em 07 out ---


def _pedir(cenario, quem: str, numero: int, valor: int) -> int:  # noqa: F811
    return int(
        aprovacoes.pedir(
            tipo="APR-03",
            origem_tipo="despesa",
            origem_id=numero,
            origem_codigo=None,
            filial_id=cenario.frota.centro.pk,
            solicitante=cenario.pessoas[quem],
            titulo=f"Despesa pedida por {quem}",
            detalhe="Conserto do portão",
            valor_centavos=valor,
        ).id
    )


@pytest.fixture
def pedidos(cenario) -> dict[str, int]:  # noqa: F811
    """A despesa de R$ 1.200,00 pedida por João e uma pedida pelo próprio Rodrigo (APR-09)."""
    return {
        "João": _pedir(cenario, "João", 1, 120000),
        "Rodrigo": _pedir(cenario, "Rodrigo", 2, 60000),
    }


def _implantacao_concluida(cenario) -> None:  # noqa: F811
    """IMP-01: com a 1ª locação, o administrador passa da implantação ao painel geral. A carteira
    já confirma locações (T-131); aqui o passo fica explícito para o teste não depender dela."""
    UsoEmpresa.objects.filter(empresa=cenario.moto.empresa).update(
        passos_implantacao={"conta": "2026-09-20", "filial": "2026-09-21", "primeira_locacao": "x"}
    )


def _implantacao_aberta(cenario) -> None:  # noqa: F811
    """A carteira confirma locações e conclui a implantação (IMP-01): volta para antes dela."""
    UsoEmpresa.objects.filter(empresa=cenario.moto.empresa).update(
        passos_implantacao={"conta": "2026-09-20", "filial": "2026-09-21"}
    )


def _kpis(corpo: dict[str, Any]) -> dict[str, Any]:
    return {kpi["chave"]: kpi for kpi in corpo["kpis"]}


def test_usr_08_geral_administrador(cenario, com_carteira):  # noqa: F811
    _implantacao_concluida(cenario)
    corpo = cenario.moto.api("Mariana").get(INICIO).json()
    assert corpo["variante"] == "geral"
    assert corpo["saudacao"] == "Bom dia, Mariana"
    # LOC-2790 (devolução atrasada) e LOC-2841 (parcela atrasada): a aba `precisam_acao`.
    assert corpo["atencao"] == {"quantidade": 2, "texto": "2 contratos pedem atenção"}
    kpis = _kpis(corpo)
    frota = veiculos_selectors.contagens(veiculos_selectors.da_frota([cenario.frota.centro.pk]))
    assert kpis["frota_ativa"]["valor"] == {"tipo": "numero", "valor": 86}
    assert kpis["frota_ativa"]["contexto"] == f"{frota['motos']} motos · {frota['carros']} carros"
    assert kpis["alugados_agora"]["valor"] == {"tipo": "numero", "valor": 42}
    assert kpis["em_atraso"]["valor"] == {"tipo": "numero", "valor": 2}
    assert kpis["em_atraso"]["contexto"] == "R$ 1.646,40 a receber"
    assert kpis["receita_locacao"]["valor"]["tipo"] == "centavos"
    assert kpis["receita_locacao"]["contexto"] == "últimos 7 dias"
    assert corpo["frota"]["meta_ocupacao_pct"] == "80.00"
    segmentos = {s["status"]: s["quantidade"] for s in corpo["frota"]["segmentos"]}
    assert list(segmentos) == ["disponivel", "alugado", "reservado", "em_manutencao", "a_venda"]
    assert segmentos["alugado"] == 42
    linhas = corpo["devolucoes_semana"]["linhas"]
    assert linhas[0]["codigo"] == "LOC-2790"
    assert linhas[0]["situacao"] == {"rotulo": "Devolução atrasada 25 dias", "tom": "perigo"}
    assert corpo["pendencias"]["titulo"] == "2 contratos precisam de ação hoje"
    assert corpo["pendencias"]["itens"][0] == {
        "texto": "1 devolução está atrasada",
        "gravidade": "critica",
        "destino": {"chave": "locacoes", "filtro": "aba=precisam_acao"},
    }
    assert corpo["caixa_hoje"] is None  # caixa da T-017

    # "Todas as filiais" (USR-07) com uma filial só: os mesmos números.
    todas = cenario.moto.api("Mariana", HTTP_X_FILIAL="todas").get(INICIO).json()
    assert _kpis(todas)["em_atraso"] == kpis["em_atraso"]


def test_vei_06_ocupacao_e_meta_no_painel(cenario, com_carteira):  # noqa: F811
    _implantacao_concluida(cenario)
    ConfiguracaoEmpresa.objects.update_or_create(unica=1, defaults={"meta_ocupacao_pct": "75.00"})
    corpo = cenario.moto.api("Mariana").get(INICIO, {"periodo": "30d"}).json()
    esperado = veiculos_selectors.ocupacao_da_frota(cenario.frota.centro.pk, 30)
    assert corpo["frota"]["ocupacao_pct"] == esperado
    assert corpo["frota"]["meta_ocupacao_pct"] == "75.00"
    assert corpo["frota"]["nota"].endswith("meta de 75%")
    assert _kpis(corpo)["receita_locacao"]["contexto"] == "últimos 30 dias"


def test_usr_08_imp_01_implantacao(cenario, com_carteira):  # noqa: F811
    _implantacao_aberta(cenario)
    Empresa._base_manager.filter(pk=cenario.moto.empresa.pk).update(
        status="em_teste", teste_fim=date(2026, 10, 21)
    )
    connection.set_tenant(Empresa.objects.get(pk=cenario.moto.empresa.pk))
    corpo = cenario.moto.api("Mariana").get(INICIO).json()
    assert corpo["variante"] == "implantacao"
    assert corpo["teste"] == {
        "fim": "2026-10-21",
        "dias_restantes": 14,
        "texto": "Seu teste grátis termina em 14 dias (21 out).",
    }
    passos = {item["chave"]: item for item in corpo["primeiros_passos"]["itens"]}
    assert passos["primeira_locacao"]["concluido"] is False
    assert passos["primeira_locacao"]["acao"] == {"rotulo": "Começar", "destino": "nova_locacao"}
    assert corpo["indicadores"]["frota_cadastrada"] == 86
    assert corpo["indicadores"]["alugados_agora"] == 42


def test_usr_08_gerente(cenario, com_carteira, pedidos):  # noqa: F811
    corpo = cenario.moto.api("Rodrigo").get(INICIO).json()
    assert corpo["variante"] == "gerente"
    kpis = _kpis(corpo)
    assert kpis["devolucoes_atrasadas"]["valor"] == {"tipo": "numero", "valor": 1}
    assert kpis["devolucoes_atrasadas"]["contexto"] == "1 há mais de 2 dias"
    assert kpis["em_manutencao"]["valor"] is None  # app manutencao (fase 2)
    assert kpis["ocupacao"]["contexto"] == "meta de 80%"
    assert corpo["frota_filial"]["total"] == 86
    assert sum(s["quantidade"] for s in corpo["frota_filial"]["segmentos"]) == 86
    equipe = {p["nome"]: p for p in corpo["equipe_hoje"]}
    assert "Rodrigo" not in equipe
    assert equipe["João"]["resumo"] == "0 de 1 vistoria feita"  # a devolução da LOC-2790
    assert equipe["Bruna"]["online"] is False


def test_apr_09_gerente_nao_ve_o_proprio_pedido_no_painel(cenario, com_carteira, pedidos):  # noqa: F811
    """A despesa de R$ 1.200,00 pedida por João aparece para Rodrigo; a dele, não."""
    api = cenario.moto.api("Rodrigo")
    do_inicio = api.get(INICIO).json()["aprovacoes"]
    assert do_inicio["total"] == 1
    assert [p["id"] for p in do_inicio["itens"]] == [pedidos["João"]]
    assert do_inicio["itens"][0]["acoes"] == ["recusar", "aprovar"]
    assert api.get(CONTADORES).json()["contadores"]["aprovacoes"] == 1
    # A administradora decide os dois.
    assert cenario.moto.api("Mariana").get(CONTADORES).json()["contadores"]["aprovacoes"] == 2


def test_usr_08_vendedor_so_os_proprios_numeros(cenario, com_carteira):  # noqa: F811
    corpo = cenario.moto.api("Bruna").get(INICIO).json()
    assert corpo["variante"] == "vendedor"
    kpis = _kpis(corpo)
    assert kpis["minhas_locacoes_ativas"]["valor"]["valor"] == 42  # a carteira é toda dela
    assert kpis["parcelas_atrasadas"]["valor"]["valor"] == 2
    assert kpis["parcelas_atrasadas"]["contexto"] == "R$ 1.646,40 de 2 clientes"
    parcelas = [(p["locacao"], p["valor_centavos"], p["dias"]) for p in corpo["parcelas_atrasadas"]]
    assert parcelas == [("LOC-2790", 134700, 25), ("LOC-2841", 29940, 7)]
    assert {x["codigo"] for x in corpo["precisam_acao"]} == {"LOC-2790", "LOC-2841"}
    assert (corpo["meta"], corpo["funil"], corpo["comissao_prevista"]) == (None, None, None)

    # As locações passam a ser de outro vendedor: Bruna fica sem números.
    Locacao.objects.update(vendedor=cenario.pessoas["Rodrigo"])
    cache.clear()  # o início fica 5 minutos no cache
    outro = cenario.moto.api("Bruna").get(INICIO).json()
    assert _kpis(outro)["minhas_locacoes_ativas"]["valor"]["valor"] == 0
    assert outro["parcelas_atrasadas"] == []


def test_usr_08_vistoriador_com_a_agenda_do_dia(cenario, com_carteira):  # noqa: F811
    api = cenario.moto.api("João")
    corpo = api.get(INICIO).json()
    assert corpo["variante"] == "vistoriador"
    agenda = api.get("/api/vistorias/agenda/", {"dia": "hoje"}).json()
    assert corpo["agenda"] == agenda
    assert corpo["avarias_abertas"] == agenda["avarias_abertas"]
    assert "_centavos" not in str(corpo)


def test_usr_08_fin_15_financeiro(cenario, com_carteira):  # noqa: F811
    """Seed em 07 out: entra hoje R$ 2.625,80 em 6 parcelas; em atraso R$ 1.646,40 em 2
    clientes; sem caixa aberto e sem despesa (T-017: a parte do caixa e das despesas está em
    `test_t017_financeiro.py`)."""
    corpo = cenario.moto.api("Lúcia").get(INICIO).json()
    assert corpo["variante"] == "financeiro"
    kpis = _kpis(corpo)
    assert kpis["entra_hoje"]["valor"] == {"tipo": "centavos", "valor": 262580}
    assert kpis["entra_hoje"]["contexto"] == "6 parcelas"
    assert kpis["em_atraso"]["valor"] == {"tipo": "centavos", "valor": 164640}
    assert kpis["em_atraso"]["contexto"] == "2 clientes"
    assert kpis["sai_hoje"]["valor"] == {"tipo": "centavos", "valor": 0}
    assert kpis["saldo_em_contas"]["valor"] is None
    assert corpo["caixas_do_dia"] == []
    assert corpo["para_hoje"] == []
    assert (corpo["fluxo_previsto"], corpo["conciliacao"]) == (None, None)


# --- Contadores (USR-05): só os itens que a pessoa vê ---


def test_usr_05_contadores_seguem_o_menu(cenario, com_carteira):  # noqa: F811
    # João tem um menu só (USR-05, T-136): sem Locações e sem Veículos, sem esses contadores.
    assert cenario.moto.api("João").get(CONTADORES).json()["contadores"] == {
        "agenda": 1,
        "avarias": 0,
    }
    # Com `financeiro` em GIRO_MODULOS_ATIVOS (T-017), o financeiro vê os itens dele.
    assert cenario.moto.api("Lúcia").get(CONTADORES).json()["contadores"] == {
        "contas_a_pagar": 0,
        "receber": 2,
    }


def test_fin_15_contador_receber_conta_parcelas_atrasadas(cenario, com_carteira, settings):  # noqa: F811
    settings.GIRO_MODULOS_ATIVOS = [*settings.GIRO_MODULOS_ATIVOS, "financeiro"]
    contadores = cenario.moto.api("Lúcia").get(CONTADORES).json()["contadores"]
    assert contadores["receber"] == 2  # Carlos e Rafael
    assert contadores["contas_a_pagar"] == 0  # nenhuma despesa a pagar vencendo (FIN-05)
    assert "conciliacao" not in contadores  # fase 2: fora do menu


# --- Escopo, erros, suporte e cache ---


def test_usr_07_painel_respeita_o_escopo_de_filial(cenario, com_carteira):  # noqa: F811
    assert cenario.moto.api("Bruna", HTTP_X_FILIAL="todas").get(INICIO).status_code == 403
    assert cenario.moto.api("Rodrigo", HTTP_X_FILIAL="99999").get(CONTADORES).status_code == 403
    resposta = cenario.moto.api("Rodrigo").get(INICIO, {"periodo": "ano"})
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "validacao"


def test_usr_08_variante_nao_vem_da_query(cenario, com_carteira):  # noqa: F811
    corpo = cenario.moto.api("Bruna").get(INICIO, {"variante": "geral"}).json()
    assert corpo["variante"] == "vendedor"


def test_usr_08_suporte_so_ve_com_a_variante_do_administrador(cenario, com_carteira, relogio_jwt):  # noqa: F811
    _implantacao_concluida(cenario)
    api = _suporte(cenario.moto, "ver")
    corpo = api.get(INICIO).json()
    assert corpo["variante"] == "geral"
    assert _kpis(corpo)["em_atraso"]["valor"]["valor"] == 2
    assert api.get(CONTADORES).status_code == 200


def test_usr_08_cache_por_pessoa_rota_e_variante(cenario, com_carteira, pedidos, monkeypatch):  # noqa: F811
    prazos: dict[str, int] = {}
    guardar = painel_views.cache.set

    def espiar(chave: str, valor: Any, prazo: int) -> None:
        prazos[chave] = prazo
        guardar(chave, valor, prazo)

    monkeypatch.setattr(painel_views.cache, "set", espiar)
    api = cenario.moto.api("Mariana")
    primeiro = api.get(CONTADORES).json()
    assert primeiro["contadores"]["aprovacoes"] == 2
    _pedir(cenario, "João", 3, 70000)
    assert api.get(CONTADORES).json() == primeiro  # do cache, dentro dos 60 segundos
    api.get(INICIO, {"periodo": "hoje"})
    mariana = cenario.pessoas["Mariana"].pk
    centro = cenario.frota.centro.pk
    # A variante entra na chave: a 1ª locação (IMP-01, T-131) não espera o cache vencer.
    assert prazos == {
        f"painel:empresa_a:{mariana}:{centro}:contadores:geral": 60,
        f"painel:empresa_a:{mariana}:{centro}:inicio:geral:hoje": 300,
    }
    # A chave é da pessoa: Rodrigo calcula o dele (sem o pedido que ele fez, APR-09).
    assert cenario.moto.api("Rodrigo").get(CONTADORES).json()["contadores"]["aprovacoes"] == 2


def test_usr_07_isolamento_a_empresa_b_nao_ve_a_frota_da_a(cenario, com_carteira, empresa_b):  # noqa: F811
    assert connection.schema_name == "empresa_b"
    centro = cenario.frota.centro.pk
    assert veiculos_selectors.contagens(veiculos_selectors.da_frota([centro]))["todos"] == 0
