"""Consultas das vendas (`docs/api/vendas.md`). Na T-420, só as da venda da quitação (`VEN-11`)."""

from collections.abc import Iterable
from typing import Any

from django.db.models import QuerySet

from comum.documentos import placa_com_hifen
from comum.permissoes import PERFIS_QUE_VEEM_TODAS, filiais_permitidas

from . import services
from .models import OrigemVenda, Venda

RELACIONADOS = (
    "filial",
    "cliente",
    "veiculo",
    "vendedor",
    "locacao",
    "transferencia_registrada_por",
)


def base() -> QuerySet[Venda]:
    return Venda.objects.select_related(*RELACIONADOS)


def visiveis(usuario: Any) -> QuerySet[Venda]:
    """As vendas das filiais da pessoa; o vendedor vê só as dele (`USR-08`); o vistoriador,
    nenhuma (a rota responde 403 antes)."""
    perfil = getattr(usuario, "perfil", "")
    qs = base().filter(filial_id__in=filiais_permitidas(usuario))
    if perfil == "vendedor":
        qs = qs.filter(vendedor_id=usuario.pk)
    elif perfil not in (*PERFIS_QUE_VEEM_TODAS, "gerente"):
        qs = qs.none()
    return qs


def filtrar(usuario: Any, parametros: Any) -> QuerySet[Venda]:
    qs = visiveis(usuario)
    if origem := parametros.get("origem"):
        qs = qs.filter(origem=origem)
    if parametros.get("transferencia_pendente") == "true":
        qs = qs.filter(origem=OrigemVenda.QUITACAO_LOCACAO, transferencia_feita_em__isnull=True)
    for campo in ("veiculo", "cliente"):
        valor = parametros.get(campo)
        if valor and str(valor).isdigit():
            qs = qs.filter(**{f"{campo}_id": int(valor)})
    return qs.order_by("-id")


def _pessoa(usuario: Any) -> dict[str, Any] | None:
    return {"id": usuario.pk, "nome": usuario.nome} if usuario is not None else None


def _transferencia(venda: Venda) -> dict[str, Any]:
    return {
        "feita_em": venda.transferencia_feita_em,
        "registrada_por": _pessoa(venda.transferencia_registrada_por),
        "pendente": (
            venda.origem == OrigemVenda.QUITACAO_LOCACAO and venda.transferencia_feita_em is None
        ),
    }


def representacao(venda: Venda, usuario: Any) -> dict[str, Any]:
    """O formato de "A venda da quitação" (`vendas.md`)."""
    veiculo = venda.veiculo
    return {
        "id": venda.pk,
        "codigo": venda.codigo,
        "status": venda.status,
        "origem": venda.origem,
        "origem_rotulo": OrigemVenda(venda.origem).label,
        "descricao": venda.descricao,
        "cliente": {"id": venda.cliente_id, "nome": venda.cliente.nome},
        "veiculo": {
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": f"{veiculo.marca} {veiculo.modelo}".strip(),
        },
        "filial": {"id": venda.filial_id, "nome": venda.filial.nome},
        "vendedor": _pessoa(venda.vendedor),
        "locacao": (
            {"id": venda.locacao_id, "codigo": venda.locacao.codigo} if venda.locacao else None
        ),
        "preco_final_centavos": venda.preco_final_centavos,
        "vendida_em": venda.vendida_em,
        "transferencia": _transferencia(venda),
        "acoes": {
            # A venda da quitação nunca se cancela (VEN-11); a de balcão é da T-418.
            "cancelar": False,
            "registrar_transferencia": services.pode_registrar_transferencia(venda, usuario),
        },
    }


# --- Interface interna (`vendas.md`) ---


def venda_da_quitacao(locacao_id: int) -> Venda | None:
    return base().filter(locacao_id=locacao_id).first()


def venda_da_locacao(locacao_id: int) -> dict[str, Any] | None:
    """O bloco `compra.venda` do detalhe da locação, sem as `acoes` (montadas por `locacoes`)."""
    venda = venda_da_quitacao(locacao_id)
    if venda is None:
        return None
    return {"id": venda.pk, "codigo": venda.codigo, "transferencia": _transferencia(venda)}


def transferencias_pendentes(filiais: Iterable[int]) -> list[dict[str, Any]]:
    """As vendas da quitação sem transferência das filiais, para as `pendencias.itens` do painel
    (`painel.md`, lido por `relatorios`). A mais antiga primeiro."""
    pendentes = base().filter(
        filial_id__in=list(filiais),
        origem=OrigemVenda.QUITACAO_LOCACAO,
        transferencia_feita_em__isnull=True,
    )
    return [
        {
            "tipo": "transferencia_quitacao",
            "rotulo": f"Transferência no Detran · {placa_com_hifen(venda.veiculo.placa)}",
            "detalhe": (
                f"{venda.cliente.nome} · {venda.locacao.codigo if venda.locacao else ''} "
                f"quitada em {services.data_da_quitacao(venda):%d/%m/%Y}"
            ),
            "link": f"/locacoes/{venda.locacao_id}",
        }
        for venda in pendentes.order_by("vendida_em", "id")
    ]


def vendas_do_veiculo(veiculo_id: int) -> list[dict[str, Any]]:
    """As vendas do veículo para o histórico da ficha (ADR 0015), a mais nova primeiro, com a
    linha da transferência no Detran (CA-420-16)."""
    itens = []
    for venda in base().filter(veiculo_id=veiculo_id).order_by("-id"):
        registrada = venda.transferencia_registrada_por
        itens.append(
            {
                "id": venda.pk,
                "codigo": venda.codigo,
                "status": venda.status,
                "origem": venda.origem,
                "origem_rotulo": OrigemVenda(venda.origem).label,
                "descricao": venda.descricao,
                "cliente": {"id": venda.cliente_id, "nome": venda.cliente.nome},
                "vendida_em": venda.vendida_em,
                "transferencia": _transferencia(venda),
                "transferencia_texto": (
                    f"Transferência no Detran feita em {venda.transferencia_feita_em:%d/%m/%Y}"
                    + (f" · {registrada.nome}" if registrada is not None else "")
                    if venda.transferencia_feita_em
                    else None
                ),
            }
        )
    return itens
