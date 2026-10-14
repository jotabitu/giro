"""T-178 · Despesas: busca, exportar, despesa por veículo e nota obrigatória
(docs/qa/criterios/despesas.md, CA-DES-01 a 15; docs/api/financeiro.md e auditoria.md).

Cenário da T-017: Moto Rápida em 07 out 2026, Filial Centro, com o caixa de 07 out (o óleo pago no
caixa) e as outras 5 despesas de outubro lançadas pela API. Os 86 veículos do cenário ganham o
histórico de status do cadastro (como o serviço grava), base da frota ativa (FIN-16).
"""

import csv
import io
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.db import connection

from apps.auditoria.models import EventoAuditoria, Exportacao
from apps.financeiro.models import Despesa, MovimentoCaixa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import FORA_DA_FROTA, HistoricoStatusVeiculo, Veiculo
from apps.veiculos.selectors import frota_ativa_em
from comum import arquivos
from comum.auditoria import Ator, TipoAtor, usar_ator

from .test_t013_veiculos import _caucaia
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t017_financeiro import (  # noqa: F401 - fixtures
    _decidir,
    _despesa,
    _pagar,
    caixa_do_seed,
    lucas,
    recebimentos,
)

DESPESAS = "/api/financeiro/despesas/"
EXPORTACOES = "/api/exportacoes/"
FUSO = ZoneInfo("America/Sao_Paulo")
CADASTRO = datetime(2025, 1, 10, 9, 0, tzinfo=FUSO)


@pytest.fixture
def frota_com_historico(cenario) -> int:  # noqa: F811
    """O histórico do cadastro de cada veículo do cenário (o serviço de cadastro grava um)."""
    veiculos = list(Veiculo.objects.all())
    HistoricoStatusVeiculo.objects.bulk_create(
        HistoricoStatusVeiculo(veiculo=v, de="", para=v.status, em=CADASTRO) for v in veiculos
    )
    assert not [v for v in veiculos if v.status in FORA_DA_FROTA]
    return len(veiculos)


@pytest.fixture
def outubro(cenario, caixa_do_seed, frota_com_historico) -> dict[str, int]:  # noqa: F811
    """As 6 despesas de outubro da Filial Centro (CA-017-19): o óleo já veio do caixa."""
    pmz = cenario.frota.veiculos["PMZ3E17"].pk
    pneus = _despesa(
        cenario, "João", descricao="Pneus (2 unidades)", valor_centavos=120000, veiculo_id=pmz
    ).json()
    fixas = {"categoria": "fixas"}
    _despesa(
        cenario,
        "Lúcia",
        descricao="Conta de luz",
        valor_centavos=41230,
        data="2026-10-06",
        vencimento="2026-10-10",
        **fixas,
    )
    aluguel = _despesa(
        cenario,
        "Lúcia",
        descricao="Aluguel do ponto",
        valor_centavos=350000,
        data="2026-10-05",
        vencimento="2026-10-05",
        **fixas,
    ).json()
    assert _decidir(cenario, aluguel["id"]).status_code == 200
    assert _pagar(cenario, aluguel["id"], "boleto").status_code == 200
    _despesa(
        cenario,
        "Lúcia",
        descricao="IPVA ROE-2A88",
        valor_centavos=18640,
        data="2026-10-03",
        vencimento="2026-10-31",
        categoria="impostos",
    )
    rastreadores = _despesa(
        cenario,
        "Lúcia",
        descricao="Rastreadores (86)",
        valor_centavos=172000,
        data="2026-10-02",
        vencimento="2026-10-02",
        categoria="rastreamento",
    ).json()
    assert _decidir(cenario, rastreadores["id"]).status_code == 200
    assert _pagar(cenario, rastreadores["id"], "cartao").status_code == 200
    assert Despesa.objects.count() == 6
    return {"pneus": pneus["id"], "centro": cenario.frota.centro.pk}


def _lista(cenario, quem: str = "Lúcia", **params: str) -> Any:  # noqa: F811
    return cenario.moto.api(quem).get(DESPESAS, {"mes": "2026-10", **params})


# --- Busca (FIN-16, CA-DES-04, CA-DES-05) ---


