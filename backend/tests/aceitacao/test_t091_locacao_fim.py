"""T-091 · Locação: renovação, atraso, cancelamento e encerramento (docs/qa/criterios/T-015.md,
CA-015-16 da LOC-2812, 17, 19 a 24 e o estorno do 25).

Cenário da T-015: Moto Rápida em 07 out 2026, 10:00, Filial Centro (seg a sex 8h–18h, sáb
8h–12h), com a carteira de outubro quando o caso é do seed. O atraso do CA-015-19 é contado a
partir do `fim_previsto` da própria locação, e não de uma data fixa (o fim da LOC-2836 muda com a
T-104).
"""

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.contratos import services as contratos
from apps.contratos.models import Contrato
from apps.filiais.models import FeriadoFilial
from apps.financeiro import services as financeiro
from apps.financeiro.models import Comissao, ContaReceber, Reembolso
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes import selectors, services
from apps.locacoes.models import Locacao
from apps.locacoes.tasks import aut_02_marcar_devolucao_atrasada
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa
from apps.veiculos.models import Veiculo
from comum.erros import TransicaoInvalida

from . import carteira
from .frota import montar_frota
from .test_t012_filiais import MotoRapida
from .test_t015_locacoes import LISTA, Cenario, _assinar, _decidir, _linha, _pagar, _vistoriar

FUSO = ZoneInfo("America/Sao_Paulo")
STREET_DIARIA = 5490
NMAX_DIARIA = 7990
DIA_TODO = {
    d: [{"abre": "08:00", "fecha": "22:00"}]
    for d in ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
}


def _ativa(cenario: Cenario, **campos: Any) -> dict[str, Any]:
    """Confirmada e retirada (vistoria, contrato e 1º pagamento): `ativa`."""
    criada = cenario.confirmada(**campos)
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    detalhe = cenario.detalhe(criada["id"])
    assert detalhe["status"] == "ativa"
    return detalhe


def _local(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=FUSO)


def _parcelas(locacao_id: int) -> list[ContaReceber]:
    return list(
        ContaReceber.objects.filter(
            origem_tipo="locacao", origem_id=locacao_id, tipo="parcela"
        ).order_by("numero_parcela")
    )


def _cancelar(cenario: Cenario, locacao_id: int, quem: str, **corpo: Any) -> Any:
    return cenario.moto.api(quem).post(
        f"{LISTA}{locacao_id}/cancelar/", {"motivo": "Cliente desistiu", **corpo}, format="json"
    )


