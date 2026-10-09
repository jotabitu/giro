"""Arquivos privados (ADR 0009, AUD-05): fotos de documentos e vistorias, comprovantes, PDFs.

Use num `FileField`:

    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado, upload_to=arquivos.caminho_privado,
        null=True, blank=True,
    )

- O caminho é `<schema>/<app>/<model>/<id>/<uuid>.<ext>`: grave o objeto antes do arquivo
  (`objeto.arquivo.save(nome, conteudo)`), para o id existir.
- `arquivo.url` é assinada e vale 15 minutos; cada leitura gera outra (`url_assinada`).
- `validar(arquivo)` recusa o que não é PDF, JPG ou PNG pelo conteúdo, não pelo nome, e o que
  passa de 10 MB (400 `validacao`).

O provedor vem de `GIRO_ARMAZENAMENTO`: `falso` (na memória, desenvolvimento e testes) ou `s3`
(qualquer serviço compatível com S3, com `boto3`, carregado só quando usado).
"""

import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import IO, Any, Protocol
from urllib.parse import quote, urlencode

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import models
from django.utils.deconstruct import deconstructible

from comum import relogio
from comum.conexao import schema_atual
from comum.erros import ErroDeValidacao

VALIDADE_DA_URL = timedelta(minutes=15)  # AUD-05
TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10 MB

# Assinatura do conteúdo → (extensão, tipo). Vale o conteúdo, não a extensão do nome.
FORMATOS: tuple[tuple[bytes, str, str], ...] = (
    (b"%PDF-", "pdf", "application/pdf"),
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
)
EXTENSOES_ACEITAS = frozenset({"pdf", "jpg", "jpeg", "png"})
MENSAGEM_FORMATO = "Envie um arquivo PDF, JPG ou PNG."
MENSAGEM_TAMANHO = "O arquivo passa de 10 MB."


@dataclass(frozen=True)
class Formato:
    extensao: str
    tipo_conteudo: str


def _formato_do_conteudo(inicio: bytes) -> Formato | None:
    for assinatura, extensao, tipo in FORMATOS:
        if inicio.startswith(assinatura):
            return Formato(extensao, tipo)
    return None


def validar(arquivo: Any, campo: str = "arquivo") -> Formato:
    """PDF, JPG ou PNG de verdade (pelo conteúdo e pela extensão), até 10 MB. Senão, 400."""
    if arquivo.size > TAMANHO_MAXIMO:
        raise ErroDeValidacao({campo: [MENSAGEM_TAMANHO]})
    extensao = os.path.splitext(arquivo.name or "")[1].lower().lstrip(".")
    arquivo.seek(0)
    formato = _formato_do_conteudo(arquivo.read(16))
    arquivo.seek(0)
    if formato is None or extensao not in EXTENSOES_ACEITAS:
        raise ErroDeValidacao({campo: [MENSAGEM_FORMATO]})
    return formato


def caminho_privado(instancia: models.Model, nome: str) -> str:
    """`<schema>/<app>/<model>/<id>/<uuid>.<ext>`. O nome original não vai para o caminho."""
    if instancia.pk is None:
        raise ValueError("Grave o objeto antes do arquivo: o caminho leva o id (ADR 0009).")
    meta = instancia._meta
    extensao = os.path.splitext(nome)[1].lower()
    prefixo = f"{schema_atual()}/{meta.app_label}/{meta.model_name}/{instancia.pk}"
    return f"{prefixo}/{uuid.uuid4().hex}{extensao}"


@dataclass(frozen=True)
class UrlAssinada:
    url: str
    expira_em: datetime


class Provedor(Protocol):
    def salvar(self, caminho: str, conteudo: bytes, tipo_conteudo: str) -> None: ...
    def ler(self, caminho: str) -> bytes: ...
    def existe(self, caminho: str) -> bool: ...
    def tamanho(self, caminho: str) -> int: ...
    def url(self, caminho: str, expira_em: datetime) -> str: ...


# --- Falso: na memória, para desenvolvimento e testes ---

guardados: dict[str, tuple[bytes, str]] = {}


