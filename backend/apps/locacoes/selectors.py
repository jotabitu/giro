"""Leituras das locações: simulação, lista com sinais e indicadores, detalhe e histórico
(`docs/api/locacoes.md`; LOC-05, LOC-06, LOC-07, LOC-10), e as simulações da renovação e do
cancelamento (LOC-08, LOC-12, LOC-13).

Os sinais (`pagamento_atrasado`, `devolve_hoje`, `cancelamento_pendente`) são calculados aqui,
nunca guardados. As parcelas vêm de `financeiro.selectors` (ADR 0011).
"""

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Q, QuerySet

from apps.auditoria.models import EventoAuditoria
from apps.clientes import selectors as clientes_selectors
from apps.contratos import selectors as contratos_selectors
from apps.contratos.models import Contrato, StatusContrato
from apps.filiais.models import Filial
from apps.financeiro import selectors as financeiro_selectors
from apps.veiculos import selectors as veiculos_selectors
from comum import leituras, relogio
from comum.dinheiro import aplicar_percentual, formatar_reais
from comum.permissoes import pode

from . import services
from .models import (
    ABERTAS,
    FormaPagamento,
    Locacao,
    PlanoEspecial,
    StatusDesconto,
    StatusLocacao,
    StatusTroca,
    TrocaVeiculo,
)

S = StatusLocacao
TROCA = "locacoes.TrocaVeiculo"
LOCACAO = "locacoes.Locacao"
ORIGEM = services.ORIGEM
ABAS = ("abertas", "precisam_acao", "devolvem_hoje", "encerradas", "canceladas", "rascunhos")
ORDENS = {"fim_previsto": "fim_previsto", "-inicio": "-inicio"}
CRIAM = frozenset({"administrador", "gerente", "vendedor"})
VISTORIAM = frozenset({"administrador", "gerente", "vendedor", "vistoriador"})


def _fuso() -> ZoneInfo:
    return ZoneInfo(settings.TIME_ZONE)


def _local(momento: datetime) -> datetime:
    return momento.astimezone(_fuso())


def _intervalo_do_dia(dia: date) -> tuple[datetime, datetime]:
    comeco = datetime.combine(dia, time.min, tzinfo=_fuso())
    return comeco, comeco + timedelta(days=1)


def primeiro_nome(nome: str) -> str:
    return nome.split()[0] if nome else ""


# --- Simulação (não grava nada, ADR 0005) ---


def simular(dados: dict[str, Any], filial: Filial, usuario: Any) -> dict[str, Any]:
    montagem = services.montar(dados, filial, exceto=dados.get("locacao_id"))
    conta = montagem.calculo
    desconto = Decimal(dados.get("desconto_pct") or 0)
    return {
        "fim_previsto": conta.fim_previsto,
        "periodos": conta.periodos,
        "linhas": conta.linhas,
        "valor_periodo_centavos": conta.valor_periodo_centavos,
        "proximos_periodos_centavos": conta.proximos_periodos_centavos,
        "hoje_na_retirada_centavos": conta.hoje_na_retirada_centavos,
        "texto_retirada": conta.texto_retirada,
        "parcelas_previstas": [
            {"numero": p.numero, "vencimento": p.vencimento, "valor_centavos": p.valor_centavos}
            for p in conta.parcelas
        ],
        "caucao_centavos": conta.caucao_centavos,
        "diaria_centavos": montagem.diaria_centavos,
        "precisa_aprovacao_desconto": services.precisa_aprovacao_desconto(desconto, usuario),
        "impedimentos": montagem.impedimentos,
        "avisos": montagem.avisos,
    }


# --- Lista ---


def base() -> QuerySet[Any]:
    qs = Locacao.objects.select_related("cliente", "veiculo__categoria", "plano_especial", "filial")
    return financeiro_selectors.anotar_resumo_da_origem(qs, ORIGEM, relogio.hoje())


def _devolvem_hoje(qs: QuerySet[Any]) -> QuerySet[Any]:
    comeco, fim = _intervalo_do_dia(relogio.hoje())
    return qs.filter(status=S.ATIVA, fim_previsto__gte=comeco, fim_previsto__lt=fim)


