"""O que `vistorias` fornece ao detalhe da locação (ADR 0015), registrado no `ready()`.

- `locacoes.TrocaVeiculo`: bloco `vistorias`, com a chegada do veículo antigo e a saída do novo
  (`{id, status}`). A ação `cancelar_troca` depende da saída ainda não concluída (LOC-09).
- `locacoes.Locacao`: bloco `devolucao`, com o `devolucao_id` da devolução em curso ou
  encerrada; `null` enquanto ela não tem chegada (troca cancelada com a chegada descartada).
"""

from typing import Any

from django.db.models import QuerySet

from comum import leituras

from .models import Devolucao, Vistoria

TROCA = "locacoes.TrocaVeiculo"
LOCACAO = "locacoes.Locacao"


def _sem_anotacao(queryset: QuerySet[Any]) -> QuerySet[Any]:
    return queryset


def _resumo(vistoria_id: int | None, status: dict[int, str]) -> dict[str, Any] | None:
    if vistoria_id is None or vistoria_id not in status:
        return None
    return {"id": vistoria_id, "status": status[vistoria_id]}


def montar_troca(troca: Any) -> dict[str, Any]:
    ids = [i for i in (troca.vistoria_devolucao_id, troca.vistoria_saida_id) if i is not None]
    status = dict(Vistoria.objects.filter(pk__in=ids).values_list("pk", "status"))
    return {
        "devolucao_vistoria": _resumo(troca.vistoria_devolucao_id, status),
        "saida_vistoria": _resumo(troca.vistoria_saida_id, status),
    }


def montar_locacao(locacao: Any) -> dict[str, Any]:
    devolucao = (
        Devolucao.objects.filter(locacao_id=locacao.pk, vistoria__isnull=False)
        .values_list("pk", flat=True)
        .first()
    )
    return {"devolucao_id": devolucao}


def registrar() -> None:
    leituras.registrar_anotacao(TROCA, "vistorias", _sem_anotacao, montar_troca)
    leituras.registrar_anotacao(LOCACAO, "devolucao", _sem_anotacao, montar_locacao)
