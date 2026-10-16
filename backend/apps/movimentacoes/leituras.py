"""O que `movimentacoes` fornece aos apps de baixo (ADR 0015, ADR 0028, item 4), no `ready()`.

- `veiculos.Veiculo`: blocos `movimentacao_aberta` (lista e ficha) e `movimentacoes` (ficha),
  filtros `em_movimentacao` e `movimentavel` da Frota.
- `contas.Usuario`: contador `movimentacoes_levando`, que traz o item Movimentações ao menu de
  quem leva (MOV-02, USR-05).
"""

from typing import Any

from django.db.models import Exists, OuterRef, QuerySet, Subquery

from apps.locacoes.models import ABERTAS as LOCACOES_ABERTAS
from apps.locacoes.models import Locacao
from apps.veiculos.models import MOVIMENTAVEIS
from comum import leituras
from comum.permissoes import filiais_permitidas

from . import selectors, services
from .models import ABERTAS, Movimentacao

VEICULO = "veiculos.Veiculo"
FICHA = "veiculos.Veiculo:ficha"
USUARIO = "contas.Usuario"
CAMPOS = ("id", "codigo", "status")


def _abertas() -> QuerySet[Movimentacao]:
    return Movimentacao.objects.filter(veiculo_id=OuterRef("pk"), status__in=ABERTAS)


def anotar_veiculo(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset.annotate(  # type: ignore[no-any-return]
        **{f"mov_{campo}": Subquery(_abertas().values(campo)[:1]) for campo in CAMPOS}
    )


def montar_aberta(veiculo: Any) -> dict[str, Any] | None:
    if not hasattr(veiculo, "mov_id"):
        return selectors.bloco_aberta(selectors.aberta(veiculo))
    if veiculo.mov_id is None:
        return None
    anotada = Movimentacao(id=veiculo.mov_id, codigo=veiculo.mov_codigo, status=veiculo.mov_status)
    return selectors.bloco_aberta(anotada)


def _sem_anotar(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset


def em_movimentacao(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset.filter(Exists(_abertas()))


def movimentavel(queryset: QuerySet[Any], usuario: Any) -> QuerySet[Any]:
    """Os que dariam `acoes.movimentar = true` (T-300): nas filiais que a pessoa gere, nos
    status da MOV-03, sem movimentação aberta e sem locação aberta (a reserva de hoje)."""
    if getattr(usuario, "perfil", "") not in services.GESTAO:
        return queryset.none()
    locacao = Locacao.objects.filter(veiculo_id=OuterRef("pk"), status__in=LOCACOES_ABERTAS)
    return (
        queryset.filter(filial_id__in=filiais_permitidas(usuario), status__in=list(MOVIMENTAVEIS))
        .exclude(Exists(_abertas()))
        .exclude(Exists(locacao))
    )


def levando(usuario_id: int) -> int:
    return int(Movimentacao.objects.filter(levado_por_id=usuario_id, status__in=ABERTAS).count())


def registrar() -> None:
    leituras.registrar_anotacao(VEICULO, "movimentacao_aberta", anotar_veiculo, montar_aberta)
    # Só a ficha pede este bloco: fica num alvo próprio para a Frota não consultá-lo.
    leituras.registrar_anotacao(FICHA, "movimentacoes", _sem_anotar, selectors.bloco_da_ficha)
    leituras.registrar_filtro(VEICULO, "em_movimentacao", em_movimentacao)
    leituras.registrar_filtro(VEICULO, "movimentavel", movimentavel)
    leituras.registrar_contador(USUARIO, "movimentacoes_levando", levando)