def _precisam_acao(qs: QuerySet[Any]) -> QuerySet[Any]:
    """Devolução atrasada, parcela atrasada, aguardando assinatura ou cancelamento pendente."""
    return qs.filter(status__in=ABERTAS).filter(
        Q(status=S.DEVOLUCAO_ATRASADA)
        | Q(fin_atrasado_centavos__gt=0)
        | Q(status=S.AGUARDANDO_RETIRADA, contrato_assinado_em__isnull=True)
        | Q(cancelamento_status=StatusDesconto.PENDENTE)
    )


def por_aba(qs: QuerySet[Any], aba: str | None) -> QuerySet[Any]:
    if aba == "precisam_acao":
        return _precisam_acao(qs)
    if aba == "devolvem_hoje":
        return _devolvem_hoje(qs)
    if aba == "encerradas":
        return qs.filter(status=S.ENCERRADA)
    if aba == "canceladas":
        # Rascunho cancelado por falta de uso nunca foi locação: não aparece.
        return qs.filter(status=S.CANCELADA, precos_de__isnull=False)
    if aba == "rascunhos":
        return qs.filter(status=S.RASCUNHO)
    return qs.filter(status__in=ABERTAS)


def filtrar(qs: QuerySet[Any], parametros: Any) -> QuerySet[Any]:
    """`?veiculo=` e `?cliente=` sem aba mostram o histórico todo (fichas do veículo e do
    cliente), menos os rascunhos."""
    historico = not parametros.get("aba") and (
        parametros.get("veiculo") or parametros.get("cliente")
    )
    if historico:
        qs = qs.exclude(status=S.RASCUNHO).exclude(status=S.CANCELADA, precos_de__isnull=True)
    else:
        qs = por_aba(qs, parametros.get("aba"))
    if parametros.get("periodicidade"):
        qs = qs.filter(periodicidade=parametros["periodicidade"])
    for campo in ("plano_especial", "veiculo", "cliente"):
        valor = str(parametros.get(campo) or "")
        if valor.isdigit():
            qs = qs.filter(**{f"{campo}_id": int(valor)})
    busca = str(parametros.get("busca") or "").strip()
    if busca:
        placa = busca.replace("-", "").upper()
        qs = qs.filter(
            Q(codigo__icontains=busca)
            | Q(cliente__nome__icontains=busca)
            | Q(veiculo__placa__icontains=placa)
        )
    return qs


def contagens(qs: QuerySet[Any]) -> dict[str, int]:
    return {aba: por_aba(qs, aba).count() for aba in ABAS}


def dias_de_atraso(locacao: Locacao) -> int:
    return max(0, (relogio.hoje() - _local(locacao.fim_previsto).date()).days)


def indicadores(qs: QuerySet[Any], filial_id: int | None) -> dict[str, Any]:
    hoje = _devolvem_hoje(qs)
    meio_dia = datetime.combine(relogio.hoje(), time(12), tzinfo=_fuso())
    atrasadas = list(qs.filter(status=S.DEVOLUCAO_ATRASADA).order_by("fim_previsto"))
    destaque = None
    if atrasadas:
        mais = atrasadas[0]
        destaque = f"{primeiro_nome(mais.cliente.nome)} · {dias_de_atraso(mais)} dias"
    com_atraso = qs.filter(status__in=ABERTAS, fin_atrasado_centavos__gt=0)
    return {
        "ativas": qs.filter(status__in=(S.ATIVA, S.DEVOLUCAO_ATRASADA)).count(),
        "frota_alugada_pct": (
            veiculos_selectors.ocupacao_da_frota(filial_id) if filial_id is not None else None
        ),
        "devolvem_hoje": hoje.count(),
        "devolvem_hoje_ate_12h": hoje.filter(fim_previsto__lte=meio_dia).count(),
        "devolucao_atrasada": len(atrasadas),
        "devolucao_atrasada_destaque": destaque,
        "pagamentos_atrasados": com_atraso.count(),
        "pagamentos_atrasados_centavos": sum(int(x.fin_atrasado_centavos) for x in com_atraso),
    }


# --- Linha ---


def sinais(locacao: Locacao) -> dict[str, bool]:
    devolve_hoje = (
        locacao.status == S.ATIVA and _local(locacao.fim_previsto).date() == relogio.hoje()
    )
    return {
        "pagamento_atrasado": int(getattr(locacao, "fin_atrasado_centavos", 0) or 0) > 0,
        "devolve_hoje": devolve_hoje,
        "cancelamento_pendente": locacao.cancelamento_status == StatusDesconto.PENDENTE,
    }


