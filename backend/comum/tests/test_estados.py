import pytest

from apps.auditoria.models import EventoAuditoria
from comum.erros import TransicaoInvalida
from comum.estados import MudancaDeStatusForaDaMaquina, transicionar
from tests.app_exemplo.models import Pedido


def test_transicao_permitida_grava_status_e_exatamente_um_evento(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    antes = EventoAuditoria.objects.count()

    transicionar(pedido, "ativa", motivo="Retirada")

    pedido.refresh_from_db()
    assert pedido.status == "ativa"
    assert EventoAuditoria.objects.count() == antes + 1
    evento = EventoAuditoria.objects.first()
    assert evento is not None
    assert evento.acao == "pedido.ativa"
    assert evento.objeto_codigo == pedido.codigo
    assert evento.antes == {"status": "reservada"}
    assert evento.depois == {"status": "ativa"}
    assert evento.motivo == "Retirada"


def test_transicao_fora_da_tabela_e_recusada_com_409(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    antes = EventoAuditoria.objects.count()

    with pytest.raises(TransicaoInvalida) as erro:
        transicionar(pedido, "encerrada")

    assert erro.value.status_http == 409
    assert erro.value.codigo == "LOC-00"
    assert erro.value.detalhes == {
        "de": "reservada",
        "para": "encerrada",
        "permitidos": ["ativa", "cancelada"],
    }
    assert "Reservada" in erro.value.mensagem
    pedido.refresh_from_db()
    assert pedido.status == "reservada"
    assert EventoAuditoria.objects.count() == antes


def test_transicao_usa_o_status_do_banco_e_nao_o_da_memoria(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    copia = Pedido.objects.get(pk=pedido.pk)
    transicionar(pedido, "cancelada")
    with pytest.raises(TransicaoInvalida):
        transicionar(copia, "ativa")


def test_save_recusa_mudanca_de_status_direta(empresa_a):
    pedido = Pedido.objects.create(cliente="Larissa")
    pedido.status = "ativa"
    with pytest.raises(MudancaDeStatusForaDaMaquina):
        pedido.save()


def test_save_depois_de_reler_o_status_mudado_por_outra_copia(empresa_a):
    """A cópia relida do banco salva outros campos sem acusar mudança de status (T-186)."""
    pedido = Pedido.objects.create(cliente="Larissa")
    copia = Pedido.objects.get(pk=pedido.pk)
    transicionar(pedido, "ativa")
    copia.refresh_from_db()
    copia.cliente = "L."
    copia.save(update_fields=["cliente"])
    copia.status = "cancelada"
    with pytest.raises(MudancaDeStatusForaDaMaquina):
        copia.save()


def test_update_recusa_mudanca_de_status(empresa_a):
    Pedido.objects.create(cliente="Larissa")
    with pytest.raises(MudancaDeStatusForaDaMaquina):
        Pedido.objects.filter(cliente="Larissa").update(status="ativa")
    assert Pedido.objects.filter(cliente="Larissa").update(cliente="L.") == 1
