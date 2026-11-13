"""T-420 · Locação com intenção de compra de ponta a ponta (`LOC-16`, `VEN-11`, `FIN-04`, `AUT-05`).

Cenário do seed Moto Rápida, como em `test_t420_locacao_com_compra`: em 10 nov 2026, Filial
Centro, a Mariana cadastrou o plano "Compra Street 24 meses" (24 × R$ 1.190,00) e publicou o
modelo da compra; a Bruna aluga o SAK-1D39 ao Lucas, com caução de R$ 300,00 (a 24ª nasce com
R$ 890,00). Aqui nenhum pagamento é marcado à mão: tudo passa pelo caminho real de baixa
(`FIN-04`), o caixa da filial (dinheiro e cartão) e o webhook do Pix (`AUT-05`), até a quitação,
a venda de R$ 0,00, o veículo vendido, o aviso, as pendências dos painéis e a transferência.
"""

from typing import Any

from django.core import mail

from apps.auditoria.models import EventoAuditoria
from apps.financeiro.models import (
    CobrancaExterna,
    Comissao,
    ContaReceber,
    PendenciaPagamento,
    Reembolso,
)
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.veiculos.models import HistoricoStatusVeiculo, Veiculo
from apps.vendas import leituras as vendas_leituras
from apps.vendas.models import Venda
from comum import relogio as relogio_do_giro
from comum.models import WebhookRecebido
from integracoes.pagamentos import falso as pagamentos

from .test_t015_locacoes import Cenario, _assinar, _vistoriar
from .test_t015_locacoes import cenario as cenario
from .test_t017_financeiro import _webhook
from .test_t017_financeiro import recebimentos as recebimentos
from .test_t420_locacao_com_compra import _compra, _confirmada, _contas
from .test_t420_locacao_com_compra import compra as compra
from .test_t420_locacao_com_compra import plano as plano

CONTAS = "/api/financeiro/contas-receber/"
CAIXAS = "/api/financeiro/caixas/"
TRANSFERENCIA = "/api/locacoes/{}/transferencia/"
TEXTO = "Transferência no Detran · SAK-1D39 · Lucas Ferreira · LOC-2856 quitada em 10/11/2026"


