"""T-365 · Reativar a empresa cancelada pela equipe Giro (`assinatura.md`, "Mudança de ciclo e
reativação pela equipe"; PLT-06, AUD-08; CA-ASS-46 e 49; B-02 da T-199).

O CA-ASS-46 (`test_plt_06_reativar_so_com_atrasada_paga`) fica no arquivo da T-195, onde era
`xfail`. Relógio de referência: Moto Rápida em teste de 07 a 21 out, FAT-0001 de R$ 449,00
vencendo em 22 out (período de 22 out a 21 nov), e as seguintes todo dia 22.
"""

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django_tenants.utils import schema_exists

from apps.contas.models import Usuario
from apps.plataforma import services
from apps.plataforma.models import FaturaAssinatura, FormaPagamentoAssinatura
from comum.erros import Conflito, ErroDeValidacao
from integracoes.pagamentos import falso as pagamentos

from .conftest import HOST_PLATAFORMA, SENHA, codigo_atual
from .test_t185_assinatura import MotoRapida, _mudar
from .test_t186b_faturas_cobranca import _ativa_com_boleto, _baixar
from .test_t195_cancelar_pausar import (
    _cancelada_em_22_out,
    _cancelar,
    _codigos,
    _em,
    _eventos,
    _gerar,
    _status,
    _virar,
)

MOTIVO = "Pedido no chamado #1090"
EMPRESAS_NO_ADMIN = "/admin/plataforma/empresa/"


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    yield MotoRapida(criar_empresa())
    pagamentos.limpar()


def _recusa(moto: MotoRapida, motivo: str = MOTIVO) -> tuple[str, str]:
    with pytest.raises(Conflito) as erro:
        services.reativar_empresa(moto.recarregar(), motivo=motivo)
    return erro.value.codigo, erro.value.mensagem


def test_plt_06_reativar_no_periodo_pago(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-49: `ativa`, FAT-0001 (22 out a 21 nov) paga; upgrade para o Completo em 01 nov,
    com a diferença de R$ 304,84 vencendo em 04 nov e não paga (`inadimplente` em 05 nov);
    cancela em 10 nov (`cancelada` na hora); a diferença é paga em 15 nov pela 2ª via, e a equipe
    reativa em 15 nov → `ativa`, sem fatura de 15 nov; a nova, de R$ 899,00, vence em 22 nov,
    "Plano Completo · 22 nov a 21 dez", e as seguintes continuam todo dia 22."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-01")
    assert _mudar(moto.api(), "Completo", valor=30484).status_code == 200
    connection.set_schema_to_public()
    diferenca = moto.fatura("FAT-0002")
    assert (diferenca.valor_centavos, diferenca.vencimento) == (30484, date(2026, 11, 4))
    _virar(relogio, "2026-11-05")
    assert _status(moto) == "inadimplente"
    _em(relogio, "2026-11-10")
    with django_capture_on_commit_callbacks(execute=True):
        assert _cancelar(moto.api()).json()["status"] == "cancelada"
    connection.set_schema_to_public()
    assert FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).forma == ""

    _em(relogio, "2026-11-15")
    assert _recusa(moto) == ("fatura_em_atraso", "Receba a fatura em atraso antes de reativar.")
    assert _status(moto) == "cancelada"
    # Sem forma depois do cancelamento, a 2ª via sai pelo "Pagar" com o meio (CA-ASS-27).
    segunda_via = services.pagar_fatura(moto.recarregar(), "FAT-0002", "boleto")
    pagamentos.simular_pagamento(segunda_via.cobranca_externa_id or "")
    assert _baixar(segunda_via.cobranca_externa_id, "evt-fat-0002-2via") == "baixada"
    services.reativar_empresa(moto.recarregar(), motivo=MOTIVO)

    empresa = moto.recarregar()
    assert (empresa.status, empresa.dia_vencimento, empresa.plano.nome) == ("ativa", 22, "Completo")
    assert (empresa.cancelada_em, empresa.acesso_ate, empresa.apagar_em) == (None, None, None)
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "paga", "FAT-0003": "aberta"}
    nova = moto.fatura("FAT-0003")
    assert (nova.valor_centavos, nova.vencimento, nova.tipo) == (
        89900,
        date(2026, 11, 22),
        "mensalidade",
    )
    assert nova.descricao == "Plano Completo · 22 nov a 21 dez"
    assert not nova.cobranca_externa_id  # sem forma; o administrador escolhe ao entrar (PLT-13)
    # A geração de 17 nov não cria outra fatura para o mesmo período.
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    assert set(_codigos(moto)) == {"FAT-0001", "FAT-0002", "FAT-0003"}


