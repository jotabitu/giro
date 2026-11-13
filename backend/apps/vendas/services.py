"""Regras das vendas: o único lugar que cria venda e muda o status dela (ADR 0009).

Na T-420 só existe a venda da quitação da locação com intenção de compra (`VEN-11`, `LOC-16`,
ADR 0037, itens 4 a 6); o resto do módulo é da T-418 e seguintes.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction

from apps.contas import selectors as contas_selectors
from apps.filiais import selectors as filiais_selectors
from apps.filiais.models import Filial
from apps.notificacoes import services as notificacoes
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import StatusVeiculo, Veiculo
from comum import estados, painel, relogio
from comum.auditoria import ATOR_SISTEMA, Categoria, auditar, usar_ator
from comum.documentos import placa_com_hifen
from comum.erros import Conflito, ErroDeValidacao, SemPermissao
from comum.permissoes import filiais_permitidas

from .models import OrigemVenda, StatusVenda, Venda

REGRA = "VEN-11"
# Quem registra a transferência no Detran (`vendas.md`, "Quem pode").
REGISTRAM_TRANSFERENCIA = frozenset({"administrador", "gerente"})
NAO_CANCELA = "A venda da quitação de uma locação não se cancela."
TRANSFERENCIA_JA_REGISTRADA = "A transferência desta venda já foi registrada."


def _data_local(filial: Filial, momento: datetime) -> date:
    return momento.astimezone(ZoneInfo(filial.fuso)).date()


def data_da_quitacao(venda: Venda) -> date:
    """A data da quitação no fuso da filial (a venda da quitação nasce com `vendida_em`)."""
    if venda.vendida_em is None:
        raise ValueError(f"{venda.codigo} sem vendida_em.")
    return _data_local(venda.filial, venda.vendida_em)


def _titulo_do_aviso(venda: Venda) -> str:
    """O texto da `LOC-16` (CA-420-11), com a placa com hífen e a data no fuso da filial."""
    quitada = data_da_quitacao(venda).strftime("%d/%m/%Y")
    codigo = venda.descricao.removeprefix("Quitação da ")
    return (
        f"Fazer a transferência no Detran: {placa_com_hifen(venda.veiculo.placa)} para "
        f"{venda.cliente.nome}. {codigo} quitada em {quitada}."
    )


def destinatarios_da_transferencia(filial: Filial) -> list[int]:
    """`LOC-16` (B-04, decisão do dono em 12 nov 2026): os gerentes ativos da filial (`FIL-02`)
    e os administradores ativos da empresa, com ou sem gerente na filial, sem repetir. Vale só
    para este aviso; os outros avisos "para o gerente" seguem a `FIL-02`."""
    ids = [g["id"] for g in filiais_selectors.gerentes(filial)]
    ids += contas_selectors.administradores().order_by("id").values_list("id", flat=True)
    return list(dict.fromkeys(ids))


def _avisar_gerentes(venda_id: int) -> None:
    """Depois do commit (ADR 0037, item 6): gerentes da filial e administradores, no sino e por
    e-mail. A chave faz a mesma venda avisar uma vez só."""
    venda = Venda.objects.select_related("filial", "veiculo", "cliente", "locacao").get(pk=venda_id)
    notificacoes.avisar(
        destinatarios_da_transferencia(venda.filial),
        tipo="transferencia_quitacao",
        titulo=_titulo_do_aviso(venda),
        link=f"/locacoes/{venda.locacao_id}",
        urgente=False,
        chave=f"quitacao-transferencia-{venda.pk}",
        por_email=True,
    )


def _perder_interessados(veiculo_id: int, exceto: int) -> None:
    """`VEN-10`: o veículo vendido leva os outros `interessado` dele para `perdida`."""
    interessados = Venda.objects.filter(veiculo_id=veiculo_id, status=StatusVenda.INTERESSADO)
    for outra in interessados.exclude(pk=exceto):
        outra.motivo_perda = "veículo vendido"
        estados.transicionar(
            outra, StatusVenda.PERDIDA, regra="VEN-10", mais_campos=("motivo_perda",)
        )


def criar_venda_da_quitacao(
    *,
    locacao_id: int,
    codigo: str,
    filial_id: int,
    cliente_id: int,
    veiculo_id: int,
    vendedor_id: int | None,
    quitada_em: datetime,
) -> Venda:
    """`VEN-11`: a venda `vendida` de R$ 0,00 da quitação, na transação da quitação.

    Idempotente pela locação (única): a segunda chamada devolve a venda que já existe, sem
    passar o veículo de novo nem avisar outra vez. Sem contas a receber, sem contrato de compra
    e venda e sem comissão (`FIN-09`). O veículo vai de `alugado` para `vendido` pelo serviço de
    `veiculos`, com a origem na venda (`VEN-06`). O ator é o Sistema."""
    with transaction.atomic():
        existente: Venda | None = Venda.objects.filter(locacao_id=locacao_id).first()
        if existente is not None:
            return existente
        descricao = f"Quitação da {codigo}"
        with usar_ator(ATOR_SISTEMA):
            venda = Venda(
                filial_id=filial_id,
                cliente_id=cliente_id,
                veiculo_id=veiculo_id,
                vendedor_id=vendedor_id,
                preco_final_centavos=0,
                status=StatusVenda.VENDIDA,
                vendida_em=quitada_em,
                origem=OrigemVenda.QUITACAO_LOCACAO,
                locacao_id=locacao_id,
                descricao=descricao,
            )
            with auditar(venda, "venda.criar_da_quitacao", Categoria.OPERACAO, regra=REGRA):
                venda.save()
            veiculo = Veiculo.objects.get(pk=veiculo_id)
            veiculos_services.transicionar(
                veiculo,
                StatusVeiculo.VENDIDO,
                origem=veiculos_services.OrigemDaMudanca("venda", venda.pk, venda.codigo),
                motivo=descricao,
            )
            _perder_interessados(veiculo_id, venda.pk)
        transaction.on_commit(lambda: _avisar_gerentes(venda.pk))
        painel.renovar()  # a pendência da transferência no Início, na hora
    return venda


def pode_registrar_transferencia(venda: Venda, usuario: Any) -> bool:
    return (
        venda.origem == OrigemVenda.QUITACAO_LOCACAO
        and venda.transferencia_feita_em is None
        and getattr(usuario, "perfil", "") in REGISTRAM_TRANSFERENCIA
        and venda.filial_id in filiais_permitidas(usuario)
    )


def registrar_transferencia(venda: Venda, feita_em: date, usuario: Any) -> Venda:
    """ "Transferência feita" (`LOC-16`, CA-420-16): fecha a tarefa da transferência no Detran.

    Só administrador e gerente da filial; a data não pode ser depois de hoje nem antes da
    quitação. Registrar de novo é 409 `VEN-11`. O veículo continua `vendido`."""
    if getattr(usuario, "perfil", "") not in REGISTRAM_TRANSFERENCIA:
        raise SemPermissao("permissao", "Seu perfil não tem acesso a esta ação.")
    if venda.filial_id not in filiais_permitidas(usuario):
        raise SemPermissao("USR-07", "Você não tem acesso a esta filial")
    with transaction.atomic():
        venda = Venda.objects.select_for_update().select_related("filial").get(pk=venda.pk)
        if venda.transferencia_feita_em is not None:
            raise Conflito(REGRA, TRANSFERENCIA_JA_REGISTRADA)
        if feita_em > _data_local(venda.filial, relogio.agora()):
            raise ErroDeValidacao({"feita_em": ["A data não pode ser depois de hoje."]})
        if feita_em < data_da_quitacao(venda):
            raise ErroDeValidacao({"feita_em": ["A data não pode ser antes da quitação."]})
        with auditar(venda, "venda.registrar_transferencia", Categoria.OPERACAO, regra=REGRA):
            venda.transferencia_feita_em = feita_em
            venda.transferencia_registrada_por = usuario
            venda.save(
                update_fields=[
                    "transferencia_feita_em",
                    "transferencia_registrada_por",
                    "atualizado_em",
                ]
            )
        painel.renovar()  # a pendência sai do Início na hora
    return venda


def cancelar(venda: Venda, motivo: str, usuario: Any) -> Venda:
    """`VEN-07`. O cancelamento da venda de balcão é da T-418; a venda da quitação nunca se
    cancela (409 `VEN-11`)."""
    if venda.origem == OrigemVenda.QUITACAO_LOCACAO:
        raise Conflito(REGRA, NAO_CANCELA)
    raise NotImplementedError("O cancelamento da venda de balcão entra com a T-418.")