def _receber(cenario: Cenario, conta: ContaReceber, forma: str = "dinheiro") -> None:
    """Baixa no caixa da Filial Centro pela API (`FIN-04`), pelo valor de hoje."""
    resposta = cenario.moto.api("Bruna").post(
        f"{CONTAS}{conta.pk}/receber/",
        {"forma": forma, "valor_centavos": conta.valor_centavos},
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()


def _cobranca_pix(cenario: Cenario, conta: ContaReceber) -> CobrancaExterna:
    gerada = cenario.moto.api("Lúcia").post(
        f"{CONTAS}{conta.pk}/cobranca/", {"tipo": "pix"}, format="json"
    )
    assert gerada.status_code == 201, gerada.json()
    return CobrancaExterna.objects.get(pk=gerada.json()["id"])


def _ativa_pelo_caixa(cenario: Cenario, plano_id: int) -> Locacao:
    """Caixa aberto, locação confirmada, a 24ª com a caução abatida, e a retirada com a parcela 1
    em dinheiro e a caução no cartão de débito, as duas no caixa."""
    aberto = cenario.moto.api("Bruna").post(CAIXAS, {"troco_centavos": 20000}, format="json")
    assert aberto.status_code == 201, aberto.json()
    locacao = _confirmada(cenario, plano_id)
    parcelas = _contas(locacao)
    [caucao] = _contas(locacao, "caucao")
    assert len(parcelas) == 24
    assert {p.valor_centavos for p in parcelas[:23]} == {119000}
    assert (parcelas[23].valor_centavos, caucao.valor_centavos) == (89000, 30000)
    _vistoriar(locacao.pk)
    _assinar(locacao.pk)
    _receber(cenario, parcelas[0])
    _receber(cenario, caucao, "cartao_debito")
    locacao.refresh_from_db()
    assert locacao.status == "ativa"
    assert Veiculo.objects.get(pk=locacao.veiculo_id).status == "alugado"
    for parcela in parcelas[1:23]:  # 2 a 23, antes do vencimento (CA-420-15)
        _receber(cenario, parcela, "cartao_credito")
    assert _compra(cenario, locacao)["andamento"] == (
        "Parcela 23 de 24 · falta 1 para a transferência"
    )
    locacao.refresh_from_db()
    assert (locacao.status, locacao.quitada_em) == ("ativa", None)
    assert not Venda.objects.exists()
    return locacao


def _painel(cenario: Cenario, quem: str) -> dict[str, Any]:
    # Sem limpar o cache: a quitação e a transferência renovam o Início na hora (A2, #577).
    resposta = cenario.moto.api(quem).get("/api/painel/inicio/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _conferir_quitacao(cenario: Cenario, locacao: Locacao) -> Venda:
    """Quitada pelo Sistema, a caução paga usada na 24ª (sem sobra), uma venda só, de R$ 0,00,
    o veículo `vendido` uma vez, e o aviso aos gerentes e administradores uma vez."""
    locacao.refresh_from_db()
    assert locacao.status == "encerrada"
    assert locacao.quitada_em == relogio_do_giro.agora()
    assert locacao.devolvida_em is None
    quitou = EventoAuditoria.objects.get(objeto_id=locacao.pk, acao="locacao.quitar")
    assert (quitou.ator_tipo, quitou.regra) == ("sistema", "LOC-16")
    [caucao] = _contas(locacao, "caucao")
    assert caucao.status == "paga"
    assert not Reembolso.objects.exists()

    venda = Venda.objects.get()
    assert (venda.status, venda.origem, venda.preco_final_centavos) == (
        "vendida",
        "quitacao_locacao",
        0,
    )
    assert venda.descricao == f"Quitação da {locacao.codigo}"
    assert (venda.locacao_id, venda.cliente_id, venda.veiculo_id, venda.filial_id) == (
        locacao.pk,
        locacao.cliente_id,
        locacao.veiculo_id,
        locacao.filial_id,
    )
    assert venda.vendedor == cenario.pessoas["Bruna"]
    assert venda.transferencia_feita_em is None
    assert not ContaReceber.objects.filter(origem_tipo="venda").exists()
    assert not Comissao.objects.filter(origem_tipo="venda").exists()
    criou = EventoAuditoria.objects.get(acao="venda.criar_da_quitacao")
    assert (criou.ator_tipo, criou.regra) == ("sistema", "VEN-11")

    assert Veiculo.objects.get(pk=locacao.veiculo_id).status == "vendido"
    [vendido] = HistoricoStatusVeiculo.objects.filter(veiculo_id=locacao.veiculo_id, para="vendido")
    assert (vendido.de, vendido.origem_codigo) == ("alugado", venda.codigo)

    avisos = Notificacao.objects.filter(tipo="transferencia_quitacao")
    assert sorted(a.destinatario.nome for a in avisos) == ["Mariana", "Rodrigo"]
    titulo = (
        "Fazer a transferência no Detran: SAK-1D39 para Lucas Ferreira. "
        "LOC-2856 quitada em 10/11/2026."
    )
    assert {a.titulo for a in avisos} == {titulo}
    assert sorted(m.to[0] for m in mail.outbox if titulo in f"{m.subject} {m.body}") == [
        "mariana@motorapida.com.br",
        "rodrigo@motorapida.com.br",
    ]
    return venda


def _conferir_pendencias_e_transferencia(cenario: Cenario, locacao: Locacao, capturar: Any) -> None:
    """A pendência nos dois painéis (administrador e gerente), "Transferência feita" pelo
    Rodrigo, a pendência some, e registrar de novo é recusado."""
    item = {
        "texto": TEXTO,
        "gravidade": "alerta",
        "destino": {"chave": "locacoes", "id": locacao.pk},
    }
    assert item in _painel(cenario, "Mariana")["pendencias"]["itens"]
    rodrigo = _painel(cenario, "Rodrigo")
    assert rodrigo["variante"] == "gerente"
    assert rodrigo["pendencias"] == {
        "titulo": "1 transferência no Detran pendente",
        "itens": [item],
    }
    detalhe = cenario.detalhe(locacao.pk, "Rodrigo")
    assert detalhe["situacao"]["codigo"] == "quitada"
    assert detalhe["compra"]["andamento"] == (
        "Quitada em 10/11/2026 · falta a transferência no Detran"
    )
    assert detalhe["compra"]["venda"]["acoes"] == {"registrar_transferencia": True}

    hoje = relogio_do_giro.hoje().isoformat()
    with capturar(execute=True):  # o Início renova depois do commit (A2)
        feita = cenario.moto.api("Rodrigo").post(
            TRANSFERENCIA.format(locacao.pk), {"feita_em": hoje}, format="json"
        )
    assert feita.status_code == 200, feita.json()
    venda = Venda.objects.get()
    assert venda.transferencia_feita_em == relogio_do_giro.hoje()
    assert venda.transferencia_registrada_por == cenario.pessoas["Rodrigo"]
    assert Veiculo.objects.get(pk=locacao.veiculo_id).status == "vendido"
    assert item not in _painel(cenario, "Mariana")["pendencias"]["itens"]
    assert _painel(cenario, "Rodrigo")["pendencias"]["itens"] == []
    assert _compra(cenario, locacao, "Rodrigo")["andamento"] == (
        "Quitada em 10/11/2026 · transferência feita em 10/11/2026"
    )
    de_novo = cenario.moto.api("Mariana").post(
        TRANSFERENCIA.format(locacao.pk), {"feita_em": hoje}, format="json"
    )
    assert de_novo.status_code == 409
    assert de_novo.json()["mensagem"] == "A transferência desta venda já foi registrada."


def test_loc_16_ven_11_ponta_a_ponta_ultima_parcela_pelo_pix(
    compra: Cenario,
    plano: dict[str, Any],
    recebimentos: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """A 24ª (R$ 890,00, a caução abatida) é paga pelo Pix: o aviso do parceiro chega duas vezes
    com o mesmo id e uma terceira com outro id (o parceiro avisa de novo a mesma cobrança). A
    baixa, a quitação e a venda acontecem uma vez só."""
    vendas_leituras.registrar()
    locacao = _ativa_pelo_caixa(compra, plano["id"])
    ultima = _contas(locacao)[23]
    cobranca = _cobranca_pix(compra, ultima)
    assert cobranca.valor_centavos == 89000

    corpo = pagamentos.simular_pagamento(cobranca.externo_id)
    for _ in range(2):
        assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    outro = pagamentos.corpo_do_webhook(cobranca.externo_id, "PAYMENT_CONFIRMED", "evt_outro")
    assert _webhook(django_capture_on_commit_callbacks, outro) == 200

    ultima.refresh_from_db()
    assert (ultima.status, ultima.forma) == ("paga", "pix")
    # O mesmo id é guardado uma vez; o outro id chega e acha a conta já paga.
    resultados = WebhookRecebido.objects.order_by("id").values_list("resultado", flat=True)
    assert list(resultados) == ["baixada", "ja_baixada"]
    pagou = EventoAuditoria.objects.filter(acao="conta_receber.pagar", objeto_id=ultima.pk)
    assert pagou.count() == 1
    assert not PendenciaPagamento.objects.exists()
    _conferir_quitacao(compra, locacao)
    _conferir_pendencias_e_transferencia(compra, locacao, django_capture_on_commit_callbacks)


def test_loc_16_ven_11_ponta_a_ponta_ultima_parcela_no_caixa_e_pix_atrasado(
    compra: Cenario,
    plano: dict[str, Any],
    recebimentos: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """O Lucas pediu o Pix da 24ª, mas pagou em dinheiro no balcão: quita pelo caixa. O Pix pago
    depois chega pelo webhook e vira pendência para o financeiro (conta não está mais em
    aberto), sem baixar de novo, sem segunda venda e sem novo aviso."""
    vendas_leituras.registrar()
    locacao = _ativa_pelo_caixa(compra, plano["id"])
    ultima = _contas(locacao)[23]
    cobranca = _cobranca_pix(compra, ultima)
    with django_capture_on_commit_callbacks(execute=True):
        _receber(compra, ultima)
    _conferir_quitacao(compra, locacao)

    corpo = pagamentos.simular_pagamento(cobranca.externo_id)
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    ultima.refresh_from_db()
    assert (ultima.status, ultima.forma) == ("paga", "dinheiro")
    assert WebhookRecebido.objects.get().resultado == "conta_nao_aberta"
    assert PendenciaPagamento.objects.count() == 1
    _conferir_quitacao(compra, locacao)
    _conferir_pendencias_e_transferencia(compra, locacao, django_capture_on_commit_callbacks)
