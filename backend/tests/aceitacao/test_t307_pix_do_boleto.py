"""T-307 · Pix do boleto (`docs/api/financeiro.md`, "O que cada cobrança devolve"; FIN-04, PLT-02,
PLT-13; T-305).

O boleto também se paga por Pix, pelo mesmo `pixQrCode` da cobrança Pix. Sem Pix disponível (a
conta sem chave Pix), o boleto sai sem ele e não é cancelado, e ninguém escreve "Pix copia e cola:"
sem o código. Vale para as contas a receber (subconta) e para as faturas da assinatura.
"""

import pytest

from apps.financeiro.models import CobrancaExterna
from apps.plataforma import selectors, services
from integracoes.pagamentos import falso as pagamentos

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t017_financeiro import (  # noqa: F401 - fixtures
    CONTAS,
    _avulsa,
    recebimentos,
)
from .test_t186b_faturas_cobranca import COBRANCA, _gerar, moto  # noqa: F401 - fixtures
from .test_t297_pix_pendente import _pix_escolhido


@pytest.fixture(autouse=True)
def _falso_limpo():
    pagamentos.limpar()
    yield
    pagamentos.limpar()


@pytest.mark.parametrize("sem_pix", [False, True])
def test_fin_04_boleto_traz_o_pix(cenario, recebimentos, sem_pix):  # noqa: F811
    """O boleto da conta a receber traz o Pix e o grava na `CobrancaExterna`; sem Pix disponível,
    o boleto sai assim mesmo, sem ele."""
    if sem_pix:
        pagamentos.sem_pix_no_boleto()
    conta = _avulsa(cenario, "Lucas", 30000)
    resposta = cenario.moto.api("Bruna").post(
        f"{CONTAS}{conta.pk}/cobranca/", {"tipo": "boleto"}, format="json"
    )
    assert resposta.status_code == 201, resposta.json()
    corpo = resposta.json()
    cobranca = CobrancaExterna.objects.get(pk=corpo["id"])
    assert corpo["linha_digitavel"] and cobranca.linha_digitavel
    if sem_pix:
        assert (corpo["pix_copia_e_cola"], cobranca.pix_copia_e_cola) == (None, "")
    else:
        assert cobranca.pix_copia_e_cola.startswith("00020126falso")
        assert corpo["pix_copia_e_cola"] == cobranca.pix_copia_e_cola


@pytest.mark.parametrize("sem_pix", [False, True])
def test_plt_02_email_do_boleto_sem_linha_pix_vazia(
    moto,  # noqa: F811
    relogio,
    mailoutbox,
    django_capture_on_commit_callbacks,
    sem_pix,
):
    """O e-mail do boleto da assinatura leva o Pix quando ele existe; sem ele, não escreve a
    linha vazia."""
    if sem_pix:
        pagamentos.sem_pix_no_boleto()
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "boleto" and fatura.cobranca_linha_digitavel
    corpo = next(m for m in mailoutbox if COBRANCA in m.to).body
    if sem_pix:
        assert fatura.cobranca_pix_copia_e_cola == ""
        assert "Pix copia e cola" not in corpo
    else:
        assert fatura.cobranca_pix_copia_e_cola
        assert f"Pix copia e cola: {fatura.cobranca_pix_copia_e_cola}\n" in corpo


def test_plt_13_pagar_devolve_o_boleto_com_pix(
    moto,  # noqa: F811
    relogio,
    django_capture_on_commit_callbacks,
):
    """T-298: o "Pagar" sem `meio` da fatura emitida em boleto por falta da autorização devolve
    o boleto vivo com o Pix dele."""
    _pix_escolhido(moto, relogio)
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    relogio.em("2026-10-18 10:00")
    fatura = services.pagar_fatura(moto.recarregar(), "FAT-0001")
    assert fatura.cobranca_tipo == "boleto"
    assert fatura.cobranca_pix_copia_e_cola.startswith("00020126falso")
    cobranca = selectors.cobranca_da_fatura(fatura)
    assert cobranca is not None
    assert cobranca["pix_copia_e_cola"] == fatura.cobranca_pix_copia_e_cola
    assert cobranca["linha_digitavel"] == fatura.cobranca_linha_digitavel
