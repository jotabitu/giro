"""Regras das contas a receber, do caixa do dia, das despesas, dos reembolsos e das comissões
(FIN-01 a FIN-09, APR-03, APR-04, DEV-02, AUT-03, AUT-05, AUT-08). Único lugar que grava nestes
models.

Interface para os outros apps (ADR 0011, `locacoes`, `vistorias` e `vendas` chamam para baixo):
`criar_contas`, `ajustar_valor`, `cancelar_abertas`, `cancelar_conta`, `lancar_comissao`,
`confirmar_comissao`, `estornar_comissao`, `devolver_ao_cliente` (dinheiro sai pelo caixa),
`pagar_com_caucao` e `marcar_paga` (baixa sem caixa nem parceiro: a caução e o seed).

Toda baixa passa por `_baixar`: grava a forma, a hora, a multa e os juros (FIN-03) e publica
`financeiro.parcela_paga`. As portas são o caixa (`receber`, FIN-04), o webhook do parceiro
(`processar_webhook`, AUT-05) e a caução do acerto (`pagar_com_caucao`, DEV-02).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from email.headerregistry import Address
from email.utils import parseaddr
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.filiais.models import Filial
from apps.filiais.selectors import gerentes
from apps.notificacoes.services import avisar
from apps.plataforma.models import ContaPagamento, StatusContaPagamento
from comum import aprovacoes, arquivos, estados, relogio
from comum.auditoria import Categoria, TipoAtor, ator_atual, auditar, registrar_evento
from comum.dinheiro import formatar_reais
from comum.empresa import nome_da_empresa
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, ParceiroForaDoAr
from comum.eventos import publicar
from comum.models import WebhookRecebido
from integracoes.pagamentos import provedor as provedor_de_pagamentos
from integracoes.pagamentos import referencia
from integracoes.pagamentos.base import (
    EventoWebhook,
    Pagador,
    ParceiroIndisponivel,
    ParceiroRecusou,
    PedidoCobranca,
    StatusDesconhecido,
    aviso_sem_cartao,
)
from integracoes.whatsapp import enviar_whatsapp

from . import selectors
from .models import (
    Caixa,
    CategoriaDespesa,
    CobrancaExterna,
    Comissao,
    ContaReceber,
    Despesa,
    FormaDespesa,
    FormaMovimento,
    FormaPagamento,
    FormaReembolso,
    MotivoPendencia,
    MovimentoCaixa,
    OrigemTipo,
    PendenciaPagamento,
    Reembolso,
    RegraComissao,
    Renegociacao,
    StatusCaixa,
    StatusCobranca,
    StatusComissao,
    StatusConta,
    StatusDespesa,
    StatusPendencia,
    StatusReembolso,
    TipoCobranca,
    TipoConta,
    TipoMovimento,
    texto_de_busca,
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
    """Baixa sem caixa nem parceiro: o acerto da devolução (`forma = caucao`, DEV-02), a
    importação do seed e os testes. Grava o pagamento, com a multa e os juros de `devido`
    (FIN-03), e publica `financeiro.parcela_paga` na mesma transação (ADR 0011)."""
    with transaction.atomic():
        _baixar(_travar(conta), forma=forma, pago_em=pago_em, devido=devido)
    conta.refresh_from_db()
    conta._status_salvo = conta.status


def _baixar(
    travada: ContaReceber,
    *,
    forma: str,
    pago_em: datetime | None = None,
    devido: selectors.Devido | None = None,
    movimento: MovimentoCaixa | None = None,
    regra: str = "",
) -> None:
    """A baixa, única para todas as portas (caixa, webhook, caução): `aberta` → `paga`, com a
    forma, a hora, a multa e os juros gravados, e o evento `financeiro.parcela_paga`."""
    travada.forma = forma
    travada.pago_em = pago_em or relogio.agora()
    mais: tuple[str, ...] = ("forma", "pago_em")
    if devido is not None:
        travada.multa_centavos = devido.multa_centavos
        travada.juros_centavos = devido.juros_centavos
        mais = (*mais, "multa_centavos", "juros_centavos")
    if movimento is not None:
        travada.movimento_caixa = movimento
        mais = (*mais, "movimento_caixa")
    estados.transicionar(
        travada, StatusConta.PAGA, acao="conta_receber.pagar", regra=regra, mais_campos=mais
    )
    publicar(
        "financeiro.parcela_paga",
        parcela_id=travada.pk,
        conta_id=travada.pk,
        cliente_id=travada.cliente_id,
        origem_tipo=travada.origem_tipo,
        origem_id=travada.origem_id,
        tipo=travada.tipo,
        valor_centavos=travada.valor_centavos,
        pago_em=travada.pago_em,
    )


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


MENSAGEM_DEVOLVER_SEM_CAIXA = "Abra o caixa do dia para devolver em dinheiro"


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
    """O `Reembolso`, na transação de quem chama (DEV-02). Valor zero não gera reembolso.

    - Dinheiro sai na hora pelo caixa aberto da filial (saída ligada à origem) e o reembolso
      nasce `feito`. Sem caixa aberto: 422 `FIN-07` (CA-016-18).
    - Pix e estorno no cartão nascem `a_fazer`, com o aviso no sino dos gerentes da filial
      (decisão de 07 out 2026, item 21)."""
    if valor_centavos <= 0:
        return None
    with transaction.atomic():
        reembolso = Reembolso(
            filial_id=filial_id,
            cliente_id=cliente_id,
            valor_centavos=valor_centavos,
            forma=forma,
            motivo=motivo[:200],
            **origem.campos(),
        )
        if forma == FormaReembolso.DINHEIRO:
            caixa = _caixa_aberto(filial_id, MENSAGEM_DEVOLVER_SEM_CAIXA)
            reembolso.movimento_caixa = _registrar_movimento(
                caixa,
                tipo=TipoMovimento.SAIDA,
                forma=FormaMovimento.DINHEIRO,
                valor_centavos=valor_centavos,
                descricao=(motivo or f"Devolução ao cliente · {origem.codigo}")[:150],
                usuario=_usuario_do_ator(),
                origem=origem,
            )
            reembolso.status = StatusReembolso.FEITO
            reembolso.feito_em = relogio.agora()
            reembolso.feito_por_id = _usuario_do_ator()
            with auditar(reembolso, "reembolso.criar", Categoria.FINANCEIRO, regra=regra):
                reembolso.save()
            return reembolso
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


# --- Quem age ---


def _usuario_do_ator() -> int | None:
    """O id da pessoa que age agora, ou `None` quando é o Sistema (webhook, tarefas)."""
    ator = ator_atual()
    return ator.id if ator.tipo == TipoAtor.USUARIO else None


def _id(usuario: Any) -> int | None:
    pk = getattr(usuario, "pk", None)
    return int(pk) if pk is not None else None


# --- Caixa do dia (FIN-07, FIN-08, APR-04) ---

MENSAGEM_ABRA_O_CAIXA = "Abra o caixa do dia para receber"
MENSAGEM_JA_ABERTO = "O caixa de hoje desta filial já foi aberto"
MENSAGEM_JA_FECHADO = "Este caixa já foi fechado"


def caixa_ja_fechado() -> Conflito:
    return Conflito("FIN-07", MENSAGEM_JA_FECHADO)


def abrir_caixa(filial: Filial, usuario: Any, troco_centavos: int) -> Caixa:
    """FIN-07: um caixa por filial por dia, mesmo com duas chamadas ao mesmo tempo (restrição
    única `(filial, data)`)."""
    hoje = relogio.hoje()
    if Caixa.objects.filter(filial=filial, data=hoje).exists():
        raise Conflito("FIN-07", MENSAGEM_JA_ABERTO)
    try:
        with transaction.atomic():
            caixa = Caixa(
                filial=filial, data=hoje, aberto_por=usuario, troco_centavos=troco_centavos
            )
            with auditar(caixa, "caixa.abrir", Categoria.FINANCEIRO, regra="FIN-07"):
                caixa.save()
    except IntegrityError as erro:
        raise Conflito("FIN-07", MENSAGEM_JA_ABERTO) from erro
    return caixa


def _caixa_aberto(filial_id: int, mensagem: str = MENSAGEM_ABRA_O_CAIXA) -> Caixa:
    """O caixa `aberto` de hoje da filial, travado. Sem ele: 422 `FIN-07`."""
    caixa: Caixa | None = (
        Caixa.objects.select_for_update()
        .filter(filial_id=filial_id, data=relogio.hoje(), status=StatusCaixa.ABERTO)
        .first()
    )
    if caixa is None:
        raise ErroDeRegra("FIN-07", mensagem)
    return caixa


def _travar_caixa_aberto(caixa: Caixa) -> Caixa:
    travado: Caixa = Caixa.objects.select_for_update().get(pk=caixa.pk)
    if travado.status != StatusCaixa.ABERTO:
        raise caixa_ja_fechado()
    return travado


def _registrar_movimento(
    caixa: Caixa,
    *,
    tipo: str,
    forma: str,
    valor_centavos: int,
    descricao: str,
    usuario: int | None,
    origem: Origem | None = None,
    estorno_de: MovimentoCaixa | None = None,
) -> MovimentoCaixa:
    """Um movimento num caixa `aberto` (já travado por quem chama). Imutável depois de gravado."""
    if caixa.status != StatusCaixa.ABERTO:
        raise caixa_ja_fechado()
    movimento = MovimentoCaixa(
        caixa=caixa,
        tipo=tipo,
        forma=forma,
        valor_centavos=valor_centavos,
        descricao=descricao[:150],
        registrado_por_id=usuario,
        estorno_de=estorno_de,
        **(origem.campos() if origem is not None else {}),
    )
    acao = "movimento_caixa.estornar" if estorno_de is not None else f"movimento_caixa.{tipo}"
    with auditar(movimento, acao, Categoria.FINANCEIRO, regra="FIN-07", filial_id=caixa.filial_id):
        movimento.save()
    return movimento


def sangria(caixa: Caixa, usuario: Any, *, valor_centavos: int, descricao: str) -> MovimentoCaixa:
    """Dinheiro tirado da gaveta (ex.: depósito no banco). Não passa do que há na gaveta."""
    with transaction.atomic():
        travado = _travar_caixa_aberto(caixa)
        esperado = selectors.esperado_na_gaveta(travado)
        if valor_centavos > esperado:
            raise ErroDeRegra(
                "sangria_maior_que_gaveta",
                f"A gaveta tem {formatar_reais(esperado)}. A sangria não pode passar disso.",
                {"esperado_centavos": esperado},
            )
        return _registrar_movimento(
            travado,
            tipo=TipoMovimento.SANGRIA,
            forma=FormaMovimento.DINHEIRO,
            valor_centavos=valor_centavos,
            descricao=descricao,
            usuario=_id(usuario),
        )


def estornar_movimento(movimento: MovimentoCaixa, usuario: Any, *, motivo: str) -> MovimentoCaixa:
    """CA-017-17: o original não muda; nasce um movimento de estorno no caixa aberto de hoje da
    filial, apontando para ele, e o resumo do dia considera os dois."""
    with transaction.atomic():
        original: MovimentoCaixa = (
            MovimentoCaixa.objects.select_for_update().select_related("caixa").get(pk=movimento.pk)
        )
        if (
            original.estorno_de_id is not None
            or MovimentoCaixa.objects.filter(estorno_de=original).exists()
        ):
            raise Conflito("movimento_estornado", "Este movimento já foi estornado.")
        caixa = _caixa_aberto(original.caixa.filial_id, "Abra o caixa do dia para estornar")
        estorno = _registrar_movimento(
            caixa,
            tipo=original.tipo,
            forma=original.forma,
            valor_centavos=original.valor_centavos,
            descricao=f"Estorno: {original.descricao}",
            usuario=_id(usuario),
            origem=(
                Origem(original.origem_tipo, original.origem_id or 0, original.origem_codigo)
                if original.origem_tipo
                else None
            ),
            estorno_de=original,
        )
        registrar_evento(
            "movimento_caixa.estorno_motivo",
            Categoria.FINANCEIRO,
            objeto=estorno,
            motivo=motivo,
            regra="FIN-07",
            filial_id=caixa.filial_id,
        )
    return estorno


def fechar_caixa(
    caixa: Caixa, usuario: Any, *, contado_centavos: int, motivo_diferenca: str | None
) -> Caixa:
    """FIN-07 e APR-04. Contado igual ao esperado: `fechado`. Diferente (falta ou sobra): exige o
    motivo, vai para `aguardando_aprovacao` e nasce o pedido para os gerentes da filial."""
    motivo = (motivo_diferenca or "").strip()
    with transaction.atomic():
        travado: Caixa = Caixa.objects.select_for_update().select_related("filial").get(pk=caixa.pk)
        if travado.status != StatusCaixa.ABERTO:
            raise caixa_ja_fechado()
        esperado = selectors.esperado_na_gaveta(travado)
        diferenca = contado_centavos - esperado
        if diferenca != 0 and not motivo:
            raise ErroDeValidacao(
                {"motivo_diferenca": ["Conte de novo ou diga o motivo da diferença."]}
            )
        travado.contado_centavos = contado_centavos
        travado.esperado_centavos = esperado
        travado.diferenca_centavos = diferenca
        travado.motivo_diferenca = motivo[:200] if diferenca else ""
        travado.fechado_por = usuario
        travado.fechado_em = relogio.agora()
        campos = (
            "contado_centavos",
            "esperado_centavos",
            "diferenca_centavos",
            "motivo_diferenca",
            "fechado_por",
            "fechado_em",
        )
        if diferenca == 0:
            estados.transicionar(
                travado,
                StatusCaixa.FECHADO,
                acao="caixa.fechar",
                regra="FIN-07",
                mais_campos=campos,
            )
            return travado
        sentido = "falta" if diferenca < 0 else "sobra"
        pedido = aprovacoes.pedir(
            tipo="APR-04",
            origem_tipo="caixa",
            origem_id=travado.pk,
            origem_codigo=None,
            filial_id=travado.filial_id,
            solicitante=usuario,
            titulo=f"Diferença de {formatar_reais(abs(diferenca))} no caixa",
            detalhe=(
                f"{travado.filial.nome} · {travado.data:%d/%m} · {sentido} de "
                f"{formatar_reais(abs(diferenca))}"
            ),
            motivo=motivo,
            valor_centavos=abs(diferenca),
            dados={"diferenca_centavos": diferenca},
            resumo=aprovacoes.Resumo(  # T-201, "Resumo por tipo"
                [
                    ("Esperado", formatar_reais(esperado)),
                    ("Contado", formatar_reais(contado_centavos)),
                    ("Diferença", f"{sentido} de {formatar_reais(abs(diferenca))}"),
                ],
                "Aprovada, o caixa fecha com a diferença registrada.",
            ),
        )
        travado.pedido_aprovacao_id = pedido.id
        estados.transicionar(
            travado,
            StatusCaixa.AGUARDANDO_APROVACAO,
            motivo=motivo,
            acao="caixa.fechar_com_diferenca",
            regra="APR-04",
            mais_campos=(*campos, "pedido_aprovacao_id"),
        )
        avisar(
            [g["id"] for g in gerentes(travado.filial) if g["id"] != _id(usuario)],
            tipo="caixa_com_diferenca",
            titulo=(
                f"Caixa de {travado.data:%d/%m} com {sentido} de "
                f"{formatar_reais(abs(diferenca))}: {motivo}"
            )[:200],
            link="/aprovacoes",
            chave=f"caixa-diferenca-{travado.pk}-{pedido.id}",
        )
    return travado


def decidir_diferenca_do_caixa(caixa_id: int, status_pedido: str, motivo: str) -> None:
    """Volta do pedido APR-04 (assinante de `aprovacoes.pedido_decidido`). Aprovado: `fechado`
    com a diferença registrada. Recusado ou cancelado: volta a `aberto` para contar de novo."""
    with transaction.atomic():
        caixa: Caixa | None = Caixa.objects.select_for_update().filter(pk=caixa_id).first()
        if caixa is None or caixa.status != StatusCaixa.AGUARDANDO_APROVACAO:
            return
        if status_pedido == "aprovado":
            estados.transicionar(
                caixa, StatusCaixa.FECHADO, motivo=motivo, acao="caixa.fechar", regra="APR-04"
            )
            return
        caixa.contado_centavos = None
        caixa.esperado_centavos = None
        caixa.diferenca_centavos = None
        caixa.fechado_por = None
        caixa.fechado_em = None
        caixa.pedido_aprovacao_id = None
        estados.transicionar(
            caixa,
            StatusCaixa.ABERTO,
            motivo=motivo,
            acao="caixa.reabrir",
            regra="APR-04",
            mais_campos=(
                "contado_centavos",
                "esperado_centavos",
                "diferenca_centavos",
                "fechado_por",
                "fechado_em",
                "pedido_aprovacao_id",
            ),
        )


def fechar_caixas_sem_conferencia() -> int:
    """FIN-08 (AUT-08, 23:59 em `America/Sao_Paulo`): caixa ainda `aberto` de hoje ou de antes
    vai para `fechado_sem_conferencia`, sem contado nem diferença, e vira tarefa para os gerentes
    da filial. `aguardando_aprovacao` não é mexido. Idempotente."""
    fechados = 0
    for caixa_id in Caixa.objects.filter(
        status=StatusCaixa.ABERTO, data__lte=relogio.hoje()
    ).values_list("pk", flat=True):
        with transaction.atomic():
            caixa: Caixa = (
                Caixa.objects.select_for_update().select_related("filial").get(pk=caixa_id)
            )
            if caixa.status != StatusCaixa.ABERTO:
                continue
            caixa.esperado_centavos = selectors.esperado_na_gaveta(caixa)
            caixa.fechado_em = relogio.agora()
            estados.transicionar(
                caixa,
                StatusCaixa.FECHADO_SEM_CONFERENCIA,
                acao="caixa.fechar_sem_conferencia",
                regra="FIN-08",
                mais_campos=("esperado_centavos", "fechado_em"),
            )
            avisar(
                [g["id"] for g in gerentes(caixa.filial)],
                tipo="caixa_sem_conferencia",
                titulo=(
                    f"Confira o caixa de {caixa.data:%d/%m} da {caixa.filial.nome}: "
                    "fechou sem conferência"
                ),
                link=f"/financeiro/caixa/{caixa.pk}",
                urgente=True,
                chave=f"caixa-sem-conferencia-{caixa.pk}",
            )
            fechados += 1
    return fechados


# --- Baixa no caixa (FIN-01, FIN-03, FIN-04) ---


def descricao_da_conta(conta: ContaReceber) -> str:
    """ "Juliana Rocha · LOC-2836 · parcela 2 de 5", para o movimento do caixa e o recibo."""
    if conta.tipo == TipoConta.PARCELA and conta.numero_parcela:
        rotulo = f"parcela {conta.numero_parcela}"
        if conta.total_parcelas:
            rotulo += f" de {conta.total_parcelas}"
    else:
        rotulo = TipoConta(conta.tipo).label.lower()
    partes = [conta.cliente.nome, conta.origem_codigo, rotulo]
    return " · ".join(p for p in partes if p)[:150]


def conta_nao_esta_aberta(conta: ContaReceber) -> Conflito:
    return Conflito(
        "transicao_conta",
        f"Esta conta está {StatusConta(conta.status).label.lower()}.",
        {"de": conta.status},
    )


def receber(
    conta: ContaReceber, usuario: Any, *, forma: str, valor_centavos: int, filial_id: int
) -> ContaReceber:
    """Baixa no caixa (FIN-04: dinheiro e cartão) pelo caixa aberto da filial da requisição, que
    pode ser outra filial que a da conta (FIL-06). O valor tem de ser o devido de hoje (FIN-03):
    não existe pagamento parcial (FIN-01)."""
    with transaction.atomic():
        travada = _travar(conta)
        if travada.status != StatusConta.ABERTA:
            raise conta_nao_esta_aberta(travada)
        devido = selectors.devido_ate(travada, relogio.hoje())
        if valor_centavos != devido.total_centavos:
            raise ErroDeRegra(
                "FIN-01",
                "Não existe pagamento parcial. Receba o valor inteiro ou renegocie.",
                {"valor_hoje_centavos": devido.total_centavos},
            )
        caixa = _caixa_aberto(filial_id)
        movimento = _registrar_movimento(
            caixa,
            tipo=TipoMovimento.ENTRADA,
            forma=forma,
            valor_centavos=devido.total_centavos,
            descricao=descricao_da_conta(travada),
            usuario=_id(usuario),
            origem=Origem(travada.origem_tipo, travada.origem_id, travada.origem_codigo),
        )
        _baixar(travada, forma=forma, devido=devido, movimento=movimento, regra="FIN-04")
    conta.refresh_from_db()
    return conta


# --- Lançamento avulso, cancelar, renegociar e estornar (FIN-01) ---


def lancar_avulsa(
    *,
    filial_id: int,
    cliente_id: int,
    tipo: str,
    descricao: str,
    vencimento: date,
    valor_centavos: int,
    origem: Origem | None = None,
) -> ContaReceber:
    """ "Novo lançamento": multa, avaria ou outro. Parcelas e caução vêm das locações."""
    criadas = criar_contas(
        origem or Origem(OrigemTipo.CLIENTE, cliente_id),
        filial_id=filial_id,
        cliente_id=cliente_id,
        contas=[NovaConta(tipo, vencimento, valor_centavos, observacao=descricao[:150])],
    )
    return criadas[0]


def cancelar(conta: ContaReceber, *, motivo: str, regra: str = "") -> ContaReceber:
    """Só a conta em aberto vai para `cancelada` (FIN-01). Paga ou cancelada: 409."""
    with transaction.atomic():
        travada = _travar(conta)
        if travada.status != StatusConta.ABERTA:
            raise conta_nao_esta_aberta(travada)
        estados.transicionar(
            travada,
            StatusConta.CANCELADA,
            motivo=motivo,
            acao="conta_receber.cancelar",
            regra=regra or "FIN-01",
        )
    conta.refresh_from_db()
    return conta


@dataclass(frozen=True)
class ContaNova:
    vencimento: date
    valor_centavos: int


def renegociar(
    contas: list[ContaReceber], novas: list[ContaNova], *, motivo: str, usuario: Any
) -> list[ContaReceber]:
    """FIN-01: as originais vão para `renegociada`, ligadas por uma `Renegociacao` às novas
    (`aberta`), e saem do em aberto. A soma e os vencimentos das novas vêm do pedido."""
    with transaction.atomic():
        travadas = [_travar(c) for c in sorted(contas, key=lambda c: c.pk)]
        for travada in travadas:
            if travada.status != StatusConta.ABERTA:
                raise conta_nao_esta_aberta(travada)
        clientes = {t.cliente_id for t in travadas}
        if len(clientes) != 1:
            raise ErroDeValidacao({"contas": ["Renegocie as contas de um cliente por vez."]})
        primeira = travadas[0]
        origens = {(t.origem_tipo, t.origem_id) for t in travadas}
        origem = (
            Origem(primeira.origem_tipo, primeira.origem_id, primeira.origem_codigo)
            if len(origens) == 1
            else Origem(OrigemTipo.CLIENTE, primeira.cliente_id)
        )
        tipos = {t.tipo for t in travadas}
        tipo = primeira.tipo if len(tipos) == 1 else TipoConta.ACERTO
        renegociacao = Renegociacao(
            motivo=motivo[:200],
            por=usuario,
            em=relogio.agora(),
            origem_tipo=OrigemTipo.CLIENTE,
            origem_id=primeira.cliente_id,
        )
        with auditar(renegociacao, "renegociacao.criar", Categoria.FINANCEIRO, regra="FIN-01"):
            renegociacao.save()
        for travada in travadas:
            travada.renegociada_em = renegociacao
            estados.transicionar(
                travada,
                StatusConta.RENEGOCIADA,
                motivo=motivo,
                acao="conta_receber.renegociar",
                regra="FIN-01",
                mais_campos=("renegociada_em",),
            )
        return criar_contas(
            origem,
            filial_id=primeira.filial_id,
            cliente_id=primeira.cliente_id,
            contas=[
                NovaConta(
                    tipo,
                    nova.vencimento,
                    nova.valor_centavos,
                    numero_parcela=numero if len(novas) > 1 else None,
                    total_parcelas=len(novas) if len(novas) > 1 else None,
                    observacao="Renegociada",
                    nasceu_de_id=renegociacao.pk,
                )
                for numero, nova in enumerate(novas, start=1)
            ],
        )


def estornar(
    conta: ContaReceber, usuario: Any, *, motivo: str, filial_id: int | None
) -> ContaReceber:
    """CA-017-09: conta paga não se edita. A original continua `paga`, com `estornada_em`; nasce
    uma conta `aberta` igual (mesmo valor e vencimento), com `estorno_de`. Se a baixa foi no
    caixa, um movimento de estorno no caixa aberto de hoje. Devolve a conta nova."""
    with transaction.atomic():
        travada = _travar(conta)
        if travada.status != StatusConta.PAGA or travada.estornada_em is not None:
            raise Conflito(
                "transicao_conta",
                "Só uma conta paga e ainda não estornada pode ser estornada.",
                {"de": travada.status},
            )
        if travada.forma == FormaPagamento.CAUCAO:
            raise ErroDeRegra(
                "DEV-02", "A conta paga com a caução se corrige no acerto da devolução."
            )
        movimento = travada.movimento_caixa
        if (
            movimento is not None
            and not MovimentoCaixa.objects.filter(estorno_de=movimento).exists()
        ):
            caixa = _caixa_aberto(
                filial_id or movimento.caixa.filial_id, "Abra o caixa do dia para estornar"
            )
            _registrar_movimento(
                caixa,
                tipo=movimento.tipo,
                forma=movimento.forma,
                valor_centavos=movimento.valor_centavos,
                descricao=f"Estorno: {movimento.descricao}",
                usuario=_id(usuario),
                origem=Origem(travada.origem_tipo, travada.origem_id, travada.origem_codigo),
                estorno_de=movimento,
            )
        with auditar(
            travada, "conta_receber.estornar", Categoria.FINANCEIRO, motivo=motivo, regra="FIN-01"
        ):
            travada.estornada_em = relogio.agora()
            travada.save(update_fields=["estornada_em", "atualizado_em"])
        nova = ContaReceber(
            filial_id=travada.filial_id,
            cliente_id=travada.cliente_id,
            tipo=travada.tipo,
            numero_parcela=travada.numero_parcela,
            total_parcelas=travada.total_parcelas,
            vencimento=travada.vencimento,
            valor_centavos=travada.valor_centavos,
            observacao=travada.observacao,
            estorno_de=travada,
            origem_tipo=travada.origem_tipo,
            origem_id=travada.origem_id,
            origem_codigo=travada.origem_codigo,
        )
        with auditar(
            nova, "conta_receber.criar", Categoria.FINANCEIRO, motivo=motivo, regra="FIN-01"
        ):
            nova.save()
    conta.refresh_from_db()
    return nova


# --- Cobrança por Pix e boleto, webhook e pendências (FIN-04, AUT-05, S-14) ---


def conta_de_pagamento() -> ContaPagamento | None:
    """A subconta aprovada da empresa atual (`plataforma.ContaPagamento`)."""
    empresa_id = getattr(getattr(connection, "tenant", None), "pk", None)
    if empresa_id is None:
        return None
    conta: ContaPagamento | None = ContaPagamento.objects.filter(
        empresa_id=empresa_id, status=StatusContaPagamento.APROVADA
    ).first()
    return conta


def recebimentos_desligados() -> ErroDeRegra:
    return ErroDeRegra("recebimentos_desligados", "Conecte os recebimentos para gerar Pix e boleto")


def parceiro_fora_do_ar() -> ParceiroForaDoAr:
    """CA-029-16: o parceiro não respondeu; nada ficou gravado pela metade."""
    return ParceiroForaDoAr(
        "parceiro_indisponivel",
        "Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos.",
    )


def gerar_cobranca(
    conta: ContaReceber,
    *,
    tipo: str,
    vence_em: date | None = None,
    caixa_filial_id: int | None = None,
) -> CobrancaExterna:
    """Pix ou boleto do valor de hoje (FIN-03). Gerar outra cancela a que está aberta no
    parceiro. Gerada pela tela `Caixa` (`caixa_filial_id`), guarda o caixa: a baixa pelo webhook
    entra como entrada nesse caixa (FIN-07). Parceiro fora do ar: 503 e nada gravado
    (CA-029-16)."""
    try:
        return _gerar_cobranca(conta, tipo=tipo, vence_em=vence_em, caixa_filial_id=caixa_filial_id)
    except ParceiroIndisponivel as erro:
        raise parceiro_fora_do_ar() from erro
    except ParceiroRecusou as erro:
        raise ErroDeRegra("parceiro_recusou", erro.mensagem) from erro


def _gerar_cobranca(
    conta: ContaReceber,
    *,
    tipo: str,
    vence_em: date | None,
    caixa_filial_id: int | None,
) -> CobrancaExterna:
    subconta = conta_de_pagamento()
    if subconta is None:
        raise recebimentos_desligados()
    ref = referencia(subconta)
    parceiro = provedor_de_pagamentos()
    hoje = relogio.hoje()
    with transaction.atomic():
        travada = _travar(conta)
        if travada.status != StatusConta.ABERTA:
            raise conta_nao_esta_aberta(travada)
        caixa = _caixa_aberto(caixa_filial_id) if caixa_filial_id is not None else None
        for aberta in CobrancaExterna.objects.select_for_update().filter(
            conta_receber=travada, status=StatusCobranca.AGUARDANDO
        ):
            parceiro.cancelar_cobranca(ref, aberta.externo_id)
            estados.transicionar(
                aberta, StatusCobranca.CANCELADA, acao="cobranca.cancelar", regra="FIN-04"
            )
        valor = selectors.devido_ate(travada, hoje).total_centavos
        vencimento = (
            hoje if tipo == TipoCobranca.PIX else (vence_em or max(travada.vencimento, hoje))
        )
        cliente = travada.cliente
        gerada = parceiro.criar_cobranca(
            ref,
            PedidoCobranca(
                tipo=tipo,
                valor_centavos=valor,
                vencimento=vencimento,
                referencia_externa=str(travada.pk),
                pagador=Pagador(
                    cliente.nome, cliente.documento_claro(), cliente.celular, cliente.email
                ),
            ),
        )
        cobranca = CobrancaExterna(
            conta_receber=travada,
            tipo=tipo,
            externo_id=gerada.id,
            valor_centavos=valor,
            vence_em=vencimento,
            gerada_no_dia=hoje,
            pix_copia_e_cola=gerada.pix_copia_e_cola,
            linha_digitavel=gerada.linha_digitavel,
            url=gerada.qr_code_url if tipo == TipoCobranca.PIX else gerada.boleto_url,
            caixa=caixa,
        )
        with auditar(cobranca, f"cobranca.{tipo}", Categoria.FINANCEIRO, regra="FIN-04"):
            cobranca.save()
    return cobranca


def registrar_webhook(evento: EventoWebhook, corpo: dict[str, Any]) -> WebhookRecebido | None:
    """Grava o aviso no schema da empresa. O mesmo `evento_id` de novo: `None`, e nada acontece
    (CA-017-07)."""
    try:
        with transaction.atomic():
            return WebhookRecebido.objects.create(
                provedor=evento.provedor,
                evento_id=evento.evento_id,
                recebido_em=relogio.agora(),
                corpo={
                    "evento": {
                        "tipo": evento.tipo,
                        "cobranca_id": evento.cobranca_id,
                        "referencia_externa": evento.referencia_externa,
                    },
                    "bruto": aviso_sem_cartao(corpo),  # ADR 0023, M-01 da T-189
                },
            )
    except IntegrityError:
        return None


def _avisar_financeiro(titulo: str, chave: str) -> None:
    pessoas = get_user_model().objects.filter(
        perfil__in=("administrador", "financeiro"), status="ativo"
    )
    avisar(
        list(pessoas.values_list("pk", flat=True)),
        tipo="pendencia_pagamento",
        titulo=titulo[:200],
        link="/financeiro/pendencias",
        urgente=True,
        chave=chave,
    )


def _pendencia(
    cobranca: CobrancaExterna, motivo: str, valor_pago_centavos: int | None
) -> PendenciaPagamento:
    pendencia = PendenciaPagamento(
        cobranca=cobranca, motivo=motivo, valor_pago_centavos=valor_pago_centavos
    )
    with auditar(pendencia, "pendencia_pagamento.criar", Categoria.FINANCEIRO, regra="AUT-05"):
        pendencia.save()
    conta = cobranca.conta_receber
    _avisar_financeiro(
        f"Pagamento para conferir: {MotivoPendencia(motivo).label.lower()} "
        f"({conta.cliente.nome}, {conta.origem_codigo or 'conta ' + str(conta.pk)})",
        f"pendencia-{pendencia.pk}",
    )
    return pendencia


FORMAS_NO_RECIBO: dict[str, str] = {
    FormaPagamento.PIX: "por Pix",
    FormaPagamento.BOLETO: "por boleto",
    FormaPagamento.PIX_AUTOMATICO: "pelo Pix automático",
    FormaPagamento.CARTAO_CREDITO: "no cartão de crédito",
    FormaPagamento.CARTAO_DEBITO: "no cartão de débito",
    FormaPagamento.DINHEIRO: "em dinheiro",
}


def texto_do_recibo(conta: ContaReceber) -> str:
    """AUT-05: o total pago (principal, multa e juros), a forma e o dia do pagamento em
    `America/Sao_Paulo`, com a marca da locadora (`docs/api/financeiro.md`, "Régua de cobrança:
    textos")."""
    total = conta.valor_centavos + conta.multa_centavos + conta.juros_centavos
    forma = FORMAS_NO_RECIBO.get(conta.forma)
    pago_em = timezone.localdate(conta.pago_em) if conta.pago_em else relogio.hoje()
    como = f" {forma}" if forma else ""
    return (
        f"{nome_da_empresa()}: recebemos {formatar_reais(total)}{como} em {pago_em:%d/%m}, "
        f"da {conta_no_texto(conta)}. Este é o seu recibo."
    )


def _enviar_recibo(conta: ContaReceber) -> None:
    """AUT-05: o recibo pelo WhatsApp, com a marca da locadora (o e-mail é só da régua)."""
    if not conta.cliente.celular:
        return
    enviar_whatsapp(conta.cliente.celular, texto_do_recibo(conta))


def processar_webhook(webhook_id: int) -> str:
    """AUT-05. Não confia no corpo: consulta a cobrança no parceiro. Paga com o valor da
    cobrança: baixa (forma pix ou boleto), entra no caixa se foi gerada nele, publica
    `financeiro.parcela_paga` e manda o recibo. Valor diferente, conta que não está mais em
    aberto ou estorno no parceiro: pendência para o financeiro, nunca baixa nem reabre sozinho.
    Idempotente: o webhook já processado não faz nada."""
    with transaction.atomic():
        webhook: WebhookRecebido = WebhookRecebido.objects.select_for_update().get(pk=webhook_id)
        if webhook.processado_em is not None:
            return webhook.resultado
        resultado = _processar(webhook)
        webhook.processado_em = relogio.agora()
        webhook.resultado = resultado
        webhook.save(update_fields=["processado_em", "resultado"])
    return resultado


def _processar(webhook: WebhookRecebido) -> str:
    cobranca_id = str(webhook.corpo.get("evento", {}).get("cobranca_id", ""))
    cobranca: CobrancaExterna | None = (
        CobrancaExterna.objects.select_for_update(of=("self",))
        .select_related("conta_receber__cliente", "caixa")
        .filter(externo_id=cobranca_id)
        .first()
    )
    if cobranca is None:
        return "cobranca_desconhecida"
    subconta = conta_de_pagamento()
    if subconta is None:
        return "recebimentos_desligados"
    try:
        situacao = provedor_de_pagamentos().consultar_cobranca(
            referencia(subconta), cobranca.externo_id
        )
    except StatusDesconhecido:
        # CA-029-08: o financeiro confere no parceiro; nunca vira baixa.
        conta = cobranca.conta_receber
        _avisar_financeiro(
            f"Pagamento para conferir: o parceiro mandou uma situação que o sistema não conhece "
            f"({conta.cliente.nome}, {conta.origem_codigo or 'conta ' + str(conta.pk)})",
            f"webhook-{webhook.pk}",
        )
        return "status_desconhecido"
    if situacao.status == "estornada":
        _pendencia(cobranca, MotivoPendencia.ESTORNADA_NO_PARCEIRO, situacao.valor_pago_centavos)
        return "estornada_no_parceiro"
    if situacao.status != "paga":
        return situacao.status
    if cobranca.status == StatusCobranca.PAGA:
        return "ja_baixada"
    conta = _travar(cobranca.conta_receber)
    if situacao.valor_pago_centavos != cobranca.valor_centavos:
        if cobranca.status == StatusCobranca.AGUARDANDO:
            estados.transicionar(
                cobranca, StatusCobranca.DIVERGENTE, acao="cobranca.divergente", regra="AUT-05"
            )
        _pendencia(cobranca, MotivoPendencia.VALOR_DIFERENTE, situacao.valor_pago_centavos)
        return "valor_diferente"
    if conta.status != StatusConta.ABERTA:
        _pendencia(cobranca, MotivoPendencia.SEM_CONTA, situacao.valor_pago_centavos)
        return "conta_nao_aberta"
    forma = situacao.forma or cobranca.tipo
    movimento = None
    caixa = cobranca.caixa
    if caixa is not None and forma == FormaMovimento.PIX:
        travado = Caixa.objects.select_for_update().get(pk=caixa.pk)
        if travado.status == StatusCaixa.ABERTO:
            movimento = _registrar_movimento(
                travado,
                tipo=TipoMovimento.ENTRADA,
                forma=FormaMovimento.PIX,
                valor_centavos=cobranca.valor_centavos,
                descricao=descricao_da_conta(conta),
                usuario=None,
                origem=Origem(conta.origem_tipo, conta.origem_id, conta.origem_codigo),
            )
    # A multa e os juros são os do dia em que a cobrança foi gerada: é o valor que foi pago.
    devido = selectors.devido_ate(conta, cobranca.dia_da_geracao())
    if cobranca.status == StatusCobranca.AGUARDANDO:
        estados.transicionar(cobranca, StatusCobranca.PAGA, acao="cobranca.paga", regra="AUT-05")
    _baixar(
        conta,
        forma=forma,
        pago_em=situacao.pago_em,
        devido=devido,
        movimento=movimento,
        regra="AUT-05",
    )
    _enviar_recibo(conta)
    return "baixada"


def resolver_pendencia(
    pendencia: PendenciaPagamento, *, acao: str, motivo: str
) -> PendenciaPagamento:
    """O financeiro decide: `baixar` (a conta é baixada pela forma da cobrança, com o valor do
    parceiro) ou `ignorar`. As duas encerram a pendência, com o motivo."""
    with transaction.atomic():
        travada: PendenciaPagamento = (
            PendenciaPagamento.objects.select_for_update(of=("self",))
            .select_related("cobranca__conta_receber")
            .get(pk=pendencia.pk)
        )
        if travada.status != StatusPendencia.ABERTA:
            raise Conflito("transicao_pendencia", "Esta pendência já foi resolvida.")
        if acao == "baixar":
            conta = _travar(travada.cobranca.conta_receber)
            if conta.status != StatusConta.ABERTA:
                raise conta_nao_esta_aberta(conta)
            devido = selectors.devido_ate(conta, travada.cobranca.dia_da_geracao())
            _baixar(conta, forma=travada.cobranca.tipo, devido=devido, regra="AUT-05")
        travada.resolucao = f"{acao}: {motivo}"[:200]
        estados.transicionar(
            travada,
            StatusPendencia.RESOLVIDA,
            motivo=motivo,
            acao=f"pendencia_pagamento.{acao}",
            regra="AUT-05",
            mais_campos=("resolucao",),
        )
    return travada


# --- Cobrança pelo WhatsApp e por e-mail, e a régua (AUT-03) ---


def _ja_cobrada_hoje(conta: ContaReceber) -> bool:
    inicio = datetime.combine(relogio.hoje(), time.min, tzinfo=timezone.get_current_timezone())
    return EventoAuditoria.objects.filter(
        objeto_tipo="contareceber",
        objeto_id=conta.pk,
        acao="conta_receber.cobrar",
        ocorrido_em__gte=inicio,
    ).exists()


ORIGENS_NO_TEXTO: dict[str, str] = {OrigemTipo.LOCACAO: "locação", OrigemTipo.VENDA: "venda"}


def conta_no_texto(conta: ContaReceber) -> str:
    """A conta pelo tipo, com a origem por extenso: "parcela 2 de 5 da locação LOC-2841",
    "cobrança de acerto da locação LOC-2841", "cobrança da locação LOC-2841" (AUT-03)."""
    if conta.tipo == TipoConta.PARCELA:
        rotulo = "parcela"
        if conta.numero_parcela:
            rotulo += f" {conta.numero_parcela}"
            if conta.total_parcelas:
                rotulo += f" de {conta.total_parcelas}"
    elif conta.tipo == TipoConta.OUTRO:
        rotulo = "cobrança"
    else:
        rotulo = f"cobrança de {TipoConta(conta.tipo).label.lower()}"
    origem = ORIGENS_NO_TEXTO.get(conta.origem_tipo)
    if origem and conta.origem_codigo:
        rotulo += f" da {origem} {conta.origem_codigo}"
    return rotulo


@dataclass(frozen=True)
class MensagemDeCobranca:
    assunto: str
    texto: str


def mensagem_de_cobranca(conta: ContaReceber, *, pix: str | None) -> MensagemDeCobranca:
    """O texto do momento (`docs/api/financeiro.md`, "Régua de cobrança: textos"): antes do
    vencimento, o lembrete sem Pix; no dia e em atraso, com o Pix (`pix`), ou a loja quando os
    recebimentos estão desligados (`None`). O valor é o do dia (FIN-03)."""
    hoje = relogio.hoje()
    marca = nome_da_empresa()
    devido = selectors.devido_ate(conta, hoje)
    valor = formatar_reais(devido.total_centavos)
    descrita = conta_no_texto(conta)  # "a parcela...", no começo da frase com maiúscula
    inicio = f"{marca}: olá, {conta.cliente.nome.split()[0]}. A {descrita}"
    if pix:
        pague = f" Pague pelo Pix copia e cola: {pix}"
    else:
        pague = " Pague na loja ou fale com a gente por aqui."
    if conta.vencimento > hoje:
        if conta.vencimento == hoje + timedelta(days=1):
            quando = f"amanhã, {conta.vencimento:%d/%m}"
        else:
            quando = f"em {conta.vencimento:%d/%m}"
        return MensagemDeCobranca(
            f"{marca}: lembrete de vencimento", f"{inicio}, de {valor}, vence {quando}."
        )
    if conta.vencimento == hoje:
        return MensagemDeCobranca(
            f"{marca}: vence hoje", f"{inicio}, de {valor}, vence hoje.{pague}"
        )
    if devido.multa_centavos or devido.juros_centavos:
        valor_do_dia = f"O valor hoje é {valor}, com multa e juros."
    else:
        valor_do_dia = f"O valor é {valor}."
    return MensagemDeCobranca(
        f"{marca}: conta em atraso",
        f"{inicio} venceu em {conta.vencimento:%d/%m}. {valor_do_dia}{pague}",
    )


def _remetente() -> str:
    """O endereço de `DEFAULT_FROM_EMAIL` com o nome da locadora (AUT-03)."""
    _, endereco = parseaddr(settings.DEFAULT_FROM_EMAIL)
    return str(Address(display_name=nome_da_empresa(), addr_spec=endereco))


def cobrar(conta: ContaReceber) -> bool:
    """A mensagem de cobrança do momento, com a marca da locadora (AUT-03): pelo WhatsApp
    quando o cliente tem celular e por e-mail quando tem e-mail, com o mesmo texto. No dia e em
    atraso, gera o Pix do valor do dia quando os recebimentos estão ligados. Uma vez por conta
    por dia, contando os dois canais; devolve se cobrou (sem celular e sem e-mail, não)."""
    cliente = conta.cliente
    if conta.status != StatusConta.ABERTA or not (cliente.celular or cliente.email):
        return False
    if _ja_cobrada_hoje(conta):
        return False
    pix = None
    if conta.vencimento <= relogio.hoje() and conta_de_pagamento() is not None:
        try:
            pix = gerar_cobranca(conta, tipo=TipoCobranca.PIX).pix_copia_e_cola
        except (ParceiroForaDoAr, ErroDeRegra):
            pix = None  # a mensagem sai sem o Pix; a régua não para por um cliente
    mensagem = mensagem_de_cobranca(conta, pix=pix)
    if cliente.celular:
        enviar_whatsapp(cliente.celular, mensagem.texto)
    if cliente.email:
        send_mail(
            subject=mensagem.assunto,
            message=mensagem.texto,
            from_email=_remetente(),
            recipient_list=[cliente.email],
        )
    registrar_evento("conta_receber.cobrar", Categoria.FINANCEIRO, objeto=conta, regra="AUT-03")
    return True


DIAS_PARA_BLOQUEIO = 15  # CLI-05
DIAS_QUE_PUBLICAM_ATRASO = (1, 3, 7)
DIAS_DA_REGUA = (-1, 0, 3, 7)  # D-1 lembrete, D0 com Pix, D+3 e D+7 nova cobrança


def pedir_bloqueio(conta: ContaReceber, dias_atraso: int) -> bool:
    """CLI-05, AUT-03: publica `financeiro.parcela_atrasou` com os dias de hoje e grava o dia do
    pedido, uma vez por conta. Depois do desbloqueio manual, esta conta não bloqueia de novo.
    Devolve se publicou."""
    marcadas = ContaReceber.objects.filter(pk=conta.pk, bloqueio_pedido_em__isnull=True).update(
        bloqueio_pedido_em=relogio.hoje()
    )
    if not marcadas:
        return False
    _publicar_atraso(conta, dias_atraso)
    return True


def _publicar_atraso(conta: ContaReceber, dias: int) -> None:
    publicar(
        "financeiro.parcela_atrasou",
        conta_id=conta.pk,
        cliente_id=conta.cliente_id,
        tipo=conta.tipo,
        origem_tipo=conta.origem_tipo,
        origem_id=conta.origem_id,
        vencimento=conta.vencimento,
        dias_atraso=dias,
    )


def regua_de_cobranca() -> int:
    """AUT-03, às 09:00: cobra em D-1, D0, D+3 e D+7 (WhatsApp e e-mail) e publica
    `financeiro.parcela_atrasou` para cada conta que completou 1, 3 ou 7 dias de atraso. Com 15
    dias ou mais, pede o bloqueio do CLI-05 uma vez por conta: se a tarefa não rodou no 15º dia,
    o pedido sai na próxima vez. A caução não entra. Devolve quantos eventos publicou."""
    hoje = relogio.hoje()
    publicados = 0
    contas = (
        ContaReceber.objects.select_related("cliente")
        .filter(status=StatusConta.ABERTA, vencimento__lte=hoje + timedelta(days=1))
        .exclude(tipo=TipoConta.CAUCAO)
    )
    for conta in contas:
        dias = (hoje - conta.vencimento).days
        if dias in DIAS_DA_REGUA:
            cobrar(conta)
        if dias in DIAS_QUE_PUBLICAM_ATRASO:
            _publicar_atraso(conta, dias)
            publicados += 1
        elif dias >= DIAS_PARA_BLOQUEIO and pedir_bloqueio(conta, dias):
            publicados += 1
    return publicados


# --- Despesas (FIN-05, FIN-06, APR-03) ---

LIMITE_SEM_APROVACAO = 50000  # R$ 500,00 (FIN-05, APR-03)


def lancar_despesa(
    *,
    filial: Filial,
    usuario: Any,
    descricao: str,
    valor_centavos: int,
    data: date,
    vencimento: date,
    categoria: str,
    veiculo_id: int | None = None,
    nota: Any = None,
    pago_no_caixa: bool = False,
    origem: Origem | None = None,
) -> Despesa:
    """Até R$ 500 nasce `a_pagar` (ou `paga`, com a saída em dinheiro no caixa aberto); acima,
    `aguardando_aprovacao`, com o pedido APR-03 para o gerente, e não pode ser paga no caixa.
    A nota é obrigatória na rota (FIN-06); aqui aceita `None` para a despesa que nasce da OS ou
    da parada da movimentação, que vem com a `origem` (MOV-04, ADR 0028)."""
    acima = valor_centavos > LIMITE_SEM_APROVACAO
    if acima and pago_no_caixa:
        raise ErroDeRegra(
            "APR-03",
            "Despesa acima de R$ 500,00 precisa da aprovação do gerente antes de ser paga.",
        )
    with transaction.atomic():
        despesa = Despesa(
            filial=filial,
            data=data,
            descricao=descricao[:150],
            descricao_busca=texto_de_busca(descricao[:150]),
            categoria=categoria,
            valor_centavos=valor_centavos,
            vencimento=vencimento,
            veiculo_id=veiculo_id,
            lancada_por=usuario,
            status=StatusDespesa.AGUARDANDO_APROVACAO if acima else StatusDespesa.A_PAGAR,
            **(origem.campos() if origem is not None else {}),
        )
        if pago_no_caixa:
            caixa = _caixa_aberto(filial.pk, "Abra o caixa do dia para pagar por ele")
            despesa.status = StatusDespesa.PAGA
            despesa.forma = FormaDespesa.DINHEIRO
            despesa.pago_em = relogio.agora()
        with auditar(despesa, "despesa.lancar", Categoria.FINANCEIRO, regra="FIN-05"):
            despesa.save()
            if nota is not None:
                nota = arquivos.nota_limpa(nota)
                despesa.nota.save(nota.name, nota, save=False)
                despesa.save(update_fields=["nota"])
        if pago_no_caixa:
            despesa.movimento_caixa = _registrar_movimento(
                caixa,
                tipo=TipoMovimento.SAIDA,
                forma=FormaMovimento.DINHEIRO,
                valor_centavos=valor_centavos,
                descricao=descricao,
                usuario=_id(usuario),
                origem=Origem(OrigemTipo.DESPESA, despesa.pk),
            )
            despesa.save(update_fields=["movimento_caixa", "atualizado_em"])
        if acima:
            pedido = aprovacoes.pedir(
                tipo="APR-03",
                origem_tipo="despesa",
                origem_id=despesa.pk,
                origem_codigo=None,
                filial_id=filial.pk,
                solicitante=usuario,
                titulo=f"Despesa de {formatar_reais(valor_centavos)}",
                detalhe=f"{descricao} · {CategoriaDespesa(categoria).label}"[:300],
                valor_centavos=valor_centavos,
                resumo=_resumo_da_despesa(despesa),
            )
            despesa.pedido_aprovacao_id = pedido.id
            despesa.save(update_fields=["pedido_aprovacao_id", "atualizado_em"])
            avisar(
                [g["id"] for g in gerentes(filial) if g["id"] != _id(usuario)],
                tipo="despesa_para_aprovar",
                titulo=f"Aprovar despesa de {formatar_reais(valor_centavos)}: {descricao}"[:200],
                link="/aprovacoes",
                chave=f"despesa-{despesa.pk}",
            )
    return despesa


def _resumo_da_despesa(despesa: Despesa) -> aprovacoes.Resumo:
    """O cartão do APR-03 (T-201, T-235 opção A): categoria, descrição, veículo, valor e
    vencimento, sem fornecedor nem forma."""
    veiculo = despesa.veiculo
    return aprovacoes.Resumo(
        [
            ("Categoria", CategoriaDespesa(despesa.categoria).label),
            ("Descrição", despesa.descricao),
            (
                "Veículo",
                f"{veiculo.marca} {veiculo.modelo} · {veiculo.placa}"
                if veiculo is not None
                else "",
            ),
            ("Valor", formatar_reais(despesa.valor_centavos)),
            ("Vencimento", aprovacoes.dia_curto(despesa.vencimento)),
        ],
        "Acima de R$ 500 precisa de aprovação. Aprovada, vai para o financeiro pagar.",
    )


def decidir_despesa(despesa_id: int, status_pedido: str, motivo: str) -> None:
    """Volta do pedido APR-03: aprovado → `a_pagar`; recusado → `recusada`, e quem lançou é
    avisado. Cancelado por quem pediu: a despesa fica como está."""
    with transaction.atomic():
        despesa: Despesa | None = Despesa.objects.select_for_update().filter(pk=despesa_id).first()
        if despesa is None or despesa.status != StatusDespesa.AGUARDANDO_APROVACAO:
            return
        if status_pedido == "aprovado":
            estados.transicionar(
                despesa,
                StatusDespesa.A_PAGAR,
                motivo=motivo,
                acao="despesa.aprovar",
                regra="APR-03",
            )
            return
        if status_pedido != "recusado":
            return
        despesa.motivo_recusa = motivo[:300]
        estados.transicionar(
            despesa,
            StatusDespesa.RECUSADA,
            motivo=motivo,
            acao="despesa.recusar",
            regra="APR-03",
            mais_campos=("motivo_recusa",),
        )
        avisar(
            [despesa.lancada_por_id],
            tipo="despesa_recusada",
            titulo=f"Despesa recusada: {despesa.descricao}. {motivo}"[:200],
            link=f"/financeiro/despesas/{despesa.pk}",
        )


def anexar_nota(despesa: Despesa, nota: Any) -> Despesa:
    """A nota que faltou na parada da movimentação (MOV-04, CA-246-14), em qualquer status.
    Com nota já anexada, 409 `nota_existente`."""
    with transaction.atomic():
        travada: Despesa = Despesa.objects.select_for_update().get(pk=despesa.pk)
        if travada.nota:
            raise Conflito("nota_existente", "Esta despesa já tem a nota.")
        with auditar(travada, "despesa.anexar_nota", Categoria.FINANCEIRO, regra="FIN-06"):
            nota = arquivos.nota_limpa(nota)
            travada.nota.save(nota.name, nota, save=False)
            travada.save(update_fields=["nota", "atualizado_em"])
    return travada


def pagar_despesa(
    despesa: Despesa, usuario: Any, *, forma: str, pago_em: datetime, comprovante: Any = None
) -> Despesa:
    """Só `a_pagar`. Em dinheiro, sai do caixa aberto da filial da despesa."""
    with transaction.atomic():
        travada: Despesa = Despesa.objects.select_for_update().get(pk=despesa.pk)
        if travada.status != StatusDespesa.A_PAGAR:
            raise Conflito(
                "transicao_despesa",
                "Só uma despesa a pagar pode ser paga.",
                {"de": travada.status},
            )
        travada.forma = forma
        travada.pago_em = pago_em
        mais: tuple[str, ...] = ("forma", "pago_em")
        if forma == FormaDespesa.DINHEIRO:
            caixa = _caixa_aberto(travada.filial_id, "Abra o caixa do dia para pagar no caixa")
            travada.movimento_caixa = _registrar_movimento(
                caixa,
                tipo=TipoMovimento.SAIDA,
                forma=FormaMovimento.DINHEIRO,
                valor_centavos=travada.valor_centavos,
                descricao=travada.descricao,
                usuario=_id(usuario),
                origem=Origem(OrigemTipo.DESPESA, travada.pk),
            )
            mais = (*mais, "movimento_caixa")
        if comprovante is not None:
            travada.comprovante.save(comprovante.name, comprovante, save=False)
            mais = (*mais, "comprovante")
        estados.transicionar(
            travada, StatusDespesa.PAGA, acao="despesa.pagar", regra="FIN-05", mais_campos=mais
        )
    return travada
