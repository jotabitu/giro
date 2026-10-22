"""T-345 · Achados da T-199 no cancelamento (`docs/seguranca/2026-10-20-t199-cancelamento.md`):
2 etapas recentes para cancelar (M-01), a empresa cancelada e a apagada fora do alcance do
suporte e do `public` (M-02), a recusa do parceiro (M-03), a variável de migração (B-01) e os
cabeçalhos do 403 `empresa_cancelada` (B-03). PLT-06, PLT-07, AUD-08, USR-02."""

import logging
from typing import Any

import pytest
from django.db import connection, transaction
from django.test import override_settings
from django_tenants.utils import schema_context, tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.plataforma import services
from apps.plataforma.models import AcessoSuporte, Dominio, FormaPagamentoAssinatura
from comum.auditoria import Categoria
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from comum.erros import Conflito, ParceiroForaDoAr
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.base import Autorizacao, ParceiroIndisponivel

from .conftest import cliente as cliente_http
from .test_t185_assinatura import _criar_matriz
from .test_t186b_faturas_cobranca import _ativa_com_cartao, _baixar
from .test_t195_cancelar_pausar import (
    CANCELAMENTO,
    EMPRESA_CANCELADA,
    HOST,
    _cancelada_em_22_out,
    _cancelar,
    _em,
    _erro,
    _eventos,
    _status,
    _virar,
    moto,  # noqa: F401 - fixture
)

PEDE_2_ETAPAS = {
    "codigo": "2fa_recente",
    "mensagem": "Confirme o código do autenticador para cancelar a assinatura.",
}


def _api_sem_2_etapas_recentes(moto: Any) -> Any:  # noqa: F811
    """Token renovado (rotação): tem `otp` no `amr`, mas não o `auth_time` do login."""
    mariana = moto.pessoas["Mariana"]
    with tenant_context(moto.empresa):
        login = emitir_tokens(mariana, AMR_SENHA_E_CODIGO)
        renovado = emitir_tokens(mariana, AMR_SENHA_E_CODIGO, sid=login["sid"]).access_token
    connection.set_schema_to_public()
    assert "auth_time" not in renovado
    return cliente_http(HOST, str(renovado))


def _apagada(moto: Any, relogio: Any) -> Any:  # noqa: F811
    _cancelada_em_22_out(moto, relogio)
    _em(relogio, "2027-01-20", "03:30")
    assert services.apagar_empresas() == 1
    return moto.recarregar()


def _eventos_no_publico() -> int:
    with schema_context("public"):
        return EventoAuditoria.objects.count()


# --- M-01 · 2 etapas recentes para cancelar ---


def test_plt_06_cancelar_pede_2_etapas_recentes(moto, relogio):  # noqa: F811
    _em(relogio, "2026-10-10")
    api = _api_sem_2_etapas_recentes(moto)
    # Antes de qualquer outra conferência: o corpo vazio também recebe o 403, não o 400.
    for corpo in ({}, {"motivo": "preco_alto", "nome_confirmacao": "Moto Rápida"}):
        resposta = api.post(CANCELAMENTO, corpo, format="json")
        assert resposta.status_code == 403
        assert _erro(resposta) == PEDE_2_ETAPAS
    assert _status(moto) == "em_teste"
    assert moto.recarregar().acesso_ate is None
    # Com as 2 etapas confirmadas agora, cancela.
    assert _cancelar(moto.api()).status_code == 200
    # Desfazer não pede de novo: é reversível.
    assert api.delete(CANCELAMENTO).status_code == 200


# --- M-02 · Suporte na cancelada e a empresa apagada ---


def test_plt_07_suporte_nao_entra_na_cancelada(moto, relogio, mailoutbox):  # noqa: F811
    _cancelada_em_22_out(moto, relogio)
    mailoutbox.clear()
    with pytest.raises(Conflito) as recusa:
        moto.suporte("ver")
    assert (recusa.value.codigo, recusa.value.mensagem) == (
        "empresa_cancelada",
        "Esta empresa cancelou a assinatura. O suporte não entra.",
    )
    with schema_context("public"):
        assert not AcessoSuporte.objects.filter(empresa=moto.empresa).exists()
    assert mailoutbox == []


