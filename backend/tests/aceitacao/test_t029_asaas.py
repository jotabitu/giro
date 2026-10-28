"""T-029 · Asaas ligado ao financeiro e à plataforma, com as respostas gravadas (sem rede).

docs/qa/criterios/T-029.md. Cenário da T-017: Moto Rápida em 07 out 2026, 10:00, Carlos com a
parcela 2 de 29940 vencida em 30 set (LOC-2841, com a cláusula de juros: R$ 306,09 hoje).
O provedor escolhido é o `asaas`, com o transporte trocado pelas gravações de
`tests/integracoes/gravacoes/asaas.json`.
"""

from pathlib import Path
from typing import Any

import pytest
from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.financeiro import services as financeiro
from apps.financeiro.models import CobrancaExterna, ContaReceber
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.plataforma import services as plataforma
from apps.plataforma.models import ContaPagamento
from comum.erros import Conflito, ErroDeRegra
from comum.models import WebhookRecebido
from integracoes.pagamentos import hash_do_token
from integracoes.pagamentos.base import EventoWebhook, ParceiroIndisponivel
from integracoes.whatsapp import falso as whatsapp
from tests.integracoes.gravacao import CHAVE_DA_SUBCONTA, Gravacao, asaas

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _contrato_com_juros
from .test_t017_financeiro import (  # noqa: F401 - fixtures
    CONTAS,
    TOKEN,
    _carlos,
    _webhook,
    com_carteira,
)

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def com_asaas(settings, monkeypatch):
    """`GIRO_PROVEDOR_PAGAMENTOS=asaas`; cada teste diz quais gravações o Asaas responde."""
    settings.GIRO_PROVEDOR_PAGAMENTOS = "asaas"
    gravacoes: list[Gravacao] = []

    def responder(*casos: str) -> Gravacao:
        parceiro, gravacao = asaas(*casos)
        monkeypatch.setattr("integracoes.pagamentos.asaas.Asaas", lambda: parceiro)
        gravacoes.append(gravacao)
        return gravacao

    yield responder
    for gravacao in gravacoes:
        gravacao.conferir_fim()


@pytest.fixture
def subconta(cenario) -> ContaPagamento:  # noqa: F811
    """A subconta aprovada da Moto Rápida, com a chave cifrada (S-05)."""
    conta = ContaPagamento(
        empresa=cenario.moto.empresa,
        conta_externa_id="4f468235-0000-4000-8000-000000000001",
        webhook_token_hash=hash_do_token(TOKEN),
        status="aprovada",
    )
    conta.definir_chave_api_cifrada(CHAVE_DA_SUBCONTA)
    conta.save()
    return conta


def _carlos_com_juros(com_carteira: dict[str, Locacao]) -> ContaReceber:  # noqa: F811
    _contrato_com_juros(com_carteira["LOC-2841"])
    return _carlos(com_carteira)


def _gerar_pix(cenario, conta: ContaReceber) -> Any:  # noqa: F811
    return cenario.moto.api("Lúcia").post(
        f"{CONTAS}{conta.pk}/cobranca/", {"tipo": "pix"}, format="json"
    )


def _aviso(evento_id: str, evento: str = "PAYMENT_RECEIVED") -> dict[str, Any]:
    # O valor do corpo não vale: a baixa consulta o Asaas (S-14).
    return {
        "id": evento_id,
        "event": evento,
        "payment": {"id": "pay_t029carlos0001", "externalReference": "9001", "value": 1.00},
    }


# --- Cobrança (FIN-04) ---


def test_fin_04_t029_pix_do_carlos_pelo_asaas(cenario, com_carteira, subconta, com_asaas):  # noqa: F811
    """CA-029-04: R$ 306,09 com o id da conta como referência, pela chave da subconta."""
    carlos = _carlos_com_juros(com_carteira)
    gravacao = com_asaas("pix_carlos_cliente_novo")
    resposta = _gerar_pix(cenario, carlos)
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    assert (corpo["valor_centavos"], corpo["vence_em"], corpo["status"]) == (
        30609,
        "2026-10-07",
        "aguardando",
    )
    assert corpo["pix_copia_e_cola"].startswith("000201")
    enviado = gravacao.corpo("POST", "/payments")
    assert enviado["externalReference"] == str(carlos.pk)
    assert str(enviado["value"]) == "306.09"
    assert {f["chave"] for f in gravacao.feitas} == {CHAVE_DA_SUBCONTA}
    # Nada do Asaas sai na resposta (CA-029-17).
    assert "asaas" not in resposta.content.decode().lower()
    assert CobrancaExterna.objects.get().externo_id == "pay_t029carlos0001"


def test_fin_04_t029_asaas_fora_do_ar_responde_503(cenario, com_carteira, subconta, com_asaas):  # noqa: F811
    """CA-029-16: 503 com a mensagem do contrato, e nenhuma cobrança gravada."""
    carlos = _carlos_com_juros(com_carteira)
    com_asaas("fora_do_ar")
    resposta = _gerar_pix(cenario, carlos)
    assert resposta.status_code == 503
    assert resposta.json()["codigo"] == "parceiro_indisponivel"
    assert resposta.json()["mensagem"] == (
        "Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos."
    )
    assert not CobrancaExterna.objects.exists()


