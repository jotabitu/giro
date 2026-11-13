"""T-410 · Locação confirmada reserva o veículo e só cobra depois da retirada
(`docs/qa/criterios/T-410.md`, ADR 0035).

Cenário da T-015 (Moto Rápida, Filial Centro). Nos casos de novembro, a locação é nova: semanal
Street, 2 semanas de 05 nov 10:00 a 19 nov 10:00, num veículo Street `disponivel` ("a moto"),
com o Lucas. Padrão A do produto nos três pontos em aberto: o prazo conta da data de início, o
último dia para retirar é o início + 3, e o cliente não recebe aviso.
"""

from datetime import date
from typing import Any

import pytest
from django.conf import settings
from django.core import mail

from apps.auditoria.models import EventoAuditoria
from apps.financeiro import leituras as financeiro_leituras
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber, Reembolso
from apps.locacoes import selectors, services
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from apps.vistorias.models import Vistoria
from comum.documentos import placa_com_hifen

from .test_t015_locacoes import (  # noqa: F401
    Cenario,
    _assinar,
    _contas,
    _pagar,
    _vistoriar,
    cenario,
)

INICIO_05_NOV = "2026-11-05T13:00:00Z"  # 05 nov, 10:00 em Fortaleza
RECEBER = "/api/financeiro/contas-receber/"


@pytest.fixture(autouse=True)
def _tokens_no_relogio(request, relogio_jwt, monkeypatch):
    """O relógio anda até novembro: os tokens seguem o relógio congelado e saem de novo a cada
    mudança, para não vencerem no meio do caso."""
    if "cenario" not in request.fixturenames:
        return
    tokens = request.getfixturevalue("cenario").moto._tokens
    em = relogio_jwt.em

    def em_com_tokens_novos(texto: str) -> Any:
        tokens.clear()
        return em(texto)

    monkeypatch.setattr(relogio_jwt, "em", em_com_tokens_novos)


def _moto(cenario: Cenario) -> Veiculo:  # noqa: F811
    return cenario.veiculo("Street 150–160", exceto=("SAK1D39",))


def _status(veiculo: Veiculo) -> str:
    return Veiculo.objects.get(pk=veiculo.pk).status


def _nova(
    cenario: Cenario,  # noqa: F811
    relogio: Any,
    *,
    confirmada_em: str = "2026-11-04 10:00",
    inicio: str = INICIO_05_NOV,
    veiculo: Veiculo | None = None,
) -> dict[str, Any]:
    relogio.em(confirmada_em)
    criada = cenario.confirmada(veiculo=veiculo or _moto(cenario), inicio=inicio, periodos=2)
    # O `criado_em` das contas vem do relógio real (`auto_now_add`), e a FIN-03 conta o atraso
    # também do dia em que a conta nasceu. Sem isto, desde 13 nov 2026 (o dia real passou o da
    # cena) a parcela 2 "nascia" depois do vencimento e não atrasava (T-410, CI da develop).
    # Como o resto da suíte (t148, t202): a conta nasce na hora do relógio dos testes.
    ContaReceber.objects.filter(origem_tipo="locacao", origem_id=criada["id"]).update(
        criado_em=relogio.agora
    )
    return criada


