"""O que `vistorias` fornece ao detalhe da locação (ADR 0015), registrado no `ready()`.

- `locacoes.TrocaVeiculo`: bloco `vistorias`, com a chegada do veículo antigo e a saída do novo
  (`{id, status}`). A ação `cancelar_troca` depende da saída ainda não concluída (LOC-09).
- `locacoes.Locacao`: bloco `devolucao`, com o `devolucao_id` da devolução em curso ou
  encerrada; `null` enquanto ela não tem chegada (troca cancelada com a chegada descartada).
- `veiculos.Veiculo:ficha`: bloco `vistoria_recente`, a última vistoria concluída do veículo, com
  as fotos fixas e as avarias abertas (VIS-01, T-275).
"""

from typing import Any

from django.db.models import QuerySet

from comum import leituras

from . import selectors
from .models import POSICOES_OBRIGATORIAS, Devolucao, StatusVistoria, Vistoria

TROCA = "locacoes.TrocaVeiculo"
LOCACAO = "locacoes.Locacao"
FICHA = "veiculos.Veiculo:ficha"


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


def montar_ficha(veiculo: Any) -> dict[str, Any] | None:
    """A última concluída e vigente (a descartada nunca); `None` se o veículo nunca teve
    vistoria. Fotos só das posições fixas, com URL assinada a cada leitura (AUD-05); avarias
    abertas do veículo, sem valor."""
    vistoria = (
        Vistoria.objects.filter(
            veiculo_id=veiculo.pk, status=StatusVistoria.CONCLUIDA, vigente=True
        )
        .select_related("responsavel", "locacao")
        .order_by("-concluida_em", "-id")
        .first()
    )
    if vistoria is None:
        return None
    fotos = [f for f in vistoria.fotos.all() if f.ativo]
    fixas = {f.posicao: f for f in fotos if f.posicao in POSICOES_OBRIGATORIAS}
    avarias = (
        selectors.avarias_abertas()
        .filter(veiculo_id=veiculo.pk)
        .select_related("vistoria__locacao")
        .order_by("vistoria__concluida_em", "id")
    )
    responsavel = vistoria.responsavel
    return {
        "id": vistoria.pk,
        "tipo": vistoria.tipo,
        "concluida_em": vistoria.concluida_em,
        "vistoriador": ({"id": responsavel.pk, "nome": responsavel.nome} if responsavel else None),
        "locacao_codigo": vistoria.locacao.codigo,
        "total_fotos": len(fotos),
        "fotos": [
            {
                "id": foto["id"],
                "posicao": foto["posicao"],
                "url": foto["url"],
                "url_expira_em": foto["url_expira_em"],
            }
            for foto in (
                selectors.representacao_foto(fixas[p]) for p in POSICOES_OBRIGATORIAS if p in fixas
            )
        ],
        "avarias": [
            {
                "id": a.pk,
                "descricao": a.descricao,
                "registrada_em": a.vistoria.concluida_em,
                "preexistente": a.preexistente,
                "locacao_codigo": a.vistoria.locacao.codigo,
                "foto_id": a.foto_id,
            }
            for a in avarias
        ],
    }


def registrar() -> None:
    leituras.registrar_anotacao(TROCA, "vistorias", _sem_anotacao, montar_troca)
    leituras.registrar_anotacao(LOCACAO, "devolucao", _sem_anotacao, montar_locacao)
    leituras.registrar_anotacao(FICHA, "vistoria_recente", _sem_anotacao, montar_ficha)
