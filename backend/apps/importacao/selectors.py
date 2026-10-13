"""Consultas e representações da importação (docs/api/importacao.md, "Representação").

O suporte Giro vê as linhas de clientes resumidas (AUD-09): só nome, tipo, documento mascarado
e celular. O administrador vê a linha inteira.
"""

import json
from datetime import timedelta
from typing import Any

from django.db.models import QuerySet

from apps.plataforma.selectors import uso_do_plano
from comum import relogio
from comum.classificacao import mascarar_documento

from .models import Importacao, LinhaImportacao, StatusLinha, TipoImportacao

DIAS_DA_LISTA = 30
FILTROS_DE_LINHA = (
    StatusLinha.COM_ERRO,
    StatusLinha.PRONTA,
    StatusLinha.IMPORTADA,
    StatusLinha.ACIMA_DO_LIMITE,
)


def valores(linha: LinhaImportacao, tipo: str) -> dict[str, str]:
    """Os textos das células da linha (decifrados em clientes, ADR 0014)."""
    if tipo == TipoImportacao.CLIENTES:
        claro = linha.dados_cifrados_claro()
        return dict(json.loads(claro)) if claro else {}
    return dict(linha.dados)


def recentes() -> QuerySet[Importacao]:
    desde = relogio.agora() - timedelta(days=DIAS_DA_LISTA)
    return Importacao.objects.filter(enviada_em__gte=desde).select_related("filial_padrao")


def _plano(importacao: Importacao) -> dict[str, Any] | None:
    """IMP-03. Clientes não têm limite de plano: `null`."""
    if importacao.tipo != TipoImportacao.VEICULOS:
        return None
    uso = uso_do_plano()["veiculos"]
    limite = uso["limite"]
    cabem = None if limite is None else max(0, limite - uso["usado"])
    return {"usado": uso["usado"], "limite": limite, "cabem": cabem}


def representacao(importacao: Importacao) -> dict[str, Any]:
    filial = importacao.filial_padrao
    return {
        "id": importacao.pk,
        "tipo": importacao.tipo,
        "arquivo": importacao.arquivo_nome,
        "status": importacao.status,
        "filial_padrao": {"id": filial.pk, "nome": filial.nome} if filial else None,
        "contagens": {
            "linhas": importacao.linhas,
            "prontas": importacao.prontas,
            "com_erro": importacao.com_erro,
            "importadas": importacao.importadas,
            "acima_do_limite": importacao.acima_do_limite,
        },
        "plano": _plano(importacao),
        "aviso": importacao.aviso,
        "enviada_por": importacao.enviada_por_nome,
        "enviada_em": importacao.enviada_em,
        "concluida_em": importacao.concluida_em,
        "apagar_em": importacao.apagar_em,
    }


def _resumidos(dados: dict[str, str]) -> dict[str, str]:
    """AUD-09: o que o suporte vê de uma linha de cliente."""
    return {
        "nome": dados.get("nome", ""),
        "tipo": dados.get("tipo", ""),
        "documento_mascarado": mascarar_documento(dados["documento"])
        if dados.get("documento")
        else "",
        "celular": dados.get("celular", ""),
    }


def linha(item: LinhaImportacao, tipo: str, usuario: Any) -> dict[str, Any]:
    dados = valores(item, tipo)
    if tipo == TipoImportacao.CLIENTES and getattr(usuario, "e_suporte", False):
        dados = _resumidos(dados)
    return {
        "numero": item.numero,
        "status": item.status,
        "dados": dados,
        "erros": item.erros,
        "objeto": {"tipo": item.objeto_tipo, "id": item.objeto_id} if item.objeto_id else None,
    }
