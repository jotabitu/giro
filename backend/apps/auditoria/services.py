"""Exportação (AUD-07, S-15; docs/api/auditoria.md). Única forma de mudar o status dela.

No MVP saem a auditoria em CSV (T-018) e as despesas em CSV (T-178), estas montadas pelo
`financeiro` pelo registro de `exportacao.py`; os outros itens e formatos respondem 422
`exportacao_indisponivel` até a exportação completa da fase 2.
"""

import csv
import io
import json
from datetime import date, timedelta
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from comum import arquivos, auditoria, relogio
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.conexao import schema_atual
from comum.erros import ErroDeRegra, ErroDeValidacao, Expirado, SemPermissao
from comum.estados import transicionar

from . import selectors
from .exportacao import item_registrado
from .models import (
    EventoAuditoria,
    Exportacao,
    FormatoExportacao,
    ItemExportacao,
    StatusExportacao,
)

VALIDADE_DO_LINK = timedelta(days=7)  # AUD-07
DOIS_FATORES_RECENTE = timedelta(minutes=15)  # S-15: backup completo
DOIS_FATORES_RECENTE_ERRO = (
    "2fa_recente",
    "Confirme o código do autenticador para gerar o backup completo",
)
INDISPONIVEL = (
    "exportacao_indisponivel",
    "Por enquanto, só a auditoria e as despesas podem ser exportadas, em CSV.",
)
EXPIRADA = ("exportacao_expirada", "O link desta exportação venceu. Peça uma nova exportação.")
NAO_PRONTA = ("exportacao_nao_pronta", "O arquivo ainda não está pronto.")
# Itens e formatos que já têm gerador (o resto vem com a exportação completa).
DISPONIVEIS = {
    (ItemExportacao.AUDITORIA.value, FormatoExportacao.CSV.value),
    (ItemExportacao.DESPESAS.value, FormatoExportacao.CSV.value),
}


def dois_fatores_recente(payload: dict[str, Any]) -> bool:
    """Token com `otp` no `amr` e `auth_time` de no máximo 15 minutos atrás."""
    if "otp" not in (payload.get("amr") or []):
        return False
    momento = payload.get("auth_time")
    if not isinstance(momento, int | float):
        return False
    return relogio.agora().timestamp() - momento <= DOIS_FATORES_RECENTE.total_seconds()


def _periodo(periodo: dict[str, Any] | None) -> tuple[date | None, date | None]:
    if not periodo:
        return None, None
    try:
        de = date.fromisoformat(str(periodo.get("de")))
        ate = date.fromisoformat(str(periodo.get("ate")))
    except ValueError as erro:
        raise ErroDeValidacao({"periodo": ["Use as datas no formato 2026-10-07."]}) from erro
    if de > ate:
        raise ErroDeValidacao({"periodo": ["A data inicial passa da final."]})
    return de, ate


