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
import io
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
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


def sem_metadados(arquivo: Any, formato: Formato) -> Any:
    """Foto (JPG ou PNG) reprocessada: só os pixels, sem EXIF, GPS nem texto embutido (AUD-05).

    PDF volta como veio. Imagem que não abre: 400 `validacao`, como formato errado.
    """
    if formato.extensao == "pdf":
        arquivo.seek(0)
        return arquivo
    from PIL import Image, ImageOps, UnidentifiedImageError

    arquivo.seek(0)
    try:
        with Image.open(arquivo) as original:
            original.load()
            # A orientação do EXIF vai para os pixels antes de o EXIF sair.
            imagem = ImageOps.exif_transpose(original)
            limpa = Image.new(imagem.mode, imagem.size)
            limpa.paste(imagem)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as erro:
        raise ErroDeValidacao({"arquivo": [MENSAGEM_FORMATO]}) from erro
    saida = io.BytesIO()
    if formato.extensao == "jpg":
        if limpa.mode not in ("RGB", "L"):
            limpa = limpa.convert("RGB")
        limpa.save(saida, format="JPEG", quality=90)
    else:
        limpa.save(saida, format="PNG")
    nome = f"{os.path.splitext(arquivo.name or 'arquivo')[0]}.{formato.extensao}"
    return ContentFile(saida.getvalue(), name=nome)


def nota_limpa(nota: Any) -> Any:
    """Nota de despesa (FIN-06): imagem ou PDF pelo conteúdo; a imagem sai sem EXIF nem GPS, como
    as fotos (B-03 da T-315). Vale para toda nota gravada."""
    return sem_metadados(nota, validar(nota, "nota"))


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
    def apagar(self, caminho: str) -> None: ...
    def apagar_prefixo(self, prefixo: str) -> int: ...


# --- Falso: na memória, para desenvolvimento e testes ---

guardados: dict[str, tuple[bytes, str]] = {}


def assinar(caminho: str, expira: str, nonce: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(), f"{caminho}|{expira}|{nonce}".encode(), hashlib.sha256
    ).hexdigest()


def _diretorio_falso() -> Path | None:
    """Pasta do armazenamento falso em disco (só no desenvolvimento, T-218). Vazia = memória."""
    pasta = getattr(settings, "GIRO_ARQUIVOS_FALSOS_DIRETORIO", "")
    return Path(pasta) if pasta else None


def _arquivo_em_disco(pasta: Path, caminho: str) -> Path:
    alvo = (pasta / caminho).resolve()
    if not alvo.is_relative_to(pasta.resolve()):
        raise ValueError("Caminho fora da pasta de arquivos.")
    return alvo


def ler_falso(caminho: str) -> tuple[bytes, str] | None:
    """Conteúdo e tipo guardados no provedor falso, ou None se não existir."""
    pasta = _diretorio_falso()
    if pasta is None:
        return guardados.get(caminho)
    try:
        alvo = _arquivo_em_disco(pasta, caminho)
        tipo = alvo.with_name(alvo.name + ".tipo").read_text(encoding="utf-8")
        return alvo.read_bytes(), tipo
    except (OSError, ValueError):
        return None


