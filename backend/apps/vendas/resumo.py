"""Números das vendas: funil, conversão, vendido, ticket médio, em negociação, meta e as
propostas para retornar (`VEN-08`, `VEN-09`, `VEN-12`, `VEN-16`, `VEN-19`; ADR 0042, item 13;
T-502, fase 1c).

Sempre a venda de balcão (`origem = "balcao"`: a da quitação, `VEN-11`, fica fora), nas filiais
do escopo (todas, para quem vê todas, `USR-07`), com as datas no fuso `America/Sao_Paulo`. O
vendedor vê só os números dele (`USR-08`). A API calcula; a tela só mostra.
"""

import calendar
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Count, Q, QuerySet, Sum

from apps.veiculos.models import StatusVeiculo, Veiculo
from comum import relogio
from comum.classificacao import mascarar_telefone
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen

from . import metas, services
from .models import EM_ANDAMENTO, OrigemVenda, StatusVenda, Venda

FUSO = ZoneInfo("America/Sao_Paulo")
MESES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)
JANELA_DA_CONVERSAO = timedelta(days=30)  # VEN-08
PARA_RETORNAR = 10  # VEN-16: as mais antigas primeiro
ABERTAS = (StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO, StatusVenda.AGUARDANDO_APROVACAO)


def vendedor_id(usuario: Any) -> int | None:
    """USR-08: o vendedor vê só os números dele."""
    return usuario.pk if getattr(usuario, "perfil", "") == "vendedor" else None


def do_balcao(filiais: Any, vendedor: int | None = None) -> QuerySet[Venda]:
    qs = Venda.objects.filter(filial_id__in=list(filiais), origem=OrigemVenda.BALCAO)
    if vendedor is not None:
        qs = qs.filter(vendedor_id=vendedor)
    return qs


def limites_do_mes(mes: date) -> tuple[datetime, datetime]:
    inicio = datetime(mes.year, mes.month, 1, tzinfo=FUSO)
    seguinte = (mes.year + 1, 1) if mes.month == 12 else (mes.year, mes.month + 1)
    return inicio, datetime(*seguinte, 1, tzinfo=FUSO)


def vendidas_do_mes(filiais: Any, mes: date, vendedor: int | None = None) -> dict[str, Any]:
    """`VEN-12`: número, soma dos preços finais e ticket médio das vendas que viraram `vendida`
    no mês e continuam `vendida` (a cancelada sai do mês dela). Ticket com `ROUND_HALF_UP`."""
    from .selectors import vendidas_entre

    quantidade, soma = vendidas_entre(filiais, *limites_do_mes(mes), vendedor_id=vendedor)
    return {
        "quantidade": quantidade,
        "soma_centavos": soma,
        "ticket_centavos": ticket(quantidade, soma),
    }


