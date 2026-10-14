"""Erros de negócio (ADR 0009) e o exception handler do DRF.

Serviços levantam estas exceções sem conhecer HTTP; `tratar_excecao` traduz para a resposta
`{"codigo", "mensagem", "detalhes"}`. Erro de validação de campo vira
`{"codigo": "validacao", "mensagem", "campos": {campo: [mensagens]}}`.
"""

from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response


class ErroDeNegocio(Exception):
    """Base. `codigo` é o código da regra (`LOC-07`) ou um identificador fechado."""

    status_http: int = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, codigo: str, mensagem: str, detalhes: dict[str, Any] | None = None) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.detalhes = detalhes

    def como_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, "detalhes": self.detalhes}


class ErroDeValidacao(ErroDeNegocio):
    """Campo inválido, detectado no serviço. HTTP 400, no mesmo formato do serializer."""

    status_http: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, campos: dict[str, list[str]]) -> None:
        super().__init__("validacao", "Confira os campos destacados")
        self.campos = campos

    def como_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, "campos": self.campos}


class ErroDeRegra(ErroDeNegocio):
    """Uma regra de negócio impediu a ação. HTTP 422."""


class LimiteDoPlano(ErroDeNegocio):
    """Limite do plano atingido (PLT-03). HTTP 422."""

    def __init__(self, mensagem: str, detalhes: dict[str, Any] | None = None) -> None:
        super().__init__("PLT-03", mensagem, detalhes)


class Conflito(ErroDeNegocio):
    """O estado atual do recurso impede a ação. HTTP 409."""

    status_http: int = status.HTTP_409_CONFLICT


class TransicaoInvalida(Conflito):
    """Mudança de status fora da tabela de transições. HTTP 409."""


class NaoAutenticado(ErroDeNegocio):
    """401 com código próprio (`credenciais_invalidas`, `2fa_obrigatorio`)."""

    status_http: int = status.HTTP_401_UNAUTHORIZED


class NaoEncontrado(ErroDeNegocio):
    """404 com código próprio (ex.: `cep_nao_encontrado`)."""

    status_http: int = status.HTTP_404_NOT_FOUND


class SemPermissao(ErroDeNegocio):
    """Perfil ou função sem acesso à ação, com o código da regra (ex.: PLT-09). HTTP 403."""

    status_http: int = status.HTTP_403_FORBIDDEN


class Expirado(ErroDeNegocio):
    """O recurso existiu e não vale mais (ex.: link de exportação depois de 7 dias). HTTP 410."""

    status_http: int = status.HTTP_410_GONE


class MuitasTentativas(ErroDeNegocio):
    """Bloqueio por tentativas erradas (PLT-08, USR-06). HTTP 429."""

    status_http: int = status.HTTP_429_TOO_MANY_REQUESTS


class ParceiroForaDoAr(ErroDeNegocio):
    """Um parceiro externo (pagamentos) não respondeu. HTTP 503: tentar de novo depois."""

    status_http: int = status.HTTP_503_SERVICE_UNAVAILABLE


class EmpresaSemOperacao(ErroDeNegocio):
    """Empresa suspensa, pausada ou cancelada tentou escrever. HTTP 403."""

    status_http: int = status.HTTP_403_FORBIDDEN

    def __init__(self, status_empresa: str) -> None:
        super().__init__(
            "empresa_sem_operacao",
            "Sua empresa está sem operação no momento. Você pode ver e exportar os dados.",
            {"status_empresa": status_empresa},
        )


def tratar_excecao(exc: Exception, context: dict[str, Any]) -> Response | None:
    # Import local: models importam este módulo, e rest_framework.views lê as settings da API.
    from rest_framework.views import exception_handler

    if isinstance(exc, ErroDeNegocio):
        return Response(exc.como_dict(), status=exc.status_http)

    resposta = exception_handler(exc, context)
    if resposta is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        campos = exc.detail if isinstance(exc.detail, dict) else {"geral": exc.detail}
        resposta.data = {
            "codigo": "validacao",
            "mensagem": "Confira os campos destacados",
            "campos": campos,
        }
    elif isinstance(exc, exceptions.Throttled):
        resposta.data = {
            "codigo": "muitas_requisicoes",
            "mensagem": "Muitas tentativas seguidas. Espere um pouco e tente de novo.",
            "detalhes": {"tentar_de_novo_em_segundos": int(getattr(exc, "wait", None) or 0) + 1},
        }
    elif isinstance(exc, exceptions.APIException):
        resposta.data = {
            "codigo": _codigo_padrao(exc),
            "mensagem": str(exc.detail),
            "detalhes": None,
        }
    return resposta


# Códigos fixos de docs/api/README.md ("Erros").
_CODIGOS_POR_STATUS = {
    status.HTTP_401_UNAUTHORIZED: "nao_autenticado",
    status.HTTP_403_FORBIDDEN: "permissao",
    status.HTTP_404_NOT_FOUND: "nao_encontrado",
}


def _codigo_padrao(exc: exceptions.APIException) -> str:
    return _CODIGOS_POR_STATUS.get(exc.status_code) or str(exc.default_code)
