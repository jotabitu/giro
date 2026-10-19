"""T-303 e T-306 · Textos da régua da assinatura e um e-mail por destinatário (`AUT-13`, `PLT-02`,
`PLT-15`).

Textos fixados pelo produto na T-299 (`docs/qa/criterios/assinatura.md`, CA-ASS-64 a 67), o D+7
perdido da decisão B de 16 out (CA-ASS-68) e os achados M-01 e M-02 da segurança na T-304
(`docs/seguranca/2026-10-16-t304-destinatarios-regua.md`). Moto Rápida, FAT-0001 de R$ 449,00
vencendo em 22 out, suspensão em 06 nov.
"""

import logging
from smtplib import SMTPException

import pytest
from django.core.exceptions import ValidationError
from django_tenants.utils import schema_context

from apps.plataforma import services
from apps.plataforma.models import Empresa
from comum.erros import ErroDeValidacao
from integracoes import whatsapp as canal_whatsapp
from integracoes.pagamentos import falso as pagamentos
from integracoes.whatsapp import falso as whatsapp

from .test_t186b_faturas_cobranca import _ativa_com_cartao, _baixar, _gerar
from .test_t186c_regua_assinatura import (
    CELULAR,
    COBRANCA,
    EQUIPE,
    MARIANA,
    _com_boleto_emitido,
    _eventos,
    _regua,
    moto,  # noqa: F401
)

INICIO = "A fatura FAT-0001 da empresa Moto Rápida, de R$ 449,00"
SUSPENSA = (
    "a empresa fica suspensa: só ver e exportar os dados, sem criar locação, venda nem cobrança"
)
JA_PAGOU = "Se você já pagou, desconsidere esta mensagem."
NADA = "Não é preciso fazer nada."
LIGAR = "A equipe Giro vai ligar para o responsável pela assinatura."


def _para(mailoutbox, email: str):
    return [m for m in mailoutbox if m.to == [email]]


def _sem_da_solto(texto: str) -> bool:
    """Nenhum "da Moto Rápida" sem "empresa" (o nome pode ser masculino)."""
    return "da Moto Rápida" not in texto.replace("da empresa Moto Rápida", "")