def test_plt_06_reativar_audita_nos_dois_lugares(moto, relogio):
    """Auditoria `empresa.reativar` no `public` e na empresa, com o motivo, e a empresa volta a
    entrar no sistema."""
    _cancelada_em_22_out(moto, relogio)
    _em(relogio, "2026-12-01")
    services.reativar_empresa(moto.recarregar(), motivo=MOTIVO)
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.reativar", schema)[-1]
        assert (evento.motivo, evento.regra) == (MOTIVO, "PLT-06")
        assert evento.antes["status"] == "cancelada"
        assert evento.antes["apagar_em"] == "2027-01-20"
        assert evento.depois == {"dia_vencimento": 1, "fatura": "FAT-0002", "por": "equipe"}
        assert _eventos("empresa.ativa", schema)
    resposta = moto.api().get("/api/assinatura/")
    connection.set_schema_to_public()
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ativa"


def test_plt_06_reativar_recusas(moto, relogio):
    """Sem motivo, fora da `cancelada` e com a empresa só com o cancelamento marcado: nada muda."""
    with pytest.raises(ErroDeValidacao) as erro:
        services.reativar_empresa(moto.recarregar(), motivo="  ")
    assert erro.value.campos == {"motivo": ["Informe o motivo."]}
    assert _recusa(moto) == ("transicao_empresa", "Só a empresa cancelada pode ser reativada.")
    _em(relogio, "2026-10-10")
    assert _cancelar(moto.api()).status_code == 200  # marcado, acesso até 21 out
    assert _recusa(moto)[0] == "transicao_empresa"
    assert _status(moto) == "em_teste"


def test_aud_08_reativar_recusa_o_apagamento_comecado(moto, relogio):
    """B-02 da T-199: no dia do apagamento (`apagar_em`, 20 jan 2027) a reativação é recusada,
    mesmo antes de a tarefa das 03:30 terminar; depois do apagamento, também. No último dos 90
    dias (19 jan), ainda reativa."""
    _cancelada_em_22_out(moto, relogio)
    _em(relogio, "2027-01-20", "03:00")
    assert _recusa(moto) == (
        "transicao_empresa",
        "O apagamento dos dados desta empresa já começou. Não dá para reativar.",
    )
    _em(relogio, "2027-01-20", "03:30")
    assert services.apagar_empresas() == 1
    assert not schema_exists(moto.empresa.schema_name)
    assert _recusa(moto) == ("transicao_empresa", "Os dados desta empresa já foram apagados.")


def test_aud_08_reativada_perde_o_aviso_do_apagamento(moto, relogio):
    """O aviso de 7 dias já enviado sai junto com o apagamento marcado: se ela cancelar de novo,
    o aviso vale para o apagamento novo."""
    _cancelada_em_22_out(moto, relogio)
    _em(relogio, "2027-01-13", "09:00")
    assert services.avisar_apagamentos() == 1
    _em(relogio, "2027-01-19")
    services.reativar_empresa(moto.recarregar(), motivo=MOTIVO)
    empresa = moto.recarregar()
    assert (empresa.status, empresa.aviso_apagamento_enviado_em) == ("ativa", None)
    nova = moto.fatura("FAT-0002")
    assert (nova.vencimento, nova.descricao) == (
        date(2027, 1, 19),
        "Plano Profissional · 19 jan a 18 fev",
    )


