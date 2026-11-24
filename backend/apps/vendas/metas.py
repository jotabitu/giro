"""Metas de vendas (`VEN-09`, `VEN-19`; ADR 0042, itens 3 e 13; T-502, fase 1c).

A meta é do vendedor, na filial e no mês. Quem define é o gerente da filial ou o administrador.
A meta da filial é a soma das metas dos vendedores dela no mês. "Sem meta" é não ter linha:
apagar a meta é a única exclusão física aceita aqui (meta não é registro de negócio com efeito),
e a auditoria guarda o valor de antes.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Sum

from apps.contas import selectors as contas_selectors
from apps.filiais.models import Filial
from comum.auditoria import Categoria, auditar, registrar_evento
from comum.erros import ErroDeValidacao, SemPermissao
from comum.permissoes import filiais_permitidas

from .models import MetaVenda

DEFINEM = frozenset({"administrador", "gerente"})


@dataclass(frozen=True)
class MetaPedida:
    vendedor_id: int
    valor_centavos: int | None  # None tira a meta


def primeiro_dia(dia: date) -> date:
    return dia.replace(day=1)


def pode_definir(usuario: Any, filial: Filial) -> bool:
    return getattr(usuario, "perfil", "") in DEFINEM and filial.pk in filiais_permitidas(usuario)


def vendedores(filial: Filial) -> list[Any]:
    """Os vendedores ativos ligados à filial, pelo nome."""
    return [u for u in contas_selectors.pessoas_da_filial(filial.pk) if u.perfil == "vendedor"]


def da_filial(filial: Filial, mes: date) -> dict[int, int]:
    """`{vendedor_id: valor}` das metas da filial no mês."""
    return dict(
        MetaVenda.objects.filter(filial=filial, mes=primeiro_dia(mes)).values_list(
            "vendedor_id", "valor_centavos"
        )
    )


def soma(filiais: Any, mes: date, vendedor_id: int | None = None) -> int | None:
    """A meta das filiais no mês (a soma), ou a do vendedor. Nula sem nenhuma linha."""
    qs = MetaVenda.objects.filter(filial_id__in=list(filiais), mes=primeiro_dia(mes))
    if vendedor_id is not None:
        qs = qs.filter(vendedor_id=vendedor_id)
    total = qs.order_by().aggregate(total=Sum("valor_centavos"))["total"]
    return int(total) if total is not None else None


def definir_metas(filial: Filial, mes: date, pedidas: list[MetaPedida], por: Any) -> None:
    """`PUT /api/vendas/metas/`: grava, muda ou tira (valor nulo) a meta de cada vendedor da
    filial no mês, numa transação, com auditoria por meta (`VEN-09`). Vendedor que não é da
    filial: 400 no campo `metas`."""
    if not pode_definir(por, filial):
        raise SemPermissao("VEN-09", "Só o gerente da filial ou o administrador define as metas.")
    mes = primeiro_dia(mes)
    da_casa = {u.pk for u in vendedores(filial)}
    fora = sorted({p.vendedor_id for p in pedidas} - da_casa)
    if fora:
        raise ErroDeValidacao({"metas": ["Escolha vendedores ativos desta filial."]})
    with transaction.atomic():
        atuais = {
            m.vendedor_id: m
            for m in MetaVenda.objects.select_for_update().filter(filial=filial, mes=mes)
        }
        for pedida in pedidas:
            meta = atuais.get(pedida.vendedor_id)
            if pedida.valor_centavos is None:
                if meta is not None:
                    registrar_evento(
                        "meta_venda.tirar",
                        Categoria.CONFIGURACOES,
                        objeto=meta,
                        antes={"valor_centavos": meta.valor_centavos},
                        regra="VEN-09",
                        filial_id=filial.pk,
                    )
                    meta.delete()
                continue
            if meta is None:
                meta = MetaVenda(vendedor_id=pedida.vendedor_id, filial=filial, mes=mes)
            elif meta.valor_centavos == pedida.valor_centavos:
                continue
            with auditar(
                meta,
                "meta_venda.definir",
                Categoria.CONFIGURACOES,
                regra="VEN-09",
                filial_id=filial.pk,
            ):
                meta.valor_centavos = pedida.valor_centavos
                meta.definida_por = por
                meta.save()


def quadro(filial: Filial, mes: date) -> dict[str, Any]:
    """`GET /api/vendas/metas/`: os vendedores da filial com a meta de cada um e a soma, mais os
    textos da tela (`VEN-19`)."""
    metas = da_filial(filial, mes)
    linhas = [
        {"vendedor": {"id": u.pk, "nome": u.nome}, "valor_centavos": metas.get(u.pk)}
        for u in vendedores(filial)
    ]
    total = sum(v for v in metas.values())
    return {
        "filial": {"id": filial.pk, "nome": filial.nome},
        "mes": primeiro_dia(mes),
        "vendedores": linhas,
        "soma_centavos": total if metas else None,
        "texto": (
            f"Defina a meta de cada vendedor da {filial.nome}. Deixe em branco para ficar sem meta."
        ),
        "ajuda": "A meta da filial é a soma das metas dos vendedores e se atualiza ao salvar.",
    }
