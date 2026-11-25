"""Máquina de estados: a única forma de mudar `status` (ADR 0009)."""

from functools import cache
from typing import Any, ClassVar, TypeVar

from django.db import models, transaction

from comum.auditoria import Categoria, auditar
from comum.erros import TransicaoInvalida


class MudancaDeStatusForaDaMaquina(RuntimeError):
    """Erro de programação: status mudado por `save()` ou `update()` direto."""


class EstadosQuerySet(models.QuerySet[Any]):
    def update(self, **kwargs: Any) -> int:
        if "status" in kwargs:
            raise MudancaDeStatusForaDaMaquina("Use comum.estados.transicionar.")
        return super().update(**kwargs)


_M = TypeVar("_M", bound=models.Model)


class _ManagerDeEstados(models.Manager[_M]):
    """VEI-22, CLI-13 (T-515): no model com `excluido_em`, o registro excluído fica guardado no
    banco e some de tudo para a empresa (listas, buscas, contagens, seletores, ficha 404). Esse
    model declara `todos` (`EstadosQuerySet.as_manager()`) para ver também os excluídos. O
    `_base_manager` continua sem filtro: a chave estrangeira de outro registro ainda abre o
    excluído (auditoria, conferência da equipe Giro)."""

    def get_queryset(self) -> models.QuerySet[_M]:
        queryset = super().get_queryset()
        if _tem_exclusao(self.model):
            queryset = queryset.filter(excluido_em__isnull=True)
        return queryset


@cache
def _tem_exclusao(modelo: type[models.Model]) -> bool:
    return any(campo.name == "excluido_em" for campo in modelo._meta.concrete_fields)


ManagerDeEstados = _ManagerDeEstados.from_queryset(EstadosQuerySet)


class MaquinaDeEstados(models.Model):
    """O model declara `status` (com choices), `TRANSICOES` e `REGRA_TRANSICAO`.

    `TRANSICOES = {"reservada": {"ativa", "cancelada"}, ...}`.
    """

    TRANSICOES: ClassVar[dict[str, set[str]]]
    REGRA_TRANSICAO: ClassVar[str]
    CATEGORIA_AUDITORIA: ClassVar[str] = Categoria.OPERACAO

    objects = ManagerDeEstados()

    class Meta:
        abstract = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._status_salvo = self.__dict__.get("status")
        self._transicionando = False

    def save(self, *args: Any, **kwargs: Any) -> None:
        status_atual = self.__dict__.get("status")
        if (
            not self._state.adding
            and status_atual != self._status_salvo
            and not self._transicionando
        ):
            raise MudancaDeStatusForaDaMaquina(
                f"{type(self).__name__}.status mudou fora de transicionar()."
            )
        super().save(*args, **kwargs)
        self._status_salvo = status_atual

    def refresh_from_db(self, *args: Any, **kwargs: Any) -> None:
        # O status relido do banco é o salvo: outra transação pode tê-lo mudado pela máquina.
        super().refresh_from_db(*args, **kwargs)
        campos = kwargs.get("fields")
        if campos is None or "status" in campos:
            self._status_salvo = self.__dict__.get("status")


def _rotulo(modelo: type[models.Model], valor: str) -> str:
    campo = modelo._meta.get_field("status")
    return str(dict(campo.flatchoices).get(valor, valor))  # type: ignore[union-attr]


def transicionar(
    objeto: MaquinaDeEstados,
    novo_status: str,
    *,
    motivo: str = "",
    acao: str | None = None,
    regra: str = "",
    mais_campos: tuple[str, ...] = (),
) -> None:
    """Valida contra `TRANSICOES`, grava e audita. Fora da tabela: `TransicaoInvalida` (409).

    `mais_campos`: campos já mudados no objeto que entram no mesmo `save` e na mesma auditoria
    (ex.: quem decidiu e quando)."""
    modelo = type(objeto)
    with transaction.atomic():
        atual = (
            modelo._base_manager.select_for_update()
            .filter(pk=objeto.pk)
            .values_list("status", flat=True)  # type: ignore[misc]
            .get()
        )
        permitidos = modelo.TRANSICOES.get(atual, set())
        if novo_status not in permitidos:
            raise TransicaoInvalida(
                modelo.REGRA_TRANSICAO,
                f"Não é possível passar de {_rotulo(modelo, atual)} "
                f"para {_rotulo(modelo, novo_status)}.",
                {"de": atual, "para": novo_status, "permitidos": sorted(permitidos)},
            )
        nome = modelo._meta.model_name
        with auditar(
            objeto,
            acao or f"{nome}.{novo_status}",
            modelo.CATEGORIA_AUDITORIA,
            motivo=motivo,
            regra=regra,
        ):
            objeto.status = novo_status  # type: ignore[attr-defined]
            campos = ["status", *mais_campos]
            if any(c.name == "atualizado_em" for c in modelo._meta.concrete_fields):
                campos.append("atualizado_em")
            objeto._transicionando = True
            try:
                objeto.save(update_fields=campos)
            finally:
                objeto._transicionando = False