def test_aut_13_textos_da_regua_no_boleto(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """CA-ASS-64: os quatro marcos no boleto, com o caminho de pagar, a página da assinatura e o
    rodapé, um por linha."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    fatura = moto.fatura("FAT-0001")
    endereco = services.endereco_da_assinatura(moto.recarregar())
    assert endereco.endswith("/admin/assinatura")
    caminho = (
        f"Boleto: {fatura.cobranca_boleto_url}\nLinha digitável: {fatura.cobranca_linha_digitavel}"
    )
    esperado = {
        "2026-10-19": (
            "Giro: a fatura FAT-0001 vence em 22 out",
            f"{INICIO}, vence em 22 out.",
        ),
        "2026-10-22": ("Giro: a fatura FAT-0001 vence hoje", f"{INICIO}, vence hoje."),
        "2026-10-25": (
            "Giro: a fatura FAT-0001 está em atraso",
            f"{INICIO}, venceu em 22 out e ainda não foi paga. "
            f"Sem o pagamento, em 06 nov {SUSPENSA}.",
        ),
        "2026-10-29": (
            "Giro: a empresa Moto Rápida fica suspensa em 06 nov",
            f"{INICIO}, venceu em 22 out e ainda não foi paga. "
            f"Em 06 nov, {SUSPENSA}. Pagando, o acesso volta na hora. {LIGAR}",
        ),
    }
    for dia, (assunto, inicio) in esperado.items():
        mailoutbox.clear()
        assert len(_regua(relogio, dia)) == 1
        for email in (COBRANCA, MARIANA):
            [mensagem] = _para(mailoutbox, email)
            assert mensagem.subject == assunto
            assert mensagem.body == f"{inicio}\n{caminho}\nAssinatura: {endereco}\n{JA_PAGOU}"
            assert "!" not in mensagem.body + mensagem.subject
            assert _sem_da_solto(mensagem.body + mensagem.subject)


def test_aut_13_automatica_nao_pede_nada(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """CA-ASS-65: cartão Visa final 4242 guardado, no D-3 de 19 nov "Não é preciso fazer nada.";
    recusado em 22 nov, o D+3 de 25 nov volta ao "Se você já pagou". O Pix automático autorizado
    diz que o pagamento sai no vencimento, com o mesmo rodapé."""
    token = _ativa_com_cartao(moto, relogio)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-11-19") == {"D-3": 1}
    corpo = _para(mailoutbox, COBRANCA)[0].body.split("\n")
    assert corpo[1] == "A cobrança é automática no cartão Visa final 4242."
    assert corpo[-1] == NADA

    pagamentos.recusar_cartao(token)
    _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks)
    _regua(relogio, "2026-11-22")
    assert _para(mailoutbox, COBRANCA)[-1].body.split("\n")[-1] == JA_PAGOU
    assert _regua(relogio, "2026-11-25") == {"D+3": 1}
    assert _para(mailoutbox, COBRANCA)[-1].body.split("\n")[-1] == JA_PAGOU

    with schema_context("public"):
        fatura = moto.fatura("FAT-0002")
        fatura.cobranca_tipo = services.COBRANCA_PELA_AUTORIZACAO
        fatura.cartao_recusado_em = None
        mensagem = services.mensagem_da_regua(fatura, "D-3", None)
    linhas = mensagem.texto.split("\n")
    assert linhas[1] == "O pagamento sai pelo Pix automático no dia do vencimento."
    assert linhas[-1] == NADA
    assert services.mensagem_da_regua(fatura, "D+3", None).texto.endswith(JA_PAGOU)


def test_aut_13_whatsapp_com_marca_e_caminho(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """CA-ASS-66: no D0, o WhatsApp diz de quem é e como pagar, com o boleto só pelo link."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    assert _regua(relogio, "2026-10-22") == {"D0": 1}
    link = moto.fatura("FAT-0001").cobranca_boleto_url
    [mensagem] = whatsapp.caixa_de_saida
    assert mensagem.celular == CELULAR
    assert mensagem.texto == (
        "Giro: a fatura FAT-0001 da empresa Moto Rápida, de R$ 449,00, vence hoje. "
        f"Boleto: {link} {JA_PAGOU}"
    )


@pytest.mark.parametrize("celular", [CELULAR, ""])
def test_aut_13_d7_e_a_ligacao(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
    celular,
):
    """CA-ASS-67: no D+7, o aviso de suspensão e a tarefa de ligação para a equipe. Sem o celular
    do responsável, o aviso sai sem a frase da ligação, e a equipe lê "celular não cadastrado"."""
    moto.estado(responsavel_telefone=celular)
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-29") == {"D+7": 1}
    [aviso] = _para(mailoutbox, COBRANCA)
    assert aviso.subject == "Giro: a empresa Moto Rápida fica suspensa em 06 nov"
    inicio = aviso.body.split("\n")[0]
    assert inicio.endswith("Pagando, o acesso volta na hora." + (f" {LIGAR}" if celular else ""))
    [ligacao] = _para(mailoutbox, EQUIPE)
    assert ligacao.subject == "Ligação de cobrança: Moto Rápida, FAT-0001 com 7 dias de atraso"
    assert ligacao.body == (
        f"{INICIO}, venceu em 22 out e ainda não foi paga. A suspensão é em 06 nov.\n"
        f"Responsável: Mariana Costa, {celular or 'celular não cadastrado'}.\n"
        f"E-mail de cobrança: {COBRANCA}."
    )


def test_aut_13_d7_perdido_sai_ate_d14(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """CA-ASS-68: a régua não roda em 25 nem em 29 out; em 30 out sai só o D+7, com a ligação, e
    em 31 out nada sai de novo."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-30") == {"D+7": 1}
    assert {m.subject for m in _para(mailoutbox, COBRANCA) + _para(mailoutbox, MARIANA)} == {
        "Giro: a empresa Moto Rápida fica suspensa em 06 nov"
    }
    assert len(_para(mailoutbox, EQUIPE)) == 1
    assert [e.depois["marco"] for e in _eventos("fatura_assinatura.regua")] == ["D+7"]
    assert len(_eventos("fatura_assinatura.pedir_ligacao")) == 1
    assert _regua(relogio, "2026-10-31") == {}
    assert len(mailoutbox) == 3


@pytest.mark.parametrize("caso", ["no_d14", "depois_do_d14", "paga", "cancelada"])
def test_aut_13_d7_perdido_ate_o_d14_e_so_em_aberto(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
    caso,
):
    """CA-ASS-68: o D+7 perdido sai até 05 nov (D+14), não em 06 nov; paga em 29 out ou com a
    empresa `cancelada`, nada sai em 30 out."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    if caso == "paga":
        relogio.em("2026-10-29 10:00")
        fatura = moto.fatura("FAT-0001")
        pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
        assert _baixar(fatura.cobranca_externa_id, "evt-1") == "baixada"
    if caso == "cancelada":
        moto.estado(status="cancelada")
    mailoutbox.clear()
    dia = {"no_d14": "2026-11-05", "depois_do_d14": "2026-11-06"}.get(caso, "2026-10-30")
    assert _regua(relogio, dia) == ({"D+7": 1} if caso == "no_d14" else {})
    assert len(mailoutbox) == (3 if caso == "no_d14" else 0)


def test_aut_13_cada_destinatario_recebe_o_seu(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """M-01 da T-304: no D-3, um e-mail para o e-mail de cobrança e outro para a Mariana, cada
    um só com o próprio endereço, sem cópia oculta, com o mesmo assunto e texto."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    assert _regua(relogio, "2026-10-19") == {"D-3": 1}
    assert [m.to for m in mailoutbox] == [[COBRANCA], [MARIANA]]
    assert all(m.cc == [] and m.bcc == [] for m in mailoutbox)
    assert mailoutbox[0].subject == mailoutbox[1].subject
    assert mailoutbox[0].body == mailoutbox[1].body


def test_plt_02_boleto_um_por_destinatario(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """M-01 da T-304: o e-mail do boleto, um por destinatário."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    assert [m.to for m in mailoutbox] == [[COBRANCA], [MARIANA]]
    assert all(m.bcc == [] for m in mailoutbox)
    assert mailoutbox[0].subject == mailoutbox[1].subject
    assert mailoutbox[0].body == mailoutbox[1].body


def test_aut_13_falha_numa_fatura_nao_para_as_outras(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    criar_empresa,
    django_capture_on_commit_callbacks,
    monkeypatch,
    caplog,
):
    """M-02 da T-304: a falha numa fatura vai ao log, sem o corpo, e a outra empresa recebe o
    aviso. Antes do commit, o aviso volta a valer na rodada seguinte; no envio, o evento fica."""
    criar_empresa(
        subdominio="outra",
        cnpj="11.222.333/0001-81",
        nome_exibicao="Outra",
        administrador=services.Administrador(nome="Ana Lima", email="ana@outra.com.br"),
    )
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()
    original = services.mensagem_da_regua

    def falha_na_moto(fatura, marco, forma):
        if fatura.empresa.nome_exibicao == "Moto Rápida":
            raise RuntimeError("falhou")
        return original(fatura, marco, forma)

    monkeypatch.setattr(services, "mensagem_da_regua", falha_na_moto)
    caplog.set_level(logging.WARNING, logger="apps.plataforma.services")
    assert _regua(relogio, "2026-10-19") == {"D-3": 1}
    assert [m.to for m in mailoutbox] == [["ana@outra.com.br"]]
    assert len(_eventos("fatura_assinatura.regua")) == 1
    monkeypatch.setattr(services, "mensagem_da_regua", original)
    assert _regua(relogio, "2026-10-19") == {"D-3": 1}  # nada ficou gravado pela metade
    assert len(_eventos("fatura_assinatura.regua")) == 2

    mailoutbox.clear()
    enviar = services.enviar_a_cada_um

    def smtp_fora(destinatarios, assunto, texto):
        if COBRANCA in destinatarios:
            raise SMTPException("fora do ar")
        return enviar(destinatarios, assunto, texto)

    monkeypatch.setattr(services, "enviar_a_cada_um", smtp_fora)
    assert _regua(relogio, "2026-10-22") == {"D0": 2}
    assert [m.to for m in mailoutbox] == [["ana@outra.com.br"]]
    assert [e.depois["marco"] for e in _eventos("fatura_assinatura.regua")][-2:] == ["D0", "D0"]
    assert "SMTPException" in caplog.text
    assert "R$ 449,00" not in caplog.text and "FAT-0001 da empresa" not in caplog.text


def test_aut_13_whatsapp_que_falha_nao_repete_o_email(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
    monkeypatch,
):
    """M-02 da T-304: o e-mail sai, o WhatsApp falha, e uma nova execução no mesmo dia não manda
    o e-mail de novo."""
    _com_boleto_emitido(moto, relogio, django_capture_on_commit_callbacks)
    mailoutbox.clear()

    def fora_do_ar(celular, texto):
        raise ConnectionError("provedor fora")

    monkeypatch.setattr(canal_whatsapp, "enviar_whatsapp", fora_do_ar)
    assert _regua(relogio, "2026-10-22") == {"D0": 1}
    assert len(mailoutbox) == 2
    assert _regua(relogio, "2026-10-22") == {}
    assert len(mailoutbox) == 2


def test_plt_15_nome_sem_quebra_de_linha(criar_empresa):
    """M-02 da T-304: o nome vai no assunto dos e-mails; com quebra de linha ou caractere de
    controle, o cadastro recusa (400)."""
    for nome in ("Moto\nRápida", "Moto\rRápida", "Moto\x07Rápida"):
        with pytest.raises(ErroDeValidacao) as erro:
            criar_empresa(nome_exibicao=nome)
        assert erro.value.campos == {"nome_exibicao": ["Use um nome sem quebra de linha."]}
    with schema_context("public"):
        assert not Empresa.objects.filter(subdominio="motorapida").exists()
    campo = Empresa._meta.get_field("nome_exibicao")  # a edição pelo Admin valida o campo
    with pytest.raises(ValidationError, match="quebra de linha"):
        campo.run_validators("Moto\nRápida")
