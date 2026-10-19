"""Leituras das movimentações (docs/api/movimentacoes.md): representação, quadro, lista e as
escolhas de quem leva e quem recebe (T-300)."""

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Q, QuerySet

from apps.contas import selectors as contas_selectors
from apps.contas.models import Perfil
from apps.filiais.models import Filial
from comum import arquivos, relogio
from comum.permissoes import filiais_permitidas

from . import services
from .models import (
    ABERTAS,
    LocalApoio,
    Movimentacao,
    ParadaMovimentacao,
    StatusMovimentacao,
)

S = StatusMovimentacao
COLUNAS = (
    (S.AGENDADA, "Agendadas"),
    (S.EM_TRANSITO, "Em trânsito"),
    (S.NO_LOCAL, "No local de apoio"),
    (S.CONCLUIDA, "Concluídas"),
)
ITENS_POR_COLUNA = 50
# `movimentacao_aberta` do veículo (veiculos.md, T-300).
ROTULO_DA_ABERTA = {
    S.AGENDADA: ("Movimentação agendada", "neutro"),
    S.EM_TRANSITO: ("Em movimentação", "info"),
    S.NO_LOCAL: ("No local de apoio", "info"),
}


def base() -> QuerySet[Movimentacao]:
    return Movimentacao.objects.select_related(
        "veiculo", "filial_saida", "destino", "categoria_destino", "levado_por", "recebido_por"
    )


def visiveis(usuario: Any) -> QuerySet[Movimentacao]:
    """Administrador e gerente: as de saída ou destino nas suas filiais (USR-07). Quem leva: só
    as que leva. O financeiro não vê nenhuma."""
    perfil = getattr(usuario, "perfil", "")
    if perfil in services.GESTAO:
        filiais = filiais_permitidas(usuario)
        return base().filter(Q(filial_saida_id__in=filiais) | Q(destino_id__in=filiais))
    if perfil in (Perfil.VENDEDOR, Perfil.VISTORIADOR):
        return base().filter(levado_por_id=getattr(usuario, "pk", None))
    return base().none()


def _curto(filial: Filial) -> str:
    nome = filial.nome
    return nome[len("Filial ") :] if nome.startswith("Filial ") else nome


def _paradas(movimentacao: Movimentacao) -> list[ParadaMovimentacao]:
    cache = getattr(movimentacao, "_paradas", None)
    if cache is None:
        cache = list(movimentacao.paradas.select_related("local", "despesa").order_by("ordem"))
        movimentacao._paradas = cache  # type: ignore[attr-defined]
    return cache


def rota(movimentacao: Movimentacao) -> str:
    saida = _curto(movimentacao.filial_saida)
    destino = saida if not movimentacao.transferencia else movimentacao.destino.nome
    return " → ".join([saida, *[p.local.nome for p in _paradas(movimentacao)], destino])


def _proxima_etapa(movimentacao: Movimentacao) -> str | None:
    if movimentacao.status not in (S.EM_TRANSITO, S.NO_LOCAL):
        return None
    for parada in _paradas(movimentacao):
        if parada.saiu_em is None:
            return f"parada:{parada.pk}"
    return "destino"


def acoes(movimentacao: Movimentacao, usuario: Any) -> dict[str, bool]:
    gere = services.gere(usuario, movimentacao.filial_saida_id)
    chega = services.registra_chegada(movimentacao, usuario)
    etapa = _proxima_etapa(movimentacao)
    status = movimentacao.status
    return {
        "editar": gere and status == S.AGENDADA,
        "iniciar": gere and status == S.AGENDADA,
        "cancelar": gere and status == S.AGENDADA,
        "chegar_parada": chega and status == S.EM_TRANSITO and bool(etapa) and etapa != "destino",
        "sair_parada": chega and status == S.NO_LOCAL,
        "registrar_chegada": chega and status == S.EM_TRANSITO and etapa == "destino",
    }


def foto(foto: Any) -> dict[str, Any]:
    assinada = arquivos.url_assinada(foto.arquivo.name)
    return {"posicao": foto.posicao, "url": assinada.url, "url_expira_em": assinada.expira_em}