def test_fin_16_busca_descricao_e_placa(cenario, outubro):  # noqa: F811
    sem_busca = _lista(cenario).json()
    pneu = _lista(cenario, busca="pneu").json()
    assert [d["descricao"] for d in pneu["resultados"]] == ["Pneus (2 unidades)"]
    assert pneu["contagens"] == {"aguardando_aprovacao": 1, "a_pagar": 0, "paga": 0, "recusada": 0}
    assert pneu["indicadores"] == sem_busca["indicadores"]
    assert pneu["indicadores"]["gasto_mes_centavos"] == 706670
    assert pneu["indicadores"]["aguardando_aprovacao_quantidade"] == 1

    def achados(termo: str) -> list[str]:
        return [d["descricao"] for d in _lista(cenario, busca=termo).json()["resultados"]]

    assert achados("pmz-3e17") == ["Pneus (2 unidades)"]
    assert achados("PMZ3E17") == ["Pneus (2 unidades)"]
    assert achados("ROE") == ["IPVA ROE-2A88"]
    assert achados("oleo") == ["Óleo 1 litro"]
    assert achados("ÓLEO") == ["Óleo 1 litro"]
    # Vazio ou só espaços é ignorado; o filtro de status não muda as contagens.
    assert len(achados("   ")) == 6
    pagas = _lista(cenario, busca="pneu", status="paga").json()
    assert pagas["resultados"] == []
    assert pagas["contagens"]["aguardando_aprovacao"] == 1
    longa = _lista(cenario, busca="x" * 61)
    assert longa.status_code == 400
    assert "busca" in longa.json()["campos"]
    assert _lista(cenario, busca="x" * 60).status_code == 200


# --- Despesa por veículo (FIN-16, CA-DES-01 a CA-DES-03) ---


def test_fin_16_despesa_por_veiculo(cenario, outubro):  # noqa: F811
    # CA-DES-01: 706670 ÷ 86 = 8217,09 → 8217.
    assert _lista(cenario).json()["indicadores"]["despesa_por_veiculo_centavos"] == 8217
    # CA-DES-02: pneus recusados e um veículo baixado → 586670 ÷ 85 = 6902.
    assert _decidir(cenario, outubro["pneus"], "recusar").status_code == 200
    baixado = Veiculo.objects.filter(status="disponivel").exclude(placa="PMZ3E17").first()
    assert baixado is not None
    mariana = cenario.pessoas["Mariana"]
    with usar_ator(Ator(tipo=TipoAtor.USUARIO, id=mariana.pk, nome=mariana.nome)):
        veiculos_services.baixar(baixado, "perda_total", "")
    indicadores = _lista(cenario).json()["indicadores"]
    assert indicadores["gasto_mes_centavos"] == 586670
    assert indicadores["despesa_por_veiculo_centavos"] == 6902
    # Mês passado: a frota do último dia (o baixado hoje ainda contava em 30 set).
    assert frota_ativa_em(date(2026, 9, 30), [outubro["centro"]]) == 86
    assert frota_ativa_em(date(2026, 10, 7), [outubro["centro"]]) == 85
    setembro = _lista(cenario, mes="2026-09").json()["indicadores"]
    assert (setembro["gasto_mes_centavos"], setembro["despesa_por_veiculo_centavos"]) == (0, 0)


def test_fin_16_despesa_por_veiculo_sem_veiculos(cenario, frota_com_historico):  # noqa: F811
    # CA-DES-03: filial sem veículo na frota, com uma despesa no mês → `null`.
    caucaia = _caucaia(cenario.moto)
    cabecalho = {"HTTP_X_FILIAL": str(caucaia.pk)}
    lancada = _despesa(cenario, "Mariana", cabecalhos=cabecalho, categoria="fixas")
    assert lancada.status_code == 201, lancada.json()
    corpo = cenario.moto.api("Mariana", **cabecalho).get(DESPESAS, {"mes": "2026-10"}).json()
    assert corpo["indicadores"]["gasto_mes_centavos"] == 4800
    assert corpo["indicadores"]["despesa_por_veiculo_centavos"] is None
    # Veículo cadastrado depois do dia não conta (o histórico manda, não o cadastro atual).
    assert frota_ativa_em(date(2025, 1, 9), [cenario.frota.centro.pk]) == 0
    assert frota_ativa_em(date(2025, 1, 10), [cenario.frota.centro.pk]) == 86


# --- Exportação (FIN-16, AUD-07, CA-DES-06 a CA-DES-09) ---


