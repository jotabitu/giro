"""T-502 · Fluxo de venda, fase 1b: assinatura e `vendida` (ADR 0042, itens 6, 6a e 7;
`docs/api/vendas.md`).

Cenário da T-015: Moto Rápida, Filial Centro, 07 out 2026, 10:00. A VEN-0177 (CB 300F, R$
22.900,00 com 8% aprovado pelo Rodrigo = R$ 21.068,00, entrada de R$ 5.000,00 e 12 × R$
1.339,00, comissão de R$ 632,04; `dados-de-teste.md`) vai à assinatura com o modelo pronto de
compra e venda publicado. A Bruna (vendedora) vende; o Rodrigo (gerente) decide e registra a
transferência.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from apps.aprovacoes import services as aprovacoes_services
from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente
from apps.contratos import services as contratos_services
from apps.contratos.models import Contrato, ModeloContrato
from apps.financeiro import services as financeiro
from apps.financeiro.models import Comissao, ContaReceber, Reembolso
from apps.notificacoes.models import Notificacao
from apps.vendas import selectors, services
from apps.vendas.models import Venda
from comum.erros import Conflito

from .test_t015_locacoes import Cenario, cenario  # noqa: F401
from .test_t016_vistorias import _completar
from .test_t502_fluxo_de_venda import VEN_0177, VENDAS, _api, _cb, _criada, _pedido

pytestmark = pytest.mark.usefixtures("modelo_de_venda")


@pytest.fixture
def modelo_de_venda(cenario: Cenario) -> ModeloContrato:  # noqa: F811
    """O modelo pronto de compra e venda, publicado pelo administrador (IMP-04, VEN-15), e o
    Diego com o cadastro completo para a etapa "Documentos" (CLI-03)."""
    _completar(cenario.cliente("Diego"))
    return contratos_services.publicar_modelo(
        contratos_services.criar_de_pronto(None, "compra_venda")
    )


def _ven_0177(cenario: Cenario, veiculo: Any = None) -> Venda:  # noqa: F811
    """A VEN-0177 com os 8% aprovados: volta a `proposta` e é enviada."""
    extra = {"veiculo": veiculo} if veiculo is not None else {}
    criada = _criada(cenario, "pedir_aprovacao", **extra, **VEN_0177)
    aprovacoes_services.aprovar(_pedido(criada["id"]), cenario.pessoas["Rodrigo"])
    return Venda.objects.get(pk=criada["id"])


def _assinatura(cenario: Cenario, venda: Venda, metodo: str = "post", quem: str = "Bruna"):  # noqa: F811
    return getattr(_api(cenario, quem), metodo)(f"{VENDAS}{venda.pk}/assinatura/", format="json")


def _preparada(cenario: Cenario, veiculo: Any = None) -> Venda:  # noqa: F811
    venda = _ven_0177(cenario, veiculo)
    resposta = _assinatura(cenario, venda)
    assert resposta.status_code == 200, resposta.json()
    return Venda.objects.get(pk=venda.pk)


def _contrato(venda: Venda) -> Contrato:
    assert venda.contrato_id is not None
    return Contrato.objects.select_related("cliente").get(pk=venda.contrato_id)


def _entrada(venda: Venda) -> ContaReceber:
    assert venda.conta_entrada_id is not None
    return ContaReceber.objects.get(pk=venda.conta_entrada_id)


def _cliente(venda: Venda) -> Cliente:
    assert venda.cliente is not None
    return venda.cliente


def _assinar(venda: Venda) -> None:
    """O cliente assina pelo link, como na retirada (S-15)."""
    contrato = _contrato(venda)
    contratos_services.marcar_enviado(contrato)
    token = contratos_services.novo_token(contrato)
    contratos_services.assinar(token, contrato.cliente.nome, "177.10.20.30", "Celular")


def _pagar_entrada(venda: Venda) -> None:
    financeiro.marcar_paga(_entrada(venda), forma="pix")


def _detalhe(cenario: Cenario, venda: Venda, quem: str = "Bruna") -> dict[str, Any]:  # noqa: F811
    resposta = _api(cenario, quem).get(f"{VENDAS}{venda.pk}/")
    assert resposta.status_code == 200
    return dict(resposta.json())


# --- VEN-13 / AUT-19: a volta da aprovação recomeça o prazo (decisão do dono de 23 nov 2026) ---


def test_ven_13_volta_da_aprovacao_recomeca_prazo(cenario, relogio):  # noqa: F811
    """Enviada em 01 out, aprovação pedida em 02 out e aprovada em 06 out: vence em 13 out
    (06 + 7), e não em 08 out. A que vinha de `negociacao` volta para ela e não vence."""
    bruna, rodrigo = cenario.pessoas["Bruna"], cenario.pessoas["Rodrigo"]
    diego = cenario.cliente("Diego").pk
    relogio.em("2026-10-01 10:00")
    dados = {"cliente_id": diego, "forma": "a_vista", "desconto_pct": Decimal("2.00")}
    venda = services.criar({**dados, "veiculo_id": _cb(cenario).pk}, bruna, "enviar")
    negociando = services.criar({**dados, "veiculo_id": _cb(cenario, 1).pk}, bruna, "enviar")
    services.registrar_resposta(negociando, bruna, "Quer pensar")
    relogio.em("2026-10-02 10:00")
    services.pedir_desconto(venda, Decimal("8.00"), "Cliente à vista", bruna)
    services.pedir_desconto(negociando, Decimal("8.00"), "Cliente à vista", bruna)
    relogio.em("2026-10-06 15:00")
    aprovacoes_services.aprovar(_pedido(venda.pk), rodrigo)
    aprovacoes_services.recusar(_pedido(negociando.pk), rodrigo, "Margem baixa")
    venda.refresh_from_db()
    assert (venda.status, venda.proposta_enviada_em) == ("proposta", relogio.agora)
    assert services.vence_em(venda) == date(2026, 10, 13)
    negociando.refresh_from_db()
    assert negociando.status == "negociacao" and services.vence_em(negociando) is None
    relogio.em("2026-10-12 02:40")
    assert services.vencer_propostas() == 0  # pela data de antes, teria vencido em 08 out
    relogio.em("2026-10-13 02:40")
    assert services.vencer_propostas() == 1
    venda.refresh_from_db()
    assert (venda.status, venda.motivo_perda) == ("perdida", "proposta vencida")
    assert Venda.objects.get(pk=negociando.pk).status == "negociacao"


def test_ven_13_recusa_tambem_recomeca_o_prazo(cenario, relogio):  # noqa: F811
    bruna = cenario.pessoas["Bruna"]
    relogio.em("2026-10-01 10:00")
    venda = services.criar(
        {
            "veiculo_id": _cb(cenario).pk,
            "cliente_id": cenario.cliente("Diego").pk,
            "forma": "a_vista",
            "desconto_pct": Decimal("2.00"),
        },
        bruna,
        "enviar",
    )
    services.pedir_desconto(venda, Decimal("8.00"), "", bruna)
    relogio.em("2026-10-04 09:00")
    aprovacoes_services.recusar(_pedido(venda.pk), cenario.pessoas["Rodrigo"], "Margem baixa")
    venda.refresh_from_db()
    assert (venda.status, venda.desconto_pct) == ("proposta", Decimal("0.00"))
    assert services.vence_em(venda) == date(2026, 10, 11)


# --- VEN-15: assinatura e conclusão (VEN-0177) ---


def test_ven_15_ven_0177_assinatura_e_entrada_concluem_a_venda(cenario, relogio):  # noqa: F811
    veiculo = _cb(cenario)
    interessado = _criada(
        cenario,
        "interessado",
        veiculo=veiculo,
        cliente_id=None,
        interessado={"nome": "Carla Mendes", "celular": "85988771100"},
    )
    venda = _preparada(cenario, veiculo)
    detalhe = _detalhe(cenario, venda)
    assert (detalhe["status"], detalhe["situacao_texto"]) == ("proposta", "Aguardando assinatura")
    assert detalhe["contrato"]["status"] == "gerado"
    assert detalhe["contrato"]["modelo"] == "Compra e venda"
    assert detalhe["conta_entrada"] == {
        "id": venda.conta_entrada_id,
        "status": "aberta",
        "valor_centavos": 500000,
        "vencimento": "2026-10-07",
        "rotulo": "Entrada de R$ 5.000,00",
        "texto": "Aguardando pagamento · vence hoje",
        "pago_em": None,
        "forma_texto": None,
    }
    assert detalhe["acoes"]["cancelar_assinatura"] and not detalhe["acoes"]["editar"]
    assert detalhe["documentos"] is None
    conta = _entrada(venda)
    assert (conta.tipo, conta.aguarda_retirada) == ("entrada", True)  # sem régua, multa e juros
    contrato = _contrato(venda)
    assert contrato.titulo == "Contrato de compra e venda"
    for trecho in (
        "R$ 22.900,00",
        "R$ 21.068,00",
        "12 parcelas mensais de R$ 1.339,00",
        "R$ 5.000,00",
        venda.codigo,
        "um mês depois da conclusão da venda",
    ):
        assert trecho in contrato.versao_texto_html, trecho
    # Com o contrato vigente, a proposta não muda (VEN-06).
    editar = _api(cenario).patch(f"{VENDAS}{venda.pk}/", {"desconto_pct": "2.00"}, format="json")
    assert (editar.status_code, editar.json()["codigo"]) == (409, "VEN-06")
    assert editar.json()["mensagem"] == "Cancele a assinatura para mudar a proposta."

    _assinar(venda)
    venda.refresh_from_db()
    assert (venda.status, venda.contrato_assinado_em) == ("proposta", relogio.agora)
    assert services.situacao_texto(venda) == "Aguardando entrada"

    _pagar_entrada(venda)
    venda.refresh_from_db()
    assert (venda.status, venda.vendida_em, venda.entrada_paga_em) == (
        "vendida",
        relogio.agora,
        relogio.agora,
    )
    assert venda.veiculo.status == "vendido"
    parcelas = list(
        ContaReceber.objects.filter(
            origem_tipo="venda", origem_id=venda.pk, tipo="parcela"
        ).order_by("numero_parcela")
    )
    assert [(c.numero_parcela, c.valor_centavos) for c in parcelas] == [
        (n, 133900) for n in range(1, 13)
    ]
    assert (parcelas[0].vencimento, parcelas[-1].vencimento) == (
        date(2026, 11, 7),
        date(2027, 10, 7),
    )
    assert not any(c.aguarda_retirada for c in parcelas)
    comissao = Comissao.objects.get(origem_tipo="venda", origem_id=venda.pk)
    assert (comissao.status, comissao.valor_centavos, comissao.mes_pagamento) == (
        "confirmada",
        63204,
        date(2026, 11, 1),
    )
    # VEN-10: o interessado do mesmo veículo é perdido.
    assert Venda.objects.get(pk=interessado["id"]).motivo_perda == "veículo vendido"
    evento = EventoAuditoria.objects.get(acao="venda.concluir", objeto_id=venda.pk)
    assert (evento.regra, evento.ator_tipo) == ("VEN-06", "sistema")
    detalhe = _detalhe(cenario, venda)
    assert detalhe["situacao_texto"] == "Vendida 07 out"
    assert detalhe["conclusao_texto"] == (
        "Venda concluída. As 12 parcelas estão em Contas a receber, a comissão de R$ 632,04 foi "
        "lançada e o veículo saiu da frota de locação."
    )
    assert detalhe["transferencia"]["pendente"] is True


def test_ven_15_entrada_antes_da_assinatura_tambem_conclui(cenario):  # noqa: F811
    venda = _preparada(cenario)
    _pagar_entrada(venda)
    venda.refresh_from_db()
    assert (venda.status, services.situacao_texto(venda)) == ("proposta", "Aguardando assinatura")
    _assinar(venda)
    assert Venda.objects.get(pk=venda.pk).status == "vendida"


def test_ven_17_transferencia_da_venda_de_balcao(cenario, django_capture_on_commit_callbacks):  # noqa: F811
    venda = _preparada(cenario)
    _assinar(venda)
    with django_capture_on_commit_callbacks(execute=True):
        _pagar_entrada(venda)
    venda.refresh_from_db()
    aviso = Notificacao.objects.get(
        tipo="transferencia_venda", destinatario=cenario.pessoas["Rodrigo"]
    )
    placa = f"{venda.veiculo.placa[:3]}-{venda.veiculo.placa[3:]}"
    assert aviso.titulo == (
        f"Fazer a transferência no Detran: {placa} para {_cliente(venda).nome}. "
        f"{venda.codigo} vendida em 07/10/2026."
    )
    assert aviso.link == f"/vendas/{venda.pk}"
    pendentes = selectors.transferencias_pendentes([venda.filial_id])
    assert [(p["tipo"], p["destino"]) for p in pendentes] == [
        ("transferencia_venda", {"chave": "vendas", "id": venda.pk})
    ]
    lista = _api(cenario, "Rodrigo").get(VENDAS, {"transferencia_pendente": "true"}).json()
    assert [v["id"] for v in lista["resultados"]] == [venda.pk]
    assert _detalhe(cenario, venda, "Rodrigo")["acoes"]["registrar_transferencia"] is True
    # A vendedora não registra; o gerente, sim, uma vez só.
    rota = f"{VENDAS}{venda.pk}/transferencia/"
    assert _api(cenario).post(rota, {"feita_em": "2026-10-07"}, format="json").status_code == 403
    feita = _api(cenario, "Rodrigo").post(rota, {"feita_em": "2026-10-07"}, format="json")
    assert feita.status_code == 200, feita.json()
    assert feita.json()["transferencia"]["pendente"] is False
    de_novo = _api(cenario, "Rodrigo").post(rota, {"feita_em": "2026-10-07"}, format="json")
    assert (de_novo.status_code, de_novo.json()["codigo"]) == (409, "VEN-17")
    assert selectors.transferencias_pendentes([venda.filial_id]) == []


# --- Antes da assinatura: modelo, cadastro e cliente (IMP-04, CLI-03, CLI-05) ---


def test_imp_04_venda_sem_modelo_de_compra_e_venda(cenario, modelo_de_venda):  # noqa: F811
    contratos_services.arquivar_modelo(modelo_de_venda)
    venda = _ven_0177(cenario)
    resposta = _assinatura(cenario, venda)
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "IMP-04"
    assert resposta.json()["mensagem"] == (
        "Publique um modelo de contrato de compra e venda antes de concluir a venda."
    )
    assert resposta.json()["detalhes"]["link"] == "/admin/contratos"
    assert not ContaReceber.objects.filter(origem_tipo="venda").exists()
    assert Venda.objects.get(pk=venda.pk).contrato_id is None


def test_cli_03_preparar_com_cadastro_incompleto(cenario):  # noqa: F811
    venda = _ven_0177(cenario)
    Cliente.objects.filter(pk=_cliente(venda).pk).update(consentimento_em=None)
    detalhe = _detalhe(cenario, venda)
    assert "consentimento" in detalhe["documentos"]["pendencias"]
    assert detalhe["documentos"]["texto"] == (
        f"Falta completar o cadastro de {_cliente(venda).nome} para preparar a assinatura."
    )
    assert detalhe["documentos"]["pode_preparar"] is False
    resposta = _assinatura(cenario, venda)
    assert (resposta.status_code, resposta.json()["codigo"]) == (422, "CLI-03")
    assert resposta.json()["mensagem"] == "Complete o cadastro do cliente antes da assinatura."


def test_cli_05_preparar_com_cliente_bloqueado(cenario):  # noqa: F811
    venda = _ven_0177(cenario)
    clientes_services.bloquear(_cliente(venda), "Cheque devolvido")
    detalhe = _detalhe(cenario, venda)
    assert detalhe["documentos"]["gravidade"] == "critica"
    assert detalhe["documentos"]["texto"] == (
        f"{_cliente(venda).nome} está bloqueado e não pode comprar. A assinatura fica liberada "
        "depois do desbloqueio. Peça o desbloqueio ao gerente."
    )
    resposta = _assinatura(cenario, venda)
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "CLI-05")


# --- VEN-19 / ADR 0042, item 6a: cancelar a assinatura e perder ---


def test_ven_19_cancelar_assinatura_para_mudar_a_proposta(cenario):  # noqa: F811
    venda = _preparada(cenario)
    contrato_id, conta_id = _contrato(venda).pk, _entrada(venda).pk
    resposta = _assinatura(cenario, venda, "delete")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["contrato"] is None and resposta.json()["acoes"]["editar"] is True
    assert Contrato.objects.get(pk=contrato_id).status == "cancelado"
    assert ContaReceber.objects.get(pk=conta_id).status == "cancelada"
    assert Venda.objects.get(pk=venda.pk).status == "proposta"
    # Dá para mudar a proposta e preparar de novo.
    editar = _api(cenario).patch(f"{VENDAS}{venda.pk}/", {"desconto_pct": "8.00"}, format="json")
    assert editar.status_code == 200, editar.json()
    assert _assinatura(cenario, venda).status_code == 200
    assert Contrato.objects.filter(origem_tipo="venda", origem_id=venda.pk).count() == 2


def test_ven_06_cancelar_assinatura_com_contrato_assinado_ou_entrada_paga(cenario):  # noqa: F811
    assinada = _preparada(cenario)
    _assinar(assinada)
    resposta = _assinatura(cenario, assinada, "delete")
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "VEN-06")
    assert resposta.json()["mensagem"] == services.CONTRATO_JA_ASSINADO
    paga = _preparada(cenario, _cb(cenario, 1))
    _pagar_entrada(paga)
    resposta = _assinatura(cenario, paga, "delete")
    assert (resposta.status_code, resposta.json()["codigo"]) == (409, "VEN-06")
    assert resposta.json()["mensagem"] == (
        "A entrada já foi paga. Para desfazer, marque a venda como perdida."
    )


def test_ven_13_perder_com_contrato_assinado_cancela_o_contrato(cenario):  # noqa: F811
    """Padrão A do item 6a: o contrato assinado vai para `cancelado`, com o PDF e a prova
    guardados; a entrada não paga é cancelada, sem reembolso, e o vendedor marca."""
    venda = _preparada(cenario)
    _assinar(venda)
    resposta = _api(cenario).post(
        f"{VENDAS}{venda.pk}/perder/", {"motivo": "Desistiu"}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    contrato = _contrato(venda)
    assert (contrato.status, contrato.motivo_cancelamento) == (
        "cancelado",
        "Venda perdida: Desistiu",
    )
    assert contrato.assinado_em is not None and contrato.assinado_ip == "177.10.20.30"
    assert _entrada(venda).status == "cancelada"
    assert not Reembolso.objects.exists()
    assert resposta.json()["contrato"]["situacao_texto"] == "Cancelado · venda perdida"
    assert Comissao.objects.get(origem_tipo="venda", origem_id=venda.pk).status == "estornada"
    assert EventoAuditoria.objects.filter(
        acao="contrato.cancelar_assinado", objeto_id=contrato.pk
    ).exists()


def test_ven_19_perder_com_entrada_paga_so_gerente_e_vira_reembolso(cenario):  # noqa: F811
    venda = _preparada(cenario)
    _pagar_entrada(venda)
    detalhe = _detalhe(cenario, venda)
    assert detalhe["acoes"]["perder"] is False
    assert detalhe["perder_texto"] == services.SO_GERENTE_PERDE
    rota = f"{VENDAS}{venda.pk}/perder/"
    negado = _api(cenario).post(rota, {"motivo": "Desistiu"}, format="json")
    assert (negado.status_code, negado.json()["codigo"]) == (403, "VEN-19")
    gerente = _detalhe(cenario, venda, "Rodrigo")
    assert gerente["perder_texto"] == (
        "A entrada de R$ 5.000,00 já foi paga. O valor vira um reembolso a fazer para o cliente."
    )
    perdida = _api(cenario, "Rodrigo").post(rota, {"motivo": "Desistiu"}, format="json")
    assert perdida.status_code == 200, perdida.json()
    reembolso = Reembolso.objects.get(origem_tipo="venda", origem_id=venda.pk)
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status, reembolso.motivo) == (
        500000,
        "pix",
        "a_fazer",
        "Venda perdida com a entrada paga",
    )
    assert _contrato(venda).status == "cancelado"
    assert Venda.objects.get(pk=venda.pk).veiculo.status == "a_venda"


def test_aut_19_venda_assinada_em_proposta_vence(cenario, relogio):  # noqa: F811
    """Item 6a, ponto 2, opção A: a `AUT-19` vale na etapa "Assinatura"."""
    venda = _preparada(cenario)
    _assinar(venda)
    relogio.em("2026-10-14 02:40")
    assert services.vencer_propostas() == 1
    venda.refresh_from_db()
    assert (venda.status, venda.motivo_perda) == ("perdida", "proposta vencida")
    assert _contrato(venda).status == "cancelado"
    assert _entrada(venda).status == "cancelada"


# --- contratos: o assinado só se cancela na venda; marcadores e prévia (VEN-15) ---


def test_ven_15_cancelar_assinado_so_no_contrato_da_venda(cenario):  # noqa: F811
    venda = _preparada(cenario)
    _assinar(venda)
    contrato = _contrato(venda)
    with pytest.raises(Conflito) as erro:
        contratos_services.cancelar(contrato, "Teste")
    assert erro.value.codigo == "contrato_assinado"
    Contrato.objects.filter(pk=contrato.pk).update(origem_tipo="locacao")
    contrato.refresh_from_db()
    with pytest.raises(Conflito):
        contratos_services.cancelar_assinado(contrato, "Teste")
    assert Contrato.objects.get(pk=contrato.pk).status == "assinado"


def test_ven_15_marcadores_da_venda_e_previa(cenario, modelo_de_venda):  # noqa: F811
    api = cenario.moto.api("Mariana")
    errado = api.post(
        "/api/contratos/modelos/",
        {"nome": "Locação", "finalidade": "locacao", "texto": "<p>{{venda.codigo}}</p>"},
        format="json",
    )
    assert (errado.status_code, errado.json()["codigo"]) == (400, "marcador_invalido")
    marcadores = api.get("/api/contratos/marcadores/").json()["resultados"]
    assert {"chave": "venda.parcelas", "finalidade": "venda"}.items() <= next(
        m for m in marcadores if m["chave"] == "venda.parcelas"
    ).items()
    venda = _ven_0177(cenario)
    previa = api.post(
        f"/api/contratos/modelos/{modelo_de_venda.pk}/previa/",
        {"venda_id": venda.pk},
        format="json",
    )
    assert previa.status_code == 200, previa.json()
    assert "R$ 21.068,00" in previa.json()["html"] and venda.codigo in previa.json()["html"]
    assert ModeloContrato.objects.get(pk=modelo_de_venda.pk).get_finalidade_display() == (
        "Compra e venda"
    )


# --- Lacunas das telas da 1b (#655): o envio, o pagamento e o PDF na lista ---

EMAIL_DO_DIEGO = "diego.martins@exemplo.com.br"


def test_ven_15_contrato_enviado_com_o_email_do_cliente(cenario, relogio):  # noqa: F811
    Cliente.objects.filter(pk=cenario.cliente("Diego").pk).update(email=EMAIL_DO_DIEGO)
    venda = _preparada(cenario)
    antes = _detalhe(cenario, venda)["contrato"]
    assert (antes["enviado_para"], antes["enviado_texto"]) == (None, None)
    relogio.em("2026-10-07 10:20")
    contratos_services.marcar_enviado(_contrato(venda))
    contrato = _detalhe(cenario, venda)["contrato"]
    assert contrato["enviado_para"] == EMAIL_DO_DIEGO
    assert contrato["enviado_texto"] == f"Contrato enviado · 07 out, 10:20 · {EMAIL_DO_DIEGO}"
    # AUD-09: o suporte vê o e-mail mascarado.
    suporte = selectors._contrato(Venda.objects.get(pk=venda.pk), SimpleNamespace(e_suporte=True))
    assert suporte is not None and suporte["enviado_para"] == "d***@e***.br"


def test_ven_15_contrato_enviado_sem_email_mostra_so_a_hora(cenario, relogio):  # noqa: F811
    Cliente.objects.filter(pk=cenario.cliente("Diego").pk).update(email="")
    venda = _preparada(cenario)
    relogio.em("2026-10-07 10:20")
    contratos_services.marcar_enviado(_contrato(venda))
    contrato = _detalhe(cenario, venda)["contrato"]
    assert (contrato["enviado_para"], contrato["enviado_texto"]) == (
        None,
        "Contrato enviado · 07 out, 10:20",
    )


def test_ven_19_entrada_paga_com_a_hora_e_a_forma(cenario, relogio):  # noqa: F811
    venda = _preparada(cenario)
    antes = _detalhe(cenario, venda)["conta_entrada"]
    assert (antes["pago_em"], antes["forma_texto"]) == (None, None)
    relogio.em("2026-10-07 11:02")
    _pagar_entrada(venda)
    entrada = _detalhe(cenario, venda)["conta_entrada"]
    assert entrada["texto"] == "Paga em 07 out, 11:02 · Pix"
    assert entrada["forma_texto"] == "Pix" and entrada["pago_em"] is not None


def test_ven_15_lista_diz_se_o_contrato_tem_pdf(cenario):  # noqa: F811
    venda = _ven_0177(cenario)

    def _da_lista() -> dict[int, bool]:
        resposta = _api(cenario).get(VENDAS)
        assert resposta.status_code == 200
        return {v["id"]: v["contrato_pdf_disponivel"] for v in resposta.json()["resultados"]}

    assert _da_lista()[venda.pk] is False  # sem contrato
    assert _assinatura(cenario, venda).status_code == 200
    venda.refresh_from_db()
    assert _da_lista()[venda.pk] is False  # PDF na fila
    Contrato.objects.filter(pk=_contrato(venda).pk).update(pdf="contratos/ven-0177.pdf")
    assert _da_lista()[venda.pk] is True
    assert _detalhe(cenario, venda)["contrato_pdf_disponivel"] is True
    assert _detalhe(cenario, venda)["contrato"]["pdf_disponivel"] is True