# --- Webhook (AUT-05, S-14) ---


def test_aut_05_t029_pix_pago_no_asaas_baixa_uma_vez(
    cenario,  # noqa: F811
    com_carteira,  # noqa: F811
    subconta,
    com_asaas,
    django_capture_on_commit_callbacks,
):
    """CA-029-10 e CA-029-11: o Asaas avisa (recebido e confirmado, e o recebido de novo); a
    tarefa consulta o Asaas e baixa uma vez, com a multa e os juros do dia da cobrança."""
    carlos = _carlos_com_juros(com_carteira)
    com_asaas("pix_carlos_cliente_novo", "consultar_pix_pago", "consultar_pix_pago")
    assert _gerar_pix(cenario, carlos).status_code == 201

    assert _webhook(django_capture_on_commit_callbacks, _aviso("evt_t029_1")) == 200
    assert _webhook(django_capture_on_commit_callbacks, _aviso("evt_t029_1")) == 200
    assert (
        _webhook(django_capture_on_commit_callbacks, _aviso("evt_t029_2", "PAYMENT_CONFIRMED"))
        == 200
    )

    carlos.refresh_from_db()
    assert (carlos.status, carlos.forma) == ("paga", "pix")
    assert (carlos.multa_centavos, carlos.juros_centavos) == (599, 70)
    assert WebhookRecebido.objects.count() == 2
    assert sorted(WebhookRecebido.objects.values_list("resultado", flat=True)) == [
        "baixada",
        "ja_baixada",
    ]
    pagou = EventoAuditoria.objects.filter(acao="conta_receber.pagar", objeto_id=carlos.pk)
    assert pagou.count() == 1
    assert (pagou.get().ator_tipo, pagou.get().regra) == ("sistema", "AUT-05")
    assert any("recebemos R$ 306,09" in m.texto for m in whatsapp.caixa_de_saida)


def test_aut_05_t029_status_desconhecido_avisa_o_financeiro(
    cenario,  # noqa: F811
    com_carteira,  # noqa: F811
    subconta,
    com_asaas,
    django_capture_on_commit_callbacks,
):
    """CA-029-08: status que o Giro não conhece vira aviso, nunca baixa."""
    carlos = _carlos_com_juros(com_carteira)
    com_asaas("pix_carlos_cliente_novo", "consultar_status_desconhecido")
    assert _gerar_pix(cenario, carlos).status_code == 201
    assert _webhook(django_capture_on_commit_callbacks, _aviso("evt_t029_3")) == 200
    carlos.refresh_from_db()
    assert carlos.status == "aberta"
    assert WebhookRecebido.objects.get().resultado == "status_desconhecido"
    avisados = set(
        Notificacao.objects.filter(tipo="pendencia_pagamento").values_list(
            "destinatario__nome", flat=True
        )
    )
    assert avisados == {"Mariana", "Lúcia"}


def test_aut_05_t029_asaas_fora_do_ar_nao_perde_o_aviso(
    cenario,  # noqa: F811
    com_carteira,  # noqa: F811
    subconta,
    com_asaas,
):
    """CA-029-16: a consulta falha, o aviso fica sem `processado_em` e a tarefa tenta de novo."""
    carlos = _carlos_com_juros(com_carteira)
    com_asaas("pix_carlos_cliente_novo", "consultar_fora_do_ar")
    assert _gerar_pix(cenario, carlos).status_code == 201
    evento = EventoWebhook("asaas", "evt_t029_4", "PAYMENT_RECEIVED", "pay_t029carlos0001", "", "")
    webhook = financeiro.registrar_webhook(evento, {})
    assert webhook is not None
    with pytest.raises(ParceiroIndisponivel):
        financeiro.processar_webhook(webhook.pk)
    webhook.refresh_from_db()
    assert webhook.processado_em is None
    carlos.refresh_from_db()
    assert carlos.status == "aberta"


def test_aut_05_t029_tarefa_tenta_de_novo_com_o_asaas_fora():
    from apps.financeiro.tasks import aut_05_processar_webhook

    assert ParceiroIndisponivel in aut_05_processar_webhook.autoretry_for
    assert (aut_05_processar_webhook.max_retries or 0) >= 1


# --- Subconta (CA-029-01, CA-029-02, S-05) ---


DADOS_MOTO_RAPIDA: dict[str, Any] = {
    "nome": "Moto Rápida Locações Ltda",
    "documento": "12.345.678/0001-95",
    "email": "financeiro@motorapida.exemplo",
    "celular": "(85) 99999-0000",
    "logradouro": "Avenida Exemplo",
    "numero": "100",
    "bairro": "Centro",
    "cep": "60000-000",
    "faturamento_mensal_centavos": 7420000,
    "tipo_empresa": "limitada",
}