def _simular_cancelamento(cenario: Cenario, locacao_id: int, data: str) -> dict[str, Any]:
    resposta = cenario.moto.api("Bruna").post(
        f"{LISTA}{locacao_id}/cancelamento/simular/", {"data": data}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


@pytest.fixture
def cenario(empresa_a, planos, relogio) -> Cenario:
    """O cenário da T-015 (`test_t015_locacoes.py`)."""
    locacoes_leituras.registrar()
    moto = MotoRapida(empresa_a, planos["Profissional"])
    return Cenario(moto, montar_frota(moto))


@pytest.fixture
def com_carteira(cenario, relogio) -> dict[str, Locacao]:
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"], relogio)


@pytest.fixture
def patricia(cenario, com_carteira) -> Locacao:
    """LOC-2812: NMax mensal de 159000, de 15 set a 15 out (seed), com a diária da Scooter."""
    locacao = com_carteira["LOC-2812"]
    locacao.diaria_centavos = NMAX_DIARIA
    locacao.save(update_fields=["diaria_centavos"])
    assert (locacao.periodicidade, locacao.valor_periodo_centavos) == ("mensal", 159000)
    return locacao


# --- CA-015-17 · Renovação (LOC-08, LOC-15) ---


def test_loc_08_ca_015_17_renovacao(
    cenario, com_carteira, relogio, django_capture_on_commit_callbacks
):
    carlos = com_carteira["LOC-2841"]
    fim_antes = carlos.fim_previsto
    antigas = [p.valor_centavos for p in _parcelas(carlos.pk)]
    assert set(antigas) == {29940}
    comissoes = Comissao.objects.count()
    api = cenario.moto.api("Bruna")

    simulacao = api.post(f"{LISTA}{carlos.pk}/renovar/simular/", {"periodos": 2}, format="json")
    assert simulacao.status_code == 200, simulacao.json()
    assert [p["valor_centavos"] for p in simulacao.json()["parcelas_novas"]] == [32900, 32900]
    assert not Contrato.objects.exists()  # simular não grava

    with django_capture_on_commit_callbacks(execute=True):
        resposta = api.post(f"{LISTA}{carlos.pk}/renovar/", {"periodos": 2}, format="json")
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["codigo"] == "LOC-2841" and corpo["status"] == "ativa"
    carlos.refresh_from_db()
    assert carlos.fim_previsto - fim_antes == timedelta(days=14)
    assert carlos.renovacoes == 1 and carlos.valor_periodo_centavos == 32900
    parcelas = _parcelas(carlos.pk)
    assert [p.valor_centavos for p in parcelas] == [*antigas, 32900, 32900]
    novas = parcelas[-2:]
    assert [p.vencimento for p in novas] == [date(2026, 10, 28), date(2026, 11, 4)]
    assert [(p.numero_parcela, p.total_parcelas) for p in novas] == [(6, 7), (7, 7)]
    assert Locacao.objects.filter(codigo__startswith="LOC-").count() == len(com_carteira)
    assert Comissao.objects.count() == comissoes  # FIN-09: renovação não gera comissão

    aditivo = Contrato.objects.get(origem_id=carlos.pk, tipo="aditivo")
    assert aditivo.status == "enviado"  # vale na hora, sem esperar a assinatura
    relogio.em("2026-10-13 10:00")
    assert contratos.avisar_aditivos_sem_assinatura() == 0
    relogio.em("2026-10-14 10:00")
    assert contratos.avisar_aditivos_sem_assinatura() == 1
    aviso = Notificacao.objects.get(tipo="aditivo_sem_assinatura")
    assert aviso.destinatario_id == cenario.pessoas["Rodrigo"].pk
    assert aviso.titulo == "Aditivo da LOC-2841 sem assinatura há 7 dias"


def test_loc_08_ca_015_17_renovar_encerrada_responde_409(cenario):
    detalhe = _ativa(cenario)
    assert detalhe["acoes"]["renovar"] is True
    services.encerrar(Locacao.objects.get(pk=detalhe["id"]))
    resposta = cenario.moto.api("Bruna").post(
        f"{LISTA}{detalhe['id']}/renovar/", {"periodos": 1}, format="json"
    )
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "transicao_locacao"


def test_loc_08_renovar_devolucao_atrasada_volta_a_ativa_e_guarda_o_atraso(cenario, relogio):
    detalhe = _ativa(cenario)
    locacao = Locacao.objects.get(pk=detalhe["id"])
    centro = locacao.filial
    centro.horario = DIA_TODO
    centro.save(update_fields=["horario"])
    fim = locacao.fim_previsto.astimezone(FUSO)
    relogio.em((fim + timedelta(days=2, hours=2)).strftime("%Y-%m-%d %H:%M"))
    assert services.marcar_devolucoes_atrasadas() == 1
    services.renovar(locacao, {"periodos": 1}, cenario.pessoas["Bruna"])
    assert locacao.status == "ativa"
    assert (locacao.atraso_anterior_dias, locacao.atraso_anterior_centavos) == (
        3,
        3 * STREET_DIARIA,
    )
    assert services.calcular_atraso(locacao)["valor_centavos"] == 3 * STREET_DIARIA


# --- CA-015-19 · Tolerância e diárias (LOC-10, AUT-02) ---


def test_loc_10_ca_015_19_tolerancia_e_diarias(cenario, relogio):
    """Filial aberta das 8h às 22h todo dia, para o atraso valer sem o LOC-11 (CA-015-20)."""
    detalhe = _ativa(cenario)
    locacao = Locacao.objects.get(pk=detalhe["id"])
    locacao.filial.horario = DIA_TODO
    locacao.filial.save(update_fields=["horario"])
    fim = locacao.fim_previsto.astimezone(FUSO).replace(hour=18, minute=0)
    locacao.fim_previsto = fim
    locacao.save(update_fields=["fim_previsto"])
    assert locacao.diaria_centavos == STREET_DIARIA

    casos = {
        timedelta(hours=1): (0, 0),  # dentro da tolerância
        timedelta(hours=1, minutes=1): (1, 5490),  # fração conta como dia
        timedelta(hours=23, minutes=59): (1, 5490),
        timedelta(hours=24, minutes=1): (2, 10980),
    }
    for depois, (dias, valor) in casos.items():
        atraso = selectors.calcular_atraso(locacao, fim + depois)
        assert (atraso["dias"], atraso["valor_centavos"]) == (dias, valor), depois

    relogio.em(fim.replace(hour=23, minute=59).strftime("%Y-%m-%d %H:%M"))
    aut_02_marcar_devolucao_atrasada("empresa_a")
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    locacao.refresh_from_db()
    assert locacao.status == "ativa"  # até 23:59 do dia do fim previsto

    relogio.em((fim + timedelta(days=1)).replace(hour=0).strftime("%Y-%m-%d %H:%M"))
    aut_02_marcar_devolucao_atrasada("empresa_a")
    aut_02_marcar_devolucao_atrasada("empresa_a")  # idempotente
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_a"))
    locacao.refresh_from_db()
    assert locacao.status == "devolucao_atrasada"
    evento = EventoAuditoria.objects.get(
        objeto_tipo="locacao", objeto_id=locacao.pk, acao="locacao.marcar_atraso"
    )
    assert evento.regra == "LOC-10"


# --- CA-015-20 · Filial fechada e feriado (LOC-11, FIL-03) ---


def test_loc_11_ca_015_20_filial_fechada_e_feriado(cenario):
    detalhe = _ativa(cenario)
    locacao = Locacao.objects.get(pk=detalhe["id"])
    assert locacao.filial.horario["sab"] == [{"abre": "08:00", "fecha": "12:00"}]
    domingo = _local("2026-10-11 10:00")
    segunda_8h = _local("2026-10-12 08:00")

    # Fecha às 12:00, antes de a tolerância acabar (12:30): a devolução de domingo vale segunda.
    atraso = services.atraso_desde(locacao, _local("2026-10-10 11:30"), domingo)
    assert (atraso.dias, atraso.valor_centavos) == (0, 0)
    assert atraso.devolucao_considerada_em == segunda_8h

    # A tolerância acabou às 11:00, antes do fechamento: 46 h até segunda às 8h.
    atraso = services.atraso_desde(locacao, _local("2026-10-10 10:00"), domingo)
    assert (atraso.dias, atraso.valor_centavos) == (2, 10980)

    # Segunda, 12 out, feriado da Filial Centro: vale terça às 8h, e o feriado não soma atraso.
    FeriadoFilial.objects.create(
        filial=locacao.filial, data=date(2026, 10, 12), nome="Feriado local", origem="local"
    )
    atraso = services.atraso_desde(locacao, _local("2026-10-10 10:00"), domingo)
    assert atraso.devolucao_considerada_em == _local("2026-10-13 08:00")
    assert (atraso.dias, atraso.valor_centavos) == (2, 10980)

    # Fim previsto no feriado: pode devolver na abertura seguinte sem atraso.
    atraso = services.atraso_desde(locacao, _local("2026-10-12 10:00"), _local("2026-10-13 08:30"))
    assert atraso.dias == 0


# --- CA-015-21 · Patrícia, LOC-2812 (LOC-12, LOC-13, APR-02) e CA-015-16 ---


def test_loc_12_loc_13_ca_015_21_patricia_loc_2812(cenario, patricia):
    simulacao = _simular_cancelamento(cenario, patricia.pk, "2026-10-07")
    assert simulacao == {
        "antes_da_retirada": False,
        "periodo_atual": {"inicio": "2026-09-15", "fim": "2026-10-15", "dias": 30},
        "dias_restantes": 8,
        "valor_restante_centavos": 42400,
        "multa_centavos": 8480,
        "credito_semanas": {"semanas": 1, "valor_centavos": 37100},
        "credito_dias": {"dias": 0, "valor_centavos": 0},
        "parcelas_canceladas_centavos": 0,
        "devolver_centavos": 28620,
        "cobrar_centavos": 0,
        "avisos": [],
    }

    resposta = _cancelar(cenario, patricia.pk, "Bruna")
    assert resposta.status_code == 202, resposta.json()
    pedido = resposta.json()["pedido_aprovacao"]
    assert (pedido["tipo"], pedido["status"]) == ("APR-02", "pendente")
    detalhe = cenario.detalhe(patricia.pk)
    assert detalhe["sinais"]["cancelamento_pendente"] is True
    assert detalhe["cancelamento"]["status"] == "pendente"
    assert detalhe["cancelamento"]["multa_centavos"] == 8480
    assert detalhe["cancelamento"]["devolver_centavos"] == 28620
    assert detalhe["acoes"]["cancelar"] is False and detalhe["acoes"]["renovar"] is False

    resposta = _decidir(cenario, "Rodrigo", pedido["id"], "aprovar")
    assert resposta.status_code == 200, resposta.json()
    detalhe = cenario.detalhe(patricia.pk)
    assert detalhe["status"] == "ativa"  # segue para a devolução
    assert detalhe["sinais"]["cancelamento_pendente"] is False
    assert detalhe["cancelamento"]["status"] == "aprovado"
    assert detalhe["cancelamento"]["antes_da_retirada"] is False
    patricia.refresh_from_db()
    assert patricia.encerramento_antecipado_aprovado_em is not None
    assert (patricia.multa_encerramento_centavos, patricia.credito_encerramento_centavos) == (
        8480,
        37100,
    )

    services.encerrar(patricia)  # a devolução (T-016) chama
    assert patricia.status == "cancelada"
    assert patricia.devolvida_em is not None


def test_apr_02_ca_015_16_loc_2812_cancelamento_pendente(cenario, patricia):
    assert _cancelar(cenario, patricia.pk, "Bruna").status_code == 202
    corpo = cenario.moto.api("Rodrigo").get(LISTA, {"tamanho": 100}).json()
    linha = _linha(corpo, "LOC-2812")
    assert linha["sinais"]["cancelamento_pendente"] is True
    assert linha["situacao"]["codigo"] == "cancelamento_pendente"
    assert linha["pagamento"]["rotulo"] == "Multa R$ 84,80"
    acao = cenario.moto.api("Rodrigo").get(LISTA, {"aba": "precisam_acao"}).json()
    assert "LOC-2812" in {x["codigo"] for x in acao["resultados"]}


def test_apr_02_ca_015_21_gerente_cancela_direto(cenario, patricia):
    resposta = _cancelar(cenario, patricia.pk, "Rodrigo")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["cancelamento"]["status"] == "aprovado"
    assert not PedidoAprovacao.objects.filter(tipo="APR-02").exists()


def test_apr_02_recusado_apaga_o_sinal_e_avisa(cenario, patricia):
    pedido = _cancelar(cenario, patricia.pk, "Bruna").json()["pedido_aprovacao"]
    resposta = _decidir(cenario, "Rodrigo", pedido["id"], "recusar", "Cliente vai ficar")
    assert resposta.status_code == 200, resposta.json()
    detalhe = cenario.detalhe(patricia.pk)
    assert detalhe["sinais"]["cancelamento_pendente"] is False
    assert detalhe["cancelamento"] is None and detalhe["status"] == "ativa"
    aviso = Notificacao.objects.get(tipo="cancelamento_recusado")
    assert aviso.destinatario_id == cenario.pessoas["Bruna"].pk
    assert aviso.titulo == "Cancelamento da LOC-2812 recusado: Cliente vai ficar"


def test_apr_02_vistoriador_nao_cancela(cenario, patricia):
    assert _cancelar(cenario, patricia.pk, "João").status_code == 403


# --- CA-015-22 · Antes da retirada, sem multa ---


def test_loc_12_ca_015_22_antes_da_retirada_sem_multa(cenario):
    # Retirada amanhã: o SAK1D39 fica reservado.
    criada = cenario.confirmada(inicio="2026-10-08T15:30:00Z")
    assert criada["codigo"] == "LOC-2856" and criada["status"] == "aguardando_retirada"
    _pagar(criada["id"])  # 1ª semana e caução: 62900
    assert Veiculo.objects.get(placa="SAK1D39").status == "reservado"
    simulacao = _simular_cancelamento(cenario, criada["id"], "2026-10-07")
    assert simulacao["antes_da_retirada"] is True
    assert (simulacao["multa_centavos"], simulacao["devolver_centavos"]) == (0, 62900)

    resposta = _cancelar(cenario, criada["id"], "Rodrigo")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "cancelada"
    assert resposta.json()["cancelamento"]["antes_da_retirada"] is True
    reembolso = Reembolso.objects.get(origem_tipo="locacao", origem_id=criada["id"])
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status) == (
        62900,
        "pix",
        "a_fazer",
    )
    assert Veiculo.objects.get(placa="SAK1D39").status == "disponivel"
    comissao = Comissao.objects.get(origem_tipo="locacao", origem_id=criada["id"])
    assert comissao.status == "estornada"  # CA-015-25
    assert Notificacao.objects.filter(
        tipo="reembolso_a_fazer", destinatario=cenario.pessoas["Rodrigo"]
    ).exists()

    imagem = BytesIO()
    from PIL import Image

    Image.new("RGB", (4, 4)).save(imagem, format="PNG")
    comprovante = SimpleUploadedFile("pix.png", imagem.getvalue(), content_type="image/png")
    financeiro.marcar_reembolso_feito(
        reembolso, usuario=cenario.pessoas["Rodrigo"], comprovante=comprovante
    )
    assert reembolso.status == "feito" and reembolso.feito_em is not None
    assert reembolso.comprovante.name


