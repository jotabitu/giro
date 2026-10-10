"""Regras das contas a receber, dos reembolsos e das comissões (FIN-01, FIN-09, DEV-02). Único
lugar que grava nestes models.

Interface para os outros apps (ADR 0011, `locacoes` e `vendas` chamam para baixo):
`criar_contas`, `ajustar_valor`, `cancelar_abertas`, `lancar_comissao`, `confirmar_comissao`,
`estornar_comissao`, `devolver_ao_cliente`, `pagar_com_caucao` e `marcar_paga`. Esta última é a
porta da baixa até a T-017 trazer o caixa e o Pix: grava o pagamento e publica
`financeiro.parcela_paga`, como a baixa de verdade vai publicar.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.db import transaction

from apps.filiais.models import Filial
from apps.filiais.selectors import gerentes
from apps.notificacoes.services import avisar
from comum import estados, relogio
from comum.auditoria import Categoria, auditar
from comum.dinheiro import formatar_reais
from comum.erros import Conflito, ErroDeValidacao
from comum.eventos import publicar

from . import selectors
from .models import (
    Comissao,
    ContaReceber,
    FormaPagamento,
    FormaReembolso,
    Reembolso,
    RegraComissao,
    Renegociacao,
    StatusComissao,
    StatusConta,
    StatusReembolso,
    TipoConta,
)


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
    nasceu_de_id: int | None = None  # a `Renegociacao` que a conta substitui


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
                nasceu_de_id=nova.nasceu_de_id,
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


def cancelar_abertas(
    origem: Origem, *, motivo: str, regra: str = "", vencendo_depois_de: date | None = None
) -> int:
    """As contas em aberto da origem vão para `cancelada`. As pagas ficam (estorno é T-017).
    Com `vencendo_depois_de`, só as parcelas que vencem depois desse dia (o encerramento
    antecipado, LOC-12)."""
    canceladas = 0
    contas = ContaReceber.objects.select_for_update().filter(
        origem_tipo=origem.tipo, origem_id=origem.id, status=StatusConta.ABERTA
    )
    if vencendo_depois_de is not None:
        contas = contas.filter(tipo="parcela", vencimento__gt=vencendo_depois_de)
    with transaction.atomic():
        for conta in contas:
            estados.transicionar(
                conta,
                StatusConta.CANCELADA,
                motivo=motivo,
                acao="conta_receber.cancelar",
                regra=regra,
            )
            canceladas += 1
    return canceladas


def cancelar_conta(conta_id: int, *, motivo: str, regra: str = "") -> bool:
    """Uma conta só vai para `cancelada`, se ainda está em aberto (ex.: a diferença de caução da
    troca cancelada, LOC-09). Paga fica como está. Devolve se cancelou."""
    with transaction.atomic():
        conta = ContaReceber.objects.select_for_update().filter(pk=conta_id).first()
        if conta is None or conta.status != StatusConta.ABERTA:
            return False
        estados.transicionar(
            conta,
            StatusConta.CANCELADA,
            motivo=motivo,
            acao="conta_receber.cancelar",
            regra=regra,
        )
    return True


def marcar_paga(
    conta: ContaReceber,
    *,
    forma: str,
    pago_em: datetime | None = None,
    devido: selectors.Devido | None = None,
) -> None:
    """Porta da baixa até a T-017 (caixa, Pix, cartão): grava o pagamento, com a multa e os
    juros de `devido` (FIN-03), e publica `financeiro.parcela_paga` na mesma transação
    (ADR 0011)."""
    with transaction.atomic():
        travada = _travar(conta)
        travada.forma = forma
        travada.pago_em = pago_em or relogio.agora()
        mais: tuple[str, ...] = ("forma", "pago_em")
        if devido is not None:
            travada.multa_centavos = devido.multa_centavos
            travada.juros_centavos = devido.juros_centavos
            mais = (*mais, "multa_centavos", "juros_centavos")
        estados.transicionar(
            travada,
            StatusConta.PAGA,
            acao="conta_receber.pagar",
            mais_campos=mais,
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


def estornar_comissao(origem: Origem, *, motivo: str) -> int:
    """`pendente` ou `confirmada` → `estornada`: locação cancelada antes da retirada (FIN-09).
    A paga não volta por aqui."""
    estornadas = 0
    with transaction.atomic():
        for comissao in Comissao.objects.select_for_update().filter(
            origem_tipo=origem.tipo,
            origem_id=origem.id,
            status__in=(StatusComissao.PENDENTE, StatusComissao.CONFIRMADA),
        ):
            estados.transicionar(
                comissao,
                StatusComissao.ESTORNADA,
                motivo=motivo,
                acao="comissao.estornar",
                regra="FIN-09",
            )
            estornadas += 1
    return estornadas


# --- Reembolsos (DEV-02: dinheiro que volta ao cliente) ---

# --- Acerto da devolução (DEV-02) ---


@dataclass(frozen=True)
class Cobranca:
    """Uma cobrança do acerto que ainda não é conta (combustível, avaria, atraso, multa)."""

    tipo: str
    valor_centavos: int
    observacao: str = ""


@dataclass(frozen=True)
class Acerto:
    pagas: list[ContaReceber]
    a_receber: ContaReceber | None


def pagar_com_caucao(
    origem: Origem,
    *,
    filial_id: int,
    cliente_id: int,
    disponivel_centavos: int,
    abertas: list[ContaReceber],
    cobrancas: list[Cobranca],
    dia: date,
    vencimento_do_saldo: date,
) -> Acerto:
    """DEV-02, na transação de quem chama. Com o que há da caução e dos créditos
    (`disponivel_centavos`), paga primeiro as parcelas em aberto, inteiras, da mais antiga para a
    mais nova, cada uma pelo devido em `dia` (FIN-03). Não existe pagamento parcial (FIN-01): a
    primeira que não cabe e todas as seguintes vão para `renegociada`, mesmo que uma seguinte
    coubesse. Depois, as cobranças viram contas pagas com a caução (`forma = caucao`), e o que
    sobrar abate as parcelas renegociadas. O que fica sem cobertura é uma conta só
    (`tipo = acerto`), com vencimento em `vencimento_do_saldo`, igual a `-saldo` do acerto."""
    restante = disponivel_centavos
    pagas: list[ContaReceber] = []
    renegociar: list[tuple[ContaReceber, selectors.Devido]] = []
    novas: list[NovaConta] = []
    a_cobrar = 0
    with transaction.atomic():
        for conta in sorted(abertas, key=lambda c: (c.vencimento, c.pk)):
            devido = selectors.devido_ate(conta, dia)
            if renegociar or devido.total_centavos > restante:
                renegociar.append((conta, devido))
                continue
            marcar_paga(conta, forma=FormaPagamento.CAUCAO, devido=devido)
            restante -= devido.total_centavos
            pagas.append(conta)
        for cobranca in cobrancas:
            coberto = min(restante, cobranca.valor_centavos)
            restante -= coberto
            a_cobrar += cobranca.valor_centavos - coberto
            novas.append(
                NovaConta(cobranca.tipo, relogio.hoje(), coberto, observacao=cobranca.observacao)
            )
        for conta in criar_contas(origem, filial_id=filial_id, cliente_id=cliente_id, contas=novas):
            marcar_paga(conta, forma=FormaPagamento.CAUCAO)
            pagas.append(conta)
        renegociacao = None
        if renegociar:
            # A primeira renegociada não coube no que sobrava: a sobra das cobranças abate a conta.
            a_cobrar += sum(d.total_centavos for _, d in renegociar) - restante
            renegociacao = _renegociar_no_acerto(origem, renegociar)
        saldo = criar_contas(
            origem,
            filial_id=filial_id,
            cliente_id=cliente_id,
            contas=[
                NovaConta(
                    TipoConta.ACERTO,
                    vencimento_do_saldo,
                    a_cobrar,
                    observacao="Saldo do acerto da devolução",
                    nasceu_de_id=renegociacao.pk if renegociacao else None,
                )
            ],
        )
    return Acerto(pagas=pagas, a_receber=saldo[0] if saldo else None)


def _renegociar_no_acerto(
    origem: Origem, parcelas: list[tuple[ContaReceber, selectors.Devido]]
) -> Renegociacao:
    """As parcelas que a caução não cobre vão para `renegociada`, com a multa e os juros do dia,
    ligadas à conta `acerto` pela `Renegociacao` (DEV-02)."""
    motivo = "Parcelas que a caução não cobriu no acerto da devolução"
    renegociacao = Renegociacao(motivo=motivo, em=relogio.agora(), **origem.campos())
    with auditar(renegociacao, "renegociacao.criar", Categoria.FINANCEIRO, regra="DEV-02"):
        renegociacao.save()
    for conta, devido in parcelas:
        travada = _travar(conta)
        travada.renegociada_em = renegociacao
        travada.multa_centavos = devido.multa_centavos
        travada.juros_centavos = devido.juros_centavos
        estados.transicionar(
            travada,
            StatusConta.RENEGOCIADA,
            motivo=motivo,
            acao="conta_receber.renegociar",
            regra="DEV-02",
            mais_campos=("renegociada_em", "multa_centavos", "juros_centavos"),
        )
        conta.refresh_from_db()
    return renegociacao


# O dinheiro sai pelo caixa do dia, que chega com a T-017.
FORMAS_SEM_CAIXA = (FormaReembolso.PIX, FormaReembolso.ESTORNO_CARTAO)


def devolver_ao_cliente(
    origem: Origem,
    *,
    filial_id: int,
    cliente_id: int,
    valor_centavos: int,
    forma: str,
    motivo: str = "",
    regra: str = "",
) -> Reembolso | None:
    """O `Reembolso` `a_fazer`, na transação de quem chama, e o aviso no sino dos gerentes da
    filial (decisão de 07 out 2026, item 21). Valor zero não gera reembolso."""
    if valor_centavos <= 0:
        return None
    if forma not in FORMAS_SEM_CAIXA:
        raise ErroDeValidacao(
            {"forma_devolucao": ["Devolva por Pix ou estorno no cartão. Dinheiro sai pelo caixa."]}
        )
    with transaction.atomic():
        reembolso = Reembolso(
            filial_id=filial_id,
            cliente_id=cliente_id,
            valor_centavos=valor_centavos,
            forma=forma,
            motivo=motivo[:200],
            **origem.campos(),
        )
        with auditar(reembolso, "reembolso.criar", Categoria.FINANCEIRO, regra=regra):
            reembolso.save()
        avisar(
            [g["id"] for g in gerentes(Filial.objects.get(pk=filial_id))],
            tipo="reembolso_a_fazer",
            titulo=(f"Devolver {formatar_reais(valor_centavos)} da {origem.codigo or origem.tipo}")[
                :200
            ],
            link="/financeiro/reembolsos",
            chave=f"reembolso-{reembolso.pk}",
        )
    return reembolso


def marcar_reembolso_feito(
    reembolso: Reembolso, *, usuario: Any, comprovante: Any = None
) -> Reembolso:
    """Quem fez o Pix (ou o estorno na maquininha) marca como feito, com o comprovante."""
    with transaction.atomic():
        travado: Reembolso = Reembolso.objects.select_for_update().get(pk=reembolso.pk)
        if travado.status != StatusReembolso.A_FAZER:
            raise Conflito("transicao_reembolso", "Este reembolso já foi feito.")
        travado.feito_em = relogio.agora()
        travado.feito_por = usuario
        mais: tuple[str, ...] = ("feito_em", "feito_por")
        if comprovante is not None:
            travado.comprovante.save(comprovante.name, comprovante, save=False)
            mais = (*mais, "comprovante")
        estados.transicionar(
            travado, StatusReembolso.FEITO, acao="reembolso.feito", mais_campos=mais
        )
    reembolso.refresh_from_db()
    return reembolso
