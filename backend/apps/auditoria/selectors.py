"""Consulta da auditoria (AUD-02, AUD-03; docs/api/auditoria.md).

Lê só o schema da conexão: na empresa, os eventos dela (que já trazem a entrada e a saída do
suporte nela); no `public`, os da plataforma (CA-018-12, CA-018-16).
"""

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from comum import auditoria, relogio
from comum.auditoria import Categoria, TipoAtor
from comum.erros import ErroDeValidacao

from . import textos
from .models import EventoAuditoria

PERIODOS = {"7d": 7, "30d": 30, "90d": 90}
PERIODO_PADRAO = "7d"
NOMES_DOS_ATORES = {TipoAtor.SISTEMA: "Sistema", TipoAtor.SUPORTE: "Suporte Giro"}


def _inteiro(parametros: Mapping[str, str], nome: str) -> int | None:
    valor = parametros.get(nome)
    if valor in (None, ""):
        return None
    if not str(valor).isdigit():
        raise ErroDeValidacao({nome: ["Informe um número."]})
    return int(str(valor))


def _data(parametros: Mapping[str, str], nome: str) -> date | None:
    valor = parametros.get(nome)
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ErroDeValidacao({nome: ["Use a data no formato 2026-10-07."]}) from erro


def inicio_do_dia(dia: date) -> datetime:
    """Meia-noite no fuso da empresa (America/Sao_Paulo)."""
    return timezone.make_aware(datetime.combine(dia, time.min))


def intervalo(parametros: Mapping[str, str]) -> tuple[datetime | None, datetime | None]:
    """`?de=&ate=` (datas no fuso da empresa, inclusivas) ou `?periodo=7d|30d|90d`.

    "Últimos 7 dias" em 07 out vai de 01 out, 00:00, até agora.
    """
    de, ate = _data(parametros, "de"), _data(parametros, "ate")
    if de or ate:
        if de and ate and de > ate:
            raise ErroDeValidacao({"de": ["A data inicial passa da final."]})
        return (
            inicio_do_dia(de) if de else None,
            inicio_do_dia(ate + timedelta(days=1)) if ate else None,
        )
    periodo = parametros.get("periodo") or PERIODO_PADRAO
    if periodo not in PERIODOS:
        raise ErroDeValidacao({"periodo": ["Use 7d, 30d ou 90d."]})
    return inicio_do_dia(relogio.hoje() - timedelta(days=PERIODOS[periodo] - 1)), None


def no_periodo(parametros: Mapping[str, str]) -> QuerySet[EventoAuditoria]:
    de, ate = intervalo(parametros)
    qs = EventoAuditoria.objects.filter(ocorrido_em__lte=relogio.agora())
    if de is not None:
        qs = qs.filter(ocorrido_em__gte=de)
    if ate is not None:
        qs = qs.filter(ocorrido_em__lt=ate)
    return qs


def filtrar(parametros: Mapping[str, str]) -> QuerySet[EventoAuditoria]:
    """Os filtros da tela combinam entre si (CA-018-10)."""
    qs = no_periodo(parametros)
    categoria = parametros.get("categoria")
    if categoria:
        if categoria not in Categoria.values:
            raise ErroDeValidacao({"categoria": ["Categoria desconhecida."]})
        qs = qs.filter(categoria=categoria)
    ator = _inteiro(parametros, "ator")
    if ator is not None:
        qs = qs.filter(ator_tipo=TipoAtor.USUARIO, ator_id=ator)
    ator_tipo = parametros.get("ator_tipo")
    if ator_tipo:
        if ator_tipo not in TipoAtor.values:
            raise ErroDeValidacao({"ator_tipo": ["Use usuario, sistema ou suporte."]})
        qs = qs.filter(ator_tipo=ator_tipo)
    filial = _inteiro(parametros, "filial")
    if filial is not None:
        qs = qs.filter(filial_id=filial)
    objeto_tipo, objeto_id = parametros.get("objeto_tipo"), _inteiro(parametros, "objeto_id")
    if objeto_tipo:
        qs = qs.filter(objeto_tipo=objeto_tipo)
    if objeto_id is not None:
        qs = qs.filter(objeto_id=objeto_id)
    codigo = (parametros.get("objeto_codigo") or "").strip().upper()
    if codigo:
        qs = qs.filter(_do_objeto(codigo))
    return qs


def _do_objeto(codigo: str) -> Q:
    """Todos os eventos do objeto que tem esse código, inclusive os gravados sem o código."""
    pares = (
        EventoAuditoria.objects.filter(objeto_codigo=codigo)
        .exclude(objeto_id=None)
        .values_list("objeto_tipo", "objeto_id")
        .distinct()
    )
    condicao = Q(objeto_codigo=codigo)
    for tipo, id_objeto in pares:
        condicao |= Q(objeto_tipo=tipo, objeto_id=id_objeto)
    return condicao