def test_loc_12_ca_015_22_vendedor_pede_e_parcela_aberta_cancela(cenario):
    criada = cenario.confirmada(periodos=2)
    pedido = _cancelar(cenario, criada["id"], "Bruna").json()["pedido_aprovacao"]
    assert _decidir(cenario, "Rodrigo", pedido["id"], "aprovar").status_code == 200
    detalhe = cenario.detalhe(criada["id"])
    assert detalhe["status"] == "cancelada"
    assert not ContaReceber.objects.filter(origem_id=criada["id"], status="aberta").exists()
    assert not Reembolso.objects.exists()  # nada pago, nada a devolver


# --- CA-015-23 · Multa mínima e casos de borda ---


def test_loc_12_ca_015_23_multa_minima_street(cenario):
    street = _ativa(cenario)  # semanal 32900, de 07 a 14 out
    simulacao = _simular_cancelamento(cenario, street["id"], "2026-10-13")
    assert simulacao["dias_restantes"] == 1
    assert simulacao["valor_restante_centavos"] == 4700  # 20% = 940, abaixo da diária
    assert simulacao["multa_centavos"] == STREET_DIARIA
    assert simulacao["cobrar_centavos"] == STREET_DIARIA


def test_loc_12_ca_015_23_multa_minima_nmax_mensal(cenario, patricia):
    nmax = _simular_cancelamento(cenario, patricia.pk, "2026-10-09")
    assert nmax["dias_restantes"] == 6
    assert nmax["credito_semanas"] == {"semanas": 0, "valor_centavos": 0}
    assert nmax["valor_restante_centavos"] == 31800
    # 20% de 31800 = 6360, abaixo da diária da NMax: vale o mínimo de 1 diária da LOC-12.
    assert nmax["multa_centavos"] == NMAX_DIARIA
    assert nmax["cobrar_centavos"] == NMAX_DIARIA


