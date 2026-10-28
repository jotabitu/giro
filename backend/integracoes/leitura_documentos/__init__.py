"""Leitura de documentos em PDF num processo filho isolado (VEI-08, ADR 0026, itens 4 e 6).

`ler(tipo, conteudo)` roda `trabalhador.py` num processo novo, com o ambiente mínimo (só `PATH` e
`LANG`, M-01, montado pelo `env -i`: ver `comando`), sem `preexec_fn` (o filho aplica os próprios
limites, M-02), no modo isolado e pelo caminho absoluto (B-01). O pai espera 8 s de relógio, mata o
grupo do filho se passar, lê no máximo 64 KB da saída e confere de novo cada campo (só as chaves do
tipo, tipos e tamanhos).

Nada do conteúdo, do texto ou dos valores sai daqui para log ou exceção: a falha é um código
fechado (`MOTIVOS`). A saída de erro do filho é descartada.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from comum import relogio

TRABALHADOR = str(Path(__file__).resolve().parent / "trabalhador.py")
AMBIENTE = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}
ENV = "/usr/bin/env"
TEMPO_DE_RELOGIO = 8  # segundos
MAXIMO_DA_SAIDA = 64 * 1024
LEITURAS_SIMULTANEAS = 2  # por processo (pedido do devops na T-258, B-02)

MOTIVOS = (
    "nao_pdf",
    "grande",
    "senha",
    "sem_texto",
    "paginas",
    "tempo",
    "memoria",
    "nao_reconhecido",
)

# O que cada tipo pode devolver: campo → (tipo do valor, tamanho máximo do texto ou None).
CAMPOS_DO_TIPO: dict[str, dict[str, tuple[type, int | None]]] = {
    "crlv": {
        "placa": (str, 7),
        "chassi": (str, 17),
        "renavam": (str, 11),
        "marca_modelo": (str, 60),  # o limite da dica (B-01 da T-328)
        "ano_fabricacao": (int, None),
        "ano_modelo": (int, None),
        "cor": (str, 30),
        "combustivel": (str, 10),
        "exercicio": (int, None),
    },
}

_vagas = threading.BoundedSemaphore(LEITURAS_SIMULTANEAS)


class LeituraOcupada(Exception):
    """As leituras simultâneas do processo estão ocupadas: 503 `leitura_ocupada`."""


@dataclass(frozen=True)
class Leitura:
    campos: dict[str, Any] = field(default_factory=dict)
    motivo: str | None = None  # um de MOTIVOS quando falhou

    @property
    def falhou(self) -> bool:
        return self.motivo is not None


@contextmanager
def vaga() -> Iterator[None]:
    """Uma das leituras simultâneas do processo, sem esperar: cheio, `LeituraOcupada`."""
    if not _vagas.acquire(blocking=False):
        raise LeituraOcupada
    try:
        yield
    finally:
        _vagas.release()


def _matar(processo: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(processo.pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError, PermissionError):
        processo.kill()
    processo.wait()


def _escrever(processo: subprocess.Popen[bytes], conteudo: bytes) -> None:
    entrada = processo.stdin
    if entrada is None:
        return
    try:
        entrada.write(conteudo)
        entrada.close()
    except OSError:  # o filho saiu antes de ler tudo
        pass


def _conversar(processo: subprocess.Popen[bytes], conteudo: bytes) -> bytes | None:
    """Manda o PDF e lê no máximo `MAXIMO_DA_SAIDA` + 1 bytes, tudo dentro do tempo de relógio.
    Passou do tempo: mata o grupo do filho e devolve `None`."""
    resposta = processo.stdout
    if resposta is None:
        return None
    saida: list[bytes] = []
    escritor = threading.Thread(target=_escrever, args=(processo, conteudo), daemon=True)
    leitor = threading.Thread(
        target=lambda: saida.append(resposta.read(MAXIMO_DA_SAIDA + 1)),
        daemon=True,
    )
    limite = time.monotonic() + TEMPO_DE_RELOGIO
    escritor.start()
    leitor.start()
    leitor.join(TEMPO_DE_RELOGIO)
    try:
        if leitor.is_alive():
            raise subprocess.TimeoutExpired(TRABALHADOR, TEMPO_DE_RELOGIO)
        if saida and len(saida[0]) > MAXIMO_DA_SAIDA:
            _matar(processo)  # saída grande demais: não espera o filho terminar de escrever
            return saida[0]
        processo.wait(max(limite - time.monotonic(), 0.1))
    except subprocess.TimeoutExpired:
        _matar(processo)
        return None
    finally:
        resposta.close()
    return saida[0] if saida else b""


def comando(tipo: str) -> list[str]:
    """`env -i` com `PATH` e `LANG` na linha de comando, e então o intérprete no modo isolado.

    O `env=` do `Popen` não basta (T-399): com o Sentry ligado, a `StdlibIntegration` troca o
    `Popen.__init__` e acrescenta `SUBPROCESS_SENTRY_TRACE` e `SUBPROCESS_BAGGAGE` a uma cópia do
    `env`. O `env -i` descarta o que vier e dá `exec` no intérprete (mesmo PID, mesmo grupo, o
    mesmo código de saída), que nasce só com `PATH` e `LANG`."""
    ambiente = [f"{nome}={valor}" for nome, valor in AMBIENTE.items()]
    return [ENV, "-i", *ambiente, sys.executable, "-I", TRABALHADOR, tipo]


def executar(tipo: str, conteudo: bytes) -> dict[str, Any]:
    """Roda o filho e devolve o JSON dele, ou `{"ok": False, "motivo": ...}`."""
    # O comando é fixo: o env, o intérprete, o arquivo do trabalhador e um tipo da lista fechada.
    processo = subprocess.Popen(  # noqa: S603
        comando(tipo),
        env=AMBIENTE,
        close_fds=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    saida = _conversar(processo, conteudo)
    if saida is None:
        return {"ok": False, "motivo": "tempo"}
    if len(saida) > MAXIMO_DA_SAIDA:
        return {"ok": False, "motivo": "nao_reconhecido"}
    if processo.returncode != 0:
        # Sinal de CPU (SIGXCPU) ou morte por memória: o filho não respondeu.
        sinal = -processo.returncode
        cpu = getattr(signal, "SIGXCPU", None)
        motivo = "tempo" if sinal in (cpu, signal.SIGKILL) else "memoria"
        return {"ok": False, "motivo": motivo}
    try:
        resposta = json.loads(saida)
    except ValueError:
        return {"ok": False, "motivo": "nao_reconhecido"}
    return resposta if isinstance(resposta, dict) else {"ok": False, "motivo": "nao_reconhecido"}


# Segunda barreira (B-01 da T-328): o filho já valida, o pai confere de novo o que vale.
ANO_MINIMO = 1900
COMBUSTIVEIS = frozenset({"gasolina", "etanol", "flex", "diesel", "eletrico", "hibrido"})
CAMPOS_DE_ANO = frozenset({"ano_fabricacao", "ano_modelo", "exercicio"})


def _imprimivel(texto: str) -> bool:
    return not any(ord(c) < 0x20 or ord(c) == 0x7F for c in texto)


def conferir(tipo: str, campos: Any) -> dict[str, Any]:
    """Só as chaves do tipo, com o tipo e o tamanho certos; o resto é descartado (B-02, B-03 da
    T-247). Anos entre 1900 e o ano que vem, texto sem caractere de controle e o combustível do
    enum (B-01 da T-328)."""
    if not isinstance(campos, dict):
        return {}
    permitidos = CAMPOS_DO_TIPO[tipo]
    ano_maximo = relogio.hoje().year + 1
    conferidos: dict[str, Any] = {}
    for nome, (classe, tamanho) in permitidos.items():
        valor = campos.get(nome)
        if type(valor) is not classe:
            continue
        if isinstance(valor, str) and (
            not valor or (tamanho and len(valor) > tamanho) or not _imprimivel(valor)
        ):
            continue
        if nome in CAMPOS_DE_ANO and not (
            isinstance(valor, int) and ANO_MINIMO <= valor <= ano_maximo
        ):
            continue
        if nome == "combustivel" and valor not in COMBUSTIVEIS:
            continue
        conferidos[nome] = valor
    return conferidos


def ler(tipo: str, conteudo: bytes) -> Leitura:
    """A leitura do documento. Quem chama segura a `vaga()` antes."""
    if tipo not in CAMPOS_DO_TIPO:
        raise ValueError("Tipo de documento sem leitura.")
    resposta = executar(tipo, conteudo)
    if resposta.get("ok") is not True:
        motivo = resposta.get("motivo")
        return Leitura(motivo=motivo if motivo in MOTIVOS else "nao_reconhecido")
    campos = conferir(tipo, resposta.get("campos"))
    if not campos:
        return Leitura(motivo="nao_reconhecido")
    return Leitura(campos=campos)
