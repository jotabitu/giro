"""Abrir, decidir e cancelar pedidos de aprovação (ADR 0019). Único lugar que grava
`PedidoAprovacao`.

Os outros apps abrem pedidos só por `comum.aprovacoes` (registrado no `ready()`). Toda decisão
publica `aprovacoes.pedido_decidido` na mesma transação, e o app da origem aplica o efeito pelo
próprio serviço (ADR 0011); se o efeito falha, a decisão volta.
"""

from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction

from comum import estados, relogio
from comum.aprovacoes import PedidoPendente, PedidoRef, Resumo
from comum.auditoria import Categoria, registrar_evento, retrato
from comum.erros import SemPermissao, TransicaoInvalida
from comum.eventos import publicar

from .models import PedidoAprovacao

S = PedidoAprovacao.Status


def ref(pedido: PedidoAprovacao) -> PedidoRef:
    return PedidoRef(id=pedido.pk, tipo=pedido.tipo, status=pedido.status)


def _pendente_igual(tipo: str, origem_tipo: str, origem_id: int) -> PedidoAprovacao | None:
    pedido: PedidoAprovacao | None = PedidoAprovacao.objects.filter(
        tipo=tipo, origem_tipo=origem_tipo, origem_id=origem_id, status=S.PENDENTE
    ).first()
    return pedido


def pedir(
    *,
    tipo: str,
    origem_tipo: str,
    origem_id: int,
    origem_codigo: str | None,
    filial_id: int,
    solicitante: Any,
    titulo: str,
    detalhe: str,
    motivo: str | None = None,
    valor_centavos: int | None = None,
    pct: Decimal | None = None,
    dados: dict[str, Any] | None = None,
    resumo: Resumo | None = None,
) -> PedidoRef:
    """Grava o pedido `pendente` e a auditoria (APR-10), na transação de quem chama.

    O aviso ao gerente (sino e push) entra com o app `notificacoes`.
    """
    with transaction.atomic():
        existente = _pendente_igual(tipo, origem_tipo, origem_id)
        if existente is not None:
            raise PedidoPendente(existente.pk)
        try:
            with transaction.atomic():
                pedido = PedidoAprovacao.objects.create(
                    tipo=tipo,
                    origem_tipo=origem_tipo,
                    origem_id=origem_id,
                    origem_codigo=origem_codigo or "",
                    filial_id=filial_id,
                    solicitante=solicitante,
                    titulo=titulo,
                    detalhe=detalhe,
                    motivo_pedido=(motivo or "")[:300],
                    valor_centavos=valor_centavos,
                    pct=pct,
                    dados=dados or {},
                    resumo=resumo.como_dict() if resumo is not None else {},
                )
        except IntegrityError as erro:  # o mesmo pedido numa corrida
            existente = _pendente_igual(tipo, origem_tipo, origem_id)
            if existente is None:
                raise
            raise PedidoPendente(existente.pk) from erro
        registrar_evento(
            "pedido_aprovacao.pedir",
            Categoria.OPERACAO,
            objeto=pedido,
            depois=retrato(pedido),
            motivo=motivo or "",
            regra="APR-10",
        )
    return ref(pedido)


def _publicar_decisao(pedido: PedidoAprovacao, decidido_por_id: int | None, motivo: str) -> None:
    publicar(
        "aprovacoes.pedido_decidido",
        pedido_id=pedido.pk,
        tipo=pedido.tipo,
        status=pedido.status,
        origem_tipo=pedido.origem_tipo,
        origem_id=pedido.origem_id,
        dados=pedido.dados,
        decidido_por_id=decidido_por_id,
        motivo=motivo,
        motivo_pedido=pedido.motivo_pedido,
        proprio_pedido=pedido.decidido_pelo_solicitante,
    )


def quem_pediu_nao_decide() -> SemPermissao:
    return SemPermissao("APR-09", "Outra pessoa precisa decidir este pedido")


