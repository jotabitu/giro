"""T-017 · Contas a receber, caixa do dia, baixa (docs/qa/criterios/T-017.md, CA-017-01 a 23).

Cenário da T-015: Moto Rápida em 07 out 2026, 10:00, Filial Centro, com a carteira de outubro
quando o caso é do seed (Carlos, LOC-2841, 29940 vencida em 30 set; Rafael, LOC-2790, 134700
vencida em 12 set). A LOC-2856 de Lucas nasce pela confirmação quando o caso é dela (parcela 1 de
32900 e caução de 30000 em 07 out, parcela 2 em 14 out).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, connection, transaction

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.empresas.models import ConfiguracaoEmpresa
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import (
    Caixa,
    CobrancaExterna,
    ContaReceber,
    Despesa,
    MovimentoCaixa,
    MovimentoImutavel,
    PendenciaPagamento,
)
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import ContaPagamento, UsoEmpresa
from comum.codigos import ajustar_sequencia
from comum.erros import Conflito
from comum.models import WebhookRecebido
from integracoes.pagamentos import CABECALHO_DO_TOKEN, hash_do_token
from integracoes.pagamentos import falso as pagamentos
from integracoes.whatsapp import falso as whatsapp

from . import carteira
from .conftest import HOST_PLATAFORMA
from .conftest import cliente as cliente_http
from .test_t013_veiculos import _caucaia
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _contrato_com_juros, _jpg

CONTAS = "/api/financeiro/contas-receber/"
CAIXAS = "/api/financeiro/caixas/"
AUDITORIA = "/api/auditoria/eventos/"
WEBHOOK = "/api/webhooks/pagamentos/asaas/"
TOKEN = "token-do-webhook-da-moto-rapida"
FUSO = ZoneInfo("America/Sao_Paulo")


@pytest.fixture
def com_carteira(cenario, relogio) -> dict[str, Locacao]:  # noqa: F811
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)


@pytest.fixture
def lucas(cenario) -> Locacao:  # noqa: F811
    """LOC-2856 confirmada: parcela 1 (32900) e caução (30000) em 07 out, parcela 2 em 14 out.
    Com a carteira, que já tem uma LOC-2856, ganha o código seguinte ao último."""
    if Locacao.objects.filter(codigo="LOC-2856").exists():
        ajustar_sequencia("LOC", 2900)
    criada = cenario.confirmada(periodos=2)
    return Locacao.objects.get(pk=criada["id"])


@pytest.fixture
def recebimentos(cenario) -> ContaPagamento:  # noqa: F811
    """A subconta aprovada no parceiro (falso), com o hash do token do webhook."""
    pagamentos.limpar()
    return ContaPagamento.objects.create(
        empresa=cenario.moto.empresa,
        conta_externa_id="acc_moto_rapida",
        webhook_token_hash=hash_do_token(TOKEN),
        status="aprovada",
    )


def _conta(origem: Locacao, tipo: str = "parcela", numero: int | None = 1) -> ContaReceber:
    filtro: dict[str, Any] = {"origem_tipo": "locacao", "origem_id": origem.pk, "tipo": tipo}
    if tipo == "parcela":
        filtro["numero_parcela"] = numero
    conta: ContaReceber = ContaReceber.objects.get(**filtro)
    return conta


def _carlos(com_carteira: dict[str, Locacao]) -> ContaReceber:
    return ContaReceber.objects.get(
        origem_tipo="locacao", origem_id=com_carteira["LOC-2841"].pk, vencimento=date(2026, 9, 30)
    )


def _rafael(com_carteira: dict[str, Locacao]) -> ContaReceber:
    return ContaReceber.objects.get(origem_tipo="locacao", origem_id=com_carteira["LOC-2790"].pk)


def _abrir(cenario, quem: str = "Bruna", troco: int = 20000, **cabecalhos: str):  # noqa: F811
    return cenario.moto.api(quem, **cabecalhos).post(
        CAIXAS, {"troco_centavos": troco}, format="json"
    )


def _receber(cenario, conta: ContaReceber, valor: int, forma: str = "dinheiro", quem="Bruna"):  # noqa: F811
    return cenario.moto.api(quem).post(
        f"{CONTAS}{conta.pk}/receber/", {"forma": forma, "valor_centavos": valor}, format="json"
    )


def _webhook(capturar: Any, corpo: dict[str, Any], token: str = TOKEN) -> int:
    """No host da plataforma (schema public), com a tarefa AUT-05 rodando no fim da transação.
    A tarefa termina no public (S-11); depois o teste volta ao schema da empresa."""
    empresa = connection.tenant
    try:
        with capturar(execute=True):
            resposta = cliente_http(HOST_PLATAFORMA).post(
                WEBHOOK, corpo, format="json", headers={CABECALHO_DO_TOKEN: token}
            )
        return int(resposta.status_code)
    finally:
        connection.set_tenant(empresa)


# --- Contas a receber (FIN-01, FIN-02) ---


def test_fin_01_ca_017_01_estados_pela_data(cenario, com_carteira):  # noqa: F811
    api = cenario.moto.api("Lúcia")
    atrasadas = api.get(CONTAS, {"situacao": "atrasadas"}).json()["resultados"]
    por_cliente = {c["cliente"]["nome"]: c for c in atrasadas}
    assert set(por_cliente) == {"Carlos Menezes", "Rafael Sousa"}
    carlos, rafael = por_cliente["Carlos Menezes"], por_cliente["Rafael Sousa"]
    assert (carlos["status"], carlos["dias_atraso"], carlos["valor_centavos"]) == (
        "atrasada",
        7,
        29940,
    )
    assert (carlos["numero"], carlos["total_parcelas"]) == (2, 5)
    assert carlos["origem"]["codigo"] == "LOC-2841"
    assert carlos["veiculo_placa"] == "QXA4B21"
    assert (rafael["status"], rafael["dias_atraso"]) == ("atrasada", 25)

    hoje = api.get(CONTAS, {"situacao": "vencem_hoje"}).json()["resultados"]
    assert hoje and {c["status"] for c in hoje} == {"vence_hoje"}
    assert {c["faixa_atraso"] for c in hoje} == {None}
    a_vencer = api.get(CONTAS, {"situacao": "a_vencer"}).json()["resultados"]
    assert a_vencer and {c["status"] for c in a_vencer} == {"aberta"}
    # O banco guarda só `aberta`: nada reescreve status à meia-noite.
    assert set(ContaReceber.objects.values_list("status", flat=True)) <= {"aberta", "paga"}


def test_fin_02_ca_017_02_faixas_de_atraso(cenario, com_carteira):  # noqa: F811
    faixa = financeiro_selectors.faixa_de_atraso
    assert [faixa(d) for d in (0, 1, 7, 8, 30, 31)] == [
        None,
        "1_7",
        "1_7",
        "8_30",
        "8_30",
        "mais_30",
    ]
    api = cenario.moto.api("Lúcia")
    um_a_sete = api.get(CONTAS, {"faixa": "1_7"}).json()["resultados"]
    assert [c["cliente"]["nome"] for c in um_a_sete] == ["Carlos Menezes"]
    oito_a_trinta = api.get(CONTAS, {"faixa": "8_30"}).json()["resultados"]
    assert [c["cliente"]["nome"] for c in oito_a_trinta] == ["Rafael Sousa"]
    corpo = api.get(CONTAS).json()
    assert corpo["indicadores"]["faixas"] == {"1_7": 29940, "8_30": 134700, "mais_30": 0}


def test_fin_01_ca_017_03_em_aberto_dos_clientes(cenario, com_carteira):  # noqa: F811
    api = cenario.moto.api("Lúcia")
    indicadores = api.get(CONTAS).json()["indicadores"]
    assert indicadores["em_atraso_centavos"] == 164640
    assert indicadores["em_atraso_clientes"] == 2
    assert indicadores["em_atraso_parcelas"] == 2

    clientes = cenario.moto.api("Rodrigo").get("/api/clientes/").json()
    assert clientes["indicadores"]["em_aberto_total_centavos"] == 164640
    assert clientes["contagens"]["em_aberto"] == 2
    carlos = Cliente.objects.get(nome="Carlos Menezes")
    ficha = cenario.moto.api("Rodrigo").get(f"/api/clientes/{carlos.pk}/").json()
    # A conta que vence hoje (parcela 3) e a caução não entram no em aberto.
    assert ficha["financeiro"]["em_aberto_centavos"] == 29940
    assert ficha["financeiro"]["conta_mais_antiga_id"] == _carlos(com_carteira).pk
    assert ficha["acao_principal"]["codigo"] == "cobrar"


def test_loc_05_loc_04_ca_017_04_parcelas_antecipadas(cenario, com_carteira, lucas):  # noqa: F811
    parcela, caucao = _conta(lucas), _conta(lucas, "caucao")
    assert (parcela.vencimento, parcela.valor_centavos) == (date(2026, 10, 7), 32900)
    assert (caucao.vencimento, caucao.valor_centavos) == (date(2026, 10, 7), 30000)
    assert parcela.valor_centavos + caucao.valor_centavos == 62900
    assert _conta(lucas, numero=2).vencimento == date(2026, 10, 14)
    # A caução não é receita: só aparece na lista da própria locação.
    da_locacao = cenario.moto.api("Lúcia").get(
        CONTAS, {"origem_tipo": "locacao", "origem_id": lucas.pk}
    )
    assert "caucao" in {c["tipo"] for c in da_locacao.json()["resultados"]}
    geral = cenario.moto.api("Lúcia").get(CONTAS, {"situacao": "vencem_hoje"}).json()
    assert "caucao" not in {c["tipo"] for c in geral["resultados"]}

    juliana = com_carteira["LOC-2836"]
    detalhe = cenario.moto.api("Rodrigo").get(f"/api/locacoes/{juliana.pk}/").json()
    assert detalhe["total_pago_centavos"] == 95800  # LOC-06
    ficha = cenario.moto.api("Rodrigo").get(f"/api/clientes/{juliana.cliente_id}/").json()
    assert ficha["financeiro"]["total_pago_centavos"] == 65800  # sem a caução


# --- Baixa no caixa (FIN-01, FIN-03, FIN-04) ---


def test_fin_04_ca_017_05_baixa_no_caixa_em_dinheiro(cenario, lucas):  # noqa: F811
    assert _abrir(cenario).status_code == 201
    parcela = _conta(lucas)
    resposta = _receber(cenario, parcela, 32900)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["status"], corpo["forma"]) == ("paga", "dinheiro")
    assert corpo["pago_em"] is not None
    parcela.refresh_from_db()
    movimento = parcela.movimento_caixa
    assert movimento is not None
    assert (movimento.tipo, movimento.forma, movimento.valor_centavos) == (
        "entrada",
        "dinheiro",
        32900,
    )
    assert EventoAuditoria.objects.filter(
        acao="conta_receber.pagar", objeto_id=parcela.pk, categoria="financeiro"
    ).exists()
    # Lúcia (financeiro) e Rodrigo também recebem; João (vistoriador) não.
    caucao = _conta(lucas, "caucao")
    assert _receber(cenario, caucao, 30000, "cartao_debito", quem="João").status_code == 403
    assert _receber(cenario, caucao, 30000, "cartao_debito", quem="Lúcia").status_code == 200
    segunda = _conta(lucas, numero=2)
    assert _receber(cenario, segunda, 32900, "cartao_credito", quem="Rodrigo").status_code == 200


def test_fin_01_ca_017_06_pagamento_parcial_nao_existe(cenario, lucas):  # noqa: F811
    _abrir(cenario)
    parcela = _conta(lucas)
    resposta = _receber(cenario, parcela, 20000)
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "FIN-01"
    assert resposta.json()["mensagem"] == (
        "Não existe pagamento parcial. Receba o valor inteiro ou renegocie."
    )
    parcela.refresh_from_db()
    assert parcela.status == "aberta"
    assert not MovimentoCaixa.objects.exists()


def test_fin_04_aut_05_ca_017_07_webhook_do_pix_baixa_sozinho(
    cenario,  # noqa: F811
    com_carteira,
    recebimentos,
    django_capture_on_commit_callbacks,
):
    carlos = _carlos(com_carteira)
    gerada = cenario.moto.api("Lúcia").post(
        f"{CONTAS}{carlos.pk}/cobranca/", {"tipo": "pix"}, format="json"
    )
    assert gerada.status_code == 201, gerada.json()
    assert gerada.json()["valor_centavos"] == 29940  # sem cláusula de juros no contrato
    assert gerada.json()["pix_copia_e_cola"]
    cobranca = CobrancaExterna.objects.get(pk=gerada.json()["id"])

    # Token errado: 401, e nada é gravado.
    corpo = pagamentos.simular_pagamento(cobranca.externo_id)
    assert _webhook(django_capture_on_commit_callbacks, corpo, token="outro") == 401
    assert not WebhookRecebido.objects.exists()

    # Sem caixa aberto e sem ninguém: a conta é baixada pelo Pix.
    for _ in range(2):  # o mesmo evento duas vezes: baixa uma vez só
        assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    carlos.refresh_from_db()
    assert (carlos.status, carlos.forma) == ("paga", "pix")
    assert carlos.movimento_caixa is None
    assert WebhookRecebido.objects.count() == 1
    pagou = EventoAuditoria.objects.filter(acao="conta_receber.pagar", objeto_id=carlos.pk)
    assert pagou.count() == 1
    assert (pagou.get().ator_tipo, pagou.get().ator_nome, pagou.get().regra) == (
        "sistema",
        "Sistema",
        "AUT-05",
    )
    assert any("recebemos R$ 299,40" in m.texto for m in whatsapp.caixa_de_saida)


def test_fin_04_ca_017_07_valor_diferente_vira_pendencia(
    cenario,  # noqa: F811
    com_carteira,
    recebimentos,
    django_capture_on_commit_callbacks,
):
    rafael = _rafael(com_carteira)
    gerada = (
        cenario.moto.api("Lúcia")
        .post(f"{CONTAS}{rafael.pk}/cobranca/", {"tipo": "pix"}, format="json")
        .json()
    )
    cobranca = CobrancaExterna.objects.get(pk=gerada["id"])
    # O corpo diz o valor certo, mas o parceiro diz que pagaram menos: o corpo não vale.
    corpo = pagamentos.simular_pagamento(cobranca.externo_id, valor_centavos=100000)
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    rafael.refresh_from_db()
    assert rafael.status == "aberta"
    pendencia = PendenciaPagamento.objects.get()
    assert (pendencia.motivo, pendencia.valor_pago_centavos) == ("valor_diferente", 100000)
    avisados = set(
        Notificacao.objects.filter(tipo="pendencia_pagamento").values_list(
            "destinatario__nome", flat=True
        )
    )
    assert avisados == {"Mariana", "Lúcia"}  # administrador e financeiro
    lista = cenario.moto.api("Lúcia").get("/api/financeiro/pendencias-pagamento/")
    assert [p["motivo"] for p in lista.json()["resultados"]] == ["valor_diferente"]


def test_fin_04_ca_017_07_sem_subconta_nao_gera_pix(cenario, com_carteira):  # noqa: F811
    resposta = cenario.moto.api("Lúcia").post(
        f"{CONTAS}{_carlos(com_carteira).pk}/cobranca/", {"tipo": "pix"}, format="json"
    )
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "recebimentos_desligados"


def test_fin_03_ca_017_08_multa_e_juros_no_pagamento(cenario, com_carteira):  # noqa: F811
    for codigo in ("LOC-2841", "LOC-2790"):
        _contrato_com_juros(com_carteira[codigo])
    api = cenario.moto.api("Lúcia")
    carlos = api.get(f"{CONTAS}{_carlos(com_carteira).pk}/").json()["valor_hoje"]
    assert carlos == {
        "data": "2026-10-07",
        "dias_atraso": 7,
        "principal_centavos": 29940,
        "multa_centavos": 599,
        "juros_centavos": 70,
        "total_centavos": 30609,
        "cobra_juros": True,
    }
    rafael = api.get(f"{CONTAS}{_rafael(com_carteira).pk}/").json()["valor_hoje"]
    assert (rafael["multa_centavos"], rafael["juros_centavos"], rafael["total_centavos"]) == (
        2694,
        1123,  # 1122,5 arredonda para cima, uma vez
        138517,
    )
    # Recebida em 07 out: a multa e os juros ficam gravados na conta.
    _abrir(cenario)
    assert _receber(cenario, _carlos(com_carteira), 29940, "cartao_debito").status_code == 422
    assert _receber(cenario, _carlos(com_carteira), 30609, "cartao_debito").status_code == 200
    paga = _carlos(com_carteira)
    assert (paga.multa_centavos, paga.juros_centavos) == (599, 70)
    # Paga no dia do vencimento (parcela 3 de Carlos): sem multa nem juros.
    no_dia = ContaReceber.objects.get(
        origem_id=com_carteira["LOC-2841"].pk, vencimento=date(2026, 10, 7)
    )
    assert api.get(f"{CONTAS}{no_dia.pk}/").json()["valor_hoje"]["total_centavos"] == 29940
    # Sem a cláusula no contrato (LOC-2848, sem contrato): multa e juros 0.
    sem = ContaReceber.objects.filter(origem_id=com_carteira["LOC-2850"].pk).first()
    assert sem is not None
    assert financeiro_selectors.valor_hoje(sem, date(2026, 12, 1))["cobra_juros"] is False
    # Tetos da FIN-03: 2% de multa e 1% ao mês.
    for campos in ({"multa_atraso_pct": Decimal("3.00")}, {"juros_mes_pct": Decimal("1.50")}):
        with pytest.raises(IntegrityError), transaction.atomic():
            ConfiguracaoEmpresa.objects.update_or_create(unica=1, defaults=campos)


def test_fin_01_ca_017_09_conta_paga_nao_se_edita_e_estorna(cenario, lucas):  # noqa: F811
    _abrir(cenario)
    parcela = _conta(lucas)
    _receber(cenario, parcela, 32900)
    parcela.refresh_from_db()
    with pytest.raises(Conflito):
        financeiro.ajustar_valor(parcela, 30000, motivo="desconto", regra="APR-01")
    assert (
        cenario.moto.api("Bruna")
        .post(
            f"{CONTAS}{parcela.pk}/estornar/", {"motivo": "Recebida em duplicidade"}, format="json"
        )
        .status_code
        == 403
    )  # vendedor não estorna
    resposta = cenario.moto.api("Rodrigo").post(
        f"{CONTAS}{parcela.pk}/estornar/", {"motivo": "Recebida em duplicidade"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    nova = resposta.json()
    assert (nova["status"], nova["valor_centavos"], nova["estorno_de"]) == (
        "vence_hoje",
        32900,
        parcela.pk,
    )
    parcela.refresh_from_db()
    assert parcela.status == "paga" and parcela.estornada_em is not None
    estorno = MovimentoCaixa.objects.get(estorno_de=parcela.movimento_caixa)
    assert estorno.valor_centavos == 32900
    caixa = Caixa.objects.get()
    assert financeiro_selectors.resumo_do_caixa(caixa)["gaveta"]["esperado_centavos"] == 20000
    # Estornada uma vez, não estorna de novo.
    de_novo = cenario.moto.api("Rodrigo").post(
        f"{CONTAS}{parcela.pk}/estornar/", {"motivo": "De novo"}, format="json"
    )
    assert de_novo.status_code == 409


def test_fin_01_loc_12_ca_017_10_cancelar_e_renegociar(cenario, com_carteira, lucas):  # noqa: F811
    api = cenario.moto.api("Rodrigo")
    caucao = _conta(lucas, "caucao")
    cancelada = api.post(
        f"{CONTAS}{caucao.pk}/cancelar/",
        {"motivo": "Locação cancelada antes da retirada"},
        format="json",
    )
    assert cancelada.status_code == 200
    assert cancelada.json()["status"] == "cancelada"
    assert (
        api.post(f"{CONTAS}{caucao.pk}/cancelar/", {"motivo": "x"}, format="json").status_code
        == 409
    )

    carlos = _carlos(com_carteira)
    renegociada = api.post(
        f"{CONTAS}renegociar/",
        {
            "contas": [carlos.pk],
            "novas": [
                {"vencimento": "2026-10-15", "valor_centavos": 15000},
                {"vencimento": "2026-10-22", "valor_centavos": 15609},
            ],
            "motivo": "Combinado com o cliente",
        },
        format="json",
    )
    assert renegociada.status_code == 201, renegociada.json()
    novas = renegociada.json()["resultados"]
    assert [(n["vencimento"], n["valor_centavos"]) for n in novas] == [
        ("2026-10-15", 15000),
        ("2026-10-22", 15609),
    ]
    carlos.refresh_from_db()
    assert carlos.status == "renegociada"
    assert {
        c.nasceu_de_id for c in ContaReceber.objects.filter(pk__in=[n["id"] for n in novas])
    } == {carlos.renegociada_em_id}
    # A original sai do em aberto.
    assert api.get(CONTAS).json()["indicadores"]["em_atraso_centavos"] == 134700
    assert (
        api.post(
            f"{CONTAS}renegociar/",
            {
                "contas": [carlos.pk],
                "novas": [{"vencimento": "2026-10-15", "valor_centavos": 1}],
                "motivo": "x",
            },
            format="json",
        ).status_code
        == 409
    )


def test_loc_07_cli_05_ca_017_11_atraso_alimenta_locacao_e_cliente(
    cenario,  # noqa: F811
    com_carteira,
    relogio,
):
    lista = cenario.moto.api("Rodrigo").get("/api/locacoes/", {"busca": "LOC-2841"}).json()
    linha = next(x for x in lista["resultados"] if x["codigo"] == "LOC-2841")
    assert linha["situacao"]["codigo"] == "pagamento_atrasado"

    # A régua das 09:00: Rafael tem 25 dias de atraso e é bloqueado.
    financeiro.regua_de_cobranca()
    rafael = Cliente.objects.get(nome="Rafael Sousa")
    assert rafael.status == "bloqueado"
    # Conta vencida em 23 set: completa 15 dias em 08 out e bloqueia nesse dia.
    diego = cenario.clientes["Diego"]
    financeiro.lancar_avulsa(
        filial_id=cenario.frota.centro.pk,
        cliente_id=diego.pk,
        tipo="multa",
        descricao="Multa de trânsito",
        vencimento=date(2026, 9, 23),
        valor_centavos=19500,
    )
    financeiro.regua_de_cobranca()
    diego.refresh_from_db()
    assert diego.status != "bloqueado"
    relogio.em("2026-10-08 09:00")
    financeiro.regua_de_cobranca()
    diego.refresh_from_db()
    assert diego.status == "bloqueado"

    # Rafael quita a última conta com mais de 15 dias e volta a ativo.
    relogio.em("2026-10-07 10:00")
    _abrir(cenario)
    assert _receber(cenario, _rafael(com_carteira), 134700).status_code == 200
    rafael.refresh_from_db()
    # Sai do bloqueio por atraso; sem os documentos na carteira, volta a incompleto (CA-014-16).
    assert rafael.status == "incompleto"
    assert rafael.bloqueio_motivo == ""


def test_fin_03_ca_017_23_conta_que_nasce_vencida(cenario, com_carteira):  # noqa: F811
    juliana = com_carteira["LOC-2836"]
    _contrato_com_juros(juliana)
    parcela = _conta(juliana)
    # No seed, paga em 01 out, na retirada: sem multa nem juros, total pago R$ 958,00.
    assert (parcela.status, parcela.multa_centavos, parcela.juros_centavos) == ("paga", 0, 0)
    assert parcela.vencimento == date(2026, 9, 30)
    # A mesma parcela em aberto, nascida em 01 out, paga em cada dia:
    aberta = ContaReceber(
        filial=parcela.filial,
        cliente_id=parcela.cliente_id,
        tipo="parcela",
        vencimento=date(2026, 9, 30),
        valor_centavos=32900,
        origem_tipo="locacao",
        origem_id=juliana.pk,
        criado_em=datetime(2026, 10, 1, 9, 0, tzinfo=FUSO),
    )
    casos = {date(2026, 10, 1): (0, 0, 32900), date(2026, 10, 2): (658, 11, 33569)}
    casos[date(2026, 10, 8)] = (658, 77, 33635)
    for dia, (multa, juros, total) in casos.items():
        devido = financeiro_selectors.devido_ate(aberta, dia)
        assert (devido.multa_centavos, devido.juros_centavos, devido.total_centavos) == (
            multa,
            juros,
            total,
        )
    # O estado e as faixas seguem o vencimento: em 02 out, atrasada há 2 dias.
    assert financeiro_selectors.status_exibido("aberta", aberta.vencimento, date(2026, 10, 2)) == (
        "atrasada"
    )
    detalhe = cenario.moto.api("Rodrigo").get(f"/api/locacoes/{juliana.pk}/").json()
    assert detalhe["total_pago_centavos"] == 95800
    # Carlos continua com 599 + 70 (nasceu antes do vencimento).
    _contrato_com_juros(com_carteira["LOC-2841"])
    devido = financeiro_selectors.devido_ate(_carlos(com_carteira), date(2026, 10, 7))
    assert (devido.multa_centavos, devido.juros_centavos) == (599, 70)


# --- Isolamento e permissão ---


def test_fin_01_contas_nao_vazam_entre_empresas(cenario, com_carteira, empresa_b):  # noqa: F811
    assert not ContaReceber.objects.exists()  # na empresa B


def test_fin_01_vistoriador_nao_ve_contas(cenario, com_carteira):  # noqa: F811
    assert cenario.moto.api("João").get(CONTAS).status_code == 403
    assert cenario.moto.api("João").get(f"{CAIXAS}hoje/").status_code == 403


# --- Caixa do dia (FIN-07, FIN-08, APR-04) ---


def _avulsa(cenario, cliente: str, valor: int) -> ContaReceber:  # noqa: F811
    return financeiro.lancar_avulsa(
        filial_id=cenario.frota.centro.pk,
        cliente_id=cenario.clientes[cliente].pk,
        tipo="outro",
        descricao=f"Recebimento de {cliente}",
        vencimento=date(2026, 10, 7),
        valor_centavos=valor,
    )


def _pix_no_caixa(cenario, conta: ContaReceber, capturar: Any) -> None:  # noqa: F811
    gerada = cenario.moto.api("Bruna").post(
        f"{CONTAS}{conta.pk}/cobranca/", {"tipo": "pix", "no_caixa": True}, format="json"
    )
    assert gerada.status_code == 201, gerada.json()
    cobranca = CobrancaExterna.objects.get(pk=gerada.json()["id"])
    assert _webhook(capturar, pagamentos.simular_pagamento(cobranca.externo_id)) == 200


def _despesa(cenario, quem: str = "Bruna", cabecalhos=None, **campos: Any) -> Any:  # noqa: F811
    """Lança pela API, com a nota (obrigatória, FIN-06); `nota=None` manda sem ela."""
    corpo = {
        "descricao": "Óleo 1 litro",
        "valor_centavos": 4800,
        "data": "2026-10-07",
        "vencimento": "2026-10-07",
        "categoria": "manutencao",
        "nota": _jpg("nota.jpg"),
        **campos,
    }
    corpo = {k: v for k, v in corpo.items() if v is not None}
    api = cenario.moto.api(quem, **(cabecalhos or {}))
    return api.post("/api/financeiro/despesas/", corpo, format="multipart")


@pytest.fixture
def caixa_do_seed(
    cenario,  # noqa: F811
    lucas,
    recebimentos,
    relogio,
    django_capture_on_commit_callbacks,
) -> Caixa:
    """CA-017-13: o caixa de 07 out da Filial Centro, com os movimentos da tabela."""
    relogio.em("2026-10-07 07:55")
    assert _abrir(cenario).status_code == 201
    relogio.em("2026-10-07 08:02")
    _pix_no_caixa(cenario, _avulsa(cenario, "Juliana", 32900), django_capture_on_commit_callbacks)
    relogio.em("2026-10-07 08:40")
    diego = _avulsa(cenario, "Diego", 10900)
    assert _receber(cenario, diego, 10900, "cartao_credito").status_code == 200
    relogio.em("2026-10-07 09:15")
    assert _receber(cenario, _conta(lucas), 32900).status_code == 200
    assert _receber(cenario, _conta(lucas, "caucao"), 30000).status_code == 200
    relogio.em("2026-10-07 10:30")
    caixa = Caixa.objects.get()
    sangria = cenario.moto.api("Bruna").post(
        f"{CAIXAS}{caixa.pk}/sangria/",
        {"valor_centavos": 50000, "descricao": "Depósito no banco"},
        format="json",
    )
    assert sangria.status_code == 201, sangria.json()
    relogio.em("2026-10-07 11:05")
    _pix_no_caixa(cenario, _avulsa(cenario, "Carlos", 4490), django_capture_on_commit_callbacks)
    relogio.em("2026-10-07 11:20")
    qxa = cenario.frota.veiculos["QXA4B21"].pk
    oleo = _despesa(cenario, veiculo_id=qxa, pago_no_caixa=True)
    assert oleo.status_code == 201, oleo.json()
    return caixa


def test_fin_07_ca_017_12_um_caixa_por_filial_por_dia(cenario, lucas):  # noqa: F811
    assert _abrir(cenario, quem="João").status_code == 403
    sem_caixa = _receber(cenario, _conta(lucas), 32900)
    assert sem_caixa.status_code == 422
    assert sem_caixa.json()["codigo"] == "FIN-07"
    assert sem_caixa.json()["mensagem"] == "Abra o caixa do dia para receber"
    aberto = _abrir(cenario)
    assert aberto.status_code == 201
    assert (aberto.json()["status"], aberto.json()["data"]) == ("aberto", "2026-10-07")
    assert aberto.json()["resumo"]["gaveta"]["esperado_centavos"] == 20000
    for quem in ("Bruna", "Rodrigo"):
        de_novo = _abrir(cenario, quem=quem)
        assert de_novo.status_code == 409
        assert de_novo.json()["codigo"] == "FIN-07"
        assert de_novo.json()["mensagem"] == "O caixa de hoje desta filial já foi aberto"
    # Duas chamadas ao mesmo tempo: a restrição única (filial, data) segura a segunda.
    with pytest.raises(IntegrityError), transaction.atomic():
        Caixa.objects.create(
            filial=cenario.frota.centro,
            data=date(2026, 10, 7),
            aberto_por=cenario.pessoas["Rodrigo"],
            troco_centavos=0,
        )
    # A Filial Caucaia abre o próprio caixa; Lúcia (financeiro) também abre.
    caucaia = _caucaia(cenario.moto)
    outro = _abrir(cenario, quem="Lúcia", HTTP_X_FILIAL=str(caucaia.pk))
    assert outro.status_code == 201, outro.json()
    hoje = cenario.moto.api("Bruna").get(f"{CAIXAS}hoje/").json()
    assert hoje["id"] == aberto.json()["id"]


def test_fin_07_ca_017_13_caixa_de_07_out_do_seed(cenario, caixa_do_seed):  # noqa: F811
    corpo = cenario.moto.api("Bruna").get(f"{CAIXAS}hoje/").json()
    resumo = corpo["resumo"]
    assert (resumo["entrou_hoje_centavos"], resumo["recebimentos"]) == (111190, 5)
    assert resumo["por_forma"]["pix"] == {"centavos": 37390, "quantidade": 2}
    assert resumo["por_forma"]["cartao"] == {
        "centavos": 10900,
        "quantidade": 1,
        "texto": "cai em 30 dias",
    }
    assert resumo["por_forma"]["dinheiro"] == {"centavos": 62900, "quantidade": 2}
    assert resumo["gaveta"] == {
        "troco_centavos": 20000,
        "entradas_dinheiro_centavos": 62900,
        "saidas_dinheiro_centavos": 54800,
        "esperado_centavos": 28100,
    }
    assert corpo["aberto_por"]["nome"] == "Bruna"
    movimentos = cenario.moto.api("Bruna").get(f"{CAIXAS}{corpo['id']}/movimentos/").json()
    tipos = [(m["tipo"], m["forma"], m["valor_centavos"]) for m in movimentos["resultados"]]
    assert tipos == [
        ("entrada", "pix", 32900),
        ("entrada", "cartao_credito", 10900),
        ("entrada", "dinheiro", 32900),
        ("entrada", "dinheiro", 30000),
        ("sangria", "dinheiro", 50000),
        ("entrada", "pix", 4490),
        ("saida", "dinheiro", 4800),
    ]
    assert movimentos["resultados"][0]["registrado_por"] == "Sistema"  # Pix pelo webhook


def test_fin_07_ca_017_14_fechar_sem_diferenca(cenario, caixa_do_seed):  # noqa: F811
    api = cenario.moto.api("Bruna")
    url = f"{CAIXAS}{caixa_do_seed.pk}/"
    maior = api.post(f"{url}sangria/", {"valor_centavos": 30000, "descricao": "x"}, format="json")
    assert maior.status_code == 422
    assert maior.json()["codigo"] == "sangria_maior_que_gaveta"
    fechado = api.post(f"{url}fechar/", {"contado_centavos": 28100}, format="json")
    assert fechado.status_code == 200, fechado.json()
    assert fechado.json()["status"] == "fechado"
    fechamento = fechado.json()["fechamento"]
    contagem = (
        fechamento["contado_centavos"],
        fechamento["esperado_centavos"],
        fechamento["diferenca_centavos"],
    )
    assert contagem == (28100, 28100, 0)
    for resposta in (
        api.post(f"{url}sangria/", {"valor_centavos": 100, "descricao": "x"}, format="json"),
        api.post(f"{url}fechar/", {"contado_centavos": 28100}, format="json"),
    ):
        assert resposta.status_code == 409
        assert resposta.json()["codigo"] == "FIN-07"
        assert resposta.json()["mensagem"] == "Este caixa já foi fechado"


def _pedido_do_caixa(caixa: Caixa) -> int:
    caixa.refresh_from_db()
    assert caixa.pedido_aprovacao_id is not None
    return caixa.pedido_aprovacao_id


def test_fin_07_apr_04_ca_017_15_diferenca_vai_para_o_gerente(cenario, caixa_do_seed):  # noqa: F811
    api = cenario.moto.api("Bruna")
    url = f"{CAIXAS}{caixa_do_seed.pk}/fechar/"
    sem_motivo = api.post(url, {"contado_centavos": 27100}, format="json")
    assert sem_motivo.status_code == 400
    assert sem_motivo.json()["codigo"] == "validacao"
    falta = api.post(
        url, {"contado_centavos": 27100, "motivo_diferenca": "Troco errado"}, format="json"
    )
    assert falta.status_code == 200, falta.json()
    assert falta.json()["status"] == "aguardando_aprovacao"
    assert falta.json()["fechamento"]["diferenca_centavos"] == -1000
    assert Notificacao.objects.filter(
        destinatario=cenario.pessoas["Rodrigo"], tipo="caixa_com_diferenca"
    ).exists()
    # Rodrigo recusa: volta a aberto, e Bruna conta de novo.
    pedido = _pedido_do_caixa(caixa_do_seed)
    recusa = cenario.moto.api("Rodrigo").post(
        f"/api/aprovacoes/{pedido}/recusar/", {"motivo": "Conte de novo"}, format="json"
    )
    assert recusa.status_code == 200, recusa.json()
    caixa_do_seed.refresh_from_db()
    assert (caixa_do_seed.status, caixa_do_seed.diferenca_centavos) == ("aberto", None)
    # Uma sobra de R$ 5,00 também precisa de motivo e aprovação; Rodrigo aprova.
    sobra = api.post(url, {"contado_centavos": 28600, "motivo_diferenca": "Sobra"}, format="json")
    assert sobra.json()["status"] == "aguardando_aprovacao"
    assert sobra.json()["fechamento"]["diferenca_centavos"] == 500
    aprovado = cenario.moto.api("Rodrigo").post(
        f"/api/aprovacoes/{_pedido_do_caixa(caixa_do_seed)}/aprovar/", {}, format="json"
    )
    assert aprovado.status_code == 200, aprovado.json()
    caixa_do_seed.refresh_from_db()
    assert (caixa_do_seed.status, caixa_do_seed.diferenca_centavos) == ("fechado", 500)


def test_apr_09_ca_017_15_gerente_nao_aprova_a_propria_diferenca(cenario, caixa_do_seed):  # noqa: F811
    rodrigo = cenario.moto.api("Rodrigo")
    rodrigo.post(
        f"{CAIXAS}{caixa_do_seed.pk}/fechar/",
        {"contado_centavos": 27100, "motivo_diferenca": "Troco errado"},
        format="json",
    )
    pedido = _pedido_do_caixa(caixa_do_seed)
    proprio = rodrigo.post(f"/api/aprovacoes/{pedido}/aprovar/", {}, format="json")
    assert proprio.status_code == 403
    assert proprio.json()["codigo"] == "APR-09"
    mariana = cenario.moto.api("Mariana")
    outro = mariana.post(f"/api/aprovacoes/{pedido}/aprovar/", {}, format="json")
    assert outro.status_code == 200, outro.json()
    caixa_do_seed.refresh_from_db()
    assert caixa_do_seed.status == "fechado"


def test_fin_08_aut_08_ca_017_16_fechamento_automatico(cenario, relogio):  # noqa: F811
    from apps.financeiro.tasks import aut_08_fechamento_automatico_do_caixa

    _abrir(cenario)
    caucaia = _caucaia(cenario.moto, "Bruna")
    _abrir(cenario, HTTP_X_FILIAL=str(caucaia.pk))
    em_aprovacao = Caixa.objects.get(filial=caucaia)
    financeiro.fechar_caixa(
        em_aprovacao, cenario.pessoas["Bruna"], contado_centavos=0, motivo_diferenca="Sumiu"
    )
    # 23:59 em São Paulo já é 08 out em UTC; o dia do caixa é o de São Paulo.
    agora = relogio.em("2026-10-07 23:59")
    assert agora.astimezone(ZoneInfo("UTC")).date() == date(2026, 10, 8)
    schema = cenario.moto.empresa.schema_name
    assert aut_08_fechamento_automatico_do_caixa(schema) == 1
    centro = Caixa.objects.get(filial=cenario.frota.centro)
    assert centro.data == date(2026, 10, 7)
    situacao = (centro.status, centro.contado_centavos, centro.diferenca_centavos)
    assert situacao == ("fechado_sem_conferencia", None, None)
    assert Notificacao.objects.filter(
        destinatario=cenario.pessoas["Rodrigo"], tipo="caixa_sem_conferencia"
    ).exists()
    em_aprovacao.refresh_from_db()
    assert em_aprovacao.status == "aguardando_aprovacao"
    assert aut_08_fechamento_automatico_do_caixa(schema) == 0


def test_fin_07_ca_017_17_movimento_imutavel(cenario, caixa_do_seed):  # noqa: F811
    cartao = MovimentoCaixa.objects.get(forma="cartao_credito")
    cartao.descricao = "outra"
    with pytest.raises(MovimentoImutavel):
        cartao.save()
    with pytest.raises(MovimentoImutavel):
        cartao.delete()
    url = f"{CAIXAS}{caixa_do_seed.pk}/movimentos/{cartao.pk}/estornar/"
    assert cenario.moto.api("Bruna").post(url, {"motivo": "x"}, format="json").status_code == 403
    estorno = cenario.moto.api("Rodrigo").post(url, {"motivo": "Lançado errado"}, format="json")
    assert estorno.status_code == 201, estorno.json()
    assert (estorno.json()["estorno_de"], estorno.json()["valor_centavos"]) == (cartao.pk, 10900)
    cartao.refresh_from_db()
    assert cartao.valor_centavos == 10900  # o original não muda
    resumo = financeiro_selectors.resumo_do_caixa(caixa_do_seed)
    assert resumo["entrou_hoje_centavos"] == 111190 - 10900
    assert resumo["por_forma"]["cartao"]["centavos"] == 0
    assert resumo["gaveta"]["esperado_centavos"] == 28100  # cartão não mexe na gaveta


def test_fin_07_movimentos_e_estorno_auditam_com_filial(cenario, caixa_do_seed):  # noqa: F811
    """T-150 (AUD-02): os eventos `movimento_caixa.*` levam a filial do caixa."""
    cartao = MovimentoCaixa.objects.get(forma="cartao_credito")
    url = f"{CAIXAS}{caixa_do_seed.pk}/movimentos/{cartao.pk}/estornar/"
    estorno = cenario.moto.api("Rodrigo").post(url, {"motivo": "Lançado errado"}, format="json")
    assert estorno.status_code == 201, estorno.json()
    eventos = EventoAuditoria.objects.filter(acao__startswith="movimento_caixa.")
    acoes = set(eventos.values_list("acao", flat=True))
    assert {
        "movimento_caixa.entrada",
        "movimento_caixa.saida",
        "movimento_caixa.sangria",
        "movimento_caixa.estornar",
        "movimento_caixa.estorno_motivo",
    } <= acoes
    assert set(eventos.values_list("filial_id", flat=True)) == {caixa_do_seed.filial_id}

    caucaia = _caucaia(cenario.moto, "Bruna")
    api = cenario.moto.api("Mariana")
    centro = api.get(AUDITORIA, {"filial": caixa_do_seed.filial_id}).json()["resultados"]
    outra = api.get(AUDITORIA, {"filial": caucaia.pk}).json()["resultados"]
    assert {e["acao"] for e in centro} >= {"movimento_caixa.entrada", "movimento_caixa.estornar"}
    assert not [e for e in outra if e["acao"].startswith("movimento_caixa.")]


def test_fil_06_ca_017_18_caixa_aberto_impede_desativar_a_filial(cenario):  # noqa: F811
    caucaia = _caucaia(cenario.moto, "Bruna")
    _abrir(cenario, HTTP_X_FILIAL=str(caucaia.pk))
    url = f"/api/filiais/{caucaia.pk}/desativar/"
    mariana = cenario.moto.api("Mariana")
    recusa = mariana.post(url, {"motivo": "Fechou"}, format="json")
    assert recusa.status_code == 422
    assert recusa.json()["codigo"] == "FIL-06"
    assert recusa.json()["detalhes"]["operacao"]["caixas"] == 1
    caixa = Caixa.objects.get(filial=caucaia)
    financeiro.fechar_caixa(
        caixa, cenario.pessoas["Bruna"], contado_centavos=20000, motivo_diferenca=None
    )
    # Fechado, e com uma conta a receber em aberto da filial: desativa (CA-012-16).
    financeiro.lancar_avulsa(
        filial_id=caucaia.pk,
        cliente_id=cenario.clientes["Diego"].pk,
        tipo="outro",
        descricao="Conta em aberto",
        vencimento=date(2026, 10, 20),
        valor_centavos=1000,
    )
    assert mariana.post(url, {"motivo": "Fechou"}, format="json").status_code == 200


# --- Despesas (FIN-05, FIN-06, APR-03) ---


def _decidir(cenario, despesa_id: int, acao: str = "aprovar", quem: str = "Rodrigo") -> Any:  # noqa: F811
    pedido = Despesa.objects.get(pk=despesa_id).pedido_aprovacao_id
    corpo = {"motivo": "Orçamento caro"} if acao == "recusar" else {}
    return cenario.moto.api(quem).post(f"/api/aprovacoes/{pedido}/{acao}/", corpo, format="json")


def _pagar(cenario, despesa_id: int, forma: str) -> Any:  # noqa: F811
    return cenario.moto.api("Lúcia").post(
        f"/api/financeiro/despesas/{despesa_id}/pagar/",
        {"forma": forma, "pago_em": "2026-10-07T13:00:00Z"},
        format="multipart",
    )


def test_fin_05_fin_06_ca_017_19_despesas_de_outubro(cenario, caixa_do_seed):  # noqa: F811
    pmz = cenario.frota.veiculos["PMZ3E17"].pk
    pneus = _despesa(cenario, "João", descricao="Pneus (2)", valor_centavos=120000, veiculo_id=pmz)
    assert pneus.status_code == 201, pneus.json()
    assert pneus.json()["status"] == "aguardando_aprovacao"
    assert pneus.json()["rotulo_situacao"] == "Aguardando gerente"
    fixas = {"categoria": "fixas"}
    luz = _despesa(
        cenario,
        "Lúcia",
        descricao="Conta de luz",
        valor_centavos=41230,
        data="2026-10-06",
        vencimento="2026-10-10",
        **fixas,
    ).json()
    assert luz["status"] == "a_pagar"
    aluguel = _despesa(
        cenario,
        "Lúcia",
        descricao="Aluguel do ponto",
        valor_centavos=350000,
        data="2026-10-05",
        vencimento="2026-10-05",
        **fixas,
    ).json()
    assert aluguel["status"] == "aguardando_aprovacao"
    assert _decidir(cenario, aluguel["id"]).status_code == 200
    assert _pagar(cenario, aluguel["id"], "boleto").json()["status"] == "paga"
    ipva = _despesa(
        cenario,
        "Lúcia",
        descricao="IPVA ROE2A88",
        valor_centavos=18640,
        data="2026-10-03",
        vencimento="2026-10-31",
        categoria="impostos",
    ).json()
    assert ipva["status"] == "a_pagar"  # abaixo de R$ 500 não vai para aprovação
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
    assert _pagar(cenario, rastreadores["id"], "cartao").json()["status"] == "paga"

    corpo = cenario.moto.api("Lúcia").get("/api/financeiro/despesas/", {"mes": "2026-10"}).json()
    indicadores = corpo["indicadores"]
    assert indicadores["gasto_mes_centavos"] == 706670
    assert indicadores["aguardando_aprovacao_centavos"] == 120000
    assert indicadores["aguardando_aprovacao_quantidade"] == 1
    assert indicadores["por_categoria"] == {
        "fixas": 391230,
        "rastreamento": 172000,
        "manutencao": 124800,
        "impostos": 18640,
    }
    contagens = {"aguardando_aprovacao": 1, "a_pagar": 2, "paga": 3, "recusada": 0}
    assert corpo["contagens"] == contagens


def test_fin_05_apr_03_ca_017_20_limite_de_500(cenario):  # noqa: F811
    assert _despesa(cenario, valor_centavos=50000).json()["status"] == "a_pagar"
    assert _despesa(cenario, valor_centavos=50001).json()["status"] == "aguardando_aprovacao"
    pneus = _despesa(cenario, "João", descricao="Pneus (2)", valor_centavos=120000).json()
    assert _decidir(cenario, pneus["id"]).status_code == 200
    assert Despesa.objects.get(pk=pneus["id"]).status == "a_pagar"
    # Recusa com motivo: recusada, e João é avisado.
    outra = _despesa(cenario, "João", descricao="Pneus de novo", valor_centavos=120000).json()
    assert _decidir(cenario, outra["id"], "recusar").status_code == 200
    assert Despesa.objects.get(pk=outra["id"]).status == "recusada"
    assert Notificacao.objects.filter(
        destinatario=cenario.pessoas["João"], tipo="despesa_recusada"
    ).exists()
    # Quem lançou não aprova a própria despesa (APR-09).
    propria = _despesa(cenario, "Rodrigo", valor_centavos=60000).json()
    assert _decidir(cenario, propria["id"]).status_code == 403
    # João lança manutenção; fixas, não. E não vê a lista.
    assert _despesa(cenario, "João", categoria="fixas").status_code == 403
    assert cenario.moto.api("João").get("/api/financeiro/despesas/").status_code == 403


def test_fin_05_ca_017_21_despesa_paga_no_caixa(cenario, caixa_do_seed):  # noqa: F811
    oleo = Despesa.objects.get(descricao="Óleo 1 litro")
    assert oleo.status == "paga"
    assert oleo.movimento_caixa is not None
    assert (oleo.movimento_caixa.tipo, oleo.movimento_caixa.forma) == ("saida", "dinheiro")
    veiculo = cenario.frota.veiculos["QXA4B21"]
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{veiculo.pk}/").json()
    assert ficha["indicadores_financeiros"]["custo_manutencao_ano_centavos"] == 4800
    acima = _despesa(cenario, valor_centavos=50001, pago_no_caixa=True)
    assert acima.status_code == 422
    assert acima.json()["codigo"] == "APR-03"


def test_fin_06_aud_05_ca_017_22_nota_e_veiculo(cenario, relogio):  # noqa: F811
    veiculo = cenario.frota.veiculos["PMZ3E17"]
    resposta = _despesa(
        cenario,
        "João",
        descricao="Pneus",
        valor_centavos=30000,
        veiculo_id=veiculo.pk,
        nota=_jpg("nota.jpg"),
    )
    assert resposta.status_code == 201, resposta.json()
    nota = resposta.json()["nota"]
    expira = datetime.fromisoformat(nota["url_expira_em"].replace("Z", "+00:00"))
    assert expira > relogio.agora
    assert resposta.json()["veiculo"] == {"id": veiculo.pk, "placa": "PMZ3E17"}
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{veiculo.pk}/").json()
    assert ficha["indicadores_financeiros"]["custo_manutencao_ano_centavos"] == 30000
    assert _despesa(cenario, categoria="festas").status_code == 400


# --- Painel: caixa e despesas (docs/api/painel.md, T-128) ---

PAINEL = "/api/painel/"


def _kpis(corpo: dict[str, Any]) -> dict[str, Any]:
    return {kpi["chave"]: kpi for kpi in corpo["kpis"]}


def test_fin_07_fin_15_caixa_hoje_no_painel_do_administrador(
    cenario,  # noqa: F811
    com_carteira,
    caixa_do_seed,
):
    UsoEmpresa.objects.filter(empresa=cenario.moto.empresa).update(
        passos_implantacao={"conta": "2026-09-20", "filial": "2026-09-21", "primeira_locacao": "x"}
    )
    corpo = cenario.moto.api("Mariana").get(f"{PAINEL}inicio/").json()
    assert corpo["variante"] == "geral"
    assert corpo["caixa_hoje"] == {
        "filial": "Filial Centro",
        "data": "2026-10-07",
        "status": "aberto",
        "recebido_centavos": 111190,
        "a_receber_hoje_centavos": 262580,  # o "vence hoje" da FIN-15
        "despesas_centavos": 4800,
        "saldo_dia_centavos": 106390,
    }
    todas = cenario.moto.api("Mariana", HTTP_X_FILIAL="todas").get(f"{PAINEL}inicio/").json()
    assert todas["caixa_hoje"] is None


def test_fin_05_fin_07_caixas_e_despesas_no_painel_do_financeiro(
    cenario,  # noqa: F811
    caixa_do_seed,
):
    _despesa(
        cenario,
        "Lúcia",
        descricao="Conta de luz",
        valor_centavos=41230,
        data="2026-10-06",
        vencimento="2026-10-07",
        categoria="fixas",
    )
    corpo = cenario.moto.api("Lúcia").get(f"{PAINEL}inicio/").json()
    assert corpo["caixas_do_dia"] == [
        {
            "filial": "Filial Centro",
            "status": "aberto",
            "aberto_por": "Bruna",
            "esperado_gaveta_centavos": 28100,
        }
    ]
    sai = _kpis(corpo)["sai_hoje"]
    assert (sai["valor"], sai["contexto"]) == (
        {"tipo": "centavos", "valor": 41230},
        "1 conta a pagar",
    )
    assert corpo["para_hoje"][-1]["texto"] == "Pagar conta de luz · R$ 412,30"
    assert corpo["para_hoje"][-1]["destino"]["chave"] == "contas_a_pagar"
    assert cenario.moto.api("Lúcia").get(f"{PAINEL}contadores/").json()["contadores"] == {
        "contas_a_pagar": 1,
        "receber": 0,
    }


def test_apr_03_apr_09_contador_de_despesas(cenario):  # noqa: F811
    _despesa(cenario, "João", descricao="Pneus (2)", valor_centavos=120000)
    _despesa(cenario, "Rodrigo", descricao="Conserto do portão", valor_centavos=60000)
    contar = cenario.moto.api("Rodrigo").get(f"{PAINEL}contadores/").json()["contadores"]
    assert contar["despesas"] == 1  # a dele não conta (APR-09)
    mariana = cenario.moto.api("Mariana").get(f"{PAINEL}contadores/").json()["contadores"]
    assert mariana["despesas"] == 2
