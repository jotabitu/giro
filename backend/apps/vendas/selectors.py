"""Consultas das vendas (`docs/api/vendas.md`): a lista e o detalhe das duas origens (`VEN-11` e o
fluxo de balcão da T-502, ADR 0042, item 14) e as leituras para os outros apps."""

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Count, QuerySet, Sum

from apps.clientes import selectors as clientes_selectors
from apps.clientes.models import StatusCliente
from apps.contratos import selectors as contratos_selectors
from apps.contratos.models import Contrato, StatusContrato
from apps.filiais import selectors as filiais_selectors
from apps.financeiro.models import Comissao, ContaReceber, StatusComissao, StatusConta
from comum import relogio
from comum.classificacao import mascarar_nome, mascarar_telefone
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen
from comum.permissoes import PERFIS_QUE_VEEM_TODAS, filiais_permitidas

from . import calculo, services
from .models import EM_ANDAMENTO, OrigemVenda, StatusVenda, Venda

RELACIONADOS = (
    "filial",
    "cliente",
    "veiculo",
    "vendedor",
    "locacao",
    "transferencia_registrada_por",
)
FUSO = ZoneInfo("America/Sao_Paulo")
ABAS = ("abertas", "minhas", "aguardando", "vendidas")
MES = re.compile(r"^(\d{4})-(\d{2})$")
# Onde a proposta ainda se edita, se envia e pede desconto (ADR 0042, item 5).
EDITAVEIS = (StatusVenda.INTERESSADO, StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO)


def base() -> QuerySet[Venda]:
    return Venda.objects.select_related(*RELACIONADOS)


def visiveis(usuario: Any) -> QuerySet[Venda]:
    """As vendas das filiais da pessoa; o vendedor vê só as dele (`USR-08`); o vistoriador,
    nenhuma (a rota responde 403 antes)."""
    perfil = getattr(usuario, "perfil", "")
    qs = base().filter(filial_id__in=filiais_permitidas(usuario))
    if perfil == "vendedor":
        qs = qs.filter(vendedor_id=usuario.pk)
    elif perfil not in (*PERFIS_QUE_VEEM_TODAS, "gerente"):
        qs = qs.none()
    return qs