def test_aud_08_empresa_apagada_nao_cai_no_publico(moto, relogio):  # noqa: F811
    """Sem o schema, o `search_path` "<schema>, public" acharia as tabelas da plataforma: a entrada
    de `plataforma` no schema da empresa recusa a apagada, e nada é lido nem gravado no public."""
    empresa = _apagada(moto, relogio)
    assert empresa.apagada_em is not None
    antes = _eventos_no_publico()
    with pytest.raises(services.EmpresaApagada):
        services.no_schema_da_empresa(empresa)
    with pytest.raises(services.EmpresaApagada):
        services.destinatarios_da_cobranca(empresa)
    with pytest.raises(services.EmpresaApagada):
        services.recalcular_uso(empresa)
    with pytest.raises(services.EmpresaApagada), transaction.atomic():
        services._registrar_nos_dois(
            empresa,
            "empresa.teste",
            antes={},
            depois={},
            categoria_publica=Categoria.CONFIGURACOES,
        )
    with pytest.raises(Conflito):
        moto.suporte("ver_editar")
    assert _eventos_no_publico() == antes


# --- M-03 · Recusa do parceiro ---


def _com_pagador(moto: Any, relogio: Any, capturar: Any) -> str:  # noqa: F811
    """Boleto pago em 18 out: a forma guarda o cliente na conta principal."""
    _criar_matriz(moto)
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _em(relogio, "2026-10-18")
    fatura = services.pagar_fatura(moto.recarregar(), "FAT-0001")
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0001") == "baixada"
    cliente = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).cliente_externo_id
    assert cliente
    _virar(relogio, "2026-10-22")
    _em(relogio, "2026-11-05")
    assert _cancelar(moto.api()).status_code == 200
    _virar(relogio, "2026-11-22", capturar)
    return str(cliente)


def test_aud_08_recusa_do_parceiro_nao_trava_o_apagamento(
    moto,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
    caplog,
):
    cliente = _com_pagador(moto, relogio, django_capture_on_commit_callbacks)
    pagamentos.recusar_operacao("anonimizar_pagador", "Campo email inválido.")
    _em(relogio, "2027-02-20", "03:30")
    with caplog.at_level(logging.ERROR):
        assert services.apagar_empresas() == 1
    empresa = moto.recarregar()
    assert empresa.apagada_em is not None
    assert (empresa.razao_social, empresa.email_cobranca) == ("", "")
    assert not FormaPagamentoAssinatura.objects.filter(empresa=empresa).exists()
    assert not Dominio.objects.filter(tenant_id=empresa.pk).exists()
    assert pagamentos.anonimizados == []
    assert pagamentos.pagadores[cliente].email  # ficou no parceiro, para a equipe resolver
    evento = _eventos("empresa.apagar", "public")[-1]
    assert evento.depois["pagador_anonimizado"] is False
    assert f"Apagamento da empresa {empresa.pk}: o parceiro recusou anonimizar" in caplog.text
    assert "Campo email" not in caplog.text  # o log leva só o id


def test_aud_08_pagador_anonimizado_no_evento(
    moto,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    cliente = _com_pagador(moto, relogio, django_capture_on_commit_callbacks)
    _em(relogio, "2027-02-20", "03:30")
    assert services.apagar_empresas() == 1
    assert pagamentos.anonimizados == [cliente]
    assert _eventos("empresa.apagar", "public")[-1].depois["pagador_anonimizado"] is True


def _forma(moto: Any) -> FormaPagamentoAssinatura:  # noqa: F811
    return FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)


