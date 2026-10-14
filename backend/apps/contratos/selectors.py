"""Leituras de contratos. Interface para os outros apps (`docs/api/contratos.md`)."""

from collections import Counter
from typing import Any

from django.db.models import Count
from django_tenants.utils import get_public_schema_name, schema_context

from comum import arquivos
from comum.empresa import nome_da_empresa
from comum.tarefas import schema_atual

from . import marcadores, pdf
from .models import Contrato, Finalidade, ModeloContrato, StatusContrato, TipoContrato


def marca_e_host() -> tuple[pdf.Marca, str]:
    """A marca da locadora (white label) e o endereço dela, para PDFs e mensagens. O nome vem
    da marca (`comum.empresa`, `docs/api/empresas.md`); o logo no PDF entra com a edição da
    marca."""
    from apps.plataforma.models import Dominio

    schema = schema_atual()
    with schema_context(get_public_schema_name()):
        dominio = Dominio.objects.select_related("tenant").get(
            tenant__schema_name=schema, is_primary=True
        )
        host = str(dominio.domain)
    return pdf.Marca(nome=nome_da_empresa()), host


def modelo_publicado(finalidade: str = Finalidade.LOCACAO) -> ModeloContrato | None:
    """`IMP-04`: o modelo publicado e não arquivado da finalidade, o mais recente."""
    return (
        ModeloContrato.objects.filter(finalidade=finalidade, publicado=True, arquivado=False)
        .order_by("-publicado_em", "-id")
        .first()
    )


# --- Modelos (tela Contratos-Modelos) ---


def _gerados_por_versao() -> Counter[int]:
    contagem: Counter[int] = Counter()
    linhas = (
        Contrato.objects.filter(modelo__isnull=False)
        .values("modelo_id")
        .annotate(n=Count("id"))
        .values_list("modelo_id", "n")
    )
    for modelo_id, n in linhas:
        contagem[int(modelo_id)] = int(n)
    return contagem


def _resumo_do_grupo(versoes: list[ModeloContrato], gerados: Counter[int]) -> dict[str, Any]:
    """`versoes` da mais nova para a mais antiga. O `id` é o da versão mais nova."""
    ultima = versoes[0]
    publicada = next((v for v in versoes if v.publicado), None)
    return {
        "id": ultima.pk,
        "grupo": ultima.grupo,
        "nome": ultima.nome,
        "finalidade": ultima.finalidade,
        "versao_publicada": publicada.versao if publicada else None,
        "tem_rascunho": not ultima.publicado and ultima.publicado_em is None,
        "status": "publicado" if publicada else "rascunho",
        "arquivado": ultima.arquivado,
        "contratos_gerados": sum(gerados[v.pk] for v in versoes),
        "editado_em": ultima.atualizado_em,
    }


def modelos(arquivados: bool = False) -> list[dict[str, Any]]:
    """Um item por modelo (grupo de versões), em ordem de nome."""
    grupos: dict[Any, list[ModeloContrato]] = {}
    for modelo in ModeloContrato.objects.filter(arquivado=arquivados).order_by("-versao"):
        grupos.setdefault(modelo.grupo, []).append(modelo)
    gerados = _gerados_por_versao()
    itens = [_resumo_do_grupo(versoes, gerados) for versoes in grupos.values()]
    return sorted(itens, key=lambda item: (str(item["nome"]).casefold(), item["id"]))


def resumo_dos_modelos() -> dict[str, Any]:
    """O cartão Modelos de contrato de Configurações, numa consulta só: modelos (grupos) não
    arquivados, os com rascunho em aberto (`tem_rascunho` de `modelos()`) e se há modelo de
    locação publicado (`IMP-04`, o mesmo de `modelo_publicado`)."""
    ultimas: dict[Any, ModeloContrato] = {}
    tem_publicado_de_locacao = False
    for modelo in (
        ModeloContrato.objects.filter(arquivado=False)
        .order_by("-versao")
        .only("grupo", "versao", "finalidade", "publicado", "publicado_em")
    ):
        ultimas.setdefault(modelo.grupo, modelo)
        if modelo.publicado and modelo.finalidade == Finalidade.LOCACAO:
            tem_publicado_de_locacao = True
    return {
        "modelos": len(ultimas),
        "rascunhos": sum(1 for m in ultimas.values() if not m.publicado and m.publicado_em is None),
        "tem_publicado_de_locacao": tem_publicado_de_locacao,
    }


def detalhe_do_modelo(modelo: ModeloContrato) -> dict[str, Any]:
    versoes = list(ModeloContrato.objects.filter(grupo=modelo.grupo).order_by("-versao"))
    gerados = _gerados_por_versao()
    ultima = versoes[0]
    return {
        **_resumo_do_grupo(versoes, gerados),
        "texto": ultima.texto,
        "marcadores_usados": marcadores.usados(ultima.texto),
        "versoes": [
            {"versao": v.versao, "publicado_em": v.publicado_em, "contratos_gerados": gerados[v.pk]}
            for v in versoes
            if v.publicado_em is not None
        ],
    }


# --- Contrato de uma origem ---


def contrato_vigente(origem_tipo: str, origem_id: int) -> Contrato | None:
    """O contrato (não aditivo) que não foi cancelado. No máximo um, pela restrição do banco."""
    return (
        Contrato.objects.select_related("modelo")
        .filter(origem_tipo=origem_tipo, origem_id=origem_id, tipo=TipoContrato.CONTRATO)
        .exclude(status=StatusContrato.CANCELADO)
        .first()
    )


def resumo(contrato: Contrato | None) -> dict[str, Any] | None:
    """O bloco `contrato` do detalhe da origem."""
    if contrato is None:
        return None
    return {
        "id": contrato.pk,
        "status": contrato.status,
        "modelo": contrato.modelo.nome if contrato.modelo else contrato.titulo,
        "versao": contrato.versao_modelo,
        "enviado_em": contrato.enviado_em,
        "assinado_em": contrato.assinado_em,
        "pdf_disponivel": bool(contrato.pdf_assinado or contrato.pdf),
    }


def url_do_pdf(contrato: Contrato) -> arquivos.UrlAssinada | None:
    """O PDF assinado, se houver; senão, o gerado. URL de 15 minutos (AUD-05)."""
    arquivo = contrato.pdf_assinado or contrato.pdf
    if not arquivo:
        return None
    return arquivos.url_assinada(arquivo.name)


def permite_juros(origem_tipo: str, origem_id: int) -> bool:
    """`FIN-03`: só cobra multa e juros por atraso se o contrato da origem tem a cláusula.
    Sem contrato, não cobra."""
    contrato = contrato_vigente(origem_tipo, origem_id)
    return bool(contrato and contrato.clausula_juros)
