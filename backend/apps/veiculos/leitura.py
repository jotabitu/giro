"""Preencher pelo CRLV-e (VEI-08, ADR 0026, docs/api/veiculos.md).

A leitura não grava nada: lê o PDF no processo filho (`integracoes.leitura_documentos`), acha a
marca e o modelo no catálogo (item 7) e devolve os 9 campos com o comprovante `leitura`. Nada do
conteúdo, do nome do arquivo ou dos valores lidos vai para log: só a linha do item 9.
"""

import logging
import time
from typing import Any

from comum import comprovante_leitura
from comum.conexao import schema_atual
from comum.erros import ErroDeRegra, ErroDeValidacao
from integracoes import leitura_documentos

from . import catalogo

logger = logging.getLogger(__name__)

TIPO = "crlv"
TAMANHO_MAXIMO = 2 * 1024 * 1024
ASSINATURA_PDF = b"%PDF-"
CAMPOS = (
    "placa",
    "chassi",
    "renavam",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "combustivel",
)
MENSAGEM_FALHA = "Não conseguimos ler este documento. Preencha os campos à mão."
MENSAGEM_NAO_PDF = "Envie o PDF do CRLV-e."


class FalhaDeLeitura(ErroDeRegra):
    """422 `VEI-08`, a mesma resposta para toda falha (CA-247-06). O `motivo` vai só para o log."""

    def __init__(self, motivo: str) -> None:
        super().__init__("VEI-08", MENSAGEM_FALHA)
        self.motivo = motivo


def conteudo_do_arquivo(arquivo: Any) -> bytes:
    """O PDF, até 2 MB, conferido pelos primeiros bytes (ADR 0026, item 6).

    Nem PDF pela extensão nem pelos primeiros bytes (a foto `foto-crlv.jpg`): 400. Com a extensão
    `.pdf` e outro conteúdo, ou acima de 2 MB: 422 `VEI-08`. Lê no máximo 2 MB + 1 byte."""
    if arquivo is None:
        raise ErroDeValidacao({"arquivo": [MENSAGEM_NAO_PDF]})
    arquivo.seek(0)
    conteudo: bytes = arquivo.read(TAMANHO_MAXIMO + 1)
    arquivo.seek(0)
    e_pdf = conteudo.startswith(ASSINATURA_PDF)
    if not e_pdf and not str(arquivo.name or "").lower().endswith(".pdf"):
        raise ErroDeValidacao({"arquivo": [MENSAGEM_NAO_PDF]})
    if len(conteudo) > TAMANHO_MAXIMO:
        raise FalhaDeLeitura("grande")
    if not e_pdf:
        raise FalhaDeLeitura("nao_pdf")
    return conteudo


def rotulo(quantidade: int) -> str:
    plural = "campo preenchido" if quantidade == 1 else "campos preenchidos"
    return f"CRLV-e lido · {quantidade} {plural}"


def _resposta(lidos_do_filho: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Os 9 campos da VEI-08 e a dica de marca e modelo."""
    campos: dict[str, Any] = dict.fromkeys(CAMPOS)
    for nome in ("placa", "chassi", "renavam", "ano_fabricacao", "ano_modelo", "cor"):
        campos[nome] = lidos_do_filho.get(nome)
    campos["combustivel"] = lidos_do_filho.get("combustivel")
    texto = lidos_do_filho.get("marca_modelo")
    modelo = catalogo.achar_modelo(texto) if texto else None
    if modelo is not None:
        campos["marca"], campos["modelo"] = modelo.marca, modelo.modelo
    return campos, (texto if texto and modelo is None else None)


def _registrar(
    resultado: str, motivo: str | None, quantidade: int, inicio: float, usuario: Any
) -> None:
    logger.info(
        "Leitura de documento: tipo=%s resultado=%s motivo=%s campos=%d ms=%d schema=%s usuario=%s",
        TIPO,
        resultado,
        motivo or "-",
        quantidade,
        int((time.monotonic() - inicio) * 1000),
        schema_atual(),
        comprovante_leitura.quem(usuario),
    )


def ler_crlv(arquivo: Any, usuario: Any) -> dict[str, Any]:
    """POST /api/veiculos/leitura-crlv/. Ocupado: `leitura_documentos.LeituraOcupada` (503)."""
    inicio = time.monotonic()
    try:
        conteudo = conteudo_do_arquivo(arquivo)
        with leitura_documentos.vaga():
            leitura = leitura_documentos.ler(TIPO, conteudo)
        if leitura.motivo is not None:
            raise FalhaDeLeitura(leitura.motivo)
        campos, dica = _resposta(leitura.campos)
        lidos = [nome for nome in CAMPOS if campos[nome] is not None]
        if not lidos:
            raise FalhaDeLeitura("nao_reconhecido")
    except FalhaDeLeitura as falha:
        _registrar("falhou", falha.motivo, 0, inicio, usuario)
        raise
    except ErroDeValidacao:
        _registrar("falhou", "nao_pdf", 0, inicio, usuario)
        raise
    _registrar(
        "lido" if len(lidos) == len(CAMPOS) else "parcial", None, len(lidos), inicio, usuario
    )
    return {
        "documento": TIPO,
        "campos": campos,
        "lidos": lidos,
        "quantidade": len(lidos),
        "rotulo": rotulo(len(lidos)),
        "exercicio": leitura.campos.get("exercicio"),
        "dicas": {"marca_modelo": dica},
        "leitura": comprovante_leitura.emitir(
            TIPO, conteudo, usuario, {nome: campos[nome] for nome in lidos}
        ),
    }