def situacao(locacao: Locacao, sinal: dict[str, bool]) -> dict[str, str]:
    """A primeira que valer, na ordem do contrato."""
    status = locacao.status
    if status == S.DEVOLUCAO_ATRASADA:
        dias = dias_de_atraso(locacao)
        rotulo = f"Devolução atrasada {dias} dia{'s' if dias != 1 else ''}"
        return {"codigo": "devolucao_atrasada", "rotulo": rotulo, "tom": "perigo"}
    if sinal["cancelamento_pendente"]:
        return {
            "codigo": "cancelamento_pendente",
            "rotulo": "Pedido de cancelamento",
            "tom": "alerta",
        }
    if sinal["pagamento_atrasado"]:
        numero = getattr(locacao, "fin_parcela_atrasada", None)
        rotulo = f"Parcela {numero} atrasada" if numero else "Pagamento atrasado"
        return {"codigo": "pagamento_atrasado", "rotulo": rotulo, "tom": "perigo"}
    if status == S.AGUARDANDO_RETIRADA:
        if locacao.contrato_assinado_em is None:
            return {
                "codigo": "aguardando_assinatura",
                "rotulo": "Aguardando assinatura",
                "tom": "alerta",
            }
        if locacao.vistoria_saida_ok_em is None:
            return {
                "codigo": "aguardando_vistoria",
                "rotulo": "Aguardando vistoria",
                "tom": "alerta",
            }
        return {
            "codigo": "aguardando_pagamento",
            "rotulo": "Aguardando pagamento",
            "tom": "alerta",
        }
    if sinal["devolve_hoje"]:
        return {"codigo": "devolve_hoje", "rotulo": "Devolve hoje", "tom": "info"}
    tons = {S.ATIVA: "sucesso", S.ENCERRADA: "neutro", S.CANCELADA: "neutro", S.RASCUNHO: "neutro"}
    return {"codigo": status, "rotulo": S(status).label, "tom": tons.get(S(status), "neutro")}


def pagamento(locacao: Locacao) -> dict[str, Any]:
    em_aberto = int(getattr(locacao, "fin_atrasado_centavos", 0) or 0)
    pago = int(getattr(locacao, "fin_pago_centavos", 0) or 0)
    abertas = int(getattr(locacao, "fin_abertas", 0) or 0)
    multa = locacao.multa_encerramento_centavos or 0
    if em_aberto > 0:
        rotulo, tom = f"{formatar_reais(em_aberto)} em aberto", "perigo"
    elif locacao.cancelamento_status == StatusDesconto.PENDENTE and multa > 0:
        rotulo, tom = f"Multa {formatar_reais(multa)}", "alerta"
    elif locacao.status == S.AGUARDANDO_RETIRADA:
        rotulo, tom = (
            (f"{formatar_reais(pago)} pago", "info") if pago else ("Aguardando pagamento", "alerta")
        )
    elif locacao.forma_pagamento == FormaPagamento.PIX_AUTOMATICO:
        rotulo, tom = "Pix automático", "info"
    elif locacao.status in (S.ATIVA, S.DEVOLUCAO_ATRASADA, S.ENCERRADA) and abertas == 0:
        rotulo, tom = "Pago", "sucesso"
    else:
        rotulo, tom = FormaPagamento(locacao.forma_pagamento).label, "neutro"
    return {
        "rotulo": rotulo,
        "tom": tom,
        "em_aberto_centavos": em_aberto,
        # Contas pagas sem a caução, como o `total_pago_centavos` do cliente (T-128, FIN-13).
        "pago_centavos": int(getattr(locacao, "fin_pago_sem_caucao_centavos", 0) or 0),
    }


def acao_principal(locacao: Locacao, sinal: dict[str, bool]) -> dict[str, str]:
    if sinal["pagamento_atrasado"]:
        return {"codigo": "cobrar", "rotulo": "Cobrar"}
    if sinal["devolve_hoje"] or locacao.status == S.DEVOLUCAO_ATRASADA:
        return {"codigo": "receber_devolucao", "rotulo": "Receber devolução"}
    return {"codigo": "abrir", "rotulo": "Abrir"}


