"""Registro de eventos de auditoria (AUD-01, ADR 0010).

O model `auditoria.EventoAuditoria` fica no app `auditoria`, que está abaixo de `comum` na
ordem da ADR 0011; por isso ele é resolvido com `apps.get_model`, sem import.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from django.apps import apps
from django.db import models, transaction
from django.db.models.fields.files import FieldFile
from django_tenants.utils import get_public_schema_name

from comum import classificacao
from comum.conexao import conexao


class Categoria(models.TextChoices):
    """AUD-02."""

    FINANCEIRO = "financeiro", "Financeiro"
    OPERACAO = "operacao", "Operação"
    CONFIGURACOES = "configuracoes", "Configurações"
    SEGURANCA = "seguranca", "Segurança"
    SUPORTE = "suporte", "Suporte"


class TipoAtor(models.TextChoices):
    USUARIO = "usuario", "Usuário"
    SISTEMA = "sistema", "Sistema"
    SUPORTE = "suporte", "Suporte Giro"


@dataclass(frozen=True)
class Ator:
    tipo: str
    nome: str
    id: int | None = None
    ip: str | None = None
    aparelho: str = ""
    acesso_suporte_id: int | None = None
    regra: str = ""


ATOR_SISTEMA = Ator(tipo=TipoAtor.SISTEMA, nome="Sistema")

_ator: ContextVar[Ator | Callable[[], Ator] | None] = ContextVar("ator_auditoria", default=None)


def ator_atual() -> Ator:
    """Quem está agindo agora. Sem requisição nem tarefa, é o Sistema."""
    valor = _ator.get()
    if valor is None:
        return ATOR_SISTEMA
    return valor() if callable(valor) else valor


def limpar_ator() -> None:
    """Volta ao Sistema. Só para o início e o fim de cada tarefa no worker (S-11)."""
    _ator.set(None)


@contextmanager
def usar_ator(ator: Ator | Callable[[], Ator]) -> Iterator[None]:
    token = _ator.set(ator)
    try:
        yield
    finally:
        _ator.reset(token)


# Só models destes pacotes declaram `CAMPOS_AUDITORIA` (teste de arquitetura da ADR 0014).
PACOTES_DO_GIRO = ("apps.", "comum.", "tests.")

# Campos que não entram no retrato (mudam a cada save e não dizem nada).
CAMPOS_IGNORADOS = frozenset({"atualizado_em"})


def retrato(objeto: models.Model) -> dict[str, Any]:
    """Valores reais dos campos. A classificação (omitir, mascarar) é aplicada ao gravar.
    Arquivo entra pelo caminho no armazenamento, nunca pelo conteúdo."""
    return {
        campo.attname: _valor(getattr(objeto, campo.attname))
        for campo in objeto._meta.concrete_fields
        if campo.name not in CAMPOS_IGNORADOS
    }


def _valor(valor: Any) -> Any:
    if isinstance(valor, FieldFile):
        return valor.name or None
    return valor


def diferenca(
    antes: dict[str, Any], depois: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Só os campos que mudaram."""
    mudados = [chave for chave in depois if antes.get(chave) != depois[chave]]
    return {c: antes[c] for c in mudados if c in antes}, {c: depois[c] for c in mudados}