def ticket(quantidade: int, soma: int) -> int | None:
    """`VEN-12`: soma ÷ número, arredondado para o centavo (`ROUND_HALF_UP`); nulo sem venda."""
    if not quantidade:
        return None
    return int((Decimal(soma) / quantidade).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def funil(filiais: Any, mes: date, vendedor: int | None = None) -> dict[str, int]:
    """`VEN-08`: as vendas que passaram por cada etapa no mês. Interessados = criadas no mês
    (também as que nasceram em `proposta`); proposta = primeira entrada em `proposta` no mês;
    negociação = primeira entrada em `negociacao` ou `aguardando_aprovacao` no mês; vendido =
    `vendida` no mês e ainda `vendida`."""
    inicio, fim = limites_do_mes(mes)
    totais = do_balcao(filiais, vendedor).aggregate(
        interessados=Count("id", filter=Q(criado_em__gte=inicio, criado_em__lt=fim)),
        proposta=Count("id", filter=Q(entrou_proposta_em__gte=inicio, entrou_proposta_em__lt=fim)),
        negociacao=Count(
            "id", filter=Q(entrou_negociacao_em__gte=inicio, entrou_negociacao_em__lt=fim)
        ),
        vendido=Count(
            "id",
            filter=Q(status=StatusVenda.VENDIDA, vendida_em__gte=inicio, vendida_em__lt=fim),
        ),
    )
    return {chave: int(valor or 0) for chave, valor in totais.items()}


def conversao(filiais: Any, vendedor: int | None = None) -> dict[str, Any]:
    """`VEN-08`: vendidas ÷ criadas nos últimos 30 dias, inteiro para baixo (4 ÷ 12 = 33%).
    Sem venda criada na janela, `pct` nulo."""
    desde = relogio.agora() - JANELA_DA_CONVERSAO
    totais = do_balcao(filiais, vendedor).aggregate(
        criadas=Count("id", filter=Q(criado_em__gte=desde)),
        vendidas=Count("id", filter=Q(status=StatusVenda.VENDIDA, vendida_em__gte=desde)),
    )
    criadas, vendidas = int(totais["criadas"] or 0), int(totais["vendidas"] or 0)
    return {
        "vendidas": vendidas,
        "criadas": criadas,
        "pct": vendidas * 100 // criadas if criadas else None,
    }


def em_negociacao(filiais: Any, vendedor: int | None = None) -> dict[str, int]:
    """Soma do preço final e número das vendas `proposta`, `negociacao` e
    `aguardando_aprovacao` (`VEN-19`: R$ 56.068,00 em 3 propostas abertas)."""
    totais = (
        do_balcao(filiais, vendedor)
        .filter(status__in=ABERTAS)
        .aggregate(
            quantidade=Count("id"),
            soma=Sum("preco_final_centavos"),
            aguardando=Count("id", filter=Q(status=StatusVenda.AGUARDANDO_APROVACAO)),
        )
    )
    return {
        "quantidade": int(totais["quantidade"] or 0),
        "soma_centavos": int(totais["soma"] or 0),
        "aguardando_aprovacao": int(totais["aguardando"] or 0),
    }


def meta(filiais: Any, mes: date, vendido: int, vendedor: int | None = None) -> dict[str, Any]:
    """`VEN-09`: a meta do vendedor (a dele nas filiais) ou a das filiais (a soma). Percentual
    inteiro para baixo (31.200 ÷ 50.000 = 62%); `faltam_dias` = dias corridos até o fim do mês
    (em 07 out, 24), só no mês corrente. Sem meta, `valor_centavos` nulo e "Sem meta em
    outubro."."""
    valor = metas.soma(filiais, mes, vendedor)
    hoje = relogio.hoje()
    faltam = None
    if (mes.year, mes.month) == (hoje.year, hoje.month):
        faltam = calendar.monthrange(hoje.year, hoje.month)[1] - hoje.day
    nome_do_mes = MESES[mes.month - 1]
    if valor is None:
        return {
            "valor_centavos": None,
            "vendido_centavos": vendido,
            "pct": None,
            "faltam_dias": faltam,
            "texto": f"Sem meta em {nome_do_mes}.",
        }
    pct = vendido * 100 // valor
    texto = f"{pct}% de {formatar_reais(valor)}"
    if faltam is not None:
        texto += f" · faltam {faltam} {'dia' if faltam == 1 else 'dias'}"
    return {
        "valor_centavos": valor,
        "vendido_centavos": vendido,
        "pct": pct,
        "faltam_dias": faltam,
        "texto": texto,
    }


def celular_do_comprador(venda: Venda, suporte: bool = False) -> str:
    """O celular para o "Chamar no WhatsApp" (`VEN-16`): o do cliente com cadastro ou o do
    interessado, só dígitos; mascarado para o suporte (`AUD-09`)."""
    celular = venda.cliente.celular if venda.cliente is not None else venda.interessado_celular
    celular = celular or ""
    return mascarar_telefone(celular) if suporte and celular else celular


def para_retornar(
    filiais: Any, vendedor: int | None = None, suporte: bool = False
) -> list[dict[str, Any]]:
    """`VEN-16`: as vendas abertas da mais antiga para a mais recente pelo último contato."""
    abertas = (
        do_balcao(filiais, vendedor)
        .filter(status__in=EM_ANDAMENTO)
        .select_related("filial", "cliente", "veiculo")
        .order_by("ultimo_contato_em", "id")[:PARA_RETORNAR]
    )
    itens = []
    for venda in abertas:
        nome = venda.cliente.nome if venda.cliente is not None else venda.interessado_nome
        itens.append(
            {
                "venda_id": venda.pk,
                "codigo": venda.codigo,
                "comprador_nome": nome,
                "celular": celular_do_comprador(venda, suporte),
                "veiculo": (
                    f"{venda.veiculo.marca} {venda.veiculo.modelo} · "
                    f"{placa_com_hifen(venda.veiculo.placa)}"
                ),
                "valor_centavos": venda.preco_final_centavos,
                "situacao_texto": services.situacao_texto(venda),
                "ultimo_contato_em": venda.ultimo_contato_em,
            }
        )
    return itens


def transferencias_pendentes(filiais: Any) -> int:
    """`VEN-11`, `VEN-17`: vendidas sem a transferência no Detran registrada (as duas origens)."""
    return Venda.objects.filter(
        filial_id__in=list(filiais), status=StatusVenda.VENDIDA, transferencia_feita_em__isnull=True
    ).count()


def a_venda(filiais: Any) -> int:
    return Veiculo.objects.filter(filial_id__in=list(filiais), status=StatusVeiculo.A_VENDA).count()


def mes_anterior(mes: date) -> date:
    return date(mes.year - 1, 12, 1) if mes.month == 1 else date(mes.year, mes.month - 1, 1)


def resumo(usuario: Any, filiais: Any, mes: date, onde: str) -> dict[str, Any]:
    """`GET /api/vendas/resumo/`: os números da tela `Vendas` e do início do vendedor."""
    vendedor = vendedor_id(usuario)
    suporte = bool(getattr(usuario, "e_suporte", False))
    mes = mes.replace(day=1)
    vendidas = vendidas_do_mes(filiais, mes, vendedor)
    anterior = vendidas_do_mes(filiais, mes_anterior(mes), vendedor)
    nome_do_mes = MESES[mes.month - 1]
    propostas = para_retornar(filiais, vendedor, suporte)
    return {
        "mes": mes,
        "subtitulo": f"Vendas de {nome_do_mes} · {onde}",
        "funil": funil(filiais, mes, vendedor),
        "conversao": conversao(filiais, vendedor),
        "vendido": {
            **vendidas,
            "vazio": None if vendidas["quantidade"] else f"Sem vendas em {nome_do_mes}.",
            "mes_anterior": anterior,
        },
        "em_negociacao": em_negociacao(filiais, vendedor),
        "a_venda": a_venda(filiais),
        "meta": meta(filiais, mes, vendidas["soma_centavos"], vendedor),
        "transferencias_pendentes": transferencias_pendentes(filiais),
        "propostas_para_retornar": propostas,
        "propostas_vazio": (
            None if propostas else "Você não tem propostas abertas." if vendedor else None
        ),
    }