def _limites_do_mes(texto: str) -> tuple[datetime, datetime] | None:
    achado = MES.match(texto or "")
    if achado is None:
        return None
    ano, mes = int(achado[1]), int(achado[2])
    if not 1 <= mes <= 12:
        return None
    inicio = datetime(ano, mes, 1, tzinfo=FUSO)
    fim = datetime(ano + mes // 12, mes % 12 + 1, 1, tzinfo=FUSO)
    return inicio, fim


def filtrar(usuario: Any, parametros: Any) -> QuerySet[Venda]:
    """Filtros da lista (ADR 0042, item 14): `status`, `aba`, `mes` (AAAA-MM; nas vendidas,
    pelo mês da venda, nas outras, pelo da criação), `filial`, e os da T-420."""
    qs = visiveis(usuario)
    if origem := parametros.get("origem"):
        qs = qs.filter(origem=origem)
    if parametros.get("transferencia_pendente") == "true":
        # VEN-11 e VEN-17: as duas origens, como o índice `venda_transferencia_pendente`.
        qs = qs.filter(status=StatusVenda.VENDIDA, transferencia_feita_em__isnull=True)
    for campo in ("veiculo", "cliente", "filial"):
        valor = parametros.get(campo)
        if valor and str(valor).isdigit():
            qs = qs.filter(**{f"{campo}_id": int(valor)})
    status = parametros.get("status")
    if status in StatusVenda.values:
        qs = qs.filter(status=status)
    aba = parametros.get("aba")
    if aba == "abertas":
        qs = qs.filter(status__in=EM_ANDAMENTO)
    elif aba == "minhas":
        qs = qs.filter(vendedor_id=getattr(usuario, "pk", None))
    elif aba == "aguardando":
        qs = qs.filter(status=StatusVenda.AGUARDANDO_APROVACAO)
    elif aba == "vendidas":
        qs = qs.filter(status=StatusVenda.VENDIDA)
    limites = _limites_do_mes(parametros.get("mes", ""))
    if limites is not None:
        inicio, fim = limites
        if aba == "vendidas" or status == StatusVenda.VENDIDA:
            qs = qs.filter(vendida_em__gte=inicio, vendida_em__lt=fim)
        else:
            qs = qs.filter(criado_em__gte=inicio, criado_em__lt=fim)
    return qs.order_by("-id")


def _pessoa(usuario: Any) -> dict[str, Any] | None:
    return {"id": usuario.pk, "nome": usuario.nome} if usuario is not None else None


def _transferencia(venda: Venda) -> dict[str, Any]:
    return {
        "feita_em": venda.transferencia_feita_em,
        "registrada_por": _pessoa(venda.transferencia_registrada_por),
        "pendente": services.transferencia_pendente(venda),
    }


def _cliente(venda: Venda) -> dict[str, Any] | None:
    if venda.cliente is None:
        return None
    return {"id": venda.cliente_id, "nome": venda.cliente.nome}


def _suporte(usuario: Any) -> bool:
    return bool(getattr(usuario, "e_suporte", False))


def _interessado(venda: Venda, usuario: Any) -> dict[str, Any] | None:
    """`VEN-14`: o interessado sem cadastro. O suporte vê mascarado (`AUD-09`)."""
    if venda.cliente is not None or not venda.interessado_nome:
        return None
    if _suporte(usuario):
        return {
            "nome": mascarar_nome(venda.interessado_nome),
            "celular": mascarar_telefone(venda.interessado_celular),
        }
    return {"nome": venda.interessado_nome, "celular": venda.interessado_celular}


def _comprador(venda: Venda, usuario: Any) -> str:
    nome = services.nome_do_comprador(venda)
    return mascarar_nome(nome) if venda.cliente is None and _suporte(usuario) else nome


def comissoes(vendas: Iterable[Venda]) -> dict[int, int]:
    """A comissão viva (não estornada) de cada venda, numa consulta (`FIN-09`)."""
    ids = [v.pk for v in vendas]
    linhas = (
        Comissao.objects.filter(origem_tipo=services.ORIGEM, origem_id__in=ids)
        .exclude(status=StatusComissao.ESTORNADA)
        .values_list("origem_id", "valor_centavos")
    )
    return {origem_id: valor for origem_id, valor in linhas}


def _calculo(venda: Venda) -> dict[str, Any] | None:
    if venda.origem != OrigemVenda.BALCAO or venda.preco_tabela_centavos is None:
        return None
    conta = services.calculo_da_venda(venda)
    return {
        "preco_tabela_centavos": conta.preco_tabela_centavos,
        "desconto_pct": conta.desconto_pct,
        "desconto_centavos": conta.desconto_centavos,
        "preco_final_centavos": conta.preco_final_centavos,
        "forma": conta.forma,
        "entrada_centavos": conta.entrada_centavos,
        "saldo_centavos": conta.saldo_centavos,
        "num_parcelas": conta.num_parcelas,
        "juros_pct": conta.juros_pct,
        "parcela_centavos": conta.parcela_centavos,
        "ultima_parcela_centavos": conta.ultima_parcela_centavos,
        "total_parcelas_centavos": conta.total_parcelas_centavos,
        "comissao_centavos": conta.comissao_centavos,
        "precisa_aprovacao": conta.precisa_aprovacao,
        "limite_desconto_pct": calculo.limite_efetivo(venda.desconto_aprovado_pct),
    }


def _aprovacao(venda: Venda) -> dict[str, Any] | None:
    if not venda.aprovacao:
        return None
    gerentes = [g["nome"] for g in filiais_selectors.gerentes(venda.filial)]
    return {
        "situacao": venda.aprovacao,
        "pedido_id": venda.pedido_aprovacao_id,
        "desconto_pedido_pct": venda.desconto_pedido_pct,
        "desconto_aprovado_pct": venda.desconto_aprovado_pct,
        "motivo_recusa": venda.motivo_recusa or None,
        "texto": services.textos_da_aprovacao(venda, gerentes),
    }


def _acoes(venda: Venda, usuario: Any) -> dict[str, bool]:
    mexe = services.pode_mexer(venda, usuario)
    edita = mexe and venda.contrato_id is None and venda.status in EDITAVEIS
    na_assinatura = mexe and venda.status in services.NA_ASSINATURA
    sem_assinatura = venda.contrato_assinado_em is None and venda.entrada_paga_em is None
    return {
        "editar": edita,
        "enviar": edita,
        "registrar_resposta": mexe and venda.status == StatusVenda.PROPOSTA,
        "pedir_aprovacao": edita,
        "perder": services.pode_perder(venda, usuario),
        # O cancelamento da venda de balcão é da fase 2; a da quitação nunca (VEN-11).
        "cancelar": False,
        "registrar_transferencia": services.pode_registrar_transferencia(venda, usuario),
        # Fase 1b (VEN-15, VEN-19): a etapa "Assinatura".
        "preparar_assinatura": na_assinatura and venda.contrato_id is None,
        "cancelar_assinatura": na_assinatura and venda.contrato_id is not None and sem_assinatura,
        "copiar_link_contrato": (
            na_assinatura
            and venda.contrato_assinado_em is None
            and contratos_selectors.pode_copiar_link(_contrato_vigente(venda))
        ),
        "reenviar_contrato": na_assinatura and venda.contrato_id is not None,
    }


def _contrato_vigente(venda: Venda) -> Contrato | None:
    """O contrato ligado à venda (vigente ou o cancelado da perdida), lido uma vez por objeto."""
    if venda.contrato_id is None:
        return None
    if not hasattr(venda, "_contrato_lido"):
        venda._contrato_lido = (  # type: ignore[attr-defined]
            Contrato.objects.select_related("modelo", "cliente")
            .filter(pk=venda.contrato_id)
            .first()
        )
    contrato: Contrato | None = venda._contrato_lido  # type: ignore[attr-defined]
    return contrato


SITUACAO_DO_CONTRATO = {
    StatusContrato.GERADO: "Contrato gerado",
    StatusContrato.ENVIADO: "Aguardando assinatura. O cliente assina pelo celular.",
    StatusContrato.ASSINADO: "Contrato assinado",
    StatusContrato.CANCELADO: "Contrato cancelado",
}


def _contrato(venda: Venda) -> dict[str, Any] | None:
    """O bloco `contrato` (VEN-15, VEN-19): o resumo de `contratos` e a situação pronta."""
    contrato = _contrato_vigente(venda)
    resumo = contratos_selectors.resumo(contrato)
    if contrato is None or resumo is None:
        return None
    texto = SITUACAO_DO_CONTRATO[StatusContrato(contrato.status)]
    if contrato.status == StatusContrato.CANCELADO and venda.status == StatusVenda.PERDIDA:
        texto = "Cancelado · venda perdida"
    return {**resumo, "situacao_texto": texto}


def _conta_entrada(venda: Venda) -> dict[str, Any] | None:
    """O bloco `conta_entrada` (VEN-15, VEN-19): "Aguardando pagamento · vence hoje"."""
    if venda.conta_entrada_id is None:
        return None
    conta: ContaReceber | None = ContaReceber.objects.filter(pk=venda.conta_entrada_id).first()
    if conta is None:
        return None
    if conta.status == StatusConta.PAGA and conta.pago_em is not None:
        dia = conta.pago_em.astimezone(ZoneInfo(venda.filial.fuso)).date()
        texto = f"Paga em {dia:%d/%m/%Y}"
    elif conta.status == StatusConta.CANCELADA:
        texto = "Cobrança cancelada"
    elif conta.vencimento == relogio.hoje():
        texto = "Aguardando pagamento · vence hoje"
    else:
        texto = f"Aguardando pagamento · venceu em {conta.vencimento:%d/%m/%Y}"
    return {
        "id": conta.pk,
        "status": conta.status,
        "valor_centavos": conta.valor_centavos,
        "vencimento": conta.vencimento,
        "texto": texto,
        "rotulo": f"Entrada de {formatar_reais(conta.valor_centavos)}",
    }


def _documentos(venda: Venda, usuario: Any) -> dict[str, Any] | None:
    """A etapa "Documentos" (VEN-14, VEN-19): o que falta no cadastro (`CLI-03`) e o cliente
    bloqueado ou inativo (`CLI-05`), com os textos prontos. Só antes de preparar a assinatura."""
    cliente = venda.cliente
    if (
        cliente is None
        or venda.status not in services.NA_ASSINATURA
        or venda.contrato_id is not None
    ):
        return None
    nome = cliente.nome
    pendencias = clientes_selectors.pendencias(cliente)
    gravidade, texto = "", ""
    if cliente.status == StatusCliente.BLOQUEADO:
        gravidade = "critica"
        texto = (
            f"{nome} está bloqueado e não pode comprar. A assinatura fica liberada depois do "
            "desbloqueio."
        )
        if getattr(usuario, "perfil", "") == "vendedor":
            texto += " Peça o desbloqueio ao gerente."
    elif cliente.status == StatusCliente.INATIVO:
        gravidade = "critica"
        texto = (
            f"{nome} está inativo e não pode comprar. O gerente ou o administrador reativa o "
            "cadastro."
        )
    elif pendencias:
        gravidade = "alerta"
        texto = f"Falta completar o cadastro de {nome} para preparar a assinatura."
    return {
        "pendencias": pendencias,
        "gravidade": gravidade or None,
        "texto": texto or None,
        "pode_preparar": not texto,
    }


def _texto_de_perder(venda: Venda, usuario: Any) -> str | None:
    """O diálogo "Marcar como perdida" (VEN-19)."""
    if venda.status not in EM_ANDAMENTO or not services.pode_mexer(venda, usuario):
        return None
    if venda.entrada_paga_em is None:
        return "A venda sai das abertas e o veículo fica livre para outra proposta."
    if not services.pode_perder(venda, usuario):
        return services.SO_GERENTE_PERDE
    valor = venda.entrada_centavos or 0
    return (
        f"A entrada de {formatar_reais(valor)} já foi paga. O valor vira um reembolso a fazer "
        "para o cliente."
    )


def _conclusao(venda: Venda, comissao_centavos: int | None) -> str | None:
    """ "Venda concluída. As 12 parcelas estão em Contas a receber, a comissão de R$ 632,04 foi
    lançada e o veículo saiu da frota de locação." (VEN-19, VEN-0177)."""
    if venda.origem != OrigemVenda.BALCAO or venda.status != StatusVenda.VENDIDA:
        return None
    partes = []
    if venda.forma == "entrada_parcelas" and venda.num_parcelas:
        partes.append(f"as {venda.num_parcelas} parcelas estão em Contas a receber")
    if comissao_centavos:
        partes.append(f"a comissão de {formatar_reais(comissao_centavos)} foi lançada")
    partes.append("o veículo saiu da frota de locação")
    frase = ", ".join(partes[:-1]) + (" e " if len(partes) > 1 else "") + partes[-1]
    return f"Venda concluída. {frase[:1].upper()}{frase[1:]}."


def representacao(
    venda: Venda, usuario: Any, comissao_centavos: int | None = None
) -> dict[str, Any]:
    """O item da lista de `docs/api/vendas.md`."""
    veiculo = venda.veiculo
    return {
        "id": venda.pk,
        "codigo": venda.codigo,
        "status": venda.status,
        "origem": venda.origem,
        "origem_rotulo": OrigemVenda(venda.origem).label,
        "descricao": venda.descricao,
        "cliente": _cliente(venda),
        "interessado": _interessado(venda, usuario),
        "comprador_nome": _comprador(venda, usuario),
        "veiculo": {
            "id": veiculo.pk,
            "placa": veiculo.placa,
            "modelo": f"{veiculo.marca} {veiculo.modelo}".strip(),
        },
        "filial": {"id": venda.filial_id, "nome": venda.filial.nome},
        "vendedor": _pessoa(venda.vendedor),
        "locacao": (
            {"id": venda.locacao_id, "codigo": venda.locacao.codigo} if venda.locacao else None
        ),
        "valor": venda.preco_final_centavos,
        "preco_final_centavos": venda.preco_final_centavos,
        "forma": venda.forma,
        "forma_texto": services.forma_texto(venda),
        "situacao_texto": services.situacao_texto(venda),
        "motivo_perda": venda.motivo_perda or None,
        "proposta_enviada_em": venda.proposta_enviada_em,
        "proposta_vence_em": services.vence_em(venda),
        "ultimo_contato_em": venda.ultimo_contato_em,
        "perdida_em": venda.perdida_em,
        "vendida_em": venda.vendida_em,
        "comissao_centavos": comissao_centavos,
        "transferencia": _transferencia(venda),
        "acoes": _acoes(venda, usuario),
    }


def detalhe(venda: Venda, usuario: Any) -> dict[str, Any]:
    """A venda inteira: o item da lista, o `calculo`, a `aprovacao` e, da fase 1b, o
    `contrato`, a `conta_entrada`, os `documentos` e os textos da etapa (ADR 0042, item 14)."""
    comissao = comissoes([venda]).get(venda.pk)
    return {
        **representacao(venda, usuario, comissao),
        "calculo": _calculo(venda),
        "aprovacao": _aprovacao(venda),
        "contrato": _contrato(venda),
        "conta_entrada": _conta_entrada(venda),
        "documentos": _documentos(venda, usuario),
        "perder_texto": _texto_de_perder(venda, usuario),
        "conclusao_texto": _conclusao(venda, comissao),
    }


# --- Interface interna (`vendas.md`) ---


def venda_da_quitacao(locacao_id: int) -> Venda | None:
    return base().filter(locacao_id=locacao_id).first()


def venda_da_locacao(locacao_id: int) -> dict[str, Any] | None:
    """O bloco `compra.venda` do detalhe da locação, sem as `acoes` (montadas por `locacoes`)."""
    venda = venda_da_quitacao(locacao_id)
    if venda is None:
        return None
    return {"id": venda.pk, "codigo": venda.codigo, "transferencia": _transferencia(venda)}


def _pendencia_da_transferencia(venda: Venda) -> dict[str, Any]:
    rotulo = f"Transferência no Detran · {placa_com_hifen(venda.veiculo.placa)}"
    dia = f"{services.data_da_quitacao(venda):%d/%m/%Y}"
    if venda.origem == OrigemVenda.QUITACAO_LOCACAO:
        return {
            "tipo": "transferencia_quitacao",
            "locacao_id": venda.locacao_id,
            "venda_id": venda.pk,
            "destino": {"chave": "locacoes", "id": venda.locacao_id},
            "rotulo": rotulo,
            "detalhe": (
                f"{services.nome_do_comprador(venda)} · "
                f"{venda.locacao.codigo if venda.locacao else ''} quitada em {dia}"
            ),
            "link": f"/locacoes/{venda.locacao_id}",
        }
    return {  # VEN-17 (T-502, fase 1b): a venda de balcão concluída
        "tipo": "transferencia_venda",
        "locacao_id": None,
        "venda_id": venda.pk,
        "destino": {"chave": "vendas", "id": venda.pk},
        "rotulo": rotulo,
        "detalhe": f"{services.nome_do_comprador(venda)} · {venda.codigo} vendida em {dia}",
        "link": f"/vendas/{venda.pk}",
    }


def transferencias_pendentes(filiais: Iterable[int]) -> list[dict[str, Any]]:
    """As vendas `vendida` sem transferência das filiais (a da quitação, `VEN-11`, e a de
    balcão, `VEN-17`), para as `pendencias.itens` do painel (`painel.md`, lido por
    `relatorios`). A mais antiga primeiro."""
    pendentes = base().filter(
        filial_id__in=list(filiais),
        status=StatusVenda.VENDIDA,
        transferencia_feita_em__isnull=True,
    )
    return [_pendencia_da_transferencia(v) for v in pendentes.order_by("vendida_em", "id")]


def vendas_do_veiculo(veiculo_id: int) -> list[dict[str, Any]]:
    """As vendas do veículo para o histórico da ficha (ADR 0015), a mais nova primeiro, com a
    linha da transferência no Detran (CA-420-16). O interessado sem cadastro não entra: o
    histórico do veículo mostra o cliente."""
    itens = []
    vendas = base().filter(veiculo_id=veiculo_id, cliente__isnull=False).order_by("-id")
    for venda in vendas:
        registrada = venda.transferencia_registrada_por
        itens.append(
            {
                "id": venda.pk,
                "codigo": venda.codigo,
                "status": venda.status,
                "origem": venda.origem,
                "origem_rotulo": OrigemVenda(venda.origem).label,
                "descricao": venda.descricao,
                "cliente": _cliente(venda),
                "vendida_em": venda.vendida_em,
                "transferencia": _transferencia(venda),
                "transferencia_texto": (
                    f"Transferência no Detran feita em {venda.transferencia_feita_em:%d/%m/%Y}"
                    + (f" · {registrada.nome}" if registrada is not None else "")
                    if venda.transferencia_feita_em
                    else None
                ),
            }
        )
    return itens


def vendidas_entre(filiais: Iterable[int], inicio: Any, fim: Any) -> tuple[int, int]:
    """VEN-12: (número, soma dos preços finais) das vendas das filiais que viraram `vendida`
    entre `inicio` (inclusive) e `fim` (exclusive) e continuam `vendida`. A venda da quitação
    (VEN-11, R$ 0,00) fica fora, como no funil e na meta."""
    totais = (
        Venda.objects.filter(
            filial_id__in=list(filiais),
            status="vendida",
            origem=OrigemVenda.BALCAO,
            vendida_em__gte=inicio,
            vendida_em__lt=fim,
        )
        .order_by()
        .aggregate(quantidade=Count("id"), soma=Sum("preco_final_centavos"))
    )
    return int(totais["quantidade"] or 0), int(totais["soma"] or 0)