def linha(locacao: Locacao) -> dict[str, Any]:
    sinal = sinais(locacao)
    plano = locacao.plano_especial
    return {
        "id": locacao.pk,
        "codigo": locacao.codigo,
        "status": locacao.status,
        "cliente": {"id": locacao.cliente_id, "nome": locacao.cliente.nome},
        "veiculo": {
            "id": locacao.veiculo_id,
            "modelo": f"{locacao.veiculo.marca} {locacao.veiculo.modelo}",
            "placa": locacao.veiculo.placa,
            "tipo": locacao.veiculo.categoria.tipo_veiculo,
        },
        "periodicidade": locacao.periodicidade,
        "plano_especial": {"id": plano.pk, "nome": plano.nome} if plano else None,
        "inicio": locacao.inicio,
        "fim_previsto": locacao.fim_previsto,
        "sinais": sinal,
        "situacao": situacao(locacao, sinal),
        "pagamento": pagamento(locacao),
        "acao_principal": acao_principal(locacao, sinal),
    }


# --- Painel (`relatorios`, docs/api/painel.md) ---


def das_filiais(filiais: Iterable[int], vendedor_id: int | None = None) -> QuerySet[Any]:
    """A base da lista nas filiais do escopo; com `vendedor_id`, só as que ele criou (USR-08)."""
    qs = base().filter(filial_id__in=list(filiais))
    return qs.filter(vendedor_id=vendedor_id) if vendedor_id is not None else qs


def devolucoes_da_semana(qs: QuerySet[Any]) -> list[Locacao]:
    """Fim previsto de hoje até 6 dias à frente, mais as `devolucao_atrasada`, por data."""
    comeco, _ = _intervalo_do_dia(relogio.hoje())
    _, fim = _intervalo_do_dia(relogio.hoje() + timedelta(days=6))
    return list(
        qs.filter(
            Q(status=S.ATIVA, fim_previsto__gte=comeco, fim_previsto__lt=fim)
            | Q(status=S.DEVOLUCAO_ATRASADA)
        ).order_by("fim_previsto", "id")
    )


def linha_do_painel(locacao: Locacao) -> dict[str, Any]:
    """Linha curta das devoluções da semana e de "precisam de ação" do vendedor."""
    rotulo = situacao(locacao, sinais(locacao))
    return {
        "locacao_id": locacao.pk,
        "codigo": locacao.codigo,
        "placa": locacao.veiculo.placa,
        "veiculo": f"{locacao.veiculo.marca} {locacao.veiculo.modelo}",
        "cliente": locacao.cliente.nome,
        "data": _local(locacao.fim_previsto).date(),
        "situacao": {"rotulo": rotulo["rotulo"], "tom": rotulo["tom"]},
    }


def criadas_hoje_por_vendedor(filiais: Iterable[int]) -> dict[int, int]:
    """Locações (fora dos rascunhos) criadas hoje, por vendedor: o resumo da equipe do gerente."""
    comeco, fim = _intervalo_do_dia(relogio.hoje())
    return dict(
        Locacao.objects.filter(
            filial_id__in=list(filiais), criado_em__gte=comeco, criado_em__lt=fim
        )
        .exclude(status=S.RASCUNHO)
        .order_by()
        .values_list("vendedor_id")
        .annotate(total=Count("id"))
        .values_list("vendedor_id", "total")
    )


# --- Detalhe ---


def _cancelamento_em_curso(locacao: Locacao) -> bool:
    return locacao.cancelamento_status in (StatusDesconto.PENDENTE, StatusDesconto.APROVADO)


def _cancelar(usuario: Any, locacao: Locacao) -> str | bool:
    """O pedido pendente se decide em Aprovações; o aprovado segue para a devolução."""
    if locacao.status in (S.ENCERRADA, S.CANCELADA) or _cancelamento_em_curso(locacao):
        return False
    valor = pode(usuario, "locacoes_cancelar")
    if valor in ("sim", "aprova"):
        return "direto"
    return "pedir" if valor == "pede" else False


def _vistorias_da_troca(troca: TrocaVeiculo) -> dict[str, Any]:
    """As duas vistorias da troca (`{id, status}`), que `vistorias` fornece (ADR 0015)."""
    vistorias = leituras.blocos(TROCA, troca).get("vistorias", {})
    return {
        "devolucao_vistoria": vistorias.get("devolucao_vistoria"),
        "saida_vistoria": vistorias.get("saida_vistoria"),
    }


