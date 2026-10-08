"""Registro de eventos de auditoria (AUD-01, ADR 0010).

O model `auditoria.EventoAuditoria` fica no app `auditoria`, que está abaixo de `comum` na
ordem da ADR 0011; por isso ele é resolvido com `apps.get_model`, sem import.
"""

import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from django.apps import apps
from django.db import models, transaction


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


@contextmanager
def usar_ator(ator: Ator | Callable[[], Ator]) -> Iterator[None]:
    token = _ator.set(ator)
    try:
        yield
    finally:
        _ator.reset(token)


# --- Dados pessoais (ADR 0010, item 7) ---
# Campos com estes nomes são gravados mascarados. Um model pode somar nomes em CAMPOS_PESSOAIS.
CAMPOS_PESSOAIS_PADRAO = frozenset({"cpf", "cnpj_cpf", "cpf_cnpj", "cnh", "rg", "documento"})
CAMPOS_IGNORADOS = frozenset({"atualizado_em", "password"})


def mascarar_cpf(valor: str) -> str:
    """`123.218.330-45` vira `***.218.330-**` (AUD-04)."""
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 11:
        return mascarar(valor)
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


def mascarar(valor: str) -> str:
    """Mantém só os 3 últimos caracteres."""
    if len(valor) <= 3:
        return "*" * len(valor)
    return "*" * (len(valor) - 3) + valor[-3:]


def _mascarar_campo(nome: str, valor: Any) -> Any:
    if valor in (None, ""):
        return valor
    texto = str(valor)
    return mascarar_cpf(texto) if "cpf" in nome else mascarar(texto)


def retrato(objeto: models.Model) -> dict[str, Any]:
    pessoais = CAMPOS_PESSOAIS_PADRAO | frozenset(getattr(objeto, "CAMPOS_PESSOAIS", ()))
    dados: dict[str, Any] = {}
    for campo in objeto._meta.concrete_fields:
        if campo.name in CAMPOS_IGNORADOS:
            continue
        valor = getattr(objeto, campo.attname)
        dados[campo.attname] = (
            _mascarar_campo(campo.name, valor) if campo.name in pessoais else valor
        )
    return dados


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
) -> Any:
    """Grava um evento. Para ações sem objeto (login, exportação), omita `objeto`."""
    evento_auditoria = apps.get_model("auditoria", "EventoAuditoria")
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
        filial_id=getattr(objeto, "filial_id", None),
        antes=antes or {},
        depois=depois or {},
        motivo=motivo,
        ip=ator.ip,
        aparelho=ator.aparelho,
        regra=regra or ator.regra,
    )


@contextmanager
def auditar(
    objeto: models.Model, acao: str, categoria: str, *, motivo: str = "", regra: str = ""
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
        )
