"""O que `vistorias` fornece ao detalhe da locação (ADR 0015), registrado no `ready()`.

- `locacoes.TrocaVeiculo`: bloco `vistorias`, com a chegada do veículo antigo e a saída do novo
  (`{id, status}`). A ação `cancelar_troca` depende da saída ainda não concluída (LOC-09).
- `locacoes.Locacao`: bloco `devolucao`, com o `devolucao_id` da devolução em curso ou
  encerrada; `null` enquanto ela não tem chegada (troca cancelada com a chegada descartada).
- `veiculos.Veiculo:ficha`: bloco `vistoria_recente`, a última vistoria concluída do veículo, com
  todas as fotos ativas (as fixas e as de avaria, VEI-10, T-414) e as avarias abertas (VIS-01,
  T-275).
"""

import os
from typing import Any

from django.db.models import QuerySet

from comum import arquivos, leituras
from comum.documentos import placa_com_hifen

from . import selectors
from .models import (
    POSICOES_OBRIGATORIAS,
    Avaria,
    Devolucao,
    FotoVistoria,
    PosicaoFoto,
    StatusVistoria,
    TipoVistoria,
    Vistoria,
)

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


ROTULO_DO_TIPO = {
    TipoVistoria.SAIDA: "Vistoria de saída",
    TipoVistoria.DEVOLUCAO: "Vistoria de chegada",
}
# No nome do arquivo baixado, a vistoria `devolucao` é a chegada (ADR 0036).
NOME_DO_TIPO = {TipoVistoria.SAIDA: "saida", TipoVistoria.DEVOLUCAO: "chegada"}


def _fotos_em_ordem(vistoria: Vistoria) -> list[tuple[FotoVistoria, str]]:
    """As ativas: as fixas na ordem das posições, depois as de avaria pela hora, cada uma com o
    rótulo ("Frente", "Avaria 1")."""
    fotos = [f for f in vistoria.fotos.all() if f.ativo]
    fixas = {f.posicao: f for f in fotos if f.posicao in POSICOES_OBRIGATORIAS}
    de_avaria = sorted(
        (f for f in fotos if f.posicao == PosicaoFoto.AVARIA), key=lambda f: (f.tirada_em, f.pk)
    )
    em_ordem = [(fixas[p], PosicaoFoto(p).label) for p in POSICOES_OBRIGATORIAS if p in fixas]
    em_ordem += [(f, f"Avaria {i}") for i, f in enumerate(de_avaria, start=1)]
    return em_ordem


def _foto_da_ficha(
    foto: FotoVistoria, numero: int, rotulo: str, prefixo: str, avaria_id: int | None
) -> dict[str, Any]:
    """Dois links de 15 minutos (AUD-05): ver e baixar com o nome (ADR 0036, item 4)."""
    extensao = os.path.splitext(foto.arquivo.name or "")[1].lower().lstrip(".") or "jpg"
    nome = f"{prefixo}-{rotulo.lower().replace(' ', '-')}.{extensao}"
    ver = arquivos.url_assinada(foto.arquivo.name)
    baixar = arquivos.url_assinada(foto.arquivo.name, baixar_como=nome)
    return {
        "id": foto.pk,
        "numero": numero,
        "posicao": foto.posicao,
        "rotulo": rotulo,
        "tirada_em": foto.tirada_em,
        "avaria_id": avaria_id,
        "url": ver.url,
        "url_download": baixar.url,
        "url_expira_em": ver.expira_em,
        "nome_arquivo": nome,
    }


def montar_ficha(veiculo: Any) -> dict[str, Any] | None:
    """A última concluída e vigente (a descartada nunca); `None` se o veículo nunca teve
    vistoria. Todas as fotos ativas, com os links assinados a cada leitura (AUD-05, VEI-10);
    avarias abertas do veículo, sem valor. A placa do nome baixado vem do veículo que a ficha
    passa (ADR 0036, item 6)."""
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
    fotos = _fotos_em_ordem(vistoria)
    avaria_da_foto = dict(
        Avaria.objects.filter(foto_id__in=[f.pk for f, _ in fotos]).values_list("foto_id", "pk")
    )
    placa = "".join(
        c for c in placa_com_hifen(veiculo.placa) if c.isascii() and (c.isalnum() or c == "-")
    )
    prefixo = f"{placa}-vistoria-{NOME_DO_TIPO[TipoVistoria(vistoria.tipo)]}"
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
        "rotulo_tipo": ROTULO_DO_TIPO[TipoVistoria(vistoria.tipo)],
        "concluida_em": vistoria.concluida_em,
        "vistoriador": ({"id": responsavel.pk, "nome": responsavel.nome} if responsavel else None),
        "locacao_codigo": vistoria.locacao.codigo,
        "total_fotos": len(fotos),
        "fotos": [
            _foto_da_ficha(foto, numero, rotulo, prefixo, avaria_da_foto.get(foto.pk))
            for numero, (foto, rotulo) in enumerate(fotos, start=1)
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


# PLT-12: sem o módulo (ramo que só vende), os blocos não vêm.
MODULO = "locacoes_vistoria"


def registrar() -> None:
    leituras.registrar_anotacao(TROCA, "vistorias", _sem_anotacao, montar_troca, recurso=MODULO)
    leituras.registrar_anotacao(LOCACAO, "devolucao", _sem_anotacao, montar_locacao, recurso=MODULO)
    leituras.registrar_anotacao(
        FICHA, "vistoria_recente", _sem_anotacao, montar_ficha, recurso=MODULO
    )
