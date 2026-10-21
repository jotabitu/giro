"""Exportação das despesas em CSV (FIN-16, AUD-07, T-178; docs/api/auditoria.md, "Despesas em CSV").

O fluxo (pedido, tarefa, storage privado, e-mail, 7 dias, baixar) é o da auditoria; daqui saem só a
validação do pedido, as linhas e o texto de "Exportações recentes", registrados no `auditoria`
em `FinanceiroConfig.ready()`.
"""

import re
from typing import Any

from django.utils import timezone

from apps.auditoria.exportacao import registrar_item
from apps.auditoria.models import Exportacao
from apps.filiais.models import Filial
from comum.documentos import placa_com_hifen
from comum.erros import ErroDeValidacao

from .models import CategoriaDespesa, Despesa, FormaDespesa, StatusDespesa

ITEM = "despesas"
COLUNAS = (
    "data",
    "descricao",
    "categoria",
    "veiculo",
    "filial",
    "valor",
    "vencimento",
    "situacao",
    "pago_em",
    "forma",
    "lancada_por",
)
MES = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def validar(dados: dict[str, Any]) -> dict[str, Any]:
    """`mes` obrigatório (`AAAA-MM`), sem `periodo`; `filial_id` da empresa (desativada vale,
    FIL-06) ou `null` para todas. O nome da filial é copiado no pedido."""
    if dados.get("periodo"):
        raise ErroDeValidacao({"periodo": ["Para as despesas, use o mês."]})
    mes = str(dados.get("mes") or "")
    if not MES.match(mes):
        raise ErroDeValidacao({"mes": ["Escolha o mês no formato 2026-10."]})
    filial_id = dados.get("filial_id")
    if filial_id is None:
        return {"mes": mes, "filial_id": None, "filial_nome": "Todas as filiais"}
    filial = Filial.objects.filter(pk=filial_id).first()
    if filial is None:
        raise ErroDeValidacao({"filial_id": ["Filial não encontrada."]})
    return {"mes": mes, "filial_id": filial.pk, "filial_nome": filial.nome}


def _reais(centavos: int) -> str:
    """`1200,00`: vírgula, sem milhar nem "R$", para a planilha ler como número."""
    return f"{centavos // 100},{centavos % 100:02d}"


def linhas(exportacao: Exportacao) -> list[list[Any]]:
    """Uma linha por despesa do mês, em qualquer status (as recusadas também, CA-DES-09)."""
    qs = Despesa.objects.select_related("veiculo", "filial", "lancada_por").filter(
        data__gte=exportacao.periodo_inicio, data__lte=exportacao.periodo_fim
    )
    filial_id = exportacao.parametros.get("filial_id")
    if filial_id is not None:
        qs = qs.filter(filial_id=filial_id)
    categorias = dict(CategoriaDespesa.choices)
    situacoes = dict(StatusDespesa.choices)
    formas = dict(FormaDespesa.choices)
    resultado: list[list[Any]] = []
    for despesa in qs.order_by("data", "id"):
        pago_em = timezone.localtime(despesa.pago_em) if despesa.pago_em else None
        resultado.append(
            [
                f"{despesa.data:%d/%m/%Y}",
                despesa.descricao,
                str(categorias.get(despesa.categoria, despesa.categoria)),
                placa_com_hifen(despesa.veiculo.placa) if despesa.veiculo else "",
                despesa.filial.nome,
                _reais(despesa.valor_centavos),
                f"{despesa.vencimento:%d/%m/%Y}",
                str(situacoes.get(despesa.status, despesa.status)),
                f"{pago_em:%d/%m/%Y}" if pago_em else "",
                str(formas.get(despesa.forma, despesa.forma)) if pago_em else "",
                despesa.lancada_por.nome,
            ]
        )
    return resultado


def conteudo(exportacao: Exportacao) -> str:
    """ "Despesas · Filial Centro · 01/10/2026 a 31/10/2026"."""
    filial = exportacao.parametros.get("filial_nome") or "Todas as filiais"
    return (
        f"Despesas · {filial} · "
        f"{exportacao.periodo_inicio:%d/%m/%Y} a {exportacao.periodo_fim:%d/%m/%Y}"
    )


def registrar() -> None:
    registrar_item(
        ITEM, rotulo="Despesas", colunas=COLUNAS, validar=validar, linhas=linhas, conteudo=conteudo
    )