def _cartao_com_autorizacao(moto: Any, relogio: Any) -> str:  # noqa: F811
    """O cartão guardado e uma autorização do Pix ainda ativa no parceiro (a forma trocada)."""
    _ativa_com_cartao(moto, relogio)
    autorizacao = "aut_falso_t345"
    pagamentos.autorizacoes[autorizacao] = Autorizacao(autorizacao, "ativa")
    FormaPagamentoAssinatura.objects.filter(empresa=moto.empresa).update(
        autorizacao_externa_id=autorizacao
    )
    assert _forma(moto).cartao_final
    return str(autorizacao)


def test_plt_06_fim_da_forma_esquece_o_cartao_com_recusa(moto, relogio, caplog):  # noqa: F811
    autorizacao = _cartao_com_autorizacao(moto, relogio)
    pagamentos.recusar_operacao("cancelar_autorizacao", "Autorização em processamento.")
    with caplog.at_level(logging.ERROR):
        assert services.encerrar_forma_pagamento(moto.empresa.pk) == "parceiro_recusou"
    forma = _forma(moto)
    assert (forma.forma, forma.cartao_final, forma.cartao_bandeira) == ("", "", "")
    assert not forma.cartao_token_cifrado
    assert forma.autorizacao_externa_id == autorizacao  # guardada, para a equipe resolver
    assert "o parceiro recusou cancelar a autorização" in caplog.text
    assert "processamento" not in caplog.text


def test_plt_06_autorizacao_ja_cancelada_conta_como_encerrada(moto, relogio):  # noqa: F811
    autorizacao = _cartao_com_autorizacao(moto, relogio)
    pagamentos.autorizacoes[autorizacao] = Autorizacao(autorizacao, "cancelada")
    pagamentos.recusar_operacao("cancelar_autorizacao", "Autorização já cancelada.")
    assert services.encerrar_forma_pagamento(moto.empresa.pk) == "encerrada"
    forma = _forma(moto)
    assert (forma.forma, forma.autorizacao_externa_id, forma.cartao_final) == ("", "", "")


def test_plt_06_fim_da_forma_com_o_parceiro_fora_do_ar(moto, relogio, monkeypatch):  # noqa: F811
    autorizacao = _cartao_com_autorizacao(moto, relogio)

    def fora_do_ar(*_: Any) -> None:
        raise ParceiroIndisponivel("timeout")

    monkeypatch.setattr(pagamentos.PagamentosFalso, "cancelar_autorizacao", fora_do_ar)
    with pytest.raises(ParceiroForaDoAr):
        services.encerrar_forma_pagamento(moto.empresa.pk)
    forma = _forma(moto)
    assert (forma.cartao_final, forma.autorizacao_externa_id) == ("", autorizacao)
    assert not forma.cartao_token_cifrado
    # A tarefa tenta de novo; com o parceiro de volta, a autorização sai.
    monkeypatch.undo()
    assert services.encerrar_forma_pagamento(moto.empresa.pk) == "encerrada"
    assert _forma(moto).autorizacao_externa_id == ""


# --- B-01 · Sem a conexão de migração ---


def test_aud_08_apagar_sem_database_url_migracao_avisa(moto, relogio, caplog):  # noqa: F811
    _cancelada_em_22_out(moto, relogio)
    _em(relogio, "2027-01-20", "03:30")
    with override_settings(DATABASE_URL_MIGRACAO=""), caplog.at_level(logging.ERROR):
        assert services.apagar_empresas() == 1
    assert "aud_08_apagar_empresas sem DATABASE_URL_MIGRACAO" in caplog.text


# --- B-03 · Cabeçalhos de segurança no 403 da cancelada ---


def test_aud_08_cancelada_responde_com_os_cabecalhos_de_seguranca(moto, relogio):  # noqa: F811
    api = moto.api()
    _cancelada_em_22_out(moto, relogio)
    resposta = api.get("/api/assinatura/")
    assert resposta.status_code == 403
    assert resposta.json() == EMPRESA_CANCELADA
    assert resposta["X-Content-Type-Options"] == "nosniff"
    assert resposta["X-Frame-Options"] == "DENY"
