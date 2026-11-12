"""Comprovante `leitura` da leitura de documentos em PDF (ADR 0026, item 8; B-04).

A leitura não grava nada. Para o evento do "Salvar" dizer o que veio do documento sem confiar na
tela, ela devolve um texto assinado (`django.core.signing`, sal próprio por tipo, 30 minutos) com
o tipo, o SHA-256 do arquivo, o schema, quem leu e, por campo lido, um resumo HMAC do valor. O
comprovante não leva valor nenhum.

O resumo usa uma chave só da leitura, derivada do pepper, e leva o SHA-256 do arquivo junto:
`HMAC(HMAC(GIRO_PEPPER_HMAC, "leitura-documento"), sha256 || campo || valor)`. Nunca é igual ao
`CampoHashBusca` (ADR 0014), e o mesmo valor em arquivos diferentes dá resumos diferentes.
"""

import hashlib
import hmac
from typing import Any

from django.conf import settings
from django.core import signing

from .conexao import schema_atual

VALIDADE = 30 * 60  # segundos
SEPARADOR = b"\x00"


def sha256(conteudo: bytes) -> str:
    return hashlib.sha256(conteudo).hexdigest()


def quem(usuario: Any) -> str:
    """O usuário da empresa pelo id; o suporte (sem usuário na empresa), pelo acesso."""
    if getattr(usuario, "pk", None) is not None:
        return str(usuario.pk)
    return f"suporte-{getattr(usuario, 'acesso_suporte_id', '')}"


def _chave() -> bytes:
    pepper = str(settings.GIRO_PEPPER_HMAC).encode()
    return hmac.new(pepper, b"leitura-documento", hashlib.sha256).digest()


def valor_comparavel(valor: Any) -> str:
    """O mesmo texto para o valor lido e o gravado: sem espaços nas pontas, em minúsculas."""
    return str(valor).strip().lower()


def resumo(hash_do_arquivo: str, campo: str, valor: Any) -> str:
    mensagem = SEPARADOR.join(
        (hash_do_arquivo.encode(), campo.encode(), valor_comparavel(valor).encode())
    )
    return hmac.new(_chave(), mensagem, hashlib.sha256).hexdigest()


def _sal(tipo: str) -> str:
    return f"giro.leitura-documento.{tipo}"


def emitir(
    tipo: str,
    conteudo: bytes,
    usuario: Any,
    campos: dict[str, Any],
    veiculo_id: int | None = None,
) -> str:
    """`veiculo_id`: a leitura no editar (T-421), que só vale para o mesmo veículo."""
    hash_do_arquivo = sha256(conteudo)
    dados = {
        "tipo": tipo,
        "arquivo": hash_do_arquivo,
        "schema": schema_atual(),
        "usuario": quem(usuario),
        "veiculo": veiculo_id,
        "resumos": {nome: resumo(hash_do_arquivo, nome, v) for nome, v in campos.items()},
    }
    return signing.dumps(dados, salt=_sal(tipo), compress=True)


def _abrir(tipo: str, texto: str | None, usuario: Any) -> dict[str, Any] | None:
    """O conteúdo do comprovante, se ele é deste tipo, desta empresa e desta pessoa e não venceu."""
    if not texto:
        return None
    try:
        dados = signing.loads(texto, salt=_sal(tipo), max_age=VALIDADE)
    except signing.BadSignature:  # inclui o vencido (SignatureExpired)
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("resumos"), dict):
        return None
    if (
        dados.get("tipo") != tipo
        or dados.get("schema") != schema_atual()
        or dados.get("usuario") != quem(usuario)
    ):
        return None
    return dados


def _resumos(dados: dict[str, Any]) -> dict[str, str]:
    return {str(k): str(v) for k, v in dados["resumos"].items()}


def conferir(tipo: str, texto: str | None, conteudo: bytes, usuario: Any) -> dict[str, str] | None:
    """Os resumos do comprovante, se ele vale para este arquivo, esta empresa e esta pessoa.
    Vencido, adulterado, de outra empresa, de outra pessoa, de outro arquivo ou de uma leitura
    no editar: `None`, e o cadastro segue sem a marca de leitura."""
    dados = _abrir(tipo, texto, usuario)
    if (
        dados is None
        or dados.get("veiculo") is not None
        or not hmac.compare_digest(str(dados.get("arquivo")), sha256(conteudo))
    ):
        return None
    return _resumos(dados)


def conferir_do_veiculo(
    tipo: str, texto: str | None, usuario: Any, veiculo_id: int
) -> tuple[str, dict[str, str]] | None:
    """A leitura no editar (T-421): o PDF não vem no `PATCH`, então o comprovante amarra o
    veículo e a pessoa, e o SHA-256 dele é o que entra nos resumos. Devolve o SHA e os resumos;
    de outro veículo, do cadastro, vencido ou de outra pessoa: `None`."""
    dados = _abrir(tipo, texto, usuario)
    if dados is None or dados.get("veiculo") != veiculo_id:
        return None
    return str(dados.get("arquivo")), _resumos(dados)


def campos_do_documento(
    resumos: dict[str, str], conteudo: bytes, gravados: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Os campos lidos do documento e, entre eles, os que a pessoa mudou antes de salvar."""
    return campos_pelo_hash(resumos, sha256(conteudo), gravados)


def campos_pelo_hash(
    resumos: dict[str, str], hash_do_arquivo: str, gravados: dict[str, Any]
) -> tuple[list[str], list[str]]:
    lidos = [campo for campo in gravados if campo in resumos]
    corrigidos = [
        campo
        for campo in lidos
        if not hmac.compare_digest(resumos[campo], resumo(hash_do_arquivo, campo, gravados[campo]))
    ]
    return lidos, corrigidos