def test_loc_12_ca_015_23_diaria_sem_multa_cobra_so_os_dias_usados(cenario):
    diaria = _ativa(cenario, periodicidade="diaria", periodos=5)
    simulacao = _simular_cancelamento(cenario, diaria["id"], "2026-10-09")
    assert simulacao["multa_centavos"] == 0
    # Fim previsto em 12 out: 3 diárias não usadas voltam ao cliente.
    assert simulacao["credito_dias"] == {"dias": 3, "valor_centavos": 3 * STREET_DIARIA}
    assert simulacao["devolver_centavos"] == 3 * STREET_DIARIA


def test_loc_12_encerramento_antecipado_cancela_as_parcelas_seguintes(cenario):
    detalhe = _ativa(cenario, periodos=3)  # parcelas de 07, 14 e 21 out
    resposta = _cancelar(cenario, detalhe["id"], "Rodrigo", data="2026-10-10")
    assert resposta.status_code == 200, resposta.json()
    situacao = {p.numero_parcela: p.status for p in _parcelas(detalhe["id"])}
    assert situacao == {1: "paga", 2: "cancelada", 3: "cancelada"}
    comissao = Comissao.objects.get(origem_tipo="locacao", origem_id=detalhe["id"])
    assert comissao.status == "confirmada"  # FIN-09: o encerramento antecipado não estorna