def _travar_pendente(pedido: PedidoAprovacao) -> PedidoAprovacao:
    travado: PedidoAprovacao = PedidoAprovacao.objects.select_for_update().get(pk=pedido.pk)
    if travado.status != S.PENDENTE:
        rotulo = S(travado.status).label.lower()
        raise TransicaoInvalida(
            "transicao_pedido",
            f"Este pedido já foi {rotulo}",
            {"de": travado.status},
        )
    return travado


def _decidir(pedido: PedidoAprovacao, decisor: Any, novo: str, motivo: str) -> PedidoAprovacao:
    """Aprovar ou recusar: quem pediu não decide, salvo o administrador, com a marca (APR-09); a
    decisão entra na auditoria (APR-10) e o evento leva a origem a aplicar o efeito na mesma
    transação. O perfil é o de quem decide agora, não o de quando pediu."""
    with transaction.atomic():
        travado = _travar_pendente(pedido)
        proprio = travado.solicitante_id == decisor.pk
        if proprio and getattr(decisor, "perfil", "") != "administrador":
            raise quem_pediu_nao_decide()
        travado.aprovador = decisor
        travado.decidido_pelo_solicitante = proprio
        travado.decidido_em = relogio.agora()
        travado.motivo_recusa = motivo if novo == S.RECUSADO else ""
        acao = "aprovar" if novo == S.APROVADO else "recusar"
        estados.transicionar(
            travado,
            novo,
            motivo=motivo,
            acao=f"pedido_aprovacao.{acao}",
            regra="APR-10",
            mais_campos=(
                "aprovador",
                "decidido_em",
                "motivo_recusa",
                *(("decidido_pelo_solicitante",) if proprio else ()),
            ),
        )
        _publicar_decisao(travado, decisor.pk, motivo)
    return travado


def aprovar(pedido: PedidoAprovacao, decisor: Any, motivo: str = "") -> PedidoAprovacao:
    return _decidir(pedido, decisor, S.APROVADO, motivo.strip()[:300])


def recusar(pedido: PedidoAprovacao, decisor: Any, motivo: str) -> PedidoAprovacao:
    """Recusar exige motivo (APR-07); o serializer já recusa motivo vazio."""
    return _decidir(pedido, decisor, S.RECUSADO, motivo.strip()[:300])


def cancelar(pedido: PedidoAprovacao, solicitante: Any) -> PedidoAprovacao:
    """Quem pediu desiste. A origem volta ao estado anterior pelo evento."""
    with transaction.atomic():
        travado = _travar_pendente(pedido)
        if travado.solicitante_id != solicitante.pk:
            raise SemPermissao("so_quem_pediu", "Só quem fez o pedido pode cancelar")
        travado.decidido_em = relogio.agora()
        estados.transicionar(
            travado,
            S.CANCELADO,
            acao="pedido_aprovacao.cancelar",
            regra="APR-10",
            mais_campos=("decidido_em",),
        )
        _publicar_decisao(travado, solicitante.pk, "")
    return travado


def cancelar_pendentes(*, origem_tipo: str, origem_id: int, motivo: str) -> int:
    """A origem deixou de existir ou mudou: os pendentes ficam `cancelado` e publicam
    `aprovacoes.pedido_decidido`."""
    cancelados = 0
    with transaction.atomic():
        pedidos = PedidoAprovacao.objects.select_for_update().filter(
            origem_tipo=origem_tipo, origem_id=origem_id, status=S.PENDENTE
        )
        for pedido in pedidos:
            pedido.decidido_em = relogio.agora()
            estados.transicionar(
                pedido,
                S.CANCELADO,
                motivo=motivo,
                acao="pedido_aprovacao.cancelar",
                regra="APR-10",
                mais_campos=("decidido_em",),
            )
            _publicar_decisao(pedido, None, motivo)
            cancelados += 1
    return cancelados