def _exportar(cenario, quem: str, capturar, **corpo: Any) -> Any:  # noqa: F811
    dados = {"itens": ["despesas"], "formato": "csv", "mes": "2026-10", **corpo}
    with capturar(execute=True):
        resposta = cenario.moto.api(quem).post(EXPORTACOES, dados, format="json")
    connection.set_tenant(cenario.moto.empresa)
    return resposta


def _linhas_do_csv(exportacao: Exportacao) -> list[list[str]]:
    conteudo = arquivos.guardados[exportacao.arquivo][0].decode("utf-8-sig")
    return list(csv.reader(io.StringIO(conteudo), delimiter=";"))


def test_fin_16_exportar_despesas_csv(
    cenario,  # noqa: F811
    outubro,
    django_capture_on_commit_callbacks,
):
    pedido = _exportar(
        cenario, "Mariana", django_capture_on_commit_callbacks, filial_id=outubro["centro"]
    )
    assert pedido.status_code == 202, pedido.json()
    assert pedido.json()["status"] == "na_fila"
    feita = Exportacao.objects.get(pk=pedido.json()["id"])
    assert feita.status == "pronta"
    assert feita.arquivo.endswith("/despesas.csv")
    assert (feita.periodo_inicio, feita.periodo_fim) == (date(2026, 10, 1), date(2026, 10, 31))
    assert feita.parametros == {
        "mes": "2026-10",
        "filial_id": outubro["centro"],
        "filial_nome": "Filial Centro",
    }
    cabecalho, *linhas = _linhas_do_csv(feita)
    assert cabecalho == [
        "data",
        "descricao",
        "categoria",
        "veiculo",
        "filial",
        "valor",
        "vencimento",
        "situacao",
        "pago_em",
        "forma",
        "lancada_por",
    ]
    assert len(linhas) == 6
    total = sum(int(linha[5].replace(",", "")) for linha in linhas)
    assert total == 706670  # R$ 7.066,70
    por_descricao = {linha[1]: linha for linha in linhas}
    assert por_descricao["Pneus (2 unidades)"] == [
        "07/10/2026",
        "Pneus (2 unidades)",
        "Manutenção",
        "PMZ-3E17",
        "Filial Centro",
        "1200,00",
        "07/10/2026",
        "Aguardando aprovação",
        "",
        "",
        cenario.pessoas["João"].nome,
    ]
    assert por_descricao["Óleo 1 litro"][3] == "QXA-4B21"
    assert por_descricao["Óleo 1 litro"][7:10] == ["Paga", "07/10/2026", "Dinheiro"]
    assert por_descricao["Rastreadores (86)"][3] == ""
    assert por_descricao["Rastreadores (86)"][8:10] == ["07/10/2026", "Cartão"]
    datas = ["02/10/2026", "03/10/2026", "05/10/2026", "06/10/2026", "07/10/2026", "07/10/2026"]
    assert [linha[0] for linha in linhas] == datas  # ordem: data, depois id
    aviso = [m for m in mail.outbox if "exportação" in m.subject]
    assert aviso and aviso[-1].to == ["mariana@motorapida.com.br"]
    assert "Despesas · Filial Centro · 01/10/2026 a 31/10/2026" in aviso[-1].body
    recentes = cenario.moto.api().get(EXPORTACOES).json()["resultados"]
    assert recentes[0]["conteudo"] == "Despesas · Filial Centro · 01/10/2026 a 31/10/2026"
    assert EventoAuditoria.objects.filter(acao="exportacao.pedir", objeto_id=feita.pk).exists()

    # CA-DES-09: com os pneus recusados, continuam 6 linhas, e a dos pneus traz "Recusada".
    assert _decidir(cenario, outubro["pneus"], "recusar").status_code == 200
    todas = _exportar(cenario, "Mariana", django_capture_on_commit_callbacks, filial_id=None)
    feita = Exportacao.objects.get(pk=todas.json()["id"])
    linhas = _linhas_do_csv(feita)[1:]
    assert len(linhas) == 6
    assert {linha[1]: linha[7] for linha in linhas}["Pneus (2 unidades)"] == "Recusada"
    recentes = cenario.moto.api().get(EXPORTACOES).json()["resultados"]
    assert recentes[0]["conteudo"] == "Despesas · Todas as filiais · 01/10/2026 a 31/10/2026"