def _pessoa(usuario: Any) -> dict[str, Any] | None:
    return {"id": usuario.pk, "nome": usuario.nome} if usuario is not None else None


def _duracao(movimentacao: Movimentacao) -> int | None:
    if movimentacao.iniciada_em is None or movimentacao.concluida_em is None:
        return None
    return int((movimentacao.concluida_em - movimentacao.iniciada_em).total_seconds() // 60)


def _parada(parada: ParadaMovimentacao) -> dict[str, Any]:
    despesa = parada.despesa
    return {
        "id": parada.pk,
        "ordem": parada.ordem,
        "local": {
            "id": parada.local_id,
            "nome": parada.local.nome,
            "tipo": parada.local.tipo,
            "ativo": parada.local.ativo,
        },
        "servico": parada.servico,
        "categoria": parada.categoria,
        "valor_previsto_centavos": parada.valor_previsto_centavos,
        "chegou_em": parada.chegou_em,
        "saiu_em": parada.saiu_em,
        "valor_pago_centavos": parada.valor_pago_centavos,
        "despesa": (
            {"id": despesa.pk, "status": despesa.status, "sem_nota": not despesa.nota}
            if despesa is not None
            else None
        ),
    }


def _comum(movimentacao: Movimentacao, usuario: Any) -> dict[str, Any]:
    veiculo = movimentacao.veiculo
    paradas = _paradas(movimentacao)
    return {
        "id": movimentacao.pk,
        "codigo": movimentacao.codigo,
        "status": movimentacao.status,
        "veiculo": {
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": f"{veiculo.marca} {veiculo.modelo}",
            "status": veiculo.status,
        },
        "filial_saida": {
            "id": movimentacao.filial_saida_id,
            "nome": movimentacao.filial_saida.nome,
        },
        "destino": {"id": movimentacao.destino_id, "nome": movimentacao.destino.nome},
        "transferencia": movimentacao.transferencia,
        "categoria_destino": (
            {"id": movimentacao.categoria_destino_id, "nome": movimentacao.categoria_destino.nome}
            if movimentacao.categoria_destino is not None
            else None
        ),
        "rota": rota(movimentacao),
        "levado_por": _pessoa(movimentacao.levado_por),
        "agendada_para": movimentacao.agendada_para,
        "iniciada_em": movimentacao.iniciada_em,
        "concluida_em": movimentacao.concluida_em,
        "duracao_minutos": _duracao(movimentacao),
        "vistoria_rapida": movimentacao.vistoria_rapida,
        "km_saida": movimentacao.km_saida,
        "cancelada_em": movimentacao.cancelada_em,
        "motivo_cancelamento": movimentacao.motivo_cancelamento or None,
        "proxima_etapa": _proxima_etapa(movimentacao),
        "custo_centavos": sum(p.valor_pago_centavos or 0 for p in paradas),
        "acoes": acoes(movimentacao, usuario),
    }


def representacao(movimentacao: Movimentacao, usuario: Any) -> dict[str, Any]:
    dados = _comum(movimentacao, usuario)
    fotos = [foto(f) for f in movimentacao.fotos_chegada.order_by("id")]
    dados["paradas"] = [_parada(p) for p in _paradas(movimentacao)]
    dados["fotos_chegada"] = fotos
    dados["chegada"] = (
        {
            "km": movimentacao.km_chegada,
            "combustivel": movimentacao.combustivel_chegada or None,
            "recebido_por": _pessoa(movimentacao.recebido_por),
            "fotos": fotos,
        }
        if movimentacao.status == S.CONCLUIDA
        else None
    )
    return dados


def _local(momento: datetime, filial: Filial) -> datetime:
    return momento.astimezone(ZoneInfo(filial.fuso))


def _dia(momento: datetime, filial: Filial, hoje: date) -> str:
    dia = _local(momento, filial).date()
    if dia == hoje:
        return "hoje"
    if dia == hoje + timedelta(days=1):
        return "amanhã"
    if dia == hoje - timedelta(days=1):
        return "ontem"
    return f"{dia:%d/%m}"


def _duracao_texto(minutos: int) -> str:
    horas, resto = divmod(minutos, 60)
    if not horas:
        return f"{resto} min"
    return f"{horas} h {resto} min" if resto else f"{horas} h"


def resumo(movimentacao: Movimentacao) -> str:
    """Texto pronto da linha do quadro, no fuso da filial de saída."""
    filial = movimentacao.filial_saida
    hoje = _local(relogio.agora(), filial).date()
    status = movimentacao.status
    if status == S.AGENDADA and movimentacao.agendada_para is not None:
        quando = movimentacao.agendada_para
        return f"{_dia(quando, filial, hoje)} {_local(quando, filial):%H:%M}"
    if status == S.EM_TRANSITO and movimentacao.iniciada_em is not None:
        total = len(_paradas(movimentacao))
        paradas = f" · {total} parada{'s' if total != 1 else ''}" if total else ""
        return f"saiu {_local(movimentacao.iniciada_em, filial):%H:%M}{paradas}"
    if status == S.NO_LOCAL:
        atual = next((p for p in _paradas(movimentacao) if p.saiu_em is None), None)
        if atual is not None and atual.chegou_em is not None:
            return f"no {atual.local.nome} desde {_local(atual.chegou_em, filial):%H:%M}"
    if status == S.CONCLUIDA and movimentacao.concluida_em is not None:
        quando = movimentacao.concluida_em
        texto = f"{_dia(quando, filial, hoje)} {_local(quando, filial):%H:%M}"
        minutos = _duracao(movimentacao)
        return f"{texto} · {_duracao_texto(minutos)}" if minutos is not None else texto
    if status == S.CANCELADA:
        return "cancelada"
    return ""


def linha(movimentacao: Movimentacao, usuario: Any) -> dict[str, Any]:
    dados = _comum(movimentacao, usuario)
    dados["paradas_total"] = len(_paradas(movimentacao))
    dados["resumo"] = resumo(movimentacao)
    return dados


def _da_filial(qs: QuerySet[Movimentacao], filial: str | None) -> QuerySet[Movimentacao]:
    if filial and filial.isdigit():
        pk = int(filial)
        return qs.filter(Q(filial_saida_id=pk) | Q(destino_id=pk))
    return qs


def _inicio_do_dia_local(filial: Filial) -> datetime:
    agora = _local(relogio.agora(), filial)
    return agora.replace(hour=0, minute=0, second=0, microsecond=0)


def quadro(usuario: Any, filial: str | None, parametros: Any = None) -> dict[str, Any]:
    """Concluídas: só as de hoje, no dia local da filial de saída (CA-246-18). `levando` e
    `busca` como na lista (T-320)."""
    qs = _levando_e_busca(_da_filial(visiveis(usuario), filial), usuario, parametros or {})
    ordens = {
        S.AGENDADA: ("agendada_para", "id"),
        S.EM_TRANSITO: ("iniciada_em", "id"),
        S.NO_LOCAL: ("iniciada_em", "id"),
        S.CONCLUIDA: ("-concluida_em", "-id"),
    }
    colunas = []
    for status, rotulo in COLUNAS:
        da_coluna = qs.filter(status=status).order_by(*ordens[status])
        if status == S.CONCLUIDA:
            ids = [
                m.pk
                for m in da_coluna
                if m.concluida_em is not None
                and m.concluida_em >= _inicio_do_dia_local(m.filial_saida)
            ]
            da_coluna = da_coluna.filter(pk__in=ids)
        colunas.append(
            {
                "status": status,
                "rotulo": rotulo,
                "total": da_coluna.count(),
                "itens": [linha(m, usuario) for m in da_coluna[:ITENS_POR_COLUNA]],
            }
        )
    return {"colunas": colunas}


def filtrar(usuario: Any, parametros: Any) -> QuerySet[Movimentacao]:
    qs = _da_filial(visiveis(usuario), parametros.get("filial"))
    status = [s for s in (parametros.get("status") or "").split(",") if s in S.values]
    if status:
        qs = qs.filter(status__in=status)
    veiculo = parametros.get("veiculo") or ""
    if veiculo.isdigit():
        qs = qs.filter(veiculo_id=int(veiculo))
    for nome, comparacao in (("periodo_inicio", "gte"), ("periodo_fim", "lte")):
        valor = parametros.get(nome)
        try:
            dia = date.fromisoformat(valor) if valor else None
        except ValueError:
            dia = None
        if dia is not None:
            qs = qs.filter(
                Q(**{f"iniciada_em__date__{comparacao}": dia})
                | Q(iniciada_em__isnull=True, **{f"agendada_para__date__{comparacao}": dia})
            )
    return _levando_e_busca(qs, usuario, parametros)


def _levando_e_busca(
    qs: QuerySet[Movimentacao], usuario: Any, parametros: Any
) -> QuerySet[Movimentacao]:
    """`?levando=eu` e `?busca=` (código ou placa), na lista e no quadro."""
    if parametros.get("levando") == "eu":
        qs = qs.filter(levado_por_id=getattr(usuario, "pk", None))
    busca = (parametros.get("busca") or "").strip().upper().replace("-", "")
    if busca:
        qs = qs.filter(
            Q(codigo__icontains=parametros.get("busca").strip())
            | Q(veiculo__placa__icontains=busca)
        )
    return qs


# --- Locais de apoio ---


def locais(parametros: Any) -> QuerySet[LocalApoio]:
    qs = LocalApoio.objects.filter(ativo=parametros.get("ativo", "true") != "false")
    tipo = parametros.get("tipo")
    if tipo:
        qs = qs.filter(tipo=tipo)
    busca = parametros.get("busca")
    if busca:
        qs = qs.filter(nome_busca__contains=services.nome_de_busca(busca))
    return qs.order_by("nome", "id")


def representacao_local(local: LocalApoio) -> dict[str, Any]:
    return {"id": local.pk, "nome": local.nome, "tipo": local.tipo, "ativo": local.ativo}


# --- Quem leva e quem recebe (T-300) ---


def _escolha(pessoas: list[Any], usuario: Any) -> dict[str, Any]:
    return {
        "resultados": [
            {
                "id": p.pk,
                "nome": p.nome,
                "perfil": p.perfil,
                "perfil_rotulo": Perfil(p.perfil).label,
                "eu": p.pk == getattr(usuario, "pk", None),
            }
            for p in pessoas
        ]
    }


def pessoas(filial_id: int, usuario: Any) -> dict[str, Any]:
    return _escolha(contas_selectors.pessoas_da_filial(filial_id, services.NAO_LEVAM), usuario)


def recebedores(movimentacao: Movimentacao, usuario: Any) -> dict[str, Any]:
    return _escolha(
        contas_selectors.pessoas_da_filial(movimentacao.destino_id, services.NAO_RECEBEM), usuario
    )


# --- Para o veículo (ADR 0028, item 4) ---


def aberta(veiculo: Any) -> Movimentacao | None:
    """A movimentação `agendada`, `em_transito` ou `no_local` do veículo (no máximo uma)."""
    return Movimentacao.objects.filter(veiculo_id=veiculo.pk, status__in=ABERTAS).first()


def bloco_aberta(movimentacao: Movimentacao | None) -> dict[str, Any] | None:
    if movimentacao is None:
        return None
    rotulo, tom = ROTULO_DA_ABERTA[S(movimentacao.status)]
    return {
        "id": movimentacao.pk,
        "codigo": movimentacao.codigo,
        "status": movimentacao.status,
        "rotulo": rotulo,
        "tom": tom,
    }


def _ultima(movimentacao: Movimentacao) -> dict[str, Any]:
    return {
        "id": movimentacao.pk,
        "codigo": movimentacao.codigo,
        "status": movimentacao.status,
        "destino_nome": movimentacao.destino.nome,
        "paradas": [p.local.nome for p in _paradas(movimentacao)],
        "iniciada_em": movimentacao.iniciada_em,
        "concluida_em": movimentacao.concluida_em,
    }


def bloco_da_ficha(veiculo: Any) -> dict[str, Any]:
    """Bloco `movimentacoes` da ficha (T-275): total, as 3 últimas e a em andamento."""
    todas = Movimentacao.objects.select_related("destino").filter(veiculo_id=veiculo.pk)
    andamento = todas.filter(status__in=ABERTAS).first()
    return {
        "total": todas.count(),
        "ultimas": [_ultima(m) for m in todas.order_by("-id")[:3]],
        "em_andamento": _ultima(andamento) if andamento is not None else None,
    }
