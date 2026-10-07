"""Cifra de dados pessoais e segredos e hash de busca (ADR 0014, item 2).

Cifra: só AES-256-GCM (`cryptography`, `AESGCM`; Fernet não aceita dado associado), com nonce
aleatório de 12 bytes por cifra. Formato gravado: `v<id_da_chave>:<base64(nonce + cifrado)>`.
Várias chaves podem estar configuradas; a de maior id cifra e as outras só decifram, o que
permite trocar de chave sem migração em massa.

Dado associado (AAD): empresa, tabela, campo e o `id_cifra` da linha. O cifrado copiado para
outra linha, outro campo ou outra empresa não decifra.

Hash de busca: HMAC-SHA256 do valor normalizado com uma chave por empresa,
`HMAC(GIRO_PEPPER_HMAC, empresa_id)`: o mesmo CPF dá hashes diferentes em empresas diferentes.
"""

import base64
import hashlib
import hmac
import os
import re
from functools import cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

from comum.conexao import conexao

DADOS_PESSOAIS = "dados_pessoais"
SEGREDOS = "segredos"

_CONFIG_DAS_CHAVES = {
    DADOS_PESSOAIS: "GIRO_CHAVE_DADOS_PESSOAIS",
    SEGREDOS: "GIRO_CHAVE_SEGREDOS",
}
_FORMATO = re.compile(r"^v(\d+):([A-Za-z0-9+/=]+)$")
TAMANHO_NONCE = 12
TAMANHO_CHAVE = 32


class ErroDeCifra(Exception):
    """Cifrado adulterado, copiado de outro lugar ou com chave que não está configurada."""


@cache
def _chaves(tipo: str) -> dict[int, bytes]:
    nome = _CONFIG_DAS_CHAVES[tipo]
    chaves: dict[int, bytes] = {}
    for item in filter(None, (parte.strip() for parte in str(getattr(settings, nome)).split(","))):
        id_texto, separador, chave_b64 = item.partition(":")
        if not separador or not id_texto.isdigit():
            raise ValueError(f"{nome}: use o formato <id>:<chave em base64>.")
        chave = base64.b64decode(chave_b64, validate=True)
        if len(chave) != TAMANHO_CHAVE:
            raise ValueError(f"{nome}: a chave {id_texto} precisa ter 32 bytes.")
        chaves[int(id_texto)] = chave
    if not chaves:
        raise ValueError(f"{nome} está vazia.")
    return chaves


def limpar_cache_de_chaves() -> None:
    """Depois de trocar as chaves nas settings (testes de rotação)."""
    _chaves.cache_clear()


def empresa_da_conexao() -> int:
    empresa_id = getattr(getattr(conexao(), "tenant", None), "pk", None)
    if empresa_id is None:
        raise ErroDeCifra("Sem empresa na conexão: não é possível cifrar nem calcular hash.")
    return int(empresa_id)


def dado_associado(empresa_id: int, tabela: str, campo: str, id_linha: str) -> bytes:
    """`empresa_id|tabela|campo|id_cifra` (ADR 0014)."""
    return f"{empresa_id}|{tabela}|{campo}|{id_linha}".encode()


def cifrar(texto: str, *, tipo: str, associado: bytes) -> str:
    chaves = _chaves(tipo)
    id_chave = max(chaves)
    nonce = os.urandom(TAMANHO_NONCE)
    cifrado = AESGCM(chaves[id_chave]).encrypt(nonce, texto.encode(), associado)
    return f"v{id_chave}:{base64.b64encode(nonce + cifrado).decode()}"


def decifrar(valor: str, *, tipo: str, associado: bytes) -> str:
    achado = _FORMATO.match(valor)
    if not achado:
        raise ErroDeCifra("Valor cifrado fora do formato.")
    chave = _chaves(tipo).get(int(achado.group(1)))
    if chave is None:
        raise ErroDeCifra("A chave deste valor cifrado não está configurada.")
    bruto = base64.b64decode(achado.group(2))
    try:
        claro = AESGCM(chave).decrypt(bruto[:TAMANHO_NONCE], bruto[TAMANHO_NONCE:], associado)
    except InvalidTag as erro:
        raise ErroDeCifra("O valor cifrado não pertence a este registro.") from erro
    return claro.decode()


def precisa_recifrar(valor: str, *, tipo: str) -> bool:
    """Verdadeiro quando o valor foi cifrado com uma chave que não é a atual."""
    achado = _FORMATO.match(valor)
    return bool(achado) and int(achado.group(1)) != max(_chaves(tipo))


def normalizar(valor: str) -> str:
    """Só letras e dígitos, maiúsculas: `123.218.330-45` e `12321833045` dão o mesmo hash."""
    return re.sub(r"[^0-9A-Za-z]", "", valor).upper()


def _chave_hmac_da_empresa(empresa_id: int) -> bytes:
    pepper = str(settings.GIRO_PEPPER_HMAC).encode()
    return hmac.new(pepper, str(empresa_id).encode(), hashlib.sha256).digest()


def hash_busca(valor: str, *, empresa_id: int | None = None) -> str:
    """HMAC-SHA256 (hex de 64) do valor normalizado, com a chave da empresa (atual, se omitida)."""
    empresa = empresa_da_conexao() if empresa_id is None else empresa_id
    return hmac.new(
        _chave_hmac_da_empresa(empresa), normalizar(valor).encode(), hashlib.sha256
    ).hexdigest()