def test_fin_16_exportar_despesas_valida_o_pedido(
    cenario,  # noqa: F811
    frota_com_historico,
    django_capture_on_commit_callbacks,
):
    capturar = django_capture_on_commit_callbacks
    sem_mes = _exportar(cenario, "Mariana", capturar, mes=None)
    assert sem_mes.status_code == 400
    assert sem_mes.json()["campos"]["mes"] == ["Escolha o mês no formato 2026-10."]
    assert _exportar(cenario, "Mariana", capturar, mes="2026-13").status_code == 400
    periodo = {"de": "2026-10-01", "ate": "2026-10-31"}
    com_periodo = _exportar(cenario, "Mariana", capturar, periodo=periodo)
    assert com_periodo.json()["campos"]["periodo"] == ["Para as despesas, use o mês."]
    sem_filial = _exportar(cenario, "Mariana", capturar, filial_id=999999)
    assert sem_filial.json()["campos"]["filial_id"] == ["Filial não encontrada."]
    junto = _exportar(cenario, "Mariana", capturar, itens=["auditoria", "despesas"])
    assert junto.status_code == 422
    assert junto.json()["codigo"] == "exportacao_indisponivel"
    assert junto.json()["mensagem"] == (
        "Por enquanto, só a auditoria e as despesas podem ser exportadas, em CSV."
    )
    assert _exportar(cenario, "Mariana", capturar, formato="planilha").status_code == 422
    assert not Exportacao.objects.exists()
    # Proteção contra fórmula em toda célula de texto.
    lancada = _despesa(
        cenario, "Lúcia", descricao="=HYPERLINK(1)", data="2026-09-20", vencimento="2026-09-20"
    )
    assert lancada.status_code == 201, lancada.json()
    setembro = _exportar(cenario, "Mariana", capturar, mes="2026-09", filial_id=None)
    linhas = _linhas_do_csv(Exportacao.objects.get(pk=setembro.json()["id"]))
    assert linhas[1][1] == "'=HYPERLINK(1)"


def test_fin_16_financeiro_exporta_despesas(
    cenario,  # noqa: F811
    outubro,
    django_capture_on_commit_callbacks,
):
    capturar = django_capture_on_commit_callbacks
    auditoria = {"itens": ["auditoria"], "formato": "csv", "periodo": None}
    with capturar(execute=True):
        da_mariana = cenario.moto.api().post(EXPORTACOES, auditoria, format="json")
    connection.set_tenant(cenario.moto.empresa)
    assert da_mariana.status_code == 202
    # CA-DES-06b: a Lúcia exporta as despesas, recebe o link e baixa.
    pedido = _exportar(cenario, "Lúcia", capturar, filial_id=outubro["centro"])
    assert pedido.status_code == 202, pedido.json()
    feita = Exportacao.objects.get(pk=pedido.json()["id"])
    assert feita.status == "pronta" and len(_linhas_do_csv(feita)) == 7
    aviso = [m for m in mail.outbox if "exportação" in m.subject]
    assert aviso[-1].to == [cenario.pessoas["Lúcia"].email]
    lucia = cenario.moto.api("Lúcia")
    link = lucia.get(f"{EXPORTACOES}{feita.pk}/baixar/")
    assert link.status_code == 302
    assert EventoAuditoria.objects.filter(acao="exportacao.baixar", objeto_id=feita.pk).count() == 1
    # Ela vê só as de despesas, e continua sem a auditoria (403).
    recentes = lucia.get(EXPORTACOES).json()["resultados"]
    assert [r["id"] for r in recentes] == [feita.pk]
    assert lucia.post(EXPORTACOES, auditoria, format="json").status_code == 403
    baixar_auditoria = lucia.get(f"{EXPORTACOES}{da_mariana.json()['id']}/baixar/")
    assert baixar_auditoria.status_code == 403
    assert baixar_auditoria.json()["codigo"] == "permissao"
    assert lucia.get("/api/auditoria/eventos/").status_code == 403
    # A Mariana vê as duas.
    assert len(cenario.moto.api().get(EXPORTACOES).json()["resultados"]) == 2


