"""Preencher pelo CRLV-e (VEI-08, ADR 0026, docs/api/veiculos.md).

A leitura não grava nada: lê o PDF no processo filho (`integracoes.leitura_documentos`), acha a
marca e o modelo no catálogo (item 7) e devolve até 18 campos (os 9 da VEI-08 e os 9 do documento
da VEI-09, T-421) com o comprovante `leitura`. No editar (T-421), confere que o documento é do
veículo e não devolve placa nem chassi. Nada do
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
IDENTIFICACAO = ("placa", "chassi")
# VEI-09 (T-421): o campo do processo filho → a chave pontuada da API.
DO_DOCUMENTO = {
    "potencia_cv": "documento.potencia_cv",
    "cilindrada_cc": "documento.cilindrada_cc",
    "especie": "documento.especie",
    "tipo": "documento.tipo",
    "carroceria": "documento.carroceria",
    "lotacao": "documento.lotacao",
    "peso_bruto_kg": "documento.peso_bruto_kg",
    "numero_motor": "documento.numero_motor",
    "observacoes": "documento.observacoes",
}
CAMPOS = (
    *IDENTIFICACAO,
    "renavam",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "cor",
    "combustivel",
    *DO_DOCUMENTO.values(),
)
LIMITE_DE_CANDIDATOS = 20  # T-415: acima disso, a pessoa busca na lista
MENSAGEM_FALHA = "Não conseguimos ler este documento. Preencha os campos à mão."
MENSAGEM_NAO_PDF = "Envie o PDF do CRLV-e."
MENSAGEM_OUTRO_VEICULO = "Este CRLV-e é de outro veículo."


class FalhaDeLeitura(ErroDeRegra):
    """422 `VEI-08`, a mesma resposta para toda falha (CA-247-06). O `motivo` vai só para o log."""

    def __init__(self, motivo: str) -> None:
        super().__init__("VEI-08", MENSAGEM_FALHA)
        self.motivo = motivo


class CrlvDeOutroVeiculo(ErroDeRegra):
    """422 `crlv_outro_veiculo` (CA-421-10): a placa ou o chassi lidos não são os do veículo."""

    def __init__(self) -> None:
        super().__init__("crlv_outro_veiculo", MENSAGEM_OUTRO_VEICULO)


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


def _resposta(lidos_do_filho: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Os campos da VEI-08 (com os da VEI-09) e as dicas de marca e modelo.

    Um candidato só: marca e modelo preenchidos, sem dica. Mais de um (o Cruze da T-415): a marca
    é preenchida quando todos são da mesma, e as versões vão em `dicas.candidatos` para a pessoa
    escolher, até `LIMITE_DE_CANDIDATOS`; acima disso, a lista vem vazia e a pessoa busca."""
    campos: dict[str, Any] = dict.fromkeys(CAMPOS)
    for nome in ("placa", "chassi", "renavam", "ano_fabricacao", "ano_modelo", "cor"):
        campos[nome] = lidos_do_filho.get(nome)
    campos["combustivel"] = lidos_do_filho.get("combustivel")
    for nome, chave in DO_DOCUMENTO.items():
        campos[chave] = lidos_do_filho.get(nome)
    texto = lidos_do_filho.get("marca_modelo")
    achados = catalogo.candidatos(texto) if texto else []
    dicas: dict[str, Any] = {"marca_modelo": None, "candidatos": []}
    if len(achados) == 1:
        campos["marca"], campos["modelo"] = achados[0].marca, achados[0].modelo
        return campos, dicas
    dicas["marca_modelo"] = texto or None
    marcas = {m.marca for m in achados}
    if len(marcas) == 1:
        campos["marca"] = marcas.pop()
    if len(achados) <= LIMITE_DE_CANDIDATOS:
        dicas["candidatos"] = [
            {"marca": m.marca, "modelo": m.modelo, "tipo": m.tipo} for m in achados
        ]
    return campos, dicas


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


def _do_veiculo(campos: dict[str, Any], veiculo: Any) -> None:
    """No editar (T-421): a placa e o chassi lidos, sem hífen e em maiúsculas, têm de ser os do
    veículo. Precisa ter lido pelo menos um dos dois; sem nenhum, não dá para conferir (422
    `VEI-08`). Depois da conferência, os dois saem da resposta: no editar eles não mudam."""
    lidos = {nome: campos[nome] for nome in IDENTIFICACAO if campos[nome] is not None}
    if not lidos:
        raise FalhaDeLeitura("sem_identificacao")
    if any(str(valor).upper() != getattr(veiculo, nome) for nome, valor in lidos.items()):
        raise CrlvDeOutroVeiculo
    for nome in IDENTIFICACAO:
        campos.pop(nome)


def ler_crlv(arquivo: Any, usuario: Any, veiculo: Any = None) -> dict[str, Any]:
    """POST /api/veiculos/leitura-crlv/ e, com o `veiculo`, POST /api/veiculos/{id}/leitura-crlv/
    (o editar, T-421). Ocupado: `leitura_documentos.LeituraOcupada` (503)."""
    inicio = time.monotonic()
    try:
        conteudo = conteudo_do_arquivo(arquivo)
        with leitura_documentos.vaga():
            leitura = leitura_documentos.ler(TIPO, conteudo)
        if leitura.motivo is not None:
            raise FalhaDeLeitura(leitura.motivo)
        campos, dicas = _resposta(leitura.campos)
        if veiculo is not None:
            _do_veiculo(campos, veiculo)
        lidos = [nome for nome in campos if campos[nome] is not None]
        if not lidos:
            raise FalhaDeLeitura("nao_reconhecido")
    except FalhaDeLeitura as falha:
        _registrar("falhou", falha.motivo, 0, inicio, usuario)
        raise
    except CrlvDeOutroVeiculo:
        _registrar("falhou", "outro_veiculo", 0, inicio, usuario)
        raise
    except ErroDeValidacao:
        _registrar("falhou", "nao_pdf", 0, inicio, usuario)
        raise
    _registrar(
        "lido" if len(lidos) == len(campos) else "parcial", None, len(lidos), inicio, usuario
    )
    return {
        "documento": TIPO,
        "campos": campos,
        "lidos": lidos,
        "quantidade": len(lidos),
        "rotulo": rotulo(len(lidos)),
        "exercicio": leitura.campos.get("exercicio"),
        "dicas": dicas,
        "leitura": comprovante_leitura.emitir(
            TIPO,
            conteudo,
            usuario,
            {nome: campos[nome] for nome in lidos},
            veiculo_id=veiculo.pk if veiculo is not None else None,
        ),
    }
