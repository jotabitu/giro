"""Regras das contas a receber e das comissões (FIN-01, FIN-09). Único lugar que grava nestes
models.

Interface para os outros apps (ADR 0011, `locacoes` e `vendas` chamam para baixo):
`criar_contas`, `ajustar_valor`, `cancelar_abertas`, `lancar_comissao`, `confirmar_comissao` e
`marcar_paga`. Esta última é a porta da baixa até a T-017 trazer o caixa e o Pix: grava o
pagamento e publica `financeiro.parcela_paga`, como a baixa de verdade vai publicar.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.db import transaction

from comum import estados, relogio
from comum.auditoria import Categoria, auditar
from comum.erros import Conflito
from comum.eventos import publicar

from .models import Comissao, ContaReceber, RegraComissao, StatusComissao, StatusConta


@dataclass(frozen=True)
class Origem:
    """Origem genérica (ADR 0011): `Origem("locacao", 2856, "LOC-2856")`."""

    tipo: str
    id: int
    codigo: str = ""

    def campos(self) -> dict[str, Any]:
        return {"origem_tipo": self.tipo, "origem_id": self.id, "origem_codigo": self.codigo}


@dataclass(frozen=True)
class NovaConta:
    tipo: str
    vencimento: date
    valor_centavos: int
    numero_parcela: int | None = None
    total_parcelas: int | None = None
    observacao: str = ""


def criar_contas(
    origem: Origem, *, filial_id: int, cliente_id: int, contas: list[NovaConta]
) -> list[ContaReceber]:
    """Contas `aberta` da origem, na transação de quem chama. Conta de valor zero não nasce."""
    criadas = []
    with transaction.atomic():
        for nova in contas:
            if nova.valor_centavos <= 0:
                continue
            conta = ContaReceber(
                filial_id=filial_id,
                cliente_id=cliente_id,
                tipo=nova.tipo,
                numero_parcela=nova.numero_parcela,
                total_parcelas=nova.total_parcelas,
                vencimento=nova.vencimento,
                valor_centavos=nova.valor_centavos,
                observacao=nova.observacao,
                **origem.campos(),
            )
            with auditar(conta, "conta_receber.criar", Categoria.FINANCEIRO):
                conta.save()
            criadas.append(conta)
    return criadas


def _travar(conta: ContaReceber) -> ContaReceber:
    travada: ContaReceber = ContaReceber.objects.select_for_update().get(pk=conta.pk)
    return travada


def conta_nao_aberta(conta: ContaReceber) -> Conflito:
    return Conflito(
        "transicao_conta",
        "Só uma conta em aberto pode mudar de valor.",
        {"de": conta.status},
    )


def ajustar_valor(conta: ContaReceber, valor_centavos: int, *, motivo: str, regra: str) -> None:
    """Refaz o valor de uma conta em aberto (ex.: desconto aprovado, `APR-01`). Paga não muda."""
    with transaction.atomic():
        travada = _travar(conta)
        if travada.status != StatusConta.ABERTA:
            raise conta_nao_aberta(travada)
        if travada.valor_centavos == valor_centavos:
            return
        with auditar(
            travada, "conta_receber.ajustar_valor", Categoria.FINANCEIRO, motivo=motivo, regra=regra
        ):
            travada.valor_centavos = valor_centavos
            travada.save(update_fields=["valor_centavos", "atualizado_em"])
    conta.refresh_from_db()


def cancelar_abertas(origem: Origem, *, motivo: str, regra: str = "") -> int:
    """As contas em aberto da origem vão para `cancelada`. As pagas ficam (estorno é T-017)."""
    canceladas = 0
    with transaction.atomic():
        for conta in ContaReceber.objects.select_for_update().filter(
            origem_tipo=origem.tipo, origem_id=origem.id, status=StatusConta.ABERTA
        ):
            estados.transicionar(
                conta,
                StatusConta.CANCELADA,
                motivo=motivo,
                acao="conta_receber.cancelar",
                regra=regra,
            )
            canceladas += 1
    return canceladas


def marcar_paga(conta: ContaReceber, *, forma: str, pago_em: datetime | None = None) -> None:
    """Porta da baixa até a T-017 (caixa, Pix, cartão): grava o pagamento e publica
    `financeiro.parcela_paga` na mesma transação (ADR 0011)."""
    with transaction.atomic():
        travada = _travar(conta)
        travada.forma = forma
        travada.pago_em = pago_em or relogio.agora()
        estados.transicionar(
            travada,
            StatusConta.PAGA,
            acao="conta_receber.pagar",
            mais_campos=("forma", "pago_em"),
        )
        publicar(
            "financeiro.parcela_paga",
            parcela_id=travada.pk,
            cliente_id=travada.cliente_id,
            origem_tipo=travada.origem_tipo,
            origem_id=travada.origem_id,
            tipo=travada.tipo,
        )
    conta.refresh_from_db()
    conta._status_salvo = conta.status


# --- Comissões (FIN-09) ---


def lancar_comissao(
    origem: Origem, *, usuario_id: int, valor_centavos: int, regra: str = RegraComissao.FIXO_LOCACAO
) -> Comissao | None:
    """Comissão `pendente` da origem. Uma por origem e pessoa (sem contar as estornadas)."""
    if valor_centavos <= 0:
        return None
    with transaction.atomic():
        existente: Comissao | None = (
            Comissao.objects.filter(usuario_id=usuario_id, **origem.campos())
            .exclude(status=StatusComissao.ESTORNADA)
            .first()
        )
        if existente is not None:
            return existente
        comissao = Comissao(
            usuario_id=usuario_id,
            base_centavos=valor_centavos,
            regra=regra,
            valor_centavos=valor_centavos,
            **origem.campos(),
        )
        with auditar(comissao, "comissao.lancar", Categoria.FINANCEIRO, regra="FIN-09"):
            comissao.save()
    return comissao


def _mes_seguinte(dia: date) -> date:
    return date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)


def confirmar_comissao(origem: Origem) -> int:
    """`pendente` → `confirmada`, paga no dia 5 do mês seguinte (FIN-09)."""
    confirmadas = 0
    with transaction.atomic():
        for comissao in Comissao.objects.select_for_update().filter(
            origem_tipo=origem.tipo, origem_id=origem.id, status=StatusComissao.PENDENTE
        ):
            comissao.mes_pagamento = _mes_seguinte(relogio.hoje())
            estados.transicionar(
                comissao,
                StatusComissao.CONFIRMADA,
                acao="comissao.confirmar",
                regra="FIN-09",
                mais_campos=("mes_pagamento",),
            )
            confirmadas += 1
    return confirmadas