class ProvedorFalso:
    """Guarda na memória (testes) ou numa pasta em disco (desenvolvimento, quando
    `GIRO_ARQUIVOS_FALSOS_DIRETORIO` está definida) e assina a URL com HMAC da SECRET_KEY, com um
    `nonce`, para cada leitura gerar uma URL diferente, como o S3 faz."""

    def salvar(self, caminho: str, conteudo: bytes, tipo_conteudo: str) -> None:
        pasta = _diretorio_falso()
        if pasta is None:
            guardados[caminho] = (conteudo, tipo_conteudo)
            return
        alvo = _arquivo_em_disco(pasta, caminho)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(conteudo)
        alvo.with_name(alvo.name + ".tipo").write_text(tipo_conteudo, encoding="utf-8")

    def ler(self, caminho: str) -> bytes:
        guardado = ler_falso(caminho)
        if guardado is None:
            raise KeyError(caminho)
        return guardado[0]

    def existe(self, caminho: str) -> bool:
        return ler_falso(caminho) is not None

    def tamanho(self, caminho: str) -> int:
        return len(self.ler(caminho))

    def apagar(self, caminho: str) -> None:
        pasta = _diretorio_falso()
        if pasta is None:
            guardados.pop(caminho, None)
            return
        alvo = _arquivo_em_disco(pasta, caminho)
        alvo.unlink(missing_ok=True)
        alvo.with_name(alvo.name + ".tipo").unlink(missing_ok=True)

    def apagar_prefixo(self, prefixo: str) -> int:
        pasta = _diretorio_falso()
        if pasta is None:
            caminhos = [caminho for caminho in guardados if caminho.startswith(prefixo)]
            for caminho in caminhos:
                del guardados[caminho]
            return len(caminhos)
        raiz = _arquivo_em_disco(pasta, prefixo)
        arquivos = [a for a in raiz.rglob("*") if a.is_file() and not a.name.endswith(".tipo")]
        for arquivo in arquivos:
            self.apagar(arquivo.relative_to(pasta.resolve()).as_posix())
        return len(arquivos)

    def url(self, caminho: str, expira_em: datetime) -> str:
        expira = str(int(expira_em.timestamp()))
        nonce = secrets.token_hex(8)
        assinatura = assinar(caminho, expira, nonce)
        consulta = urlencode({"expira": expira, "nonce": nonce, "assinatura": assinatura})
        base = settings.GIRO_ARQUIVOS_FALSOS_BASE
        return f"{base}/{quote(caminho)}?{consulta}"


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

    def apagar(self, caminho: str) -> None:
        """Com versionamento no bucket, apaga também as versões antigas e o marcador de
        exclusão: o arquivo temporário não fica recuperável (importação de clientes)."""
        self.cliente.delete_object(Bucket=self.bucket, Key=caminho)
        resposta = self.cliente.list_object_versions(Bucket=self.bucket, Prefix=caminho)
        for item in [*resposta.get("Versions", []), *resposta.get("DeleteMarkers", [])]:
            if item["Key"] == caminho and item.get("VersionId") not in (None, "null"):
                self.cliente.delete_object(
                    Bucket=self.bucket, Key=caminho, VersionId=item["VersionId"]
                )

    def apagar_prefixo(self, prefixo: str) -> int:
        """Todos os objetos do prefixo, com as versões antigas e os marcadores de exclusão
        (AUD-08, ADR 0025): nada fica recuperável pelo bucket. Devolve quantos arquivos saíram."""
        apagados = 0
        paginas = self.cliente.get_paginator("list_object_versions").paginate(
            Bucket=self.bucket, Prefix=prefixo
        )
        for pagina in paginas:
            versoes = [*pagina.get("Versions", []), *pagina.get("DeleteMarkers", [])]
            apagados += sum(1 for item in pagina.get("Versions", []) if item.get("IsLatest"))
            objetos = [
                {"Key": item["Key"], "VersionId": item["VersionId"]}
                for item in versoes
                if item["Key"].startswith(prefixo)
            ]
            for inicio in range(0, len(objetos), 1000):  # o limite do DeleteObjects
                self.cliente.delete_objects(
                    Bucket=self.bucket, Delete={"Objects": objetos[inicio : inicio + 1000]}
                )
        return apagados

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


def apagar_temporario(caminho: str) -> None:
    """Só para arquivo temporário (exportação vencida, AUD-07; planilha da importação). Arquivo
    de negócio não sai."""
    provedor().apagar(caminho)


def apagar_arquivos_da_empresa(schema_name: str) -> int:
    """AUD-08 (ADR 0025): todos os arquivos do prefixo `<schema>/` da empresa apagada no 90º dia.
    Só pelo `plataforma.services.apagar_empresa`. Pode rodar de novo (prefixo vazio: 0)."""
    if not schema_name or "/" in schema_name or schema_name in ("public", "."):
        raise ValueError(f"Prefixo de empresa inválido: {schema_name!r}")
    return provedor().apagar_prefixo(f"{schema_name}/")


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