def test_plt_06_reativada_antes_do_fim_da_forma_fica_com_ela(moto, relogio):
    """A tarefa que encerra a forma de pagamento tenta de novo por até 24 h. Se a empresa voltou
    antes, ela não apaga a forma de quem voltou."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    moto.pagar_fat_0001()
    moto.estado(status="inadimplente")
    _em(relogio, "2026-10-25")
    assert _cancelar(moto.api()).json()["status"] == "cancelada"  # sem rodar o on_commit
    services.reativar_empresa(moto.recarregar(), motivo=MOTIVO)
    assert services.encerrar_forma_pagamento(moto.empresa.pk) == "reativada"
    assert FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).forma == "boleto"


# --- Django Admin (plataforma.md, "Faturas de todas as empresas") ---


@pytest.fixture
def dono_do_admin(equipe):
    dono, dispositivo = equipe["Você"]
    Usuario.objects.filter(pk=dono.pk).update(is_staff=True, is_superuser=True)
    dono.refresh_from_db()
    return dono, dispositivo


def _admin(dono: Any, dispositivo: Any) -> Client:
    navegador = Client(HTTP_HOST=HOST_PLATAFORMA, REMOTE_ADDR="10.0.0.5", HTTP_USER_AGENT="pytest")
    resposta = navegador.post(
        "/admin/login/",
        {
            "username": dono.email,
            "password": SENHA,
            "otp_token": codigo_atual(dispositivo),
            "next": "/admin/",
        },
    )
    connection.set_schema_to_public()
    assert resposta.status_code == 302, resposta.content
    return navegador


def _acao(navegador: Client, empresa_id: int, motivo: str) -> list[str]:
    resposta = navegador.post(
        EMPRESAS_NO_ADMIN,
        {"action": "reativar", "_selected_action": [empresa_id], "motivo": motivo},
        follow=True,
    )
    connection.set_schema_to_public()
    assert resposta.status_code == 200
    return [str(m) for m in resposta.context["messages"]]


def test_plt_06_admin_reativa_pelo_servico(moto, relogio, dono_do_admin):
    """A ação "Reativar" pede o motivo, mostra a recusa do serviço e grava a auditoria com o
    usuário da equipe."""
    dono, dispositivo = dono_do_admin
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    moto.estado(status="inadimplente")
    FaturaAssinatura._base_manager.filter(empresa=moto.empresa, codigo="FAT-0001").update(
        status="atrasada"
    )
    _em(relogio, "2026-10-25")
    assert _cancelar(moto.api()).json()["status"] == "cancelada"
    navegador = _admin(dono, dispositivo)
    pk = moto.empresa.pk

    assert _acao(navegador, pk, "") == ["Informe o motivo para reativar."]
    assert _acao(navegador, pk, MOTIVO) == [
        "Moto Rápida: Receba a fatura em atraso antes de reativar."
    ]
    assert _status(moto) == "cancelada"
    moto.pagar_fat_0001()
    assert _acao(navegador, pk, MOTIVO) == ["Moto Rápida reativada."]
    assert _status(moto) == "ativa"
    evento = _eventos("empresa.reativar", "public")[-1]
    assert (evento.ator_tipo, evento.ator_id, evento.motivo) == ("usuario", dono.pk, MOTIVO)


def test_plt_06_so_o_dono_reativa_no_admin(moto, relogio, equipe):
    """Quem entra no Admin sem ser o dono não vê a ação."""
    pessoa, dispositivo = equipe["Paula Andrade"]  # financeiro
    Usuario.objects.filter(pk=pessoa.pk).update(is_staff=True, is_superuser=True)
    pessoa.refresh_from_db()
    _cancelada_em_22_out(moto, relogio)
    navegador = _admin(pessoa, dispositivo)
    resposta = navegador.get(EMPRESAS_NO_ADMIN)
    connection.set_schema_to_public()
    assert resposta.status_code == 200
    # Sem nenhuma ação permitida, o Admin nem mostra o seletor.
    seletor = resposta.context["action_form"]
    assert seletor is None or "reativar" not in dict(seletor.fields["action"].choices)
    _acao(navegador, moto.empresa.pk, MOTIVO)
    assert _status(moto) == "cancelada"