def test_loc_12_sem_dias_restantes_e_devolucao(cenario, com_carteira):
    rafael = com_carteira["LOC-2790"]  # devolução atrasada há 25 dias
    resposta = _cancelar(cenario, rafael.pk, "Rodrigo")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "sem_dias_restantes"


# --- CA-015-24 · Estados finais ---


def test_loc_12_ca_015_24_estados_finais(cenario):
    cancelada = cenario.confirmada()
    assert _cancelar(cenario, cancelada["id"], "Rodrigo").status_code == 200
    encerrada = _ativa(cenario, cliente="Juliana", veiculo=cenario.veiculo("Street 150–160"))
    services.encerrar(Locacao.objects.get(pk=encerrada["id"]))
    for locacao_id in (cancelada["id"], encerrada["id"]):
        resposta = _cancelar(cenario, locacao_id, "Rodrigo")
        assert resposta.status_code == 409
        assert resposta.json()["codigo"] == "transicao_locacao"

    evento = EventoAuditoria.objects.get(
        objeto_tipo="locacao", objeto_id=cancelada["id"], acao="locacao.cancelar"
    )
    assert evento.motivo == "Cliente desistiu" and evento.regra == "LOC-12"
    historico = cenario.moto.api("Bruna").get(f"{LISTA}{cancelada['id']}/historico/").json()
    assert "Locação cancelada" in [i["rotulo"] for i in historico["resultados"]]


