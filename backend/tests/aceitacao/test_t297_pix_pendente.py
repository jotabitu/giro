"""T-297 · Boleto com Pix para o Pix automático ainda não autorizado (`docs/api/assinatura.md`,
"Emissão no parceiro" e `POST faturas/{codigo}/pagar/`; PLT-02, PLT-13, CA-ASS-63).

Moto Rápida com o Pix automático escolhido em 10 out e ainda não autorizado no banco: a FAT-0001
(R$ 449,00, vence em 22 out) sai em boleto com Pix em 17 out, e a forma continua esperando a
autorização. Autorizada em 20 out, a FAT-0001 fica no boleto; a FAT-0002 sai pela autorização em
17 nov.
"""

from apps.plataforma import selectors, services
from apps.plataforma.models import FormaAssinatura, StatusFormaPagamento
from integracoes.pagamentos import falso as pagamentos

from .test_t184_faturas import _webhook
from .test_t186b_faturas_cobranca import (  # noqa: F401 - fixtures
    COBRANCA,
    MARIANA,
    _baixar,
    _forma,
    _gerar,
    _virar,
    conta_principal_ligada,
    moto,
)

LINHA = "Seu Pix automático ainda não foi autorizado. Esta fatura vai por boleto com Pix."


def _pix_escolhido(moto, relogio) -> None:  # noqa: F811
    relogio.em("2026-10-10 10:00")
    services.escolher_forma_pagamento(moto.recarregar(), "pix_automatico")
    assert _forma(moto).status == StatusFormaPagamento.PENDENTE


def test_plt_13_pix_automatico_sem_autorizacao_sai_boleto(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    """Em 17 out, sem a autorização, a FAT-0001 sai em boleto com Pix, com o e-mail nesse dia
    para o e-mail de cobrança e a Mariana, com a linha da PLT-13. A forma não muda."""
    _pix_escolhido(moto, relogio)
    geracao = _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    assert geracao.emitidas == {"boleto_sem_autorizacao": 1}
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "boleto"
    assert fatura.cobranca_boleto_url and fatura.cobranca_linha_digitavel
    cobranca = selectors.cobranca_da_fatura(fatura)
    assert cobranca is not None and cobranca["forma"] == "boleto"
    forma = _forma(moto)
    assert (forma.forma, forma.status) == (FormaAssinatura.PIX_AUTOMATICO, "pendente")

    assert [m.to for m in mailoutbox] == [[COBRANCA], [MARIANA]]  # um por destinatário (T-306)
    assert LINHA in mailoutbox[0].body
    assert "R$ 449,00" in mailoutbox[0].body and "22 out" in mailoutbox[0].body

    # Idempotente: rodar de novo não emite outro nem manda outro e-mail.
    assert _gerar(relogio, "2026-10-18", django_capture_on_commit_callbacks).emitidas == {}
    assert moto.fatura("FAT-0001").cobranca_externa_id == fatura.cobranca_externa_id
    assert len(mailoutbox) == 2


def test_plt_13_boleto_comum_sem_a_linha(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
):
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    assert len(mailoutbox) == 2
    assert LINHA not in mailoutbox[0].body


def test_plt_13_pagar_sem_meio_devolve_o_boleto(
    moto,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    """T-298: o "Pagar" sem `meio` da fatura emitida em boleto por falta da autorização devolve
    o boleto vivo, sem Pix avulso por cima. Com `meio`, vale o de sempre."""
    _pix_escolhido(moto, relogio)
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    boleto = moto.fatura("FAT-0001").cobranca_externa_id

    relogio.em("2026-10-18 10:00")
    fatura = services.pagar_fatura(moto.recarregar(), "FAT-0001")
    assert (fatura.cobranca_tipo, fatura.cobranca_externa_id) == ("boleto", boleto)
    assert fatura.cobranca_boleto_url

    pelo_cartao = services.pagar_fatura(moto.recarregar(), "FAT-0001", "cartao")
    assert pelo_cartao.cobranca_tipo == "cartao_link"
    assert pelo_cartao.cobranca_externa_id != boleto


def test_plt_13_autorizado_depois_vale_na_fatura_seguinte(
    moto,  # noqa: F811
    relogio,
    conta_principal_ligada,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """FAT-0001 em boleto em 17 out; autorizada em 20 out, a forma vira `ativa`, mas o boleto não
    é cancelado nem ganha cobrança pela autorização. A FAT-0002 sai pela autorização em 17 nov."""
    _pix_escolhido(moto, relogio)
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    boleto = moto.fatura("FAT-0001").cobranca_externa_id

    relogio.em("2026-10-20 10:00")
    corpo = pagamentos.autorizar_pix(_forma(moto).autorizacao_externa_id)
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    assert _forma(moto).status == StatusFormaPagamento.ATIVA

    for dia in ("2026-10-21", "2026-10-22"):
        assert _gerar(relogio, dia, django_capture_on_commit_callbacks).emitidas == {}
    fatura = moto.fatura("FAT-0001")
    assert (fatura.cobranca_tipo, fatura.cobranca_externa_id) == ("boleto", boleto)
    relogio.em("2026-10-22 10:00")
    assert services.pagar_fatura(moto.recarregar(), "FAT-0001").cobranca_externa_id == boleto

    pagamentos.simular_pagamento(boleto or "")
    assert _baixar(boleto, "evt-fat-0001") == "baixada"
    _virar(relogio, "2026-10-23")
    assert moto.recarregar().status == "ativa"

    geracao = _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    assert (geracao.faturas, geracao.emitidas) == (1, {"pix_automatico": 1})
    assert moto.fatura("FAT-0002").cobranca_tipo == "pix_auto"
