"""Consultas e representações da importação (docs/api/importacao.md, "Representação").

O suporte Giro vê as linhas de clientes resumidas (AUD-09): só nome, tipo, documento mascarado
e celular. O administrador vê a linha inteira.
"""

import json
from datetime import timedelta
from typing import Any

from django.db.models import QuerySet

from apps.filiais.models import Filial
from apps.plataforma.selectors import uso_do_plano
from apps.veiculos.models import Categoria
from comum import relogio
from comum.classificacao import mascarar_documento

from . import linhas
from .models import Importacao, LinhaImportacao, StatusImportacao, StatusLinha, TipoImportacao

DIAS_DA_LISTA = 30
FILTROS_DE_LINHA = (
    StatusLinha.COM_ERRO,
    StatusLinha.PRONTA,
    StatusLinha.IMPORTADA,
    StatusLinha.ACIMA_DO_LIMITE,
)


A_GRAVAR = (StatusLinha.PRONTA, StatusLinha.ACIMA_DO_LIMITE)
ABERTAS = (StatusImportacao.VALIDADA, StatusImportacao.CONCLUIDA)
SEM_CATEGORIA = "Cadastre os preços antes de importar veículos."


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


def faltam_categorias(importacao: Importacao) -> bool:
    """Alguma linha a gravar sem categoria: "Importar" fica travado (IMP-08)."""
    if importacao.tipo != TipoImportacao.VEICULOS:
        return False
    contexto = linhas.Contexto.carregar(importacao.filial_padrao_id)
    return any(
        contexto.categoria(item.dados) is None
        for item in importacao.itens.filter(status__in=A_GRAVAR)
    )


def _categorias(importacao: Importacao) -> dict[str, Any] | None:
    """IMP-08: as categorias que a filial da importação oferece e "Categoria de cada modelo",
    com os modelos das linhas a gravar que seguem o modelo. Só em veículos."""
    if importacao.tipo != TipoImportacao.VEICULOS:
        return None
    contexto = linhas.Contexto.carregar(importacao.filial_padrao_id)
    modelos: dict[str, dict[str, Any]] = {}
    falta = False
    if importacao.status in ABERTAS:
        for item in importacao.itens.filter(status__in=A_GRAVAR).order_by("numero"):
            falta = falta or contexto.categoria(item.dados) is None
            if item.dados.get(linhas.CATEGORIA_PROPRIA) == "1":
                continue
            marca, modelo = str(item.dados.get("marca", "")), str(item.dados.get("modelo", ""))
            grupo = modelos.setdefault(
                linhas.chave_do_modelo(marca, modelo),
                {"marca": marca, "modelo": modelo, "veiculos": 0, "categoria_id": None},
            )
            grupo["veiculos"] += 1
            escolhida = item.dados.get(linhas.CATEGORIA)
            if escolhida and grupo["categoria_id"] is None:
                grupo["categoria_id"] = int(escolhida)
    return {
        "pergunta": len(contexto.categorias) > 1,
        "opcoes": [
            {"id": c.pk, "nome": c.nome, "tipo_veiculo": c.tipo_veiculo}
            for c in contexto.categorias
        ],
        "modelos": list(modelos.values()),
        "falta_escolher": falta,
    }


def preparo(filial_id: int | None) -> dict[str, Any]:
    """IMP-08, antes do envio de veículos: a filial (a única ativa, ou a escolhida) e se dá para
    importar. Com mais de uma filial ativa, a tela pede "Filial dos veículos"."""
    ativas = list(Filial.ativos.order_by("nome", "id"))
    filial = ativas[0] if len(ativas) == 1 else None
    if filial_id is not None:
        filial = next((f for f in ativas if f.pk == filial_id), filial)
    if filial is not None:
        tem_categoria = bool(linhas.categorias_da_filial(filial.pk))
    else:
        tem_categoria = Categoria.ativos.exists()
    return {
        "filiais": [{"id": f.pk, "nome": f.nome} for f in ativas],
        "pede_filial": len(ativas) > 1,
        "filial": {"id": filial.pk, "nome": filial.nome} if filial else None,
        "pode_importar": tem_categoria and bool(ativas),
        "motivo": None if tem_categoria else SEM_CATEGORIA,
    }


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
        "categorias": _categorias(importacao),
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
    categoria = {
        "categoria_id": int(dados[linhas.CATEGORIA]) if dados.get(linhas.CATEGORIA) else None,
        "categoria_propria": dados.get(linhas.CATEGORIA_PROPRIA) == "1",
    }
    dados = {coluna: texto for coluna, texto in dados.items() if coluna not in linhas.INTERNAS}
    return {
        "numero": item.numero,
        "status": item.status,
        "dados": dados,
        **(categoria if tipo == TipoImportacao.VEICULOS else {}),
        "erros": item.erros,
        "objeto": {"tipo": item.objeto_tipo, "id": item.objeto_id} if item.objeto_id else None,
    }