def _periodo_do_mes(mes: str) -> tuple[date, date]:
    """Primeiro e último dia do mês `AAAA-MM` (já conferido por quem registrou o item)."""
    inicio = date.fromisoformat(f"{mes}-01")
    seguinte = date(inicio.year + inicio.month // 12, inicio.month % 12 + 1, 1)
    return inicio, seguinte - timedelta(days=1)


def solicitar(
    *,
    itens: list[str],
    formato: str,
    periodo: dict[str, Any] | None,
    token: dict[str, Any],
    dados: dict[str, Any] | None = None,
) -> Exportacao:
    """POST /api/exportacoes/: 202 `na_fila`. O arquivo sai da tarefa `auditoria_exportar`.

    Item registrado por outro app (as despesas) vai sozinho: período e filial são diferentes. O
    corpo passa pelo `validar` dele, e o mês vira `periodo_inicio` e `periodo_fim`."""
    if formato == FormatoExportacao.ZIP:
        itens = list(ItemExportacao.values)  # backup completo: tudo, com fotos
        if not dois_fatores_recente(token):
            raise SemPermissao(*DOIS_FATORES_RECENTE_ERRO)
    if not itens:
        raise ErroDeValidacao({"itens": ["Escolha ao menos um item."]})
    if any((item, formato) not in DISPONIVEIS for item in itens):
        raise ErroDeRegra(*INDISPONIVEL)
    registrado = next((r for i in set(itens) if (r := item_registrado(i)) is not None), None)
    if registrado is not None and len(set(itens)) > 1:
        raise ErroDeRegra(*INDISPONIVEL)
    parametros: dict[str, Any] = {}
    de: date | None
    ate: date | None
    if registrado is not None:
        parametros = registrado.validar({**(dados or {}), "periodo": periodo})
        de, ate = _periodo_do_mes(parametros["mes"])
    else:
        de, ate = _periodo(periodo)
    ator = auditoria.ator_atual()
    with transaction.atomic():
        exportacao = Exportacao.objects.create(
            solicitada_por_id=ator.id,
            solicitada_por_nome=ator.nome,
            itens=sorted(set(itens)),
            formato=formato,
            periodo_inicio=de,
            periodo_fim=ate,
            parametros=parametros,
        )
        registrar_evento(
            "exportacao.pedir",
            Categoria.SEGURANCA,
            objeto=exportacao,
            depois=retrato(exportacao),
            regra="AUD-07",
        )
    return exportacao


# --- Geração (na tarefa) ---

INICIOS_PERIGOSOS = ("=", "+", "-", "@", "\t", "\r")
COLUNAS = (
    "ocorrido_em",
    "ator",
    "suporte",
    "categoria",
    "acao",
    "resumo",
    "detalhe",
    "objeto",
    "codigo",
    "filial",
    "regra",
    "antes",
    "depois",
)


def celula(valor: Any) -> Any:
    """Texto que começa com fórmula sai com apóstrofo (docs/api/README.md)."""
    if isinstance(valor, str) and valor.startswith(INICIOS_PERIGOSOS):
        return f"'{valor}"
    return valor


def _linhas_da_auditoria(exportacao: Exportacao) -> list[list[Any]]:
    qs = EventoAuditoria.objects.order_by("ocorrido_em", "id")
    if exportacao.periodo_inicio:
        qs = qs.filter(ocorrido_em__gte=selectors.inicio_do_dia(exportacao.periodo_inicio))
    if exportacao.periodo_fim:
        fim = exportacao.periodo_fim + timedelta(days=1)
        qs = qs.filter(ocorrido_em__lt=selectors.inicio_do_dia(fim))
    linhas: list[list[Any]] = []
    # `antes` e `depois` saem como foram gravados: já classificados (ADR 0014, CA-018-13).
    for evento, dados in zip(qs, selectors.representar(qs), strict=True):
        objeto = dados["objeto"] or {}
        suporte = dados["suporte"] or {}
        linhas.append(
            [
                evento.ocorrido_em.isoformat().replace("+00:00", "Z"),
                dados["ator"]["nome"],
                suporte.get("atendente", ""),
                evento.categoria,
                evento.acao,
                dados["resumo"],
                dados["detalhe"],
                objeto.get("tipo", ""),
                objeto.get("codigo") or "",
                objeto.get("filial") or "",
                evento.regra,
                _json(evento.antes),
                _json(evento.depois),
            ]
        )
    return linhas


def _json(valor: Any) -> str:
    return json.dumps(valor, cls=DjangoJSONEncoder, ensure_ascii=False) if valor else ""


def _csv(linhas: list[list[Any]], colunas: tuple[str, ...] = COLUNAS) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(colunas)
    for linha in linhas:
        escritor.writerow([celula(v) for v in linha])
    return saida.getvalue().encode("utf-8-sig")  # BOM: a planilha abre os acentos certos


def gerar(exportacao_id: int) -> Exportacao | None:
    """Gera o arquivo no storage privado e marca `pronta` (link de 7 dias). Idempotente."""
    exportacao: Exportacao | None = Exportacao.objects.filter(pk=exportacao_id).first()
    if exportacao is None or exportacao.status != StatusExportacao.NA_FILA:
        return exportacao
    item = exportacao.itens[0] if len(exportacao.itens) == 1 else ""
    registrado = item_registrado(item)
    try:
        if registrado is not None:
            conteudo = _csv(registrado.linhas(exportacao), registrado.colunas)
        else:
            item = "auditoria"
            conteudo = _csv(_linhas_da_auditoria(exportacao))
        caminho = f"{schema_atual()}/auditoria/exportacao/{exportacao.pk}/{item}.csv"
        arquivos.provedor().salvar(caminho, conteudo, "text/csv")
    except Exception:
        transicionar(exportacao, StatusExportacao.FALHOU, acao="exportacao.falhar", regra="AUD-07")
        raise
    exportacao.arquivo = caminho
    exportacao.tamanho_bytes = len(conteudo)
    exportacao.expira_em = relogio.agora() + VALIDADE_DO_LINK
    transicionar(
        exportacao,
        StatusExportacao.PRONTA,
        acao="exportacao.concluir",
        regra="AUD-07",
        mais_campos=("arquivo", "tamanho_bytes", "expira_em"),
    )
    return exportacao


# --- Download (S-15) ---


def expirar(exportacao: Exportacao) -> None:
    """Depois dos 7 dias: o arquivo sai do storage e a linha fica `expirada`."""
    with transaction.atomic():
        travada = Exportacao.objects.select_for_update().get(pk=exportacao.pk)
        if travada.status != StatusExportacao.PRONTA:
            return
        caminho = travada.arquivo
        travada.arquivo = ""
        transicionar(
            travada,
            StatusExportacao.EXPIRADA,
            acao="exportacao.expirar",
            regra="AUD-07",
            mais_campos=("arquivo",),
        )
        if caminho:
            transaction.on_commit(lambda: arquivos.apagar_temporario(caminho))


def vencida(exportacao: Exportacao) -> bool:
    """Passou dos 7 dias. Quem chama expira (`expirar`) e responde 410, sem levantar erro: o
    erro desfaria a transação da requisição junto com a expiração."""
    return (
        exportacao.status == StatusExportacao.PRONTA
        and exportacao.expira_em is not None
        and exportacao.expira_em <= relogio.agora()
    )


def baixar(exportacao: Exportacao, token: dict[str, Any]) -> str:
    """URL assinada de 15 minutos (AUD-05) e o evento `exportacao.baixar`. Expirada: 410."""
    if exportacao.formato == FormatoExportacao.ZIP and not dois_fatores_recente(token):
        raise SemPermissao(*DOIS_FATORES_RECENTE_ERRO)
    if exportacao.status == StatusExportacao.EXPIRADA or vencida(exportacao):
        raise Expirado(*EXPIRADA)
    if exportacao.status != StatusExportacao.PRONTA or not exportacao.arquivo:
        raise ErroDeRegra(*NAO_PRONTA)
    registrar_evento("exportacao.baixar", Categoria.SEGURANCA, objeto=exportacao, regra="AUD-07")
    return arquivos.url_assinada(exportacao.arquivo).url


def conteudo_rotulo(exportacao: Exportacao) -> str:
    """ "Auditoria · 01/10 a 07/10" para a lista de exportações recentes."""
    registrado = item_registrado(exportacao.itens[0]) if len(exportacao.itens) == 1 else None
    if registrado is not None:
        return registrado.conteudo(exportacao)
    rotulos = dict(ItemExportacao.choices)
    nomes = ", ".join(str(rotulos.get(i, i)) for i in exportacao.itens)
    if exportacao.formato == FormatoExportacao.ZIP:
        nomes = "Backup completo"
    if exportacao.periodo_inicio and exportacao.periodo_fim:
        periodo = f"{exportacao.periodo_inicio:%d/%m/%Y} a {exportacao.periodo_fim:%d/%m/%Y}"
        return f"{nomes} · {periodo}"
    return nomes