def _pode_cancelar_troca(troca: TrocaVeiculo) -> bool:
    """T-122: com a saída do veículo novo concluída, a troca não se cancela."""
    saida = _vistorias_da_troca(troca)["saida_vistoria"]
    return saida is None or saida["status"] != "concluida"


def acoes(locacao: Locacao, usuario: Any, contrato: Contrato | None = None) -> dict[str, Any]:
    perfil = getattr(usuario, "perfil", "")
    cria = perfil in CRIAM
    em_curso = locacao.status in (S.ATIVA, S.DEVOLUCAO_ATRASADA)
    troca = services.troca_pendente(locacao)
    return {
        "editar": cria and locacao.status == S.RASCUNHO,
        "confirmar": cria and locacao.status == S.RASCUNHO,
        "renovar": cria and em_curso and not _cancelamento_em_curso(locacao),
        "registrar_devolucao": perfil in VISTORIAM and em_curso,
        "trocar_veiculo": cria
        and locacao.status == S.ATIVA
        and not _cancelamento_em_curso(locacao)
        and troca is None,
        "cancelar_troca": cria and em_curso and troca is not None and _pode_cancelar_troca(troca),
        # LOC-12: com a troca pendente, o cancelamento responde 409 `troca_pendente`.
        "cancelar": _cancelar(usuario, locacao) if troca is None else False,
        # T-263: as mesmas condições de `contrato.gerar` (o `POST .../contrato/`), menos o modelo
        # publicado: sem ele o botão aparece e o 422 `IMP-04` mostra o atalho. `contrato` é o
        # vigente: `None` também com o anterior cancelado.
        "gerar_contrato": cria
        and locacao.status == S.AGUARDANDO_RETIRADA
        and locacao.desconto_status != StatusDesconto.PENDENTE
        and not _cancelamento_em_curso(locacao)
        and contrato is None,
        "imprimir_contrato": perfil != "vistoriador"
        and contrato is not None
        and bool(contrato.pdf_assinado or contrato.pdf),
        "reenviar_contrato": cria
        and contrato is not None
        and contrato.status in (StatusContrato.ENVIADO, StatusContrato.ASSINADO),
        "continuar_vistoria": perfil in VISTORIAM
        and locacao.status == S.AGUARDANDO_RETIRADA
        and locacao.vistoria_saida_ok_em is None,
        "receber": bool(pode(usuario, "caixa_receber"))
        and int(getattr(locacao, "fin_abertas", 0) or 0) > 0,
    }


def _extras(locacao: Locacao) -> list[dict[str, Any]]:
    if locacao.status != S.RASCUNHO:
        return [
            {
                "id": e.extra_id,
                "nome": e.nome,
                "quantidade": e.quantidade,
                "valor_centavos": e.valor_centavos,
                "cobranca": e.cobranca,
            }
            for e in locacao.extras.all()
        ]
    from apps.veiculos.models import Extra

    cadastro = {
        e.pk: e
        for e in Extra.objects.filter(pk__in=[x["extra_id"] for x in locacao.extras_rascunho])
    }
    return [
        {
            "id": item["extra_id"],
            "nome": cadastro[item["extra_id"]].nome,
            "quantidade": item["quantidade"],
            "valor_centavos": cadastro[item["extra_id"]].valor_centavos,
            "cobranca": cadastro[item["extra_id"]].cobranca,
        }
        for item in locacao.extras_rascunho
        if item["extra_id"] in cadastro
    ]


def _desconto(locacao: Locacao) -> dict[str, Any] | None:
    if not locacao.desconto_status:
        return None
    return {
        "status": locacao.desconto_status,
        "pedido_aprovacao_id": locacao.pedido_desconto_id,
        "pct": locacao.desconto_pedido_pct,
    }


