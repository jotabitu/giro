"""T-328 · Revisão de segurança da leitura do CRLV-e (T-265, ADR 0026).

Relatório: `docs/seguranca/2026-10-19-t328-leitura-crlv.md`. Os `xfail` estritos são os achados
que pedem código (tarefa de backend no handoff `tarefas/handoffs/T-328-seguranca.md`): quem
corrigir tira o `xfail`.
"""

from typing import Any

import pytest

from apps.veiculos import services
from comum.erros import ErroDeRegra
from integracoes import leitura_documentos
from integracoes.leitura_documentos import crlv

from . import documentos_pdf as pdfs
from .test_t265_leitura_crlv import _ler, _pdf, frota, moto  # noqa: F401


@pytest.mark.xfail(strict=True, reason="M-01 da T-328: a cor aceita qualquer palavra")
def test_aud_09_cor_nao_aceita_o_nome_do_proprietario() -> None:
    """O valor da cor é o primeiro texto abaixo do rótulo; sem a cor ali, o nome de uma pessoa
    passa no validador. Com a lista fechada de cores do Denatran, não passa."""
    assert "cor" not in crlv.extrair("COR PREDOMINANTE\n\nMARIA DA SILVA\n")
    assert crlv.cor("PROPRIETARIO") is None


@pytest.mark.xfail(strict=True, reason="B-01 da T-328: o pai não confere a faixa dos anos")
def test_vei_08_pai_confere_a_faixa_dos_anos() -> None:
    campos = leitura_documentos.conferir(
        "crlv", {"placa": "TBC5H21", "ano_fabricacao": 99999, "exercicio": -1}
    )
    assert campos == {"placa": "TBC5H21"}


@pytest.mark.xfail(strict=True, reason="B-02 da T-328: o armazenamento privado não apaga")
def test_vei_08_falha_depois_de_gravar_o_arquivo_devolve_o_erro_certo(
    moto,  # noqa: F811
    frota,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uma falha depois de o CRLV ir para o armazenamento devolve o erro original, não 500."""
    conteudo = pdfs.CRLV_TBC5H21.pdf()
    lido = _ler(moto, conteudo).json()
    original = services.registrar_evento

    def falha_no_documento(acao: str, *args: Any, **kwargs: Any) -> Any:
        if acao == "documento_veiculo.enviar":
            raise ErroDeRegra("VEI-08", "Falha simulada.")
        return original(acao, *args, **kwargs)

    monkeypatch.setattr(services, "registrar_evento", falha_no_documento)
    corpo = {
        **{k: v for k, v in lido["campos"].items() if v is not None},
        "km_atual": 0,
        "categoria_id": frota.categorias["Urbana 110–125"].pk,
        "filial_id": frota.centro.pk,
        "crlv_arquivo": _pdf(conteudo),
        "crlv_validade": "2027-10-31",
        "leitura": lido["leitura"],
    }
    resposta = moto.api().post("/api/veiculos/", corpo, format="multipart")
    assert resposta.status_code == 422
