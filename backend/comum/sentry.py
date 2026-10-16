"""Sentry sem segredos (T-270: B-01 da T-189 e M-03 da T-247).

Módulo puro (só `sentry_sdk`), para `config/settings/base.py` importar sem circularidade. O que
sai do processo para o Sentry:

- sem variáveis locais dos quadros da pilha (`include_local_variables=False`): o CPF, o nome e o
  número da CNH lidos do PDF (ADR 0026, item 9) estariam num dicionário local;
- sem corpo de requisição (`max_request_body_size="never"`) e sem `request.data`;
- sem o cabeçalho `asaas-access-token`, `Authorization` e cookies; nas rotas `/api/webhooks/`,
  sem cabeçalho nenhum nem query string;
- o `EventScrubber` (recursivo) passa a cobrir também `asaas-access-token` e `creditCardToken`;
- nas tarefas do Celery, só o nome da tarefa (a integração anexaria `args` e `kwargs`).

O rastro da pilha, o tipo e a mensagem da exceção continuam: a mensagem não pode carregar dado
pessoal nem a saída do filho da leitura de PDF (B-02 da T-247).
"""

from typing import Any

from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

CABECALHOS_SECRETOS = frozenset(
    {"asaas-access-token", "authorization", "proxy-authorization", "cookie", "set-cookie"}
)
# Minúsculas: o EventScrubber compara a chave em minúsculas.
CHAVES_SECRETAS = [
    *DEFAULT_DENYLIST,
    "asaas-access-token",
    "creditcardtoken",
    "credit_card_token",
    "cartao_token",
    "authtoken",
    "access_token",
]
ROTA_DE_WEBHOOK = "/api/webhooks/"
FILTRADO = "[Filtrado]"


def _chave_secreta(nome: str) -> bool:
    return nome.lower() in CABECALHOS_SECRETOS


def limpar_evento(evento: Any, dica: Any) -> Any:
    requisicao = evento.get("request")
    if isinstance(requisicao, dict):
        requisicao.pop("data", None)
        requisicao.pop("cookies", None)
        if ROTA_DE_WEBHOOK in str(requisicao.get("url", "")):
            requisicao.pop("headers", None)
            requisicao.pop("query_string", None)
        cabecalhos = requisicao.get("headers")
        if isinstance(cabecalhos, dict):
            requisicao["headers"] = {
                nome: (FILTRADO if _chave_secreta(nome) else valor)
                for nome, valor in cabecalhos.items()
            }
    tarefa = (evento.get("extra") or {}).get("celery-job")
    if isinstance(tarefa, dict):
        evento["extra"]["celery-job"] = {"task_name": tarefa.get("task_name")}
    return evento


def opcoes_do_sentry(dsn: str, ambiente: str) -> dict[str, Any]:
    return {
        "dsn": dsn,
        "environment": ambiente,
        "send_default_pii": False,
        "traces_sample_rate": 0.0,
        "include_local_variables": False,
        "max_request_body_size": "never",
        "event_scrubber": EventScrubber(denylist=CHAVES_SECRETAS, recursive=True),
        "before_send": limpar_evento,
    }
