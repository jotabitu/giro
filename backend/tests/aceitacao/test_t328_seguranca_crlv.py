"""T-328 · Revisão de segurança da leitura do CRLV-e (T-265, ADR 0026).

Relatório: `docs/seguranca/2026-10-19-t328-leitura-crlv.md`. Os achados que pediam código (M-01,
B-01 e B-02) eram `xfail` estritos até a correção da T-329; agora são testes comuns.
"""

from typing import Any

import pytest

from apps.veiculos import services
from comum.erros import ErroDeRegra
from integracoes import leitura_documentos
from integracoes.leitura_documentos import crlv

from . import documentos_pdf as pdfs
from .test_t265_leitura_crlv import _ler, _pdf, frota, moto  # noqa: F401


def test_aud_09_cor_nao_aceita_o_nome_do_proprietario() -> None:
    """O valor da cor é o primeiro texto abaixo do rótulo; sem a cor ali, o nome de uma pessoa
    passa no validador. Com a lista fechada de cores do Denatran, não passa."""
    assert "cor" not in crlv.extrair("COR PREDOMINANTE\n\nMARIA DA SILVA\n")
    assert crlv.cor("PROPRIETARIO") is None


def test_vei_08_pai_confere_a_faixa_dos_anos() -> None:
    campos = leitura_documentos.conferir(
        "crlv", {"placa": "TBC5H21", "ano_fabricacao": 99999, "exercicio": -1}
    )
    assert campos == {"placa": "TBC5H21"}


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


def test_vei_08_cor_da_lista_do_denatran() -> None:
    """M-01 (T-329): a cor da lista, sem acento na comparação e com o acento da lista."""
    assert crlv.cor("VERMELHA") == "vermelha"
    assert crlv.cor("GRENA") == "grená"
    assert crlv.cor("  Prata ") == "prata"
    assert crlv.cor("AZUL CLARO") is None


def test_vei_08_pai_confere_texto_combustivel_e_dica() -> None:
    """B-01 (T-329): caractere de controle, combustível fora do enum e dica acima de 60."""
    campos = leitura_documentos.conferir(
        "crlv",
        {
            "placa": "TBC5H21",
            "cor": "preta\x00",
            "combustivel": "querosene",
            "marca_modelo": "HONDA/" + "X" * 60,
            "ano_modelo": 2027,
            "exercicio": 1899,
        },
    )
    assert campos == {"placa": "TBC5H21", "ano_modelo": 2027}


def test_vei_08_upload_ate_3_mb_fica_na_memoria(settings) -> None:
    """B-03 (T-329): o teto da borda é 3 MB; até ele, nada vai para o disco do contêiner."""
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE >= 3 * 1024 * 1024
