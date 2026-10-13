"""T-148: código das decisões da T-017 (T-147). Histórico da análise pela FIN-03 com o cliente
novo `ok` (CLI-04), bloqueio pedido uma vez por conta (AUT-03, CLI-05), textos da régua por
momento, com e-mail (AUT-03), recibo com a forma e o dia (AUT-05) e a semana e as contagens do
`Receber` (FIN-15). Números dos dados de referência das regras, em 07 out 2026."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.cache import cache

from apps.clientes.models import Cliente
from apps.empresas.models import ConfiguracaoEmpresa
from apps.financeiro import leituras as financeiro_leituras
from apps.financeiro import services as financeiro
from apps.financeiro.models import CobrancaExterna, ContaReceber
from apps.locacoes.models import Locacao
from comum import leituras
from integracoes.pagamentos import falso as pagamentos
from integracoes.whatsapp import falso as whatsapp

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _contrato_com_juros
from .test_t017_financeiro import (  # noqa: F401 - fixtures
    CONTAS,
    _carlos,
    _conta,
    _rafael,
    _webhook,
    com_carteira,
    recebimentos,
)

LISTA_CLIENTES = "/api/clientes/"
FUSO = ZoneInfo("America/Sao_Paulo")


def _historico(cliente: Cliente) -> dict[str, str]:
    return financeiro_leituras.montar_historico(cliente)


def _item_da_api(cenario, cliente: Cliente) -> dict[str, str]:  # noqa: F811
    corpo = cenario.moto.api("Bruna").get(f"{LISTA_CLIENTES}{cliente.pk}/analise/").json()
    return next(i for i in corpo["itens"] if i["codigo"] == "historico")


def _parcela(locacao, numero: int) -> ContaReceber:
    return _conta(locacao, numero=numero)


def _ultima_mensagem(celular: str) -> str:
    return [m.texto for m in whatsapp.caixa_de_saida if m.celular == celular][-1]


@pytest.fixture(autouse=True)
def moto_rapida(cenario):  # noqa: F811
    """A marca dos textos do contrato: o nome de exibição da empresa é "Moto Rápida"."""
    configuracao = ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()
    configuracao.nome_exibicao = "Moto Rápida"
    configuracao.save()
    cache.clear()


@pytest.fixture
def caixas_vazias():
    whatsapp.caixa_de_saida.clear()
    mail.outbox.clear()


# --- CLI-04: histórico da análise ---


def test_cli_04_historico_conta_que_nasce_vencida_nao_e_atraso(cenario, com_carteira, relogio):  # noqa: F811
    """Caso "Histórico da análise em 07 out"."""
    sem_atraso = {"situacao": "ok", "rotulo": "Sem atraso na empresa"}
    em_atraso = {"situacao": "problema", "rotulo": "Conta em atraso na empresa"}
    juliana = cenario.clientes["Juliana"]
    assert _historico(juliana) == sem_atraso  # a parcela 1 nasceu vencida e foi paga no dia
    assert _historico(cenario.clientes["Lucas"]) == sem_atraso
    assert _historico(cenario.clientes["Carlos"]) == em_atraso
    assert _historico(Cliente.objects.get(nome="Rafael Sousa")) == em_atraso
    assert _item_da_api(cenario, juliana) == {"codigo": "historico", **sem_atraso}

    # Em 01 out, antes de pagar na retirada: a parcela 1 nasceu vencida naquele dia.
    locacao = com_carteira["LOC-2836"]
    (aberta,) = financeiro.criar_contas(
        financeiro.Origem("locacao", locacao.pk, locacao.codigo),
        filial_id=locacao.filial_id,
        cliente_id=juliana.pk,
        contas=[financeiro.NovaConta("parcela", date(2026, 9, 30), 32900, 1, 5)],
    )
    nasceu = datetime(2026, 10, 1, 9, 10, tzinfo=FUSO)
    ContaReceber.objects.filter(pk=aberta.pk).update(criado_em=nasceu)
    relogio.em("2026-10-01 10:00")
    assert _historico(juliana) == sem_atraso
    # No dia seguinte, ainda em aberto, é atraso (FIN-03).
    relogio.em("2026-10-02 10:00")
    assert _historico(juliana) == em_atraso


def test_cli_04_historico_pagou_com_atraso_fica_pendente(cenario, com_carteira, relogio):  # noqa: F811
    carlos = _carlos(com_carteira)
    financeiro.marcar_paga(carlos, forma="pix")  # 07 out, 7 dias depois do vencimento
    assert _historico(cenario.clientes["Carlos"]) == {
        "situacao": "pendente",
        "rotulo": "Já pagou com atraso na empresa",
    }


def test_cli_04_historico_cliente_novo_ok(cenario, monkeypatch):  # noqa: F811
    novo = cenario.clientes["Diego"]  # cadastrado, sem conta
    assert not ContaReceber.objects.filter(cliente=novo).exists()
    novo_ok = {"codigo": "historico", "situacao": "ok", "rotulo": "Cliente novo na empresa"}
    assert _item_da_api(cenario, novo) == novo_ok
    # Com o módulo financeiro desligado (sem fornecedor do bloco), "Sem histórico".
    sem_financeiro = [a for a in leituras._anotacoes["clientes.Cliente"] if a.bloco != "historico"]
    monkeypatch.setitem(leituras._anotacoes, "clientes.Cliente", sem_financeiro)
    assert _item_da_api(cenario, novo) == {
        "codigo": "historico",
        "situacao": "pendente",
        "rotulo": "Sem histórico",
    }


# --- AUT-03, CLI-05: bloqueio uma vez por conta ---


def test_cli_05_desbloqueio_manual_nao_volta_a_bloquear(cenario, com_carteira, relogio):  # noqa: F811
    from apps.clientes import services as clientes_services

    financeiro.regua_de_cobranca()  # 07 out, 09:00: Rafael tem 25 dias e é bloqueado
    rafael = Cliente.objects.get(nome="Rafael Sousa")
    assert rafael.status == "bloqueado"
    assert _rafael(com_carteira).bloqueio_pedido_em == date(2026, 10, 7)

    relogio.em("2026-10-12 15:00")
    clientes_services.desbloquear(rafael, "Combinou pagar na sexta")  # Rodrigo, na ficha
    rafael.refresh_from_db()
    depois_do_desbloqueio = rafael.status
    assert depois_do_desbloqueio != "bloqueado"

    relogio.em("2026-10-13 09:00")
    financeiro.regua_de_cobranca()
    rafael.refresh_from_db()
    assert rafael.status == depois_do_desbloqueio


def test_aut_03_bloqueio_recupera_dia_perdido(cenario, com_carteira, relogio):  # noqa: F811
    diego = cenario.clientes["Diego"]
    multa = financeiro.lancar_avulsa(
        filial_id=cenario.frota.centro.pk,
        cliente_id=diego.pk,
        tipo="multa",
        descricao="Multa de trânsito",
        vencimento=date(2026, 9, 23),
        valor_centavos=19500,
    )
    financeiro.regua_de_cobranca()  # 07 out: 14 dias
    diego.refresh_from_db()
    assert diego.status != "bloqueado"
    # A tarefa não roda em 08 out (15 dias); em 09 out, com 16, o bloqueio sai.
    relogio.em("2026-10-09 09:00")
    financeiro.regua_de_cobranca()
    diego.refresh_from_db()
    multa.refresh_from_db()
    assert diego.status == "bloqueado"
    assert multa.bloqueio_pedido_em == date(2026, 10, 9)
    # Uma vez por conta: no dia seguinte, a conta não pede de novo.
    relogio.em("2026-10-10 09:00")
    assert not financeiro.pedir_bloqueio(multa, 17)


# --- AUT-03: textos da régua ---


def _cobrar_carlos(com_carteira, numero: int) -> str:  # noqa: F811
    assert financeiro.cobrar(_parcela(com_carteira["LOC-2841"], numero))
    return _ultima_mensagem("85985554433")


def test_aut_03_texto_d_menos_1(cenario, com_carteira, relogio, caixas_vazias):  # noqa: F811
    relogio.em("2026-10-06 09:00")
    assert _cobrar_carlos(com_carteira, 3) == (
        "Moto Rápida: olá, Carlos. A parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence "
        "amanhã, 07/10."
    )
    # "Cobrar" manual antes de D-1: a data, sem "amanhã".
    assert _cobrar_carlos(com_carteira, 4) == (
        "Moto Rápida: olá, Carlos. A parcela 4 de 5 da locação LOC-2841, de R$ 299,40, vence "
        "em 14/10."
    )
    assert not CobrancaExterna.objects.exists()  # lembrete não gera Pix


def test_aut_03_texto_d0_com_pix(cenario, com_carteira, recebimentos, caixas_vazias):  # noqa: F811
    texto = _cobrar_carlos(com_carteira, 3)
    pix = CobrancaExterna.objects.get().pix_copia_e_cola
    assert pix
    assert texto == (
        "Moto Rápida: olá, Carlos. A parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence "
        f"hoje. Pague pelo Pix copia e cola: {pix}"
    )


def test_aut_03_texto_d0_sem_recebimentos(cenario, com_carteira, caixas_vazias):  # noqa: F811
    assert _cobrar_carlos(com_carteira, 3).endswith(
        "vence hoje. Pague na loja ou fale com a gente por aqui."
    )


def test_aut_03_texto_d_mais_7_valor_do_dia(cenario, com_carteira, recebimentos, caixas_vazias):  # noqa: F811
    _contrato_com_juros(com_carteira["LOC-2841"])
    texto = _cobrar_carlos(com_carteira, 2)
    pix = CobrancaExterna.objects.get().pix_copia_e_cola
    assert texto == (
        "Moto Rápida: olá, Carlos. A parcela 2 de 5 da locação LOC-2841 venceu em 30/09. O valor "
        f"hoje é R$ 306,09, com multa e juros. Pague pelo Pix copia e cola: {pix}"
    )


def test_aut_03_texto_d_mais_3_e_sem_clausula(cenario, com_carteira, relogio, caixas_vazias):  # noqa: F811
    _contrato_com_juros(com_carteira["LOC-2841"])
    relogio.em("2026-10-03 09:00")
    assert "venceu em 30/09. O valor hoje é R$ 305,69, com multa e juros." in _cobrar_carlos(
        com_carteira, 2
    )
    # Sem a cláusula de juros no contrato (Rafael): "O valor é", sem multa e juros.
    assert financeiro.cobrar(_rafael(com_carteira))
    assert _ultima_mensagem(Cliente.objects.get(nome="Rafael Sousa").celular).endswith(
        "venceu em 12/09. O valor é R$ 1.347,00. Pague na loja ou fale com a gente por aqui."
    )


def test_aut_03_texto_acerto(cenario, com_carteira, relogio, caixas_vazias):  # noqa: F811
    locacao = com_carteira["LOC-2841"]
    (acerto,) = financeiro.criar_contas(
        financeiro.Origem("locacao", locacao.pk, locacao.codigo),
        filial_id=locacao.filial_id,
        cliente_id=locacao.cliente_id,
        contas=[financeiro.NovaConta("acerto", date(2026, 10, 10), 36537)],
    )
    relogio.em("2026-10-09 09:00")
    assert financeiro.cobrar(acerto)
    assert _ultima_mensagem("85985554433") == (
        "Moto Rápida: olá, Carlos. A cobrança de acerto da locação LOC-2841, de R$ 365,37, vence "
        "amanhã, 10/10."
    )
    assert financeiro.conta_no_texto(
        ContaReceber(tipo="outro", origem_tipo="locacao", origem_codigo="LOC-2841")
    ) == ("cobrança da locação LOC-2841")
    assert financeiro.conta_no_texto(
        ContaReceber(tipo="avaria", origem_tipo="venda", origem_codigo="VEN-0177")
    ) == ("cobrança de avaria da venda VEN-0177")


def test_aut_03_email_mesmo_texto(cenario, com_carteira, relogio, caixas_vazias):  # noqa: F811
    Cliente.objects.filter(pk=cenario.clientes["Carlos"].pk).update(email="carlos@exemplo.com")
    relogio.em("2026-10-06 09:00")
    texto = _cobrar_carlos(com_carteira, 3)
    (email,) = mail.outbox
    assert email.subject == "Moto Rápida: lembrete de vencimento"
    assert email.body == texto
    assert email.to == ["carlos@exemplo.com"]
    assert email.from_email.startswith("Moto Rápida <")
    # Uma vez por conta por dia, contando os dois canais.
    assert not financeiro.cobrar(_parcela(com_carteira["LOC-2841"], 3))
    assert len(mail.outbox) == 1

    # Só com e-mail: recebe o e-mail e conta como cobrada (enviadas 1).
    Cliente.objects.filter(pk=cenario.clientes["Carlos"].pk).update(celular="")
    relogio.em("2026-10-07 09:00")
    antes = len(whatsapp.caixa_de_saida)
    resposta = cenario.moto.api("Lúcia").post(
        f"{CONTAS}{_carlos(com_carteira).pk}/cobrar/", format="json"
    )
    assert resposta.json() == {"enviadas": 1}
    assert len(whatsapp.caixa_de_saida) == antes
    assert mail.outbox[-1].subject == "Moto Rápida: conta em atraso"
    # Sem celular e sem e-mail: nada sai, e não conta.
    Cliente.objects.filter(pk=cenario.clientes["Carlos"].pk).update(email="")
    assert not financeiro.cobrar(_parcela(com_carteira["LOC-2841"], 3))


def test_aut_03_cobrar_em_lote_conta_contas(cenario, com_carteira, caixas_vazias):  # noqa: F811
    """Carlos (com e-mail) e Rafael: 2 contas cobradas; de novo no mesmo dia, 0."""
    Cliente.objects.filter(pk=cenario.clientes["Carlos"].pk).update(email="carlos@exemplo.com")
    ids = [_carlos(com_carteira).pk, _rafael(com_carteira).pk]
    api = cenario.moto.api("Lúcia")
    lote = f"{CONTAS}cobrar-em-lote/"
    assert api.post(lote, {"ids": ids}, format="json").json() == {"enviadas": 2}
    assert len(mail.outbox) == 1
    assert api.post(lote, {"ids": ids}, format="json").json() == {"enviadas": 0}


# --- AUT-05: recibo ---


def test_aut_05_recibo_texto(
    cenario,  # noqa: F811
    com_carteira,  # noqa: F811
    recebimentos,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
    caixas_vazias,
):
    _contrato_com_juros(com_carteira["LOC-2841"])
    carlos = _carlos(com_carteira)
    gerada = cenario.moto.api("Lúcia").post(
        f"{CONTAS}{carlos.pk}/cobranca/", {"tipo": "pix"}, format="json"
    )
    cobranca = CobrancaExterna.objects.get(pk=gerada.json()["id"])
    # `criado_em` é a hora real; a multa e os juros são os do dia da cobrança (07 out).
    CobrancaExterna.objects.filter(pk=cobranca.pk).update(criado_em=relogio.agora)
    corpo = pagamentos.simular_pagamento(cobranca.externo_id)
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    assert _ultima_mensagem("85985554433") == (
        "Moto Rápida: recebemos R$ 306,09 por Pix em 07/10, da parcela 2 de 5 da locação "
        "LOC-2841. Este é o seu recibo."
    )
    assert not mail.outbox  # o recibo é só pelo WhatsApp


def test_aut_05_recibo_forma_e_dia(cenario):  # noqa: F811
    conta = ContaReceber(
        tipo="parcela",
        numero_parcela=1,
        total_parcelas=2,
        origem_tipo="locacao",
        origem_codigo="LOC-2856",
        valor_centavos=32900,
        forma="dinheiro",
        pago_em=datetime(2026, 10, 8, 1, 30, tzinfo=UTC),  # 07 out, 22:30 em São Paulo
    )
    assert financeiro.texto_do_recibo(conta) == (
        "Moto Rápida: recebemos R$ 329,00 em dinheiro em 07/10, da parcela 1 de 2 da locação "
        "LOC-2856. Este é o seu recibo."
    )


# --- FIN-15: semana e contagens ---


def test_fin_15_semana_de_segunda_a_domingo(cenario, com_carteira):  # noqa: F811
    """Caso "Contas a receber da semana em 07 out" (05 a 11 out)."""
    corpo = cenario.moto.api("Lúcia").get(CONTAS, {"periodo": "semana"}).json()
    assert corpo["contagens"] == {
        "todas": 36,
        "atrasadas": 2,
        "vencem_hoje": 6,
        "a_vencer": 13,
        "pagas": 15,
    }
    # Os indicadores não seguem o período: são os do mês.
    assert corpo["indicadores"]["previsto_mes_parcelas"] == 128
    api = cenario.moto.api("Lúcia")
    # A busca recorta as contagens; a situação não (T-148).
    busca = api.get(CONTAS, {"busca": "LOC-2841", "situacao": "atrasadas"}).json()
    assert [c["origem"]["codigo"] for c in busca["resultados"]] == ["LOC-2841"]
    assert busca["contagens"]["atrasadas"] == 1
    assert busca["contagens"]["todas"] == len(
        api.get(CONTAS, {"busca": "LOC-2841"}).json()["resultados"]
    )


def test_fin_15_contagens_do_cliente_sem_caucao(cenario):  # noqa: F811
    """Lucas em 07 out (LOC-2856 com a caução de R$ 300,00): a lista do cliente traz a parcela e
    a caução; as contagens, só a parcela. Os indicadores continuam os da filial."""
    api = cenario.moto.api("Lúcia")
    criada = cenario.confirmada(periodos=2)
    lucas = Locacao.objects.get(pk=criada["id"]).cliente_id
    geral = api.get(CONTAS, {"periodo": "semana"}).json()
    corpo = api.get(CONTAS, {"cliente": lucas, "periodo": "semana"}).json()
    assert sorted(c["tipo"] for c in corpo["resultados"]) == ["caucao", "parcela"]
    assert corpo["contagens"]["todas"] == 1
    assert corpo["indicadores"] == geral["indicadores"]
    assert "caucao" not in {c["tipo"] for c in geral["resultados"]}