def _ficha(cenario: Cenario, veiculo: Veiculo, quem: str = "Rodrigo") -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(f"/api/veiculos/{veiculo.pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


# --- Reserva na confirmação ---


def test_vei_reserva_na_confirmacao(cenario, relogio):  # noqa: F811
    """CA-410-01, 04 e 05: o rascunho não reserva; a confirmação com início hoje reserva na
    hora, com "Reservado na LOC-x", e a moto sai da Nova locação de outro cliente."""
    moto = _moto(cenario)
    relogio.em("2026-11-05 09:00")
    criada = cenario.criar(veiculo=moto, inicio=INICIO_05_NOV, periodos=2)
    assert _status(moto) == "disponivel"  # CA-410-04
    juliana = {"cliente": "Juliana", "veiculo": moto, "inicio": INICIO_05_NOV}
    assert cenario.simular(**juliana).json()["impedimentos"] == []

    resposta = cenario.confirmar(criada["id"])
    assert resposta.status_code == 200, resposta.json()
    codigo = resposta.json()["codigo"]
    assert _status(moto) == "reservado"
    ultima = Veiculo.objects.get(pk=moto.pk).historico.last()
    assert ultima is not None and ultima.motivo == f"Reserva da {codigo}"

    ficha = _ficha(cenario, moto)
    assert ficha["situacao"] == {
        "codigo": "reservado",
        "rotulo": f"Reservado na {codigo}",
        "tom": "info",
        "desde": "2026-11-05",  # LOC-10 (T-449): o início da locação que reservou
    }
    assert ficha["reserva"] == {"locacao_id": criada["id"], "codigo": codigo, "motivo": "locacao"}
    linha = cenario.moto.api("Rodrigo").get("/api/veiculos/", {"busca": moto.placa}).json()
    assert linha["resultados"][0]["situacao"]["rotulo"] == f"Reservado na {codigo}"
    assert ficha["acoes"]["movimentar"] is False  # MOV-03

    # CA-410-05: outro cliente não leva a moto reservada.
    outra = cenario.simular(**juliana).json()
    assert [i["codigo"] for i in outra["impedimentos"]] == ["LOC-03"]
    segunda = cenario.criar(cliente="Juliana", veiculo=moto, inicio=INICIO_05_NOV)
    recusa = cenario.confirmar(segunda["id"])
    assert (recusa.status_code, recusa.json()["codigo"]) == (409, "LOC-03")


@pytest.mark.parametrize(
    ("hoje", "inicio"),
    [("2026-11-06 09:00", INICIO_05_NOV), ("2026-11-01 09:00", "2026-11-05T13:00:00Z")],
)
def test_vei_reserva_com_inicio_passado_ou_futuro(cenario, relogio, hoje, inicio):  # noqa: F811
    """CA-410-02 (início no passado, dentro do prazo) e CA-410-03 (início futuro)."""
    moto = _moto(cenario)
    _nova(cenario, relogio, confirmada_em=hoje, inicio=inicio, veiculo=moto)
    assert _status(moto) == "reservado"


# --- Nada vence antes da retirada ---


def test_loc_05_nada_vence_antes_da_retirada(cenario, relogio):  # noqa: F811
    """CA-410-07 e 08: parcela 1 com vencimento em 05 nov e caução, não retirada. Nem no dia do
    vencimento gravado, nem depois, ficam `vence_hoje` ou `atrasada`: Receber, painel, régua,
    análise do cliente, lista de locações e ficha do veículo."""
    moto = _moto(cenario)
    criada = _nova(cenario, relogio, veiculo=moto)
    contas = _contas(criada["id"])
    assert all(c.aguarda_retirada for c in contas)
    parcela_1 = next(c for c in contas if c.tipo == "parcela" and c.numero_parcela == 1)
    assert parcela_1.vencimento == date(2026, 11, 5)

    for momento in ("2026-11-05 12:00", "2026-11-06 10:00"):
        relogio.em(momento)
        detalhe = cenario.detalhe(criada["id"], "Rodrigo")
        assert {p["status"] for p in detalhe["parcelas"]} == {"aberta"}
        assert detalhe["sinais"]["pagamento_atrasado"] is False
        receber = cenario.moto.api("Rodrigo").get(RECEBER, {"origem_tipo": "locacao"}).json()
        indicadores = receber["indicadores"]
        assert indicadores["em_atraso_parcelas"] == 0
        assert indicadores["vence_hoje_parcelas"] == 0
        assert receber["contagens"]["atrasadas"] == 0
        assert receber["contagens"]["vencem_hoje"] == 0
        conta = next(c for c in receber["resultados"] if c["id"] == parcela_1.pk)
        assert (conta["status"], conta["aguarda_retirada"], conta["dias_atraso"]) == (
            "aberta",
            True,
            0,
        )
        assert conta["valor_hoje"]["multa_centavos"] == 0
        assert financeiro.regua_de_cobranca() == 0
        assert not EventoAuditoria.objects.filter(acao="conta_receber.cobrar").exists()
        assert financeiro_leituras.montar_historico(cenario.cliente("Lucas"))["situacao"] == "ok"
        assert (
            financeiro_selectors.atrasadas([moto.filial_id], relogio.agora.date()).quantidade == 0
        )
        pagamento = _ficha(cenario, moto)["locacao_atual"]["pagamento"]
        assert pagamento["situacao"] == "em_dia"


def test_fin_03_retirada_sem_multa(cenario, relogio):  # noqa: F811
    """CA-410-09 e 10: retirada em 07 nov, dois dias depois do vencimento gravado da parcela 1:
    R$ 629,00 sem multa nem juros. Dali em diante, o calendário de sempre: a parcela 2 vence em
    12 nov e atrasa em 13 nov."""
    moto = _moto(cenario)
    criada = _nova(cenario, relogio, veiculo=moto)
    relogio.em("2026-11-07 10:00")
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    pagas = [c for c in _contas(criada["id"]) if c.status == "paga"]
    assert sum(c.valor_centavos for c in pagas) == 62900
    assert all(c.multa_centavos == 0 and c.juros_centavos == 0 for c in pagas)
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"
    assert _status(moto) == "alugado"
    contas = _contas(criada["id"])
    assert all(not c.aguarda_retirada and c.liberada_em == date(2026, 11, 7) for c in contas)

    detalhe = cenario.detalhe(criada["id"], "Rodrigo")
    assert detalhe["fim_previsto"].startswith("2026-11-19")
    parcela_2 = next(c for c in contas if c.numero_parcela == 2)
    assert parcela_2.vencimento == date(2026, 11, 12)
    relogio.em("2026-11-13 10:00")
    detalhe = cenario.detalhe(criada["id"], "Rodrigo")
    assert next(p for p in detalhe["parcelas"] if p["numero"] == 2)["status"] == "atrasada"
    assert detalhe["sinais"]["pagamento_atrasado"] is True
    # Liberada na retirada, o atraso conta como sempre (FIN-03).
    assert financeiro_selectors.devido_ate(parcela_2, date(2026, 11, 13)).dias_atraso == 1


# --- Prazo para retirar e cancelamento automático ---


def test_loc_12_inicio_vencido(cenario, relogio):  # noqa: F811
    """CA-410-18: em 09 nov, o início em 05 nov passou de 3 dias. A simulação mostra o
    impedimento, e a confirmação recusa com 409 `inicio_vencido` sem mexer em nada."""
    moto = _moto(cenario)
    relogio.em("2026-11-09 09:00")
    simulada = cenario.simular(veiculo=moto, inicio=INICIO_05_NOV).json()
    assert {"codigo": "inicio_vencido", "mensagem": services.INICIO_VENCIDO} in simulada[
        "impedimentos"
    ]
    criada = cenario.criar(veiculo=moto, inicio=INICIO_05_NOV)
    recusa = cenario.confirmar(criada["id"])
    assert recusa.status_code == 409, recusa.json()
    assert recusa.json()["codigo"] == "inicio_vencido"
    assert recusa.json()["mensagem"] == (
        "O início passou de 3 dias. Mude a data de início para confirmar."
    )
    assert recusa.json()["detalhes"] == {
        "inicio": "2026-11-05",
        "ultimo_dia_retirada": "2026-11-08",
    }
    assert Locacao.objects.get(pk=criada["id"]).status == "rascunho"
    assert not ContaReceber.objects.filter(origem_id=criada["id"]).exists()
    assert _status(moto) == "disponivel"
    # Com início em 06 nov, o último dia é 09 nov: passa.
    no_prazo = cenario.simular(veiculo=moto, inicio="2026-11-06T13:00:00Z").json()
    assert all(i["codigo"] != "inicio_vencido" for i in no_prazo["impedimentos"])


def test_loc_12_cancelamento_automatico(cenario, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-410-13, 14 e 21: início em 05 nov (com 07 nov de feriado, que conta), 1ª parcela e
    caução pagas, vistoria de saída em rascunho e sem assinatura. Aviso ao gerente em 08 nov
    08:00, uma vez; cancelada pelo Sistema em 09 nov 00:10."""
    moto = _moto(cenario)
    criada = _nova(cenario, relogio, veiculo=moto)
    locacao = Locacao.objects.get(pk=criada["id"])
    assert selectors.ultimo_dia_retirada(locacao) == date(2026, 11, 8)
    assert cenario.detalhe(criada["id"])["prazo_retirada"] == {
        "ultimo_dia": "2026-11-08",
        "cancela_em": "2026-11-09",
    }
    _pagar(criada["id"])
    rascunho = Vistoria.objects.create(locacao=locacao, veiculo=moto, tipo="saida")

    relogio.em("2026-11-07 08:00")
    assert services.avisar_nao_retiradas() == 0
    relogio.em("2026-11-08 08:00")
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        assert services.avisar_nao_retiradas() == 1
    rodrigo = cenario.pessoas["Rodrigo"]
    texto = (
        f"A {criada['codigo']} será cancelada amanhã se não for retirada hoje. "
        f"{moto.marca} {moto.modelo} {placa_com_hifen(moto.placa)}, cliente Lucas Ferreira."
    )
    aviso = Notificacao.objects.get(tipo="locacao_nao_retirada")
    assert (aviso.destinatario_id, aviso.titulo, aviso.link, aviso.urgente) == (
        rodrigo.pk,
        texto,
        f"/locacoes/{criada['id']}",
        True,
    )
    assert [(m.to, m.subject) for m in mail.outbox] == [([rodrigo.email], texto)]
    with django_capture_on_commit_callbacks(execute=True):
        assert services.avisar_nao_retiradas() == 0  # uma vez só
    assert len(mail.outbox) == 1
    assert services.cancelar_nao_retiradas() == 0  # ainda no prazo

    relogio.em("2026-11-09 00:10")
    with django_capture_on_commit_callbacks(execute=True):
        assert services.cancelar_nao_retiradas() == 1
    locacao.refresh_from_db()
    assert locacao.status == "cancelada"
    assert locacao.motivo_cancelamento == "Não retirada em 3 dias da data de início"
    evento = EventoAuditoria.objects.get(
        objeto_tipo="locacao", objeto_id=locacao.pk, acao="locacao.cancelar_nao_retirada"
    )
    assert (evento.ator_tipo, evento.regra) == ("sistema", "LOC-12")
    contas = ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk)
    assert not contas.filter(status="aberta").exists()
    reembolso = Reembolso.objects.get(origem_tipo="locacao", origem_id=locacao.pk)
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status) == (
        62900,
        "pix",
        "a_fazer",
    )
    rascunho.refresh_from_db()
    assert rascunho.status == "descartada"
    assert _status(moto) == "disponivel"
    livre = cenario.simular(cliente="Juliana", veiculo=moto, inicio="2026-11-10T13:00:00Z")
    assert livre.json()["impedimentos"] == []
    cancelamento = cenario.detalhe(criada["id"], "Rodrigo")["cancelamento"]
    assert cancelamento["automatico"] is True
    assert (cancelamento["multa_centavos"], cancelamento["devolver_centavos"]) == (0, 62900)
    assert services.cancelar_nao_retiradas() == 0  # a cancelada sai da seleção


def test_loc_12_retirada_no_ultimo_dia_nao_cai(cenario, relogio):  # noqa: F811
    """CA-410-15 e 20: retirada em 08 nov 23:00, a locação vira `ativa` e não cai em 09 nov."""
    criada = _nova(cenario, relogio)
    relogio.em("2026-11-08 23:00")
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    relogio.em("2026-11-09 00:10")
    assert services.cancelar_nao_retiradas() == 0
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"


def test_aut_17_execucao_perdida(cenario, relogio):  # noqa: F811
    """CA-410-19: sem a execução de 09 nov, a locação cai em 10 nov 00:10, uma vez só, e o aviso
    do dia perdido não sai depois."""
    criada = _nova(cenario, relogio)
    relogio.em("2026-11-10 00:10")
    assert services.cancelar_nao_retiradas() == 1
    assert services.cancelar_nao_retiradas() == 0
    relogio.em("2026-11-10 08:00")
    assert services.avisar_nao_retiradas() == 0
    assert Locacao.objects.get(pk=criada["id"]).status == "cancelada"
    assert not Notificacao.objects.filter(tipo="locacao_nao_retirada").exists()


def test_aut_17_aviso_uma_vez(cenario, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    """CA-410-16 e 17: com início futuro (10 nov, confirmada em 01 nov), nada antes de 13 nov; o
    aviso sai em 13 nov 08:00 e a queda em 14 nov 00:10. Confirmada no próprio último dia depois
    das 08:00, o aviso sai na confirmação, e a tarefa não repete."""
    futura = _nova(
        cenario, relogio, confirmada_em="2026-11-01 10:00", inicio="2026-11-10T13:00:00Z"
    )
    relogio.em("2026-11-12 08:00")
    assert services.avisar_nao_retiradas() == 0
    relogio.em("2026-11-13 00:10")
    assert services.cancelar_nao_retiradas() == 0
    relogio.em("2026-11-13 08:00")
    assert services.avisar_nao_retiradas() == 1
    relogio.em("2026-11-14 00:10")
    assert services.cancelar_nao_retiradas() == 1
    assert Locacao.objects.get(pk=futura["id"]).status == "cancelada"

    moto = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    relogio.em("2026-11-08 15:00")
    criada = cenario.criar(cliente="Juliana", veiculo=moto, inicio=INICIO_05_NOV)
    with django_capture_on_commit_callbacks(execute=True):
        assert cenario.confirmar(criada["id"]).status_code == 200
    chave = f"aut17-aviso-{criada['id']}"
    assert Notificacao.objects.filter(chave=chave).count() == 1
    assert services.avisar_nao_retiradas() == 0


def test_loc_12_cancelamento_pedido_descarta_a_saida(
    cenario,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    """ADR 0035, item 5: o cancelamento pedido antes da retirada também descarta a vistoria de
    saída em rascunho, pelo evento `locacoes.locacao_cancelada`."""
    moto = _moto(cenario)
    criada = _nova(cenario, relogio, veiculo=moto)
    locacao = Locacao.objects.get(pk=criada["id"])
    rascunho = Vistoria.objects.create(locacao=locacao, veiculo=moto, tipo="saida")
    with django_capture_on_commit_callbacks(execute=True):
        services.cancelar(locacao, cenario.pessoas["Rodrigo"], motivo="Cliente desistiu")
    rascunho.refresh_from_db()
    assert rascunho.status == "descartada"
    assert cenario.detalhe(criada["id"], "Rodrigo")["cancelamento"]["automatico"] is False


# --- Acerto do ambiente e tarefas ---


def test_loc_05_acerto_das_reservas_antigas(cenario, relogio):  # noqa: F811
    """CA-410-23: a locação `aguardando_retirada` de antes da T-410 (contas sem a espera e o
    veículo `disponivel`) é acertada pelo comando, e a segunda vez não muda nada."""
    moto = _moto(cenario)
    criada = _nova(cenario, relogio, veiculo=moto)
    ContaReceber.objects.filter(origem_id=criada["id"]).update(aguarda_retirada=False)
    veiculos_services.transicionar(
        Veiculo.objects.get(pk=moto.pk),
        "disponivel",
        origem=veiculos_services.OrigemDaMudanca("seed", 0, "seed"),
        motivo="Como antes da T-410",
    )
    relogio.em("2026-11-06 10:00")
    assert cenario.detalhe(criada["id"], "Rodrigo")["sinais"]["pagamento_atrasado"] is True

    abertas = ContaReceber.objects.filter(origem_id=criada["id"], status="aberta").count()
    assert services.acertar_reservas_t410() == (abertas, 1)
    assert services.acertar_reservas_t410() == (0, 0)
    assert _status(moto) == "reservado"
    assert cenario.detalhe(criada["id"], "Rodrigo")["sinais"]["pagamento_atrasado"] is False
    assert _ficha(cenario, moto)["situacao"]["rotulo"] == f"Reservado na {criada['codigo']}"


def test_aut_17_tarefas_no_beat():
    """AUT-17: cancelamento às 00:10 e aviso às 08:00, uma tarefa por empresa."""
    agenda = settings.CELERY_BEAT_SCHEDULE
    cancelar = agenda["aut_17_cancelar_nao_retiradas"]
    avisar = agenda["aut_17_avisar_nao_retiradas"]
    assert cancelar["task"] == "aut_17_cancelar_nao_retiradas_de_todas"
    assert avisar["task"] == "aut_17_avisar_nao_retiradas_de_todas"
    assert (cancelar["schedule"].hour, cancelar["schedule"].minute) == ({0}, {10})
    assert (avisar["schedule"].hour, avisar["schedule"].minute) == ({8}, {0})
