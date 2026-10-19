"""T-186 (parte 3) · Régua da assinatura `AUT-13` (`docs/api/assinatura.md`, "Faturas, cobrança e
régua"; PLT-02).

Relógio de referência (ADR 0021): Moto Rápida, FAT-0001 de R$ 449,00 vencendo em 22 out. Às
09:00: D-3 (19 out) lembrete por e-mail; D0 (22 out) e D+3 (25 out) e-mail e WhatsApp; D+7
(29 out) aviso de suspensão por e-mail e a tarefa de ligação para a equipe Giro. Os e-mails vão
para o e-mail de cobrança e os administradores; o WhatsApp, para o responsável da compra.
"""

from collections.abc import Iterator

import pytest
from django.db import connection
from django_tenants.utils import schema_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.plataforma import services
from integracoes.pagamentos import falso as pagamentos
from integracoes.whatsapp import falso as whatsapp

from .test_t185_assinatura import MotoRapida
from .test_t186b_faturas_cobranca import _ativa_com_cartao, _baixar, _gerar

COBRANCA = "financeiro@motorapida.com.br"
MARIANA = "mariana@motorapida.com.br"
CELULAR = "85999990000"
EQUIPE = "lucas@girolocadoras.com.br"


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    whatsapp.caixa_de_saida.clear()
    moto = MotoRapida(criar_empresa())
    moto.estado(email_cobranca=COBRANCA, responsavel_telefone=CELULAR)
    with schema_context("public"):
        Usuario.objects.create_user(
            EQUIPE, "senha-forte-123", nome="Lucas Prado", funcao_plataforma="financeiro"
        )
    connection.set_schema_to_public()
    yield moto
    pagamentos.limpar()
    whatsapp.caixa_de_saida.clear()


def _regua(relogio, dia: str) -> dict[str, int]:
    relogio.em(f"{dia} 09:00")
    return services.regua_da_assinatura()


def _eventos(acao: str) -> list[EventoAuditoria]:
    with schema_context("public"):
        return list(EventoAuditoria.objects.filter(acao=acao).order_by("id"))


def _com_boleto_emitido(moto: MotoRapida, relogio, capturar) -> None:
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", capturar)