# --- Representação ---


def iniciais(nome: str) -> str:
    partes = [p for p in nome.split() if p[:1].isalpha()]
    if not partes:
        return ""
    if len(partes) == 1:
        return partes[0][0].upper()
    return f"{partes[0][0]}{partes[-1][0]}".upper()


def _ator(evento: EventoAuditoria) -> dict[str, Any]:
    nome = NOMES_DOS_ATORES.get(TipoAtor(evento.ator_tipo), evento.ator_nome)
    return {
        "tipo": evento.ator_tipo,
        "id": evento.ator_id if evento.ator_tipo == TipoAtor.USUARIO else None,
        "nome": nome,
        "iniciais": iniciais(nome),
    }


def _id_do_acesso(evento: EventoAuditoria) -> int | None:
    if evento.acesso_suporte_id is not None:
        return evento.acesso_suporte_id
    if evento.categoria == Categoria.SUPORTE and evento.objeto_tipo == "acessosuporte":
        return evento.objeto_id
    return None


def _suporte(evento: EventoAuditoria, acessos: dict[int, Any]) -> dict[str, Any] | None:
    """AUD-03: todo evento ligado a um acesso de suporte vem marcado, com o motivo."""
    id_acesso = _id_do_acesso(evento)
    if id_acesso is None:
        return None
    acesso = acessos.get(id_acesso) or {}
    atendente = acesso.get("atendente") or (
        evento.ator_nome if evento.ator_tipo == TipoAtor.SUPORTE else ""
    )
    return {
        "atendente": atendente,
        "motivo": acesso.get("motivo") or evento.motivo,
        "permissao": acesso.get("permissao") or evento.depois.get("permissao") or "",
        "acesso_suporte_id": id_acesso,
    }


def representar(eventos: Iterable[EventoAuditoria]) -> list[dict[str, Any]]:
    """Uma consulta por tipo de apoio para a página toda (filiais e acessos de suporte)."""
    eventos = list(eventos)
    filiais = auditoria.consultar("filiais", {e.filial_id for e in eventos if e.filial_id})
    ids_acessos = {i for i in (_id_do_acesso(e) for e in eventos) if i is not None}
    acessos = auditoria.consultar("acessos_suporte", ids_acessos)
    apoio: dict[str, Any] = {"acessos_suporte": dict(acessos)}
    resultado = []
    for evento in eventos:
        texto = textos.texto(evento, apoio)
        objeto = None
        if evento.objeto_tipo:
            objeto = {
                "tipo": evento.objeto_tipo,
                "id": evento.objeto_id,
                "codigo": evento.objeto_codigo or None,
                "filial": filiais.get(evento.filial_id) if evento.filial_id else None,
            }
        resultado.append(
            {
                "id": evento.pk,
                "ocorrido_em": evento.ocorrido_em,
                "ator": _ator(evento),
                "suporte": _suporte(evento, acessos),
                "categoria": evento.categoria,
                "acao": evento.acao,
                "resumo": texto.resumo,
                "detalhe": texto.detalhe,
                "objeto": objeto,
                "regra": evento.regra or None,
            }
        )
    return resultado


def detalhar(evento: EventoAuditoria) -> dict[str, Any]:
    """`antes` e `depois` como foram gravados: já classificados (ADR 0014, CA-018-06)."""
    return {
        **representar([evento])[0],
        "antes": evento.antes,
        "depois": evento.depois,
        "ip": evento.ip,
        "aparelho": evento.aparelho,
    }


def pessoas(parametros: Mapping[str, str]) -> list[dict[str, Any]]:
    """Quem aparece como ator no período (o nome mais recente de cada um), mais Sistema e
    Suporte Giro, para o filtro "Pessoa"."""
    nomes: dict[int, str] = {}
    linhas = (
        no_periodo(parametros)
        .filter(ator_tipo=TipoAtor.USUARIO)
        .exclude(ator_id=None)
        .order_by("-ocorrido_em", "-id")
        .values_list("ator_id", "ator_nome")
    )
    for ator_id, nome in linhas:
        if ator_id is not None:
            nomes.setdefault(ator_id, nome)
    usuarios = [
        {"tipo": TipoAtor.USUARIO.value, "id": i, "nome": n}
        for i, n in sorted(nomes.items(), key=lambda par: par[1].casefold())
    ]
    return [
        *usuarios,
        {"tipo": TipoAtor.SISTEMA.value, "id": None, "nome": "Sistema"},
        {"tipo": TipoAtor.SUPORTE.value, "id": None, "nome": "Suporte Giro"},
    ]