def registrar_evento(
    acao: str,
    categoria: str,
    *,
    objeto: models.Model | None = None,
    antes: dict[str, Any] | None = None,
    depois: dict[str, Any] | None = None,
    motivo: str = "",
    regra: str = "",
    filial_id: int | None = None,
) -> Any:
    """Grava um evento. Para ações sem objeto (login, exportação), omita `objeto`.

    Com `objeto`, `antes` e `depois` passam pela classificação do model (ADR 0014, item 3):
    passe os valores reais, nunca já mascarados. A filial do evento é `filial_id`, quando vier
    (o objeto sem filial própria, como o movimento do caixa), senão a do objeto (AUD-02).
    """
    evento_auditoria = apps.get_model("auditoria", "EventoAuditoria")
    # R-06 da T-050: o que vai para `antes`/`depois` sempre passa pela classificação, e só models
    # do Giro a declaram (os do django-otp e da blacklist do simplejwt não entram na auditoria).
    if objeto is None and (antes or depois):
        raise ValueError("Evento sem objeto não leva antes nem depois: não há como classificar.")
    if objeto is not None and not type(objeto).__module__.startswith(PACOTES_DO_GIRO):
        raise ValueError(f"{type(objeto).__name__} não é model do Giro; audite pelo dono dele.")
    if objeto is not None:
        no_public = conexao().schema_name == get_public_schema_name()
        antes, depois = classificacao.aplicar(
            type(objeto), antes or {}, depois or {}, no_public=no_public
        )
    ator = ator_atual()
    return evento_auditoria.objects.create(
        ator_tipo=ator.tipo,
        ator_id=ator.id,
        ator_nome=ator.nome,
        acesso_suporte_id=ator.acesso_suporte_id,
        acao=acao,
        categoria=categoria,
        objeto_tipo=objeto._meta.model_name if objeto is not None else "",
        objeto_id=objeto.pk if objeto is not None else None,
        objeto_codigo=getattr(objeto, "codigo", "") or "",
        filial_id=filial_id if filial_id is not None else getattr(objeto, "filial_id", None),
        antes=antes or {},
        depois=depois or {},
        motivo=motivo,
        ip=ator.ip,
        aparelho=ator.aparelho,
        regra=regra or ator.regra,
    )


@contextmanager
def auditar(
    objeto: models.Model,
    acao: str,
    categoria: str,
    *,
    motivo: str = "",
    regra: str = "",
    filial_id: int | None = None,
) -> Iterator[None]:
    """Retrato antes e depois do bloco e evento gravado na mesma transação.

    Uso: `with auditar(veiculo, "veiculo.editar", Categoria.OPERACAO): ... veiculo.save()`.
    O "antes" vem do banco, então o objeto pode ser alterado dentro ou fora do bloco.
    """
    with transaction.atomic():
        antes: dict[str, Any] = {}
        if objeto.pk is not None:
            salvo = type(objeto)._base_manager.filter(pk=objeto.pk).first()
            if salvo is not None:
                antes = retrato(salvo)
        yield
        mudou_antes, mudou_depois = diferenca(antes, retrato(objeto))
        registrar_evento(
            acao,
            categoria,
            objeto=objeto,
            antes=mudou_antes,
            depois=mudou_depois,
            motivo=motivo,
            regra=regra,
            filial_id=filial_id,
        )


# --- Leitura dos eventos (T-018, docs/api/auditoria.md) ---


@dataclass(frozen=True)
class Texto:
    """`resumo` e `detalhe` prontos para a tela: o frontend não monta frase."""

    resumo: str
    detalhe: str = ""


# O formatador recebe o evento e um dicionário de apoio da requisição (cache das consultas).
Formatador = Callable[[Any, dict[str, Any]], Texto | None]
_formatadores: dict[str, Formatador] = {}


def registrar_formatador(acoes: str | tuple[str, ...], funcao: Formatador) -> None:
    """Chame no `ready()` do app dono das ações: `registrar_formatador("caixa.abrir", f)`.

    Ação sem formatador sai pelo texto genérico do app `auditoria` (verbo e objeto).
    """
    for acao in (acoes,) if isinstance(acoes, str) else acoes:
        _formatadores[acao] = funcao


def formatador(acao: str) -> Formatador | None:
    return _formatadores.get(acao)


# Consultas que o app `auditoria` faz aos apps de cima sem importá-los (ADR 0011): ids → dados.
Consulta = Callable[[set[int]], dict[int, Any]]
_consultas: dict[str, Consulta] = {}


def registrar_consulta(nome: str, funcao: Consulta) -> None:
    """`filiais` (id → nome) pelo app `filiais`; `acessos_suporte` (id → atendente, motivo,
    permissão, início e fim) pelo app `plataforma`."""
    _consultas[nome] = funcao


def consultar(nome: str, ids: set[int]) -> dict[int, Any]:
    funcao = _consultas.get(nome)
    return funcao(ids) if funcao is not None and ids else {}