# --- CA-015-25 · Comissão (FIN-09) ---


def test_fin_09_ca_015_25_estorno_e_renovacao_sem_comissao(cenario):
    antes = cenario.confirmada()
    assert _cancelar(cenario, antes["id"], "Rodrigo").status_code == 200
    assert Comissao.objects.get(origem_id=antes["id"]).status == "estornada"

    depois = _ativa(cenario, cliente="Juliana", veiculo=cenario.veiculo("Street 150–160"))
    renovada = cenario.moto.api("Bruna").post(
        f"{LISTA}{depois['id']}/renovar/", {"periodos": 1}, format="json"
    )
    assert renovada.status_code == 200, renovada.json()
    assert Comissao.objects.filter(origem_id=depois["id"]).count() == 1
    assert _cancelar(cenario, depois["id"], "Rodrigo", data="2026-10-10").status_code == 200
    assert Comissao.objects.get(origem_id=depois["id"]).status == "confirmada"


# --- Isolamento ---


def test_loc_12_reembolso_da_empresa_a_nao_aparece_na_b(cenario):
    criada = cenario.confirmada()
    _pagar(criada["id"])
    assert _cancelar(cenario, criada["id"], "Rodrigo").status_code == 200
    assert Reembolso.objects.count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Reembolso.objects.exists()
    finally:
        connection.set_tenant(cenario.moto.empresa)


def test_loc_12_so_o_cancelamento_libera_o_veiculo_reservado(cenario):
    """`reservado` → `disponivel` vale para a reserva cancelada, não pelos botões da ficha."""
    from apps.veiculos import services as veiculos_services

    cenario.confirmada(inicio="2026-10-08T15:30:00Z")
    sak = Veiculo.objects.get(placa="SAK1D39")
    assert sak.status == "reservado"
    for acao in (veiculos_services.desbloquear, veiculos_services.voltar_para_frota):
        with pytest.raises(TransicaoInvalida):
            acao(sak)
    assert Veiculo.objects.get(placa="SAK1D39").status == "reservado"
