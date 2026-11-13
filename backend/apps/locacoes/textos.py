"""Textos prontos da auditoria para as ações da locação com intenção de compra (`LOC-16`,
T-420; A5 da conferência de 13 nov 2026). Registrados no `ready()` por
`comum.auditoria.registrar_formatador`, como os de `veiculos` (T-460, T-464).
"""

from typing import Any

from comum.auditoria import Texto

from .models import PlanoCompra


def _com_codigo(resumo: str, evento: Any, depois: str = "") -> str:
    codigo = f" {evento.objeto_codigo}" if evento.objeto_codigo else ""
    return f"{resumo}{codigo}{depois}"


def quitar(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Quitou a locação LOC-2877", "Todas as parcelas pagas"."""
    return Texto(_com_codigo("Quitou a locação", evento), evento.motivo or "")


def encerrar_por_atraso(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Encerrou a locação LOC-2877 por atraso", com o motivo de quem encerrou."""
    return Texto(_com_codigo("Encerrou a locação", evento, " por atraso"), evento.motivo or "")


RESUMOS_DO_PLANO = {
    "plano_compra.criar": "Criou o plano de compra",
    "plano_compra.editar": "Editou o plano de compra",
    "plano_compra.desativar": "Desativou o plano de compra",
}


def _nome_do_plano(evento: Any, apoio: dict[str, Any]) -> str:
    """O nome gravado no evento (vai inteiro, `CAMPOS_AUDITORIA`); sem ele, o nome de hoje."""
    for lado in (evento.depois or {}, evento.antes or {}):
        if isinstance(lado.get("nome"), str):
            return str(lado["nome"])
    nomes: dict[int, str] = apoio.setdefault("planos_de_compra", {})
    if evento.objeto_id is None:
        return ""
    if evento.objeto_id not in nomes:
        nome = PlanoCompra.objects.filter(pk=evento.objeto_id).values_list("nome", flat=True)
        nomes[evento.objeto_id] = nome.first() or ""
    return nomes[evento.objeto_id]


def plano_de_compra(evento: Any, apoio: dict[str, Any]) -> Texto:
    """ "Criou o plano de compra Compra Street 24 meses"; editar e desativar do mesmo jeito."""
    nome = _nome_do_plano(evento, apoio)
    resumo = RESUMOS_DO_PLANO[evento.acao]
    return Texto(f"{resumo} {nome}" if nome else resumo, evento.motivo or "")
