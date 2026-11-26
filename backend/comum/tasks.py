"""Tarefas de `comum` (ADR 0012).

`arquivos_apagar` tira do armazenamento os arquivos de dado pessoal que o registro já soltou
(AUD-06, CLI-13, S-15; revisão da Segurança no #679, B3). Roda depois do commit, fora da resposta,
e tenta de novo quando o armazenamento falha: o arquivo não fica órfão.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)

TENTATIVAS = 12


def _conferir(schema_name: str, caminhos: list[str], pastas: list[str]) -> None:
    """Só caminhos dentro do schema da empresa, e pasta com pelo menos `<schema>/<app>/<x>/`:
    nunca o prefixo inteiro da empresa (esse é só da AUD-08)."""
    if not schema_name or "/" in schema_name or schema_name in ("public", "."):
        raise ValueError(f"Schema inválido: {schema_name!r}")
    prefixo = f"{schema_name}/"
    for caminho in [*caminhos, *pastas]:
        if not caminho.startswith(prefixo) or ".." in caminho.split("/"):
            raise ValueError(f"Caminho fora da empresa: {caminho!r}")
    for pasta in pastas:
        if len([parte for parte in pasta.split("/") if parte]) < 3:
            raise ValueError(f"Pasta curta demais: {pasta!r}")


@shared_task(
    name="arquivos_apagar",
    autoretry_for=(Exception,),
    dont_autoretry_for=(ValueError,),
    retry_backoff=60,
    retry_backoff_max=60 * 60,
    max_retries=TENTATIVAS,
)
def arquivos_apagar(
    schema_name: str, caminhos: list[str] | None = None, pastas: list[str] | None = None
) -> int:
    """Idempotente: apagar o que já saiu não falha. Devolve quantos arquivos saíram."""
    from comum import arquivos

    caminhos, pastas = list(caminhos or []), list(pastas or [])
    _conferir(schema_name, caminhos, pastas)
    provedor = arquivos.provedor()
    for caminho in caminhos:
        provedor.apagar(caminho)
    return len(caminhos) + sum(provedor.apagar_prefixo(pasta) for pasta in pastas)


def _agendar(schema_name: str, caminhos: list[str], pastas: list[str]) -> None:
    try:
        arquivos_apagar.delay(schema_name, caminhos, pastas)
    except Exception:  # a resposta não depende da remoção (B3); o erro vai ao log e ao Sentry
        logger.exception("Remoção de arquivos não agendada (%s).", schema_name)


def apagar_depois_do_commit(caminhos: list[str], pastas: list[str] | None = None) -> None:
    """Agenda a remoção para depois do commit da transação atual (se algo falhar antes, nenhum
    arquivo some sem o registro mudar). Sem nada a apagar, não agenda."""
    from django.db import transaction

    from comum.conexao import schema_atual

    caminhos, lista_de_pastas = list(caminhos), list(pastas or [])
    if not caminhos and not lista_de_pastas:
        return
    schema = schema_atual()
    transaction.on_commit(lambda: _agendar(schema, caminhos, lista_de_pastas))
