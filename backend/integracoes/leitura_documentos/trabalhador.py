"""Processo filho da leitura de documentos em PDF (ADR 0026, item 4).

Chamado só por `integracoes.leitura_documentos.ler`, como
`[sys.executable, "-I", <este arquivo>, <tipo>]`: o PDF chega pela entrada padrão e a resposta
sai pela saída padrão, em JSON (`{"ok": true, "campos": {...}}` ou `{"ok": false, "motivo": ...}`).

A primeira coisa é aplicar os próprios limites (M-02), antes de importar o `pypdf`. Depois, só a
biblioteca padrão, o `pypdf` e os módulos irmãos (`crlv.py`): nunca o Django nem outro app (B-01).
O texto extraído morre aqui: só os campos permitidos voltam ao pai.
"""

import json
import os
import sys

TEMPO_DE_CPU = 5  # segundos
MEMORIA = 512 * 1024 * 1024  # espaço de endereço
ARQUIVOS_ABERTOS = 16
MAXIMO_DE_PAGINAS = 3
MAXIMO_DE_CARACTERES = 200_000
TAMANHO_MAXIMO = 2 * 1024 * 1024

# O tipo `_diagnostico` existe para os testes da ADR 0026 (ambiente, limites e módulos do filho):
# devolve só nomes e números, nunca valores do ambiente.
TIPOS = ("crlv", "_diagnostico")


def aplicar_limites() -> None:
    """RLIMIT_CPU, AS, FSIZE, NOFILE e CORE. Sem `resource` (Windows fora do Docker), segue só
    com o tempo do pai. Se algum `setrlimit` falhar, sai com erro antes de ler o arquivo."""
    try:
        import resource
    except ImportError:
        return
    for limite, valor in (
        (resource.RLIMIT_CPU, TEMPO_DE_CPU),
        (resource.RLIMIT_AS, MEMORIA),
        (resource.RLIMIT_FSIZE, 0),
        (resource.RLIMIT_NOFILE, ARQUIVOS_ABERTOS),
        (resource.RLIMIT_CORE, 0),
    ):
        resource.setrlimit(limite, (valor, valor))


def _responder(resposta: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(resposta))
    sys.stdout.flush()


def _falha(motivo: str) -> dict[str, object]:
    return {"ok": False, "motivo": motivo}


def _diagnostico() -> dict[str, object]:
    limites: dict[str, list[int]] = {}
    try:
        import resource

        for nome in ("RLIMIT_CPU", "RLIMIT_AS", "RLIMIT_FSIZE", "RLIMIT_NOFILE", "RLIMIT_CORE"):
            limites[nome] = list(resource.getrlimit(getattr(resource, nome)))
    except ImportError:
        pass
    import crlv  # type: ignore[import-not-found]  # noqa: F401
    import pypdf  # noqa: F401  (o diagnóstico confere os módulos depois do import de verdade)

    modulos = sorted(m for m in ("django", "comum", "apps", "config") if m in sys.modules)
    return {"ok": True, "ambiente": sorted(os.environ), "limites": limites, "modulos": modulos}


def ler_pdf(tipo: str, conteudo: bytes) -> dict[str, object]:
    if len(conteudo) > TAMANHO_MAXIMO:
        return _falha("grande")
    if not conteudo.startswith(b"%PDF-"):
        return _falha("nao_pdf")
    import io

    import crlv
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        leitor = PdfReader(io.BytesIO(conteudo))
        if leitor.is_encrypted:
            return _falha("senha")
        if len(leitor.pages) > MAXIMO_DE_PAGINAS:
            return _falha("paginas")
        partes: list[str] = []
        total = 0
        for pagina in leitor.pages:
            parte = pagina.extract_text(extraction_mode="layout")
            total += len(parte)
            if total > MAXIMO_DE_CARACTERES:
                return _falha("nao_reconhecido")
            partes.append(parte)
    except MemoryError:
        return _falha("memoria")
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError, IndexError):
        return _falha("nao_reconhecido")
    texto = "\n".join(partes)
    if not texto.strip():
        return _falha("sem_texto")
    campos = crlv.extrair(texto)
    if not campos:
        return _falha("nao_reconhecido")
    return {"ok": True, "campos": campos}


def principal() -> None:
    aplicar_limites()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    tipo = sys.argv[1] if len(sys.argv) > 1 else ""
    if tipo not in TIPOS:
        _responder(_falha("nao_reconhecido"))
        return
    if tipo == "_diagnostico":
        _responder(_diagnostico())
        return
    conteudo = sys.stdin.buffer.read(TAMANHO_MAXIMO + 1)
    try:
        resposta = ler_pdf(tipo, conteudo)
    except MemoryError:
        resposta = _falha("memoria")
    except Exception:  # qualquer outra falha do parser: só o código, nunca a mensagem
        resposta = _falha("nao_reconhecido")
    _responder(resposta)


if __name__ == "__main__":
    principal()
