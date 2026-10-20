"""Textos prontos da auditoria para as ações de `veiculos` (`auditoria.md`, T-201).

Registrados no `ready()` por `comum.auditoria.registrar_formatador`.
"""

from datetime import date
from typing import Any

from django.utils import timezone

from comum.auditoria import Texto
from comum.dinheiro import formatar_reais

from .models import Categoria

# Na ordem do texto: diária, semanal, (quinzenal,) mensal e caução.
PERIODOS = (
    ("diaria_centavos", "diária"),
    ("semanal_centavos", "semanal"),
    ("mensal_centavos", "mensal"),
    ("caucao_centavos", "caução"),
)
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def tabela_de_preco(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Mudou a tabela de preço", "Street 150–160 · semanal R$ 299,40 → R$ 329,00"; sem preço
    anterior, "Definiu a tabela de preço" com os valores. Preço futuro: "a partir de 15 out"."""
    antes, depois = evento.antes or {}, evento.depois or {}
    nome = (
        Categoria.objects.filter(pk=evento.objeto_id).values_list("nome", flat=True).first() or ""
    )
    if antes:
        resumo = "Mudou a tabela de preço"
        trechos = [
            f"{rotulo} {formatar_reais(antes[campo])} → {formatar_reais(depois[campo])}"
            for campo, rotulo in PERIODOS
            if campo in antes and campo in depois
        ]
    else:
        resumo = "Definiu a tabela de preço"
        trechos = [
            f"{rotulo} {formatar_reais(depois[campo])}"
            for campo, rotulo in PERIODOS
            if isinstance(depois.get(campo), int)
        ]
    vigente = depois.get("vigente_desde")
    if vigente and date.fromisoformat(vigente) > timezone.localdate(evento.ocorrido_em):
        dia = date.fromisoformat(vigente)
        trechos.append(f"a partir de {dia.day:02d} {MESES[dia.month - 1]}")
    return Texto(resumo, " · ".join([nome, *trechos]) if nome else " · ".join(trechos))