def test_aut_13_ca_ass_10_lembrete_d3_por_email(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """D-3 em 19 out: só e-mail, para o e-mail de cobrança e a Mariana, com o boleto. Nem antes,
    nem depois, nem duas vezes no mesmo dia."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-18") == {}
    assert _regua(relogio, "2026-10-19") == {"D-3": 1}
    assert [m.to for m in mailoutbox] == [[COBRANCA], [MARIANA]]  # um por destinatário (T-306)
    lembrete = mailoutbox[0]
    assert lembrete.subject == "Giro: a fatura FAT-0001 vence em 22 out"
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_boleto_url in lembrete.body
    assert "R$ 449,00" in lembrete.body
    assert "!" not in lembrete.body
    assert whatsapp.caixa_de_saida == []
    assert _regua(relogio, "2026-10-19") == {}
    assert len(mailoutbox) == 2
    evento = _eventos("fatura_assinatura.regua")[-1]
    assert (evento.depois["marco"], evento.regra, evento.ator_tipo) == ("D-3", "AUT-13", "sistema")
    assert _regua(relogio, "2026-10-20") == {}


def test_aut_13_ca_ass_11_d3_com_o_link_da_pagina_do_cartao(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Cartão escolhido e nenhum guardado: o lembrete de 19 out leva o link da página do
    parceiro."""
    services.escolher_forma_pagamento(moto.recarregar(), "cartao")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    assert _regua(relogio, "2026-10-19") == {"D-3": 1}
    pagina = moto.fatura("FAT-0001").cobranca_url_pagina
    assert pagina
    assert f"Cadastre o cartão e pague por este link: {pagina}" in mailoutbox[-1].body


def test_aut_13_d0_d3_d7_com_whatsapp_e_ligacao(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Sem pagar: D0 e D+3 por e-mail e WhatsApp; D+7 o aviso de suspensão (06 nov) por e-mail,
    sem WhatsApp, e a tarefa de ligação para o Financeiro da equipe Giro."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    _regua(relogio, "2026-10-19")
    mailoutbox.clear()

    assert _regua(relogio, "2026-10-22") == {"D0": 1}
    assert mailoutbox[-1].subject == "Giro: a fatura FAT-0001 vence hoje"
    assert [m.celular for m in whatsapp.caixa_de_saida] == [CELULAR]
    assert "vence hoje" in whatsapp.caixa_de_saida[-1].texto

    relogio.em("2026-10-23 00:05")
    services.virar_estados()  # a empresa vira inadimplente, e a régua segue
    assert _regua(relogio, "2026-10-25") == {"D+3": 1}
    assert mailoutbox[-1].subject == "Giro: a fatura FAT-0001 está em atraso"
    assert "06 nov" in mailoutbox[-1].body
    assert len(whatsapp.caixa_de_saida) == 2

    assert _regua(relogio, "2026-10-29") == {"D+7": 1}
    ligacao = next(m for m in mailoutbox[-3:] if m.to == [EQUIPE])
    avisos = [m for m in mailoutbox[-3:] if m is not ligacao]
    assert {m.subject for m in avisos} == {"Giro: a empresa Moto Rápida fica suspensa em 06 nov"}
    assert [m.to for m in avisos] == [[COBRANCA], [MARIANA]]
    assert CELULAR in ligacao.body and "FAT-0001" in ligacao.body
    assert len(whatsapp.caixa_de_saida) == 2  # o D+7 não vai por WhatsApp
    assert [e.regra for e in _eventos("fatura_assinatura.pedir_ligacao")] == ["PLT-02"]
    assert [e.depois["marco"] for e in _eventos("fatura_assinatura.regua")] == [
        "D-3",
        "D0",
        "D+3",
        "D+7",
    ]


def test_aut_13_ca_ass_03_paga_nao_recebe_mais_nada(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Paga em 18 out: nenhuma mensagem da régua depois (CA-ASS-03)."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    relogio.em("2026-10-18 10:00")
    fatura = moto.fatura("FAT-0001")
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-1") == "baixada"
    mailoutbox.clear()
    for dia in ("2026-10-19", "2026-10-22", "2026-10-25", "2026-10-29"):
        assert _regua(relogio, dia) == {}
    assert mailoutbox == []
    assert whatsapp.caixa_de_saida == []


def test_aut_13_ca_ass_12_cartao_recusado_a_regua_segue(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Cartão guardado: o D-3 de 19 nov diz que a cobrança é automática no cartão; recusado
    duas vezes, a régua segue em 25 e 29 nov com o "Pagar"."""
    token = _ativa_com_cartao(moto, relogio)
    pagamentos.recusar_cartao(token)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    assert _regua(relogio, "2026-11-19") == {"D-3": 1}
    assert "cobrança é automática no cartão Visa final 4242" in mailoutbox[-1].body
    _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks)
    _gerar(relogio, "2026-11-23", django_capture_on_commit_callbacks)
    assert moto.fatura("FAT-0002").tentativas_cartao == 2
    assert _regua(relogio, "2026-11-25") == {"D+3": 1}
    assert "O cartão foi recusado de novo. Pague por Pix ou boleto" in mailoutbox[-1].body
    assert _regua(relogio, "2026-11-29") == {"D+7": 1}


def test_aut_13_cancelada_a_regua_para(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """PLT-06: na empresa `cancelada`, a régua para inteira, mesmo com a fatura em atraso."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    moto.estado(status="cancelada")
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-19") == {}
    assert _regua(relogio, "2026-10-22") == {}
    assert mailoutbox == []


def test_aut_13_regua_isolada_por_empresa(
    moto, relogio, mailoutbox, criar_empresa, django_capture_on_commit_callbacks
):
    """Cada empresa recebe só a própria fatura: a outra, sem forma, também tem o D-3, e nenhum
    e-mail mistura os destinatários."""
    outra = criar_empresa(
        subdominio="outra",
        cnpj="11.222.333/0001-81",
        nome_exibicao="Outra",
        administrador=services.Administrador(nome="Ana Lima", email="ana@outra.com.br"),
    )
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-19") == {"D-3": 2}
    destinos = sorted(tuple(m.to) for m in mailoutbox)
    assert destinos == [("ana@outra.com.br",), (COBRANCA,), (MARIANA,)]
    para_outra = next(m for m in mailoutbox if m.to == ["ana@outra.com.br"])
    assert "Outra" in para_outra.body and "Moto Rápida" not in para_outra.body
    assert "Escolha a forma de pagamento" in para_outra.body
    assert outra.pk != moto.empresa.pk