def test_fin_04_t029_conectar_recebimentos_guarda_a_chave_cifrada(cenario, com_asaas, settings):  # noqa: F811
    settings.GIRO_URL_WEBHOOK_PAGAMENTOS = ""
    gravacao = com_asaas("subconta_moto_rapida")
    conta = plataforma.conectar_recebimentos(**DADOS_MOTO_RAPIDA)

    chave = "chave-ficticia-da-subconta-t029"
    salva = ContaPagamento.objects.get(empresa=cenario.moto.empresa)
    assert salva.pk == conta.pk
    assert (salva.status, salva.carteira_id) == ("pendente", "c0c1688f-0000-4000-8000-000000000001")
    assert salva.chave_api_cifrada and chave not in salva.chave_api_cifrada
    assert salva.chave_api_cifrada_claro() == chave
    assert chave not in str(salva) and chave not in repr(salva)
    # O token do webhook vai para o Asaas e só o hash fica guardado (S-14).
    token = gravacao.corpo("POST", "/accounts")["webhooks"][0]["authToken"]
    assert len(token) >= 32
    assert salva.webhook_token_hash == hash_do_token(token)
    assert gravacao.corpo("POST", "/accounts")["webhooks"][0]["url"].endswith(
        "/api/webhooks/pagamentos/asaas/"
    )
    assert gravacao.corpo("POST", "/accounts")["cpfCnpj"] == "12345678000195"
    # Auditoria sem a chave e sem o hash (S-05, S-06).
    evento = EventoAuditoria.objects.get(acao="conta_pagamento.criar")
    texto = f"{evento.antes}{evento.depois}"
    assert chave not in texto and token not in texto and salva.webhook_token_hash not in texto
    assert salva.chave_api_cifrada not in texto
    # O passo "Recebimentos" só conta com a subconta aprovada (IMP-07, T-366).
    from apps.plataforma.models import UsoEmpresa

    uso = UsoEmpresa.objects.get(empresa=cenario.moto.empresa)
    assert "recebimentos" not in uso.passos_implantacao


def test_fin_04_t029_subconta_em_analise_nao_gera_pix(cenario, com_carteira, com_asaas):  # noqa: F811
    """CA-029-02: até o Asaas aprovar, 422 `recebimentos_desligados`; aprovada, liga."""
    com_asaas("subconta_moto_rapida", "subconta_em_analise", "subconta_aprovada")
    plataforma.conectar_recebimentos(**DADOS_MOTO_RAPIDA)
    resposta = _gerar_pix(cenario, _carlos(com_carteira))
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "recebimentos_desligados"

    connection.set_tenant(cenario.moto.empresa)
    for esperado in ("pendente", "aprovada"):
        conta = plataforma.atualizar_recebimentos()
        assert conta is not None
        assert conta.status == esperado
    assert EventoAuditoria.objects.filter(acao="conta_pagamento.aprovada").count() == 1


def test_fin_04_t029_subconta_recusada_nao_grava_nada(cenario, com_asaas):  # noqa: F811
    com_asaas("subconta_recusada")
    with pytest.raises(ErroDeRegra) as erro:
        plataforma.conectar_recebimentos(**DADOS_MOTO_RAPIDA)
    assert (erro.value.codigo, erro.value.mensagem) == (
        "parceiro_recusou",
        "O CPF/CNPJ informado é inválido.",
    )
    assert not ContaPagamento.objects.exists()


def test_fin_04_t029_recebimentos_conectados_uma_vez(cenario, subconta):  # noqa: F811
    with pytest.raises(Conflito):
        plataforma.conectar_recebimentos(**DADOS_MOTO_RAPIDA)


# --- Nada do Asaas fora da interface (CA-029-17, ADR 0011) ---


def _importa(arquivo: Path, modulo: str) -> bool:
    texto = arquivo.read_text(encoding="utf-8")
    return f"from {modulo}" in texto or f"import {modulo}" in texto


def test_fin_04_t029_so_financeiro_e_plataforma_usam_pagamentos():
    fora = [
        str(arquivo.relative_to(RAIZ))
        for arquivo in (RAIZ / "apps").rglob("*.py")
        if "tests" not in arquivo.parts
        and arquivo.parts[len(RAIZ.parts) + 1] not in ("financeiro", "plataforma")
        and _importa(arquivo, "integracoes.pagamentos")
    ]
    assert not fora


def test_fin_04_t029_asaas_so_dentro_da_interface():
    fora = [
        str(arquivo.relative_to(RAIZ))
        for pasta in ("apps", "comum", "config", "integracoes")
        for arquivo in (RAIZ / pasta).rglob("*.py")
        if "tests" not in arquivo.parts
        and arquivo != RAIZ / "integracoes" / "pagamentos" / "__init__.py"
        and (
            _importa(arquivo, "integracoes.pagamentos.asaas")
            or "from .asaas" in arquivo.read_text(encoding="utf-8")
        )
    ]
    assert not fora