class ProvedorFalso:
    """Guarda na memória e assina a URL com HMAC da SECRET_KEY, com um `nonce`, para cada
    leitura gerar uma URL diferente, como o S3 faz."""

    def salvar(self, caminho: str, conteudo: bytes, tipo_conteudo: str) -> None:
        guardados[caminho] = (conteudo, tipo_conteudo)

    def ler(self, caminho: str) -> bytes:
        return guardados[caminho][0]

    def existe(self, caminho: str) -> bool:
        return caminho in guardados

    def tamanho(self, caminho: str) -> int:
        return len(guardados[caminho][0])

    def url(self, caminho: str, expira_em: datetime) -> str:
        expira = str(int(expira_em.timestamp()))
        nonce = secrets.token_hex(8)
        assinatura = hmac.new(
            settings.SECRET_KEY.encode(),
            f"{caminho}|{expira}|{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        consulta = urlencode({"expira": expira, "nonce": nonce, "assinatura": assinatura})
        return f"https://arquivos.invalid/{quote(caminho)}?{consulta}"


# --- S3 (ou compatível) ---


class ProvedorS3:
    """Bucket privado; leitura só por URL assinada."""

    def __init__(self) -> None:
        import boto3  # type: ignore[import-untyped,import-not-found,unused-ignore]

        self.bucket = settings.S3_BUCKET
        self.cliente = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            region_name=settings.S3_REGIAO or None,
            aws_access_key_id=settings.S3_CHAVE_DE_ACESSO or None,
            aws_secret_access_key=settings.S3_CHAVE_SECRETA or None,
        )

    def salvar(self, caminho: str, conteudo: bytes, tipo_conteudo: str) -> None:
        self.cliente.put_object(
            Bucket=self.bucket,
            Key=caminho,
            Body=conteudo,
            ContentType=tipo_conteudo,
            ServerSideEncryption="AES256",
        )

    def ler(self, caminho: str) -> bytes:
        resposta = self.cliente.get_object(Bucket=self.bucket, Key=caminho)
        return bytes(resposta["Body"].read())

    def existe(self, caminho: str) -> bool:
        try:
            self.cliente.head_object(Bucket=self.bucket, Key=caminho)
        except self.cliente.exceptions.ClientError:
            return False
        return True

    def tamanho(self, caminho: str) -> int:
        return int(self.cliente.head_object(Bucket=self.bucket, Key=caminho)["ContentLength"])

    def url(self, caminho: str, expira_em: datetime) -> str:
        segundos = max(1, int((expira_em - relogio.agora()).total_seconds()))
        return str(
            self.cliente.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": caminho},
                ExpiresIn=segundos,
            )
        )


def provedor() -> Provedor:
    nome = getattr(settings, "GIRO_ARMAZENAMENTO", "falso")
    if nome == "falso":
        return ProvedorFalso()
    if nome == "s3":
        return ProvedorS3()
    raise ValueError(f"Armazenamento desconhecido: {nome}")


def url_assinada(caminho: str) -> UrlAssinada:
    """Nova a cada chamada; vale 15 minutos (AUD-05)."""
    expira_em = relogio.agora() + VALIDADE_DA_URL
    return UrlAssinada(provedor().url(caminho, expira_em), expira_em)


@deconstructible
class ArmazenamentoPrivado(Storage):
    """O `Storage` do Django por cima do provedor. Nada é apagado (registro de negócio)."""

    def _save(self, name: str, content: Any) -> str:
        content.seek(0)
        dados = content.read()
        formato = _formato_do_conteudo(dados[:16])
        tipo = formato.tipo_conteudo if formato else "application/octet-stream"
        provedor().salvar(name, dados, tipo)
        return name

    def _open(self, name: str, mode: str = "rb") -> IO[Any]:
        return ContentFile(provedor().ler(name), name=name)

    def exists(self, name: str) -> bool:
        return provedor().existe(name)

    def size(self, name: str) -> int:
        return provedor().tamanho(name)

    def url(self, name: str | None) -> str:
        return url_assinada(name or "").url

    def delete(self, name: str) -> None:
        raise NotImplementedError("Arquivo de negócio não é apagado (ADR 0009).")

    def get_available_name(self, name: str, max_length: int | None = None) -> str:
        return name  # o caminho já leva um uuid


_armazenamento = ArmazenamentoPrivado()


def armazenamento_privado() -> ArmazenamentoPrivado:
    """Callable para `FileField(storage=...)`, para a migração não guardar a instância."""
    return _armazenamento
