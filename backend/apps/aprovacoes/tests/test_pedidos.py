"""Porta dos pedidos de aprovação (ADR 0019): os testes obrigatórios da decisão."""

import pytest
from django.db import IntegrityError, transaction

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.filiais.models import Filial
from comum import aprovacoes, eventos
from comum.aprovacoes import PedidoPendente


@pytest.fixture
def pessoas(empresa_a):
    filial = Filial.objects.create(
        nome="Filial Centro",
        cep="60325000",
        logradouro="Av. Bezerra de Menezes",
        numero="1200",
        bairro="São Gerardo",
        cidade="Fortaleza",
        uf="CE",
        matriz=True,
    )
    joao = Usuario.objects.create_user("joao@a.com", "x", nome="João", perfil="vistoriador")
    rodrigo = Usuario.objects.create_user("rodrigo@a.com", "x", nome="Rodrigo", perfil="gerente")
    return filial, joao, rodrigo


def _pedir(filial, solicitante, origem_id=501):
    return aprovacoes.pedir(
        tipo="APR-06",
        origem_tipo="veiculo",
        origem_id=origem_id,
        origem_codigo="SAK1D39",
        filial_id=filial.pk,
        solicitante=solicitante,
        titulo="Correção de km para baixo",
        detalhe="SAK1D39 · 3.500 → 3.400 km · Erro de digitação",
        motivo="Erro de digitação",
        dados={"km_novo": 3400, "km_anterior": 3500},
    )


def test_apr_10_pedir_grava_o_pedido_e_a_auditoria(pessoas):
    filial, joao, _ = pessoas
    ref = _pedir(filial, joao)
    assert (ref.tipo, ref.status) == ("APR-06", "pendente")
    pedido = PedidoAprovacao.objects.get(pk=ref.id)
    assert (pedido.solicitante, pedido.motivo_pedido, pedido.aprovador) == (
        joao,
        "Erro de digitação",
        None,
    )
    evento = EventoAuditoria.objects.get(acao="pedido_aprovacao.pedir")
    assert (evento.objeto_id, evento.regra, evento.filial_id) == (pedido.pk, "APR-10", filial.pk)
    assert evento.depois["dados"] == {"km_novo": 3400, "km_anterior": 3500}
    assert aprovacoes.pendente(tipo="APR-06", origem_tipo="veiculo", origem_id=501) == ref


def test_apr_06_pedido_repetido_e_pedido_pendente(pessoas):
    filial, joao, rodrigo = pessoas
    primeiro = _pedir(filial, joao)
    with pytest.raises(PedidoPendente) as erro:
        _pedir(filial, rodrigo)
    assert (erro.value.codigo, erro.value.status_http) == ("pedido_pendente", 409)
    assert erro.value.detalhes == {"pedido_id": primeiro.id}
    assert _pedir(filial, joao, origem_id=502).id != primeiro.id  # outra origem, outro pedido
    assert PedidoAprovacao.objects.count() == 2


def test_apr_09_quem_pede_nao_aprova_no_banco(pessoas):
    filial, joao, rodrigo = pessoas
    pedido = PedidoAprovacao.objects.get(pk=_pedir(filial, joao).id)
    with pytest.raises(IntegrityError), transaction.atomic():
        PedidoAprovacao.objects.filter(pk=pedido.pk).update(aprovador=joao)
    PedidoAprovacao.objects.filter(pk=pedido.pk).update(aprovador=rodrigo)


def test_apr_10_cancelar_pendentes_publica_a_decisao(pessoas):
    filial, joao, _ = pessoas
    ref = _pedir(filial, joao)
    recebidos: list[dict[str, object]] = []

    def guardar(**dados):
        recebidos.append(dados)

    eventos.assinar("aprovacoes.pedido_decidido", guardar)
    try:
        cancelados = aprovacoes.cancelar_pendentes(
            origem_tipo="veiculo", origem_id=501, motivo="Veículo baixado"
        )
    finally:
        eventos.remover_assinante("aprovacoes.pedido_decidido", guardar)
    assert cancelados == 1
    assert PedidoAprovacao.objects.get(pk=ref.id).status == "cancelado"
    assert [(r["pedido_id"], r["status"], r["dados"]) for r in recebidos] == [
        (ref.id, "cancelado", {"km_novo": 3400, "km_anterior": 3500})
    ]
    assert aprovacoes.pendente(tipo="APR-06", origem_tipo="veiculo", origem_id=501) is None


def test_apr_10_pedir_sem_implementacao_registrada_falha(monkeypatch):
    monkeypatch.setattr(aprovacoes, "_pedir", None)
    with pytest.raises(RuntimeError, match="ADR 0019"):
        aprovacoes.pedir(
            tipo="APR-06",
            origem_tipo="veiculo",
            origem_id=1,
            origem_codigo=None,
            filial_id=1,
            solicitante=None,
            titulo="t",
            detalhe="d",
        )