def _devolucao(locacao: Locacao) -> dict[str, Any]:
    faltam = None
    if locacao.status in (S.ATIVA, S.AGUARDANDO_RETIRADA):
        faltam = max(0, int((locacao.fim_previsto - relogio.agora()).total_seconds() // 60))
    return {
        "prevista_para": locacao.fim_previsto,
        "faltam_minutos": faltam,
        "aviso_atraso": (
            f"Se atrasar, cobra {formatar_reais(locacao.diaria_centavos)} por dia a mais (diária)"
        ),
        # A devolução com chegada, que `vistorias` fornece (ADR 0015); `null` sem chegada.
        "devolucao_id": leituras.blocos(LOCACAO, locacao).get("devolucao", {}).get("devolucao_id"),
    }


def _veiculo_da_troca(veiculo: Any) -> dict[str, Any]:
    return {"id": veiculo.pk, "placa": veiculo.placa, "modelo": veiculo.modelo}


def _troca(locacao: Locacao) -> dict[str, Any] | None:
    """A troca pendente (LOC-09, T-122): as concluídas ficam em `trechos` e no histórico."""
    troca = services.troca_pendente(locacao)
    if troca is None:
        return None
    caucao = None
    if troca.conta_caucao_id is not None:
        conta = (
            financeiro_selectors.contas_da_origem(ORIGEM, locacao.pk)
            .filter(pk=troca.conta_caucao_id)
            .first()
        )
        if conta is not None:
            caucao = {
                "conta_id": conta.pk,
                "valor_centavos": conta.valor_centavos,
                "status": conta.status,
            }
    return {
        "id": troca.pk,
        "status": troca.status,
        "motivo": troca.motivo,
        "pedida_em": troca.criado_em,
        "veiculo_antigo": _veiculo_da_troca(troca.veiculo_antigo),
        "veiculo_novo": _veiculo_da_troca(troca.veiculo_novo),
        **_vistorias_da_troca(troca),
        "preco": {
            "valor_periodo_centavos": troca.valor_periodo_centavos,
            "diaria_centavos": troca.diaria_centavos,
            "caucao_centavos": troca.caucao_centavos,
            "preco_do_dia": troca.preco_do_dia,
        },
        "caucao": caucao,
    }


def trocas_concluidas(locacao: Locacao | int) -> QuerySet[TrocaVeiculo]:
    """As trocas concluídas, com a diferença do período guardada, para o acerto (`vistorias`)."""
    locacao_id = locacao.pk if isinstance(locacao, Locacao) else locacao
    return (
        TrocaVeiculo.objects.select_related("veiculo_antigo", "veiculo_novo")
        .filter(locacao_id=locacao_id, status=StatusTroca.CONCLUIDA)
        .order_by("concluida_em", "id")
    )


def _cancelamento(locacao: Locacao) -> dict[str, Any] | None:
    """O pedido `APR-02` pendente ou o cancelamento aprovado (com o encerramento antecipado).
    Depois da retirada, a multa e o crédito são a estimativa para `data`: o acerto da devolução
    os recalcula pelo dia em que o veículo volta (T-116)."""
    if not _cancelamento_em_curso(locacao):
        return None
    credito = locacao.credito_encerramento_centavos or 0
    multa = locacao.multa_encerramento_centavos or 0
    # O encerramento antecipado (depois da retirada) grava quando foi aprovado.
    antes = locacao.encerramento_antecipado_aprovado_em is None and locacao.status in (
        *services.ANTES_DA_RETIRADA,
        S.CANCELADA,
    )
    return {
        "status": locacao.cancelamento_status,
        "pedido_aprovacao_id": locacao.pedido_cancelamento_id,
        "antes_da_retirada": antes,
        "data": locacao.cancelamento_data,
        "multa_centavos": multa,
        "credito_centavos": credito,
        "devolver_centavos": max(0, credito - multa),
        "cobrar_centavos": max(0, multa - credito),
        "motivo": locacao.motivo_cancelamento,
    }


def _cliente_do_detalhe(locacao: Locacao, usuario: Any) -> dict[str, Any]:
    """USR-09: o celular e a CNH vêm com a locação, e `ficha_liberada` diz se o perfil abre a
    ficha do cliente; o vistoriador não abre (`GET /api/clientes/{id}/` responde 403)."""
    cliente = locacao.cliente
    return {
        "id": cliente.pk,
        "nome": cliente.nome,
        "celular": cliente.celular or None,
        "cnh_categoria": cliente.cnh_categoria or None,
        "ficha_liberada": getattr(usuario, "perfil", "") in clientes_selectors.PERFIS_QUE_VEEM,
    }


def detalhe(locacao: Locacao, usuario: Any) -> dict[str, Any]:
    hoje = relogio.hoje()
    contrato = contratos_selectors.contrato_vigente(ORIGEM, locacao.pk)
    parcelas = [
        financeiro_selectors.representacao_conta(c, hoje)
        for c in financeiro_selectors.contas_da_origem(ORIGEM, locacao.pk)
    ]
    efetivo = locacao.valor_periodo_centavos - aplicar_percentual(
        locacao.valor_periodo_centavos, locacao.desconto_pct
    )
    vendedor = locacao.vendedor
    return {
        **linha(locacao),
        "cliente": _cliente_do_detalhe(locacao, usuario),
        "filial": {"id": locacao.filial_id, "nome": locacao.filial.nome},
        "vendedor": {"id": vendedor.pk, "nome": vendedor.nome},
        "periodos": locacao.periodos,
        "precos": {
            "valor_periodo_centavos": efetivo,
            "diaria_centavos": locacao.diaria_centavos,
            "caucao_centavos": locacao.caucao_centavos,
            "desconto_pct": locacao.desconto_pct,
            "assinado_em_preco_de": locacao.precos_de,
        },
        "desconto": _desconto(locacao),
        "extras": _extras(locacao),
        "km_saida": locacao.km_saida,
        "km_livre": True,  # km livre em todos os planos (dados de referência)
        "forma_pagamento": locacao.forma_pagamento,
        "parcelamento_mensal": locacao.parcelamento_mensal or None,
        "primeiro_vencimento": locacao.primeiro_vencimento,
        "condicoes": {
            "vistoria_saida_ok_em": locacao.vistoria_saida_ok_em,
            "contrato_assinado_em": locacao.contrato_assinado_em,
            "primeiro_pagamento_em": locacao.primeiro_pagamento_em,
        },
        "parcelas": parcelas,
        "total_pago_centavos": sum(p["valor_centavos"] for p in parcelas if p["status"] == "paga"),
        "contrato": contratos_selectors.resumo(contrato),
        "devolucao": _devolucao(locacao),
        "trechos": [
            {"veiculo": t.veiculo.placa, "inicio": t.inicio, "fim": t.fim}
            for t in locacao.trechos.select_related("veiculo")
        ],
        "cancelamento": _cancelamento(locacao),
        "troca": _troca(locacao),
        "acoes": acoes(locacao, usuario, contrato),
    }


def sem_valores(dados: Any) -> Any:
    """Vistoriador: nenhum campo `_centavos`, nem pagamento, preços ou parcelas (`Vistoriador`:
    "Valores e dados de pagamento ficam ocultos")."""
    if isinstance(dados, dict):
        return {
            chave: sem_valores(valor)
            for chave, valor in dados.items()
            if not chave.endswith("_centavos")
            and chave
            not in ("pagamento", "precos", "parcelas", "desconto", "extras", "preco", "caucao")
        }
    if isinstance(dados, list):
        return [sem_valores(item) for item in dados]
    return dados


# --- Histórico (linha do tempo de Locacao-Detalhe) ---

ROTULOS_DO_HISTORICO = {
    "locacao.criar": ("Rascunho criado", "status"),
    "locacao.confirmar": ("Locação confirmada", "status"),
    "locacao.vistoria_saida": ("Vistoria de saída", "vistoria"),
    "locacao.contrato_assinado": ("Contrato assinado", "contrato"),
    "locacao.primeiro_pagamento": ("1º pagamento recebido", "pagamento"),
    "locacao.ativar": ("Locação ativa", "status"),
    "locacao.aprovar_desconto": ("Desconto aprovado", "status"),
    "locacao.recusar_desconto": ("Desconto recusado", "status"),
    "locacao.cancelar_rascunho": ("Rascunho cancelado", "status"),
    "locacao.renovar": ("Locação renovada", "status"),
    "locacao.marcar_atraso": ("Devolução atrasada", "status"),
    "locacao.pedir_cancelamento": ("Cancelamento pedido", "status"),
    "locacao.recusar_cancelamento": ("Cancelamento recusado", "status"),
    "locacao.cancelar_pedido_cancelamento": ("Pedido de cancelamento cancelado", "status"),
    "locacao.cancelar": ("Locação cancelada", "status"),
    "locacao.aprovar_encerramento": ("Encerramento antecipado aprovado", "status"),
    "locacao.encerrar": ("Locação encerrada", "status"),
}


def historico(locacao: Locacao, usuario: Any) -> list[dict[str, Any]]:
    """Eventos de auditoria da locação e pagamentos das contas dela (o vistoriador não vê os
    pagamentos). As vistorias entram com a T-016."""
    itens: list[dict[str, Any]] = []
    for evento in EventoAuditoria.objects.filter(objeto_tipo="locacao", objeto_id=locacao.pk):
        rotulo, tipo = ROTULOS_DO_HISTORICO.get(evento.acao, (evento.acao, "status"))
        itens.append(
            {"em": evento.ocorrido_em, "rotulo": rotulo, "detalhe": evento.ator_nome, "tipo": tipo}
        )
    if getattr(usuario, "perfil", "") != "vistoriador":
        for conta in financeiro_selectors.contas_da_origem(ORIGEM, locacao.pk).filter(
            status="paga"
        ):
            nome = "Caução" if conta.tipo == "caucao" else f"Parcela {conta.numero_parcela}"
            itens.append(
                {
                    "em": conta.pago_em,
                    "rotulo": f"{nome} paga · {formatar_reais(conta.valor_centavos)}",
                    "detalhe": conta.get_forma_display() if conta.forma else "",
                    "tipo": "pagamento",
                }
            )
    if getattr(usuario, "perfil", "") == "vistoriador":
        itens = [item for item in itens if item["tipo"] != "pagamento"]
    return sorted(itens, key=lambda item: item["em"], reverse=True)


# --- Renovação, atraso e cancelamento (LOC-08, LOC-10 a LOC-13) ---


def calcular_atraso(locacao: Locacao, momento: datetime | None = None) -> dict[str, Any]:
    """`{dias, valor_centavos}` para o acerto da devolução (T-016; LOC-10, LOC-11, FIL-03)."""
    return services.calcular_atraso(locacao, momento)


def calcular_encerramento_antecipado(locacao: Locacao, dia: date | None = None) -> dict[str, Any]:
    """LOC-12 e LOC-13; o mesmo cálculo de `cancelamento/simular`."""
    return services.calcular_encerramento(locacao, dia).como_dict()


def simular_renovacao(locacao: Locacao, dados: dict[str, Any]) -> dict[str, Any]:
    renovacao = services.montar_renovacao(locacao, dados)
    conta = renovacao.calculo
    return {
        "fim_previsto_atual": locacao.fim_previsto,
        "fim_previsto": conta.fim_previsto,
        "periodos": conta.periodos,
        "valor_periodo_centavos": conta.valor_periodo_centavos,
        "parcelas_novas": [
            {"numero": p.numero, "vencimento": p.vencimento, "valor_centavos": p.valor_centavos}
            for p in conta.parcelas
        ],
        "total_centavos": sum(p.valor_centavos for p in conta.parcelas),
    }


# --- Planos especiais ---


def planos_especiais(ativo: str | None = None) -> QuerySet[PlanoEspecial]:
    qs = PlanoEspecial.objects.prefetch_related("categorias")
    if ativo == "false":
        return qs.filter(ativo=False)
    if ativo == "todos":
        return qs
    return qs.filter(ativo=True)


def planos_especiais_ativos() -> int:
    """Cartão Tabelas de preço de Configurações (LOC-01)."""
    return int(PlanoEspecial.ativos.count())


def representacao_plano(plano: PlanoEspecial) -> dict[str, Any]:
    return {
        "id": plano.pk,
        "nome": plano.nome,
        "periodicidade": plano.periodicidade,
        "regra": plano.regra,
        "preco_centavos": plano.preco_centavos,
        "desconto_pct": plano.desconto_pct,
        "a_partir_do_periodo": plano.a_partir_do_periodo,
        "categorias": [{"id": c.pk, "nome": c.nome} for c in plano.categorias.all()],
        "condicoes": plano.condicoes,
        "locacoes_ativas": Locacao.objects.filter(plano_especial=plano, status__in=ABERTAS).count(),
        "ativo": plano.ativo,
    }


def locacao_aberta(veiculo: Any) -> Locacao | None:
    """A locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada` do veículo (no máximo
    uma, LOC-03). Lida pela movimentação ao criar e ao iniciar (MOV-03, ADR 0028)."""
    return Locacao.objects.filter(veiculo=veiculo, status__in=ABERTAS).order_by("-id").first()