def test_aud_07_despesas_administrador_e_financeiro(
    cenario,  # noqa: F811
    frota_com_historico,
    django_capture_on_commit_callbacks,
):
    # CA-DES-08: gerente, vendedora e vistoriador não exportam; a flag do `pode` acompanha.
    for nome in ("Rodrigo", "Bruna", "João"):
        recusa = _exportar(cenario, nome, django_capture_on_commit_callbacks)
        assert recusa.status_code == 403, nome
        assert recusa.json()["codigo"] == "permissao"
        assert cenario.moto.api(nome).get(EXPORTACOES).status_code == 403
    assert not Exportacao.objects.exists()
    flags = {
        nome: cenario.moto.api(nome).get("/api/auth/eu/").json()["pode"]["despesas_exportar"]
        for nome in ("Mariana", "Rodrigo", "Bruna", "João", "Lúcia")
    }
    assert flags == {
        "Mariana": True,
        "Rodrigo": False,
        "Bruna": False,
        "João": False,
        "Lúcia": True,
    }
    assert _exportar(cenario, "Mariana", django_capture_on_commit_callbacks).status_code == 202
    assert _exportar(cenario, "Lúcia", django_capture_on_commit_callbacks).status_code == 202


# --- Lançamento (FIN-05, FIN-06, FIN-07, CA-DES-11 a CA-DES-15) ---


def test_fin_06_nota_obrigatoria(cenario, relogio):  # noqa: F811
    eventos = EventoAuditoria.objects.filter(acao="despesa.lancar").count()
    for nome in ("Mariana", "Bruna", "Lúcia", "João"):
        sem_nota = _despesa(cenario, nome, nota=None)
        assert sem_nota.status_code == 400, nome
        assert sem_nota.json()["codigo"] == "validacao"
        assert sem_nota.json()["campos"]["nota"] == ["Envie a foto da nota."]
    assert not Despesa.objects.exists()
    assert EventoAuditoria.objects.filter(acao="despesa.lancar").count() == eventos
    # A recusa de perfil vem antes da validação: o vistoriador com outra categoria, sem nota.
    fixas = _despesa(cenario, "João", nota=None, categoria="fixas")
    assert (fixas.status_code, fixas.json()["codigo"]) == (403, "FIN-06")
    com_nota = _despesa(cenario, "Bruna")
    assert com_nota.status_code == 201, com_nota.json()
    assert com_nota.json()["nota"]["url"]


def test_fin_05_pago_no_caixa_sem_caixa_aberto(cenario):  # noqa: F811
    # CA-DES-12: sem caixa aberto hoje na filial → 422 FIN-07, e nada é gravado.
    sem_caixa = _despesa(cenario, pago_no_caixa=True)
    assert sem_caixa.status_code == 422, sem_caixa.json()
    assert sem_caixa.json()["codigo"] == "FIN-07"
    assert sem_caixa.json()["mensagem"] == "Abra o caixa do dia para pagar por ele"
    assert not Despesa.objects.exists() and not MovimentoCaixa.objects.exists()
    assert not EventoAuditoria.objects.filter(acao="despesa.lancar").exists()


def test_fin_05_pago_no_caixa_perfil_e_limite(cenario, caixa_do_seed):  # noqa: F811
    despesas, movimentos = Despesa.objects.count(), MovimentoCaixa.objects.count()
    # CA-DES-13: acima de R$ 500 no caixa, 422 APR-03, com o caixa aberto.
    acima = _despesa(cenario, "Mariana", valor_centavos=60000, pago_no_caixa=True)
    assert (acima.status_code, acima.json()["codigo"]) == (422, "APR-03")
    # CA-DES-14: quem não abre caixa (o vistoriador) recebe 403 FIN-05.
    vistoriador = _despesa(cenario, "João", pago_no_caixa=True)
    assert vistoriador.status_code == 403, vistoriador.json()
    assert vistoriador.json()["codigo"] == "FIN-05"
    assert vistoriador.json()["mensagem"] == "Seu perfil não paga despesa pelo caixa."
    assert (Despesa.objects.count(), MovimentoCaixa.objects.count()) == (despesas, movimentos)
    # CA-DES-11: até R$ 500 com o caixa aberto, nasce paga, com a saída em dinheiro.
    oleo = _despesa(cenario, pago_no_caixa=True)
    assert (oleo.json()["status"], oleo.json()["forma"]) == ("paga", "dinheiro")
    assert MovimentoCaixa.objects.count() == movimentos + 1
    # Sem marcar o caixa, a mesma despesa de R$ 600,00 vai para o gerente.
    sem_marcar = _despesa(cenario, "Mariana", valor_centavos=60000)
    assert sem_marcar.json()["status"] == "aguardando_aprovacao"
