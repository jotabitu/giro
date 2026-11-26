"""Regras das vendas: o único lugar que cria venda e muda o status dela (ADR 0009).

- Venda da quitação da locação com intenção de compra (`VEN-11`, `LOC-16`, ADR 0037, itens 4 a
  6): igual à da T-420.
- Venda de balcão, fase 1a da T-502 (ADR 0042, itens 2, 5, 9 e 11): `simular`, `criar`,
  `editar`, `enviar_proposta` (só o estado e a data; o e-mail é da 1c), `registrar_resposta`,
  `pedir_desconto`, `aplicar_decisao_desconto`, `perder` e `vencer_propostas` (`AUT-19`).
- Fase 1b (ADR 0042, itens 6, 6a e 7): `preparar_assinatura`, `cancelar_assinatura`, os
  assinantes da assinatura e da entrada, `concluir_se_pronto` e a perda com a entrada paga.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django_tenants.utils import tenant_context

from apps.clientes import selectors as clientes_selectors
from apps.clientes.models import Cliente, StatusCliente
from apps.contas import selectors as contas_selectors
from apps.contratos import selectors as contratos_selectors
from apps.contratos import services as contratos_services
from apps.contratos.models import Contrato, StatusContrato
from apps.empresas import selectors as empresas_selectors
from apps.filiais import selectors as filiais_selectors
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro
from apps.financeiro.models import (
    ContaReceber,
    FormaReembolso,
    RegraComissao,
    StatusConta,
    TipoConta,
)
from apps.notificacoes import services as notificacoes
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import StatusVeiculo, Veiculo
from comum import aprovacoes, estados, painel, relogio
from comum.auditoria import ATOR_SISTEMA, Categoria, auditar, usar_ator
from comum.conexao import conexao
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen, so_digitos
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, SemPermissao
from comum.permissoes import filiais_permitidas

from . import calculo
from . import contrato as contrato_da_venda
from .models import (
    ABERTAS,
    EM_ANDAMENTO,
    AntesDaAprovacao,
    FormaVenda,
    OrigemVenda,
    SituacaoAprovacao,
    StatusVenda,
    Venda,
)

logger = logging.getLogger(__name__)

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
        f"{nome_do_comprador(venda)}. {codigo} quitada em {quitada}."
    )


def nome_do_comprador(venda: Venda) -> str:
    """O cliente ou, no interessado sem cadastro, o nome digitado (`VEN-14`)."""
    return venda.cliente.nome if venda.cliente is not None else venda.interessado_nome


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
        _perder(outra, "veículo vendido", regra="VEN-10", acao="venda.perdida")


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
        # Na empresa da quitação, mesmo que o commit chegue com a conexão em outro schema: a
        # tarefa do Pix (`AUT-05`) volta ao public ao terminar (T-420).
        empresa = conexao().tenant

        def _depois() -> None:
            with tenant_context(empresa):
                _avisar_gerentes(venda.pk)

        transaction.on_commit(_depois)
        painel.renovar()  # a pendência da transferência no Início, na hora
    return venda


def transferencia_pendente(venda: Venda) -> bool:
    """`VEN-11`, `VEN-17`: a venda `vendida` (das duas origens) sem a transferência no Detran."""
    return venda.status == StatusVenda.VENDIDA and venda.transferencia_feita_em is None


def pode_registrar_transferencia(venda: Venda, usuario: Any) -> bool:
    return (
        transferencia_pendente(venda)
        and getattr(usuario, "perfil", "") in REGISTRAM_TRANSFERENCIA
        and venda.filial_id in filiais_permitidas(usuario)
    )


def registrar_transferencia(venda: Venda, feita_em: date, usuario: Any) -> Venda:
    """ "Transferência feita" (`LOC-16`, CA-420-16; `VEN-17` na venda de balcão): fecha a tarefa
    da transferência no Detran.

    Só administrador e gerente da filial; a data não pode ser depois de hoje nem antes da venda
    (a quitação, na da locação). Registrar de novo é 409 (`VEN-11`; `VEN-17` na de balcão). O
    veículo continua `vendido`."""
    if getattr(usuario, "perfil", "") not in REGISTRAM_TRANSFERENCIA:
        raise SemPermissao("permissao", "Seu perfil não tem acesso a esta ação.")
    if venda.filial_id not in filiais_permitidas(usuario):
        raise SemPermissao("USR-07", "Você não tem acesso a esta filial")
    with transaction.atomic():
        venda = (
            Venda.objects.select_for_update(of=("self",)).select_related("filial").get(pk=venda.pk)
        )
        da_quitacao = venda.origem == OrigemVenda.QUITACAO_LOCACAO
        regra = REGRA if da_quitacao else "VEN-17"
        if venda.transferencia_feita_em is not None:
            raise Conflito(regra, TRANSFERENCIA_JA_REGISTRADA)
        if venda.status != StatusVenda.VENDIDA:
            raise Conflito(regra, "A transferência sai depois de a venda ser concluída.")
        if feita_em > _data_local(venda.filial, relogio.agora()):
            raise ErroDeValidacao({"feita_em": ["A data não pode ser depois de hoje."]})
        if feita_em < data_da_quitacao(venda):
            antes = "da quitação" if da_quitacao else "da venda"
            raise ErroDeValidacao({"feita_em": [f"A data não pode ser antes {antes}."]})
        with auditar(venda, "venda.registrar_transferencia", Categoria.OPERACAO, regra=regra):
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
    """`VEN-07`. O cancelamento da venda de balcão é da fase 2 (ADR 0042, item 10); a venda da
    quitação nunca se cancela (409 `VEN-11`)."""
    if venda.origem == OrigemVenda.QUITACAO_LOCACAO:
        raise Conflito(REGRA, NAO_CANCELA)
    raise Conflito("VEN-07", "O cancelamento de venda ainda não está disponível.")


# --- Venda de balcão: fase 1a da T-502 (ADR 0042) ---

ORIGEM = "venda"
LIMITE_DESCONTO_PCT = calculo.LIMITE_DESCONTO_PCT  # VEN-02
VENCE_EM_DIAS = 7  # VEN-13, AUT-19
# Quem cria e mexe na venda (ADR 0042, item 2); o financeiro só lê e o vistoriador nem vê.
CRIAM = frozenset({"administrador", "gerente", "vendedor"})
# VEN-19: a venda com a entrada paga só o gerente ou o administrador marca como perdida.
PERDEM_COM_ENTRADA_PAGA = frozenset({"administrador", "gerente"})
SO_GERENTE_PERDE = (
    "Só o gerente ou o administrador marca como perdida uma venda com a entrada paga."
)
MOTIVO_DO_REEMBOLSO = "Venda perdida com a entrada paga"  # VEN-19, DEV-02
# VEN-19 e ADR 0042, item 6a: os 409 VEN-06 do "Cancelar a assinatura".
ENTRADA_JA_PAGA = "A entrada já foi paga. Para desfazer, marque a venda como perdida."
CONTRATO_JA_ASSINADO = (
    "O cliente já assinou o contrato. Para mudar a proposta, marque esta venda como perdida e "
    "faça uma nova."
)
COM_ASSINATURA = "Cancele a assinatura para mudar a proposta."


class Acao:
    """O botão da Nova venda (`POST /api/vendas/`, campo `acao`)."""

    INTERESSADO = "interessado"
    ENVIAR = "enviar"
    PEDIR_APROVACAO = "pedir_aprovacao"
    TODAS = (INTERESSADO, ENVIAR, PEDIR_APROVACAO)


# Os campos que o cálculo grava (VEN-02, VEN-04).
CAMPOS_DO_CALCULO = (
    "desconto_pct",
    "desconto_centavos",
    "preco_final_centavos",
    "forma",
    "entrada_centavos",
    "num_parcelas",
    "juros_pct",
    "parcela_centavos",
)
EDITAVEIS = ("forma", "desconto_pct", "entrada_centavos", "num_parcelas")


def _pct_texto(pct: Decimal) -> str:
    return f"{Decimal(pct):.2f}%".replace(".", ",")


ACIMA_DO_LIMITE = calculo.ACIMA_DO_LIMITE
EM_APROVACAO = "A venda está esperando o gerente. Espere a decisão ou cancele o pedido."


def _origem(venda: Venda) -> financeiro.Origem:
    return financeiro.Origem(ORIGEM, venda.pk, venda.codigo)


def _perfil(usuario: Any) -> str:
    return str(getattr(usuario, "perfil", "") or "")


def _exigir_quem_vende(usuario: Any) -> None:
    if _perfil(usuario) not in CRIAM:
        raise SemPermissao("permissao", "Seu perfil não tem acesso a esta ação.")


def pode_mexer(venda: Venda, usuario: Any) -> bool:
    """O vendedor só nas dele (`USR-08`); gerente e administrador nas da filial (`USR-07`). A
    venda da quitação não passa pelo fluxo (`VEN-11`)."""
    perfil = _perfil(usuario)
    return (
        perfil in CRIAM
        and venda.origem == OrigemVenda.BALCAO
        and venda.filial_id in filiais_permitidas(usuario)
        and (perfil != "vendedor" or venda.vendedor_id == getattr(usuario, "pk", None))
    )


def _exigir_mexer(venda: Venda, usuario: Any) -> None:
    _exigir_quem_vende(usuario)
    if venda.origem != OrigemVenda.BALCAO:
        raise Conflito(REGRA, "A venda da quitação de uma locação não muda por aqui.")
    if venda.filial_id not in filiais_permitidas(usuario):
        raise SemPermissao("USR-07", "Você não tem acesso a esta filial")
    if _perfil(usuario) == "vendedor" and venda.vendedor_id != getattr(usuario, "pk", None):
        raise SemPermissao("USR-08", "Você só mexe nas suas vendas.")


def _travar(venda: Venda | int) -> Venda:
    pk = venda if isinstance(venda, int) else venda.pk
    # Só a linha da venda: o cliente é nulo no interessado sem cadastro (junção externa).
    travada: Venda = (
        Venda.objects.select_for_update(of=("self",))
        .select_related("filial", "cliente", "veiculo")
        .get(pk=pk)
    )
    return travada


def _valor(dados: dict[str, Any], campo: str, atual: Any) -> Any:
    return dados.get(campo, atual)


def _entrada(venda: Venda, dados: dict[str, Any], juros_pct: Decimal) -> calculo.Entrada:
    """A proposta da venda com as mudanças de `dados` por cima (para simular e editar)."""
    configuracao = empresas_selectors.configuracao()
    return calculo.Entrada(
        preco_tabela_centavos=venda.preco_tabela_centavos or 0,
        desconto_pct=Decimal(_valor(dados, "desconto_pct", venda.desconto_pct) or 0),
        forma=_valor(dados, "forma", venda.forma) or "",
        entrada_centavos=_valor(dados, "entrada_centavos", venda.entrada_centavos),
        num_parcelas=_valor(dados, "num_parcelas", venda.num_parcelas),
        juros_pct=Decimal(juros_pct),
        comissao_pct=Decimal(configuracao.comissao_venda_pct),
        desconto_aprovado_pct=venda.desconto_aprovado_pct,
    )


def _juros_da_empresa() -> Decimal:
    """`VEN-04`: copiados da empresa ao criar e a cada edição antes da assinatura."""
    return Decimal(empresas_selectors.configuracao().juros_venda_mes_pct)


def calculo_da_venda(venda: Venda) -> calculo.Calculo:
    """O cálculo com o que está gravado (o detalhe e a lista mostram)."""
    return calculo.calcular(_entrada(venda, {}, Decimal(venda.juros_pct)))


def _aplicar(venda: Venda, conta: calculo.Calculo) -> None:
    venda.desconto_pct = conta.desconto_pct
    venda.desconto_centavos = conta.desconto_centavos
    venda.preco_final_centavos = conta.preco_final_centavos
    venda.forma = conta.forma
    venda.entrada_centavos = conta.entrada_centavos
    venda.num_parcelas = conta.num_parcelas
    venda.juros_pct = conta.juros_pct
    venda.parcela_centavos = conta.parcela_centavos


def _veiculo_para_venda(veiculo_id: Any, usuario: Any, *, travar: bool = False) -> Veiculo:
    """`VEN-01`: só veículo `a_venda`, com o valor de venda, numa filial da pessoa."""
    veiculo: Veiculo | None = Veiculo.objects.filter(
        pk=veiculo_id, filial_id__in=filiais_permitidas(usuario)
    ).first()
    if veiculo is None:
        raise ErroDeValidacao({"veiculo_id": ["Escolha um veículo à venda."]})
    if travar:
        veiculo = veiculos_services.travar(veiculo)
    if veiculo.status != StatusVeiculo.A_VENDA:
        raise Conflito("VEN-01", "Só se vende veículo à venda.")
    if not veiculo.valor_venda_centavos:
        raise Conflito("VEN-01", "Este veículo não tem valor de venda.")
    return veiculo


def _cliente(cliente_id: Any) -> Cliente:
    cliente: Cliente | None = Cliente.objects.filter(pk=cliente_id).first()
    if cliente is None:
        raise ErroDeValidacao({"cliente_id": ["Cliente não encontrado."]})
    return cliente


def _interessado(dados: dict[str, Any]) -> tuple[str, str]:
    """`VEN-14`: o interessado sem cadastro, só nome e celular (como o do catálogo)."""
    nome = str(dados.get("nome") or "").strip()
    celular = so_digitos(str(dados.get("celular") or ""))
    erros: dict[str, list[str]] = {}
    if not nome:
        erros["interessado.nome"] = ["Informe o nome."]
    if not celular:
        erros["interessado.celular"] = ["Informe o celular."]
    elif not 10 <= len(celular) <= 13:
        erros["interessado.celular"] = ["Telefone inválido."]
    if erros:
        raise ErroDeValidacao(erros)
    return nome[:150], celular


def _exigir_proposta_completa(cliente: Cliente | None, conta: calculo.Calculo) -> None:
    """`VEN-14`: a proposta pede o cliente cadastrado com CPF (ou CNPJ); `VEN-03`: a forma."""
    if cliente is None:
        raise ErroDeValidacao(
            {"cliente_id": ["Cadastre o cliente com o CPF para enviar a proposta."]}
        )
    if not cliente.documento:
        raise ErroDeValidacao({"cliente_id": ["Complete o CPF do cliente para enviar a proposta."]})
    if conta.erros:
        raise ErroDeValidacao(conta.erros)
    if not conta.completo:
        raise ErroDeValidacao({"forma": ["Escolha a forma de pagamento."]})


def venda_em_andamento(veiculo_id: int, exceto: int | None = None) -> Venda | None:
    """`VEN-10`: a venda aberta do veículo (`interessado` não conta)."""
    abertas = Venda.objects.filter(veiculo_id=veiculo_id, status__in=ABERTAS)
    if exceto is not None:
        abertas = abertas.exclude(pk=exceto)
    venda: Venda | None = abertas.order_by("id").first()
    return venda


def _em_andamento(venda: Venda) -> Conflito:
    return Conflito("VEN-10", f"Este veículo tem uma venda em andamento ({venda.codigo}).")


def _conferir_ven_10(veiculo_id: int, exceto: int | None = None) -> None:
    outra = venda_em_andamento(veiculo_id, exceto)
    if outra is not None:
        raise _em_andamento(outra)


def trava_do_estoque(veiculo: Veiculo) -> None:
    """Registrada em `veiculos` no `ready()` (ADR 0042, item 1): o veículo com venda aberta não
    volta para a frota nem é baixado (409 `VEN-10`)."""
    _conferir_ven_10(veiculo.pk)


def _salvar_abrindo(funcao: Any, veiculo_id: int, exceto: int | None) -> None:
    """Grava o que abre a venda; na corrida pelo mesmo veículo, o único do banco responde e a
    resposta é o 409 `VEN-10`, como na conferência."""
    try:
        with transaction.atomic():
            funcao()
    except IntegrityError as erro:
        if "uma_venda_aberta_por_veiculo" not in str(erro):
            raise
        outra = venda_em_andamento(veiculo_id, exceto)
        if outra is None:
            raise
        raise _em_andamento(outra) from erro


def simular(dados: dict[str, Any], usuario: Any) -> tuple[calculo.Calculo, Decimal]:
    """Só a conta, sem gravar (ADR 0005): a tela chama a cada mudança. Com `venda_id`, parte da
    venda (preço de tabela copiado e desconto já aprovado); senão, do veículo. Devolve também o
    limite do desconto sem o gerente."""
    _exigir_quem_vende(usuario)
    if dados.get("venda_id"):
        venda: Venda | None = (
            Venda.objects.filter(pk=dados["venda_id"], origem=OrigemVenda.BALCAO)
            .select_related("filial")
            .first()
        )
        if venda is None or not pode_mexer(venda, usuario):
            raise ErroDeValidacao({"venda_id": ["Venda não encontrada."]})
        juros = _juros_da_empresa() if venda.contrato_id is None else Decimal(venda.juros_pct)
    else:
        veiculo = _veiculo_para_venda(dados.get("veiculo_id"), usuario)
        venda = Venda(preco_tabela_centavos=veiculo.valor_venda_centavos)
        juros = _juros_da_empresa()
    conta = calculo.calcular(_entrada(venda, dados, juros))
    return conta, calculo.limite_efetivo(venda.desconto_aprovado_pct)


def _resumo_do_pedido(venda: Venda) -> aprovacoes.Resumo:
    veiculo = venda.veiculo
    forma = forma_texto(venda)
    return aprovacoes.Resumo(
        [
            ("Veículo", f"{veiculo.marca} {veiculo.modelo} · {placa_com_hifen(veiculo.placa)}"),
            ("Preço de tabela", formatar_reais(venda.preco_tabela_centavos or 0)),
            ("Com desconto", formatar_reais(venda.preco_final_centavos)),
            (
                "Desconto",
                f"{formatar_reais(venda.desconto_centavos)} · {_pct_texto(venda.desconto_pct)}",
            ),
            ("Forma", forma),
        ],
        f"O limite da venda é {_pct_texto(LIMITE_DESCONTO_PCT)}.",
    )


def _abrir_pedido(venda: Venda, por: Any, motivo: str) -> None:
    """`APR-01` pela porta de `comum.aprovacoes` (ADR 0019). O `valor_centavos` é o desconto em
    reais (tabela − com desconto), que os "Descontos aprovados" da `APR-12` somam, como na
    locação; o preço final pedido vai no `resumo`."""
    ref = aprovacoes.pedir(
        tipo="APR-01",
        origem_tipo=ORIGEM,
        origem_id=venda.pk,
        origem_codigo=venda.codigo,
        filial_id=venda.filial_id,
        solicitante=por,
        titulo="Desconto acima do limite",
        detalhe=(
            f"{venda.codigo} · {nome_do_comprador(venda)} · "
            f"desconto de {_pct_texto(venda.desconto_pct)}"
        ),
        motivo=motivo or None,
        valor_centavos=venda.desconto_centavos,
        pct=venda.desconto_pct,
        dados={"desconto_pct": str(venda.desconto_pct)},
        resumo=_resumo_do_pedido(venda),
    )
    venda.pedido_aprovacao_id = ref.id
    venda.aprovacao = SituacaoAprovacao.PENDENTE
    venda.desconto_pedido_pct = venda.desconto_pct
    venda.aprovacao_decidida_por = None
    venda.save(
        update_fields=[
            "pedido_aprovacao_id",
            "aprovacao",
            "desconto_pedido_pct",
            "aprovacao_decidida_por",
            "atualizado_em",
        ]
    )


def _comissao(venda: Venda) -> tuple[int, Decimal]:
    pct = Decimal(empresas_selectors.configuracao().comissao_venda_pct)
    return calculo.arredondar(Decimal(venda.preco_final_centavos) * pct / calculo.CEM), pct


def _lancar_comissao_pendente(venda: Venda) -> None:
    """`FIN-09`: o pedido de desconto lança a comissão `pendente` sobre o preço final pedido; se
    já existe (pedido de novo), é recalculada. O vendedor é quem criou a venda."""
    if venda.vendedor_id is None:
        return
    valor, pct = _comissao(venda)
    financeiro.lancar_comissao(
        _origem(venda),
        usuario_id=venda.vendedor_id,
        valor_centavos=valor,
        regra=RegraComissao.PERCENTUAL_VENDA,
        base_centavos=venda.preco_final_centavos,
        pct=pct,
    )
    _recalcular_comissao(venda)


def _recalcular_comissao(venda: Venda) -> None:
    """`FIN-09`: o preço mudou (edição ou recusa); só a `pendente` acompanha."""
    valor, _ = _comissao(venda)
    financeiro.recalcular_comissao(
        _origem(venda), base_centavos=venda.preco_final_centavos, valor_centavos=valor
    )


def criar(dados: dict[str, Any], por: Any, acao: str) -> Venda:
    """A Nova venda (ADR 0042, item 5). `interessado`: aceita cliente incompleto ou só nome e
    celular (`VEN-14`). `enviar` e `pedir_aprovacao` pedem o cliente com CPF e a forma completa,
    e abrem a venda do veículo (409 `VEN-10` se já há outra). O vendedor é quem cria (`FIN-09`);
    o preço de tabela é copiado do veículo (`VEN-01`) e não muda depois."""
    _exigir_quem_vende(por)
    if acao not in Acao.TODAS:
        raise ErroDeValidacao({"acao": ["Escolha interessado, enviar ou pedir_aprovacao."]})
    with transaction.atomic():
        veiculo = _veiculo_para_venda(dados.get("veiculo_id"), por, travar=True)
        cliente: Cliente | None = None
        nome = celular = ""
        if dados.get("cliente_id"):
            cliente = _cliente(dados["cliente_id"])
        elif dados.get("interessado"):
            nome, celular = _interessado(dados["interessado"])
        else:
            raise ErroDeValidacao(
                {"cliente_id": ["Escolha o cliente ou informe o nome e o celular."]}
            )
        venda = Venda(
            filial_id=veiculo.filial_id,
            veiculo=veiculo,
            cliente=cliente,
            interessado_nome=nome,
            interessado_celular=celular,
            vendedor=por if getattr(por, "pk", None) is not None else None,
            preco_tabela_centavos=veiculo.valor_venda_centavos,
            origem=OrigemVenda.BALCAO,
        )
        conta = calculo.calcular(_entrada(venda, dados, _juros_da_empresa()))
        if conta.erros:
            raise ErroDeValidacao(conta.erros)
        if acao != Acao.PEDIR_APROVACAO and conta.precisa_aprovacao:
            raise ErroDeValidacao({"desconto_pct": [ACIMA_DO_LIMITE]})
        if acao == Acao.PEDIR_APROVACAO and not conta.precisa_aprovacao:
            raise ErroDeValidacao(
                {"desconto_pct": ["Até 5% você dá sem o gerente. Use Salvar proposta."]}
            )
        if acao != Acao.INTERESSADO:
            _exigir_proposta_completa(cliente, conta)
            _conferir_ven_10(veiculo.pk)
        _aplicar(venda, conta)
        agora = relogio.agora()
        venda.ultimo_contato_em = agora
        if acao == Acao.INTERESSADO:
            venda.status = StatusVenda.INTERESSADO
        elif acao == Acao.ENVIAR:
            venda.status = StatusVenda.PROPOSTA
            venda.proposta_enviada_em = venda.entrou_proposta_em = agora
        else:
            venda.status = StatusVenda.AGUARDANDO_APROVACAO
            venda.status_antes_aprovacao = AntesDaAprovacao.INTERESSADO
            venda.entrou_negociacao_em = agora

        def _gravar() -> None:
            with auditar(venda, "venda.criar", Categoria.OPERACAO, regra="VEN-13"):
                venda.save()

        _salvar_abrindo(_gravar, veiculo.pk, None)
        if acao == Acao.ENVIAR:
            _agendar_envio(venda)
        if acao == Acao.PEDIR_APROVACAO:
            _abrir_pedido(venda, por, str(dados.get("motivo") or "").strip())
            _lancar_comissao_pendente(venda)
    return venda


def editar(venda: Venda, dados: dict[str, Any], por: Any) -> Venda:
    """Os campos da proposta, antes da assinatura (ADR 0042, item 5). Em `aguardando_aprovacao`
    não edita (409 `APR-01`); desconto acima do limite não grava (400 `VEN-02`). Os juros são
    copiados da empresa de novo e a comissão pendente acompanha o preço (`FIN-09`)."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.status == StatusVenda.AGUARDANDO_APROVACAO:
            raise Conflito("APR-01", EM_APROVACAO)
        if venda.status not in EM_ANDAMENTO:
            raise Conflito("transicao_venda", "Esta venda não se edita mais.")
        if venda.contrato_id is not None:
            raise Conflito("VEN-06", COM_ASSINATURA)
        cliente = venda.cliente
        nome, celular = venda.interessado_nome, venda.interessado_celular
        quem_antes = (venda.cliente_id, nome, celular)
        if dados.get("cliente_id"):
            cliente = _cliente(dados["cliente_id"])
            nome = celular = ""
        elif dados.get("interessado"):
            if cliente is not None:
                raise ErroDeValidacao({"interessado": ["A venda já tem cliente cadastrado."]})
            nome, celular = _interessado(dados["interessado"])
        propostos = {campo: dados[campo] for campo in EDITAVEIS if campo in dados}
        conta = calculo.calcular(_entrada(venda, propostos, _juros_da_empresa()))
        if conta.erros:
            raise ErroDeValidacao(conta.erros)
        if conta.precisa_aprovacao:
            raise ErroDeValidacao({"desconto_pct": [ACIMA_DO_LIMITE]})
        if venda.status != StatusVenda.INTERESSADO:
            _exigir_proposta_completa(cliente, conta)
        with auditar(venda, "venda.editar", Categoria.OPERACAO, regra="VEN-02"):
            venda.cliente = cliente
            venda.interessado_nome, venda.interessado_celular = nome, celular
            _aplicar(venda, conta)
            venda.motivo_recusa = ""  # o vendedor refez a proposta (VEN-13)
            venda.ultimo_contato_em = relogio.agora()
            # S-15 (revisão da Segurança no #650): a proposta mudou, e o link e o PDF de antes
            # (com o cliente e os valores de antes) deixam de valer. Com o mesmo cliente, o
            # arquivo fica guardado (ADR 0009); só a venda deixa de apontar para ele.
            _soltar_link_e_pdf(venda)
            venda.save(
                update_fields=[
                    "cliente",
                    "interessado_nome",
                    "interessado_celular",
                    *CAMPOS_DO_CALCULO,
                    "motivo_recusa",
                    "ultimo_contato_em",
                    "token_proposta_hash",
                    "token_proposta_expira_em",
                    "proposta_pdf",
                    "atualizado_em",
                ]
            )
        if (venda.cliente_id, nome, celular) != quem_antes:
            # T-517 (Segurança no #650, b): os PDFs de antes têm o nome do cliente de antes, e a
            # anonimização dele procura pelas vendas em que ele está. Saem do armazenamento
            # depois do commit, com as versões antigas (a pasta da venda só guarda a proposta).
            from comum.tasks import apagar_depois_do_commit

            apagar_depois_do_commit([], [pasta_da_venda(venda.pk)])
        _recalcular_comissao(venda)
    return venda


def pasta_da_venda(venda_id: int) -> str:
    """`<schema>/vendas/venda/<id>/`: só os PDFs da proposta (`proposta_pdf`, todas as versões)."""
    from comum.conexao import schema_atual

    return f"{schema_atual()}/vendas/venda/{venda_id}/"


def _soltar_link_e_pdf(venda: Venda) -> tuple[str, ...]:
    """S-15: a proposta mudou; o link vivo e o PDF de antes deixam de valer (o próximo link grava
    o PDF de agora). Devolve os campos para o `save`."""
    venda.token_proposta_hash = None
    venda.token_proposta_expira_em = None
    venda.proposta_pdf = None
    return ("token_proposta_hash", "token_proposta_expira_em", "proposta_pdf")


def _marcar_envio(venda: Venda) -> tuple[str, ...]:
    """O último envio (o vencimento conta dele) e a primeira entrada em `proposta` (funil)."""
    agora = relogio.agora()
    venda.proposta_enviada_em = agora
    venda.ultimo_contato_em = agora
    if venda.entrou_proposta_em is None:
        venda.entrou_proposta_em = agora
    return ("proposta_enviada_em", "entrou_proposta_em", "ultimo_contato_em")


def _agendar_envio(venda: Venda) -> bool:
    """`VEN-15` (fase 1c): o PDF e o e-mail saem depois do commit (`vendas.envio`)."""
    from . import envio

    return envio.agendar_envio(venda)


def enviar_proposta(venda: Venda, por: Any) -> tuple[Venda, bool]:
    """ "Salvar proposta e enviar ao cliente" (`VEN-15`): `interessado` → `proposta`, ou o
    reenvio em `proposta` e `negociacao` (o estado não muda). O PDF e o e-mail saem depois do
    commit; devolve `email_enviado` (falso sem e-mail no cadastro, para o "Copiar link")."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.status == StatusVenda.AGUARDANDO_APROVACAO:
            raise Conflito("APR-01", EM_APROVACAO)
        if venda.status in (StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO):
            with auditar(venda, "venda.reenviar_proposta", Categoria.OPERACAO, regra="VEN-15"):
                campos = _marcar_envio(venda)
                venda.save(update_fields=[*campos, "atualizado_em"])
            return venda, _agendar_envio(venda)
        if venda.status == StatusVenda.INTERESSADO:
            conta = calculo_da_venda(venda)
            _exigir_proposta_completa(venda.cliente, conta)
            if conta.precisa_aprovacao:
                raise ErroDeValidacao({"desconto_pct": [ACIMA_DO_LIMITE]})
            _conferir_ven_10(venda.veiculo_id, venda.pk)
        campos = _marcar_envio(venda)

        def _transicionar() -> None:
            estados.transicionar(
                venda,
                StatusVenda.PROPOSTA,
                acao="venda.enviar_proposta",
                regra="VEN-13",
                mais_campos=campos,
            )

        _salvar_abrindo(_transicionar, venda.veiculo_id, venda.pk)
        enviado = _agendar_envio(venda)
    return venda, enviado


def registrar_resposta(venda: Venda, por: Any, nota: str = "") -> Venda:
    """ "Registrar resposta do cliente" (`VEN-13`): `proposta` → `negociacao`. A nota vai só
    para a auditoria nesta fase."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        agora = relogio.agora()
        venda.ultimo_contato_em = agora
        if venda.entrou_negociacao_em is None:
            venda.entrou_negociacao_em = agora
        estados.transicionar(
            venda,
            StatusVenda.NEGOCIACAO,
            motivo=(nota or "").strip()[:300],
            acao="venda.registrar_resposta",
            regra="VEN-13",
            mais_campos=("entrou_negociacao_em", "ultimo_contato_em"),
        )
    return venda


def pedir_desconto(venda: Venda, pct: Decimal, motivo: str, por: Any) -> Venda:
    """ "Pedir aprovação do gerente" (`VEN-02`, `VEN-13`, `APR-01`): de `interessado`,
    `proposta` ou `negociacao` para `aguardando_aprovacao`, guardando o estado de antes. Abre o
    pedido e lança a comissão `pendente` sobre o preço final pedido (`FIN-09`)."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.status == StatusVenda.AGUARDANDO_APROVACAO:
            raise aprovacoes.PedidoPendente(venda.pedido_aprovacao_id or 0)
        if venda.status not in EM_ANDAMENTO:
            raise Conflito("transicao_venda", "Esta venda não pede mais desconto.")
        if venda.contrato_id is not None:
            raise Conflito("VEN-06", COM_ASSINATURA)
        conta = calculo.calcular(_entrada(venda, {"desconto_pct": pct}, _juros_da_empresa()))
        if conta.erros:
            raise ErroDeValidacao(conta.erros)
        if not conta.precisa_aprovacao:
            limite = _pct_texto(calculo.limite_efetivo(venda.desconto_aprovado_pct))
            raise ErroDeValidacao(
                {"desconto_pct": [f"Até {limite} você dá sem o gerente. Use Salvar proposta."]}
            )
        _exigir_proposta_completa(venda.cliente, conta)
        if venda.status == StatusVenda.INTERESSADO:
            _conferir_ven_10(venda.veiculo_id, venda.pk)
        antes = venda.status
        _aplicar(venda, conta)
        # T-517 (Segurança no #650, a): os valores mudaram, como no `editar`.
        soltos = _soltar_link_e_pdf(venda)
        agora = relogio.agora()
        venda.status_antes_aprovacao = antes
        venda.motivo_recusa = ""
        venda.ultimo_contato_em = agora
        if venda.entrou_negociacao_em is None:
            venda.entrou_negociacao_em = agora

        def _transicionar() -> None:
            estados.transicionar(
                venda,
                StatusVenda.AGUARDANDO_APROVACAO,
                motivo=(motivo or "").strip()[:300],
                acao="venda.pedir_desconto",
                regra="APR-01",
                mais_campos=(
                    *CAMPOS_DO_CALCULO,
                    "status_antes_aprovacao",
                    "motivo_recusa",
                    "entrou_negociacao_em",
                    "ultimo_contato_em",
                    *soltos,
                ),
            )

        _salvar_abrindo(_transicionar, venda.veiculo_id, venda.pk)
        _abrir_pedido(venda, por, (motivo or "").strip())
        _lancar_comissao_pendente(venda)
    return venda


def aplicar_decisao_desconto(
    venda_id: int, status: str, motivo: str = "", decidido_por_id: int | None = None
) -> None:
    """Volta do `APR-01` (assinante de `aprovacoes.pedido_decidido`, `VEN-13`).

    Aprovado: o desconto fica aprovado e a venda volta ao estado de antes; a que vinha de
    `interessado` vira `proposta` e é enviada. Recusado: o desconto vai a zero, o preço e a
    comissão pendente são refeitos, o motivo fica à vista e o vendedor é avisado. Cancelado (quem
    pediu desistiu): como recusado, sem motivo. Idempotente pela `aprovacao == pendente`."""
    with transaction.atomic():
        if not Venda.objects.filter(pk=venda_id).exists():
            return
        venda = _travar(venda_id)
        if venda.aprovacao != SituacaoAprovacao.PENDENTE:
            return
        if venda.status != StatusVenda.AGUARDANDO_APROVACAO:
            return
        antes = venda.status_antes_aprovacao or StatusVenda.PROPOSTA
        agora = relogio.agora()
        campos: list[str] = [
            "aprovacao",
            "status_antes_aprovacao",
            "ultimo_contato_em",
            "aprovacao_decidida_por",
        ]
        venda.aprovacao_decidida_por_id = decidido_por_id
        if status == "aprovado":
            venda.aprovacao = SituacaoAprovacao.APROVADO
            venda.desconto_aprovado_pct = venda.desconto_pct
            campos.append("desconto_aprovado_pct")
            destino = antes
            acao = "venda.aprovar_desconto"
            if antes == StatusVenda.INTERESSADO:
                destino = StatusVenda.PROPOSTA
                campos += list(_marcar_envio(venda))
        else:
            recusado = status == "recusado"
            venda.aprovacao = (
                SituacaoAprovacao.RECUSADO if recusado else SituacaoAprovacao.CANCELADO
            )
            venda.motivo_recusa = (motivo or "")[:300] if recusado else ""
            _aplicar(venda, calculo.calcular(_entrada(venda, {"desconto_pct": 0}, venda.juros_pct)))
            campos += [*CAMPOS_DO_CALCULO, "motivo_recusa"]
            destino = antes
            acao = "venda.recusar_desconto" if recusado else "venda.cancelar_desconto"
        venda.status_antes_aprovacao = ""
        venda.ultimo_contato_em = agora
        if destino == StatusVenda.PROPOSTA and status in ("aprovado", "recusado"):
            # Decisão do dono de 23 nov 2026 (VEN-13, AUT-19): a volta à `proposta` recomeça os
            # 7 dias, sem reenviar ao cliente; a espera pelo gerente não gasta o prazo.
            venda.proposta_enviada_em = agora
            campos.append("proposta_enviada_em")
        estados.transicionar(
            venda,
            destino,
            motivo=motivo or "",
            acao=acao,
            regra="APR-01",
            mais_campos=tuple(dict.fromkeys(campos)),
        )
        if status != "aprovado":
            _recalcular_comissao(venda)
        if status == "aprovado" and antes == StatusVenda.INTERESSADO:
            # VEN-13 (decisão do dono de 18 nov 2026, #665): o pedido tomou o lugar do "Salvar
            # proposta e enviar"; o cliente ainda não recebeu nada, e a proposta sai sozinha na
            # aprovação. Sem e-mail, vale o "Cliente sem e-mail" da VEN-19 (só o PDF). A que
            # vinha de `proposta` ou `negociacao` não é reenviada: o vendedor usa "Enviar".
            _agendar_envio(venda)
        if status == "recusado" and venda.vendedor_id is not None:
            notificacoes.avisar(
                [venda.vendedor_id],
                tipo="desconto_recusado",
                titulo=f"Desconto da {venda.codigo} recusado: {motivo}"[:200],
                link=f"/vendas/{venda.pk}",
            )


def _entrada_paga(venda: Venda) -> ContaReceber | None:
    """A conta da entrada já paga (`VEN-15`), ou `None`."""
    if venda.conta_entrada_id is None:
        return None
    conta: ContaReceber | None = ContaReceber.objects.filter(
        pk=venda.conta_entrada_id, status=StatusConta.PAGA
    ).first()
    return conta


def _desfazer_assinatura_da_perdida(venda: Venda, motivo: str) -> None:
    """`VEN-13`, ADR 0042, item 6a (padrão A): o contrato da venda perdida vai para
    `cancelado` (o assinado também, com o PDF e a prova guardados); a conta da entrada em aberto
    vai para `cancelada`; a paga vira um reembolso "a fazer" por Pix (`DEV-02`, `VEN-19`). O
    contrato fica ligado à venda, para a tela mostrar "Cancelado · venda perdida"."""
    texto = f"Venda perdida: {motivo}"[:200]
    if venda.contrato_id is not None:
        contrato = Contrato.objects.select_for_update().get(pk=venda.contrato_id)
        if contrato.status == StatusContrato.ASSINADO:
            contratos_services.cancelar_assinado(contrato, texto)
        elif contrato.status != StatusContrato.CANCELADO:
            contratos_services.cancelar(contrato, texto)
    if venda.conta_entrada_id is None:
        return
    paga = _entrada_paga(venda)
    if paga is None:
        financeiro.cancelar_conta(venda.conta_entrada_id, motivo=texto, regra="VEN-13")
        return
    if venda.cliente_id is None:  # a entrada só existe com o cliente (VEN-14)
        return
    financeiro.devolver_ao_cliente(
        _origem(venda),
        filial_id=venda.filial_id,
        cliente_id=venda.cliente_id,
        valor_centavos=paga.valor_centavos,
        forma=FormaReembolso.PIX,
        motivo=MOTIVO_DO_REEMBOLSO,
        regra="DEV-02",
    )


def _perder(venda: Venda, motivo: str, *, regra: str, acao: str) -> None:
    """Qualquer estado em andamento → `perdida` (`VEN-13`), na transação de quem chama: cancela o
    pedido de desconto pendente (o pedido vai para `cancelado`), o contrato e a conta da entrada
    (ou devolve a entrada paga, fase 1b) e estorna a comissão pendente (`FIN-09`). A `aprovacao`
    muda antes do cancelamento, para o evento de volta não fazer nada."""
    pendente = venda.aprovacao == SituacaoAprovacao.PENDENTE
    agora = relogio.agora()
    venda.motivo_perda = motivo[:200]
    venda.perdida_em = agora
    venda.ultimo_contato_em = agora
    campos = ["motivo_perda", "perdida_em", "ultimo_contato_em"]
    if pendente:
        venda.aprovacao = SituacaoAprovacao.CANCELADO
        venda.status_antes_aprovacao = ""
        campos += ["aprovacao", "status_antes_aprovacao"]
    estados.transicionar(
        venda,
        StatusVenda.PERDIDA,
        motivo=motivo,
        acao=acao,
        regra=regra,
        mais_campos=tuple(campos),
    )
    if pendente:
        aprovacoes.cancelar_pendentes(
            origem_tipo=ORIGEM, origem_id=venda.pk, motivo=f"Venda perdida: {motivo}"[:300]
        )
    _desfazer_assinatura_da_perdida(venda, motivo)
    financeiro.estornar_comissao(_origem(venda), motivo=f"Venda perdida: {motivo}"[:200])


def pode_perder(venda: Venda, usuario: Any) -> bool:
    """`VEN-19`: com a entrada paga, só o gerente ou o administrador marca como perdida."""
    if not pode_mexer(venda, usuario) or venda.status not in EM_ANDAMENTO:
        return False
    return venda.entrada_paga_em is None or _perfil(usuario) in PERDEM_COM_ENTRADA_PAGA


def perder(venda: Venda, motivo: str, por: Any) -> Venda:
    """ "Marcar como perdida" (`VEN-13`), motivo obrigatório. O vendedor perde as próprias vendas;
    gerente e administrador, as da filial (decisão do dono de 18 nov 2026). Com a entrada paga,
    só o gerente ou o administrador (403 para o vendedor), e o valor vira um reembolso "a fazer"
    (`VEN-19`, `DEV-02`)."""
    _exigir_mexer(venda, por)
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with transaction.atomic():
        venda = _travar(venda)
        if venda.entrada_paga_em is not None and _perfil(por) not in PERDEM_COM_ENTRADA_PAGA:
            raise SemPermissao("VEN-19", SO_GERENTE_PERDE)
        _perder(venda, texto, regra="VEN-13", acao="venda.perder")
    return venda


def _vencida(venda: Venda, hoje_utc: datetime) -> bool:
    """Enviada em 07 out, perdida na rodada de 14 out: a data local do último envio + 7 dias
    corridos ≤ hoje, no fuso da filial (`AUT-19`)."""
    if venda.proposta_enviada_em is None:
        return False
    enviada = _data_local(venda.filial, venda.proposta_enviada_em)
    return enviada + timedelta(days=VENCE_EM_DIAS) <= _data_local(venda.filial, hoje_utc)


def vencer_propostas() -> int:
    """`AUT-19`, rotina diária: a `proposta` sem resposta há 7 dias vira `perdida` com o motivo
    "proposta vencida". `interessado`, `negociacao` e `aguardando_aprovacao` não vencem. O ator é
    o Sistema; idempotente, e a rodada perdida pega as vencidas na próxima."""
    agora = relogio.agora()
    # Pré-filtro largo (o fuso da filial fica para a conferência de cada uma).
    candidatas = Venda.objects.filter(
        status=StatusVenda.PROPOSTA,
        origem=OrigemVenda.BALCAO,
        proposta_enviada_em__lte=agora - timedelta(days=VENCE_EM_DIAS - 1),
    ).values_list("pk", flat=True)
    vencidas = 0
    with usar_ator(ATOR_SISTEMA):
        for pk in list(candidatas):
            with transaction.atomic():
                venda = _travar(pk)
                if venda.status != StatusVenda.PROPOSTA or not _vencida(venda, agora):
                    continue
                _perder(venda, "proposta vencida", regra="AUT-19", acao="venda.vencer_proposta")
                vencidas += 1
    return vencidas


# --- Fase 1b: assinatura e `vendida` (ADR 0042, itens 6, 6a e 7) ---

NA_ASSINATURA = (StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO)
CLIENTE_BLOQUEADO = "O cliente está bloqueado e não pode comprar."
CLIENTE_INATIVO = "O cliente está inativo e não pode comprar."
CADASTRO_INCOMPLETO = "Complete o cadastro do cliente antes da assinatura."
OBSERVACAO_A_VISTA = "Pagamento à vista"


def _exigir_cliente_que_compra(cliente: Cliente) -> None:
    """`VEN-14`: a etapa "Documentos". Bloqueado ou inativo: 409 `CLI-05`; cadastro com
    pendência: 422 `CLI-03` (a lista vem no detalhe, `documentos.pendencias`)."""
    if cliente.status == StatusCliente.BLOQUEADO:
        raise Conflito("CLI-05", CLIENTE_BLOQUEADO)
    if cliente.status == StatusCliente.INATIVO or cliente.anonimizado_em is not None:
        raise Conflito("CLI-05", CLIENTE_INATIVO)
    pendencias = clientes_selectors.pendencias(cliente)
    if pendencias:
        raise ErroDeRegra("CLI-03", CADASTRO_INCOMPLETO, {"pendencias": pendencias})


def preparar_assinatura(venda: Venda, por: Any) -> Venda:
    """ "Preparar assinatura" (`VEN-15`, ADR 0042, item 6): da etapa "Documentos" para a
    "Assinatura". A venda continua em `proposta` ou `negociacao`.

    Pede a proposta enviada, o desconto dentro do limite (ou aprovado), o cliente sem pendência
    (`CLI-03`), nem bloqueado nem inativo (`CLI-05`), e o veículo ainda à venda (`VEN-01`). Na
    mesma transação: o contrato do modelo publicado de compra e venda (422 `IMP-04` sem ele; o
    PDF e o envio saem depois do commit, como na retirada) e a conta da entrada (ou do total à
    vista) com vencimento hoje, esperando a conclusão (`aguarda_retirada`: sem régua, sem bloqueio,
    sem multa nem juros)."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.status == StatusVenda.AGUARDANDO_APROVACAO:
            raise Conflito("APR-01", EM_APROVACAO)
        if venda.status not in NA_ASSINATURA:
            raise Conflito("transicao_venda", "A assinatura sai de uma proposta enviada.")
        if venda.contrato_id is not None:
            raise Conflito("VEN-06", "A assinatura desta venda já foi preparada.")
        conta = calculo_da_venda(venda)
        if conta.precisa_aprovacao:
            raise Conflito("VEN-02", ACIMA_DO_LIMITE)
        _exigir_proposta_completa(venda.cliente, conta)
        cliente = venda.cliente
        if cliente is None:  # já conferido acima; para o mypy
            raise ErroDeValidacao({"cliente_id": ["Cadastre o cliente."]})
        _exigir_cliente_que_compra(cliente)
        veiculo = veiculos_services.travar(venda.veiculo)
        if veiculo.status != StatusVeiculo.A_VENDA:
            raise Conflito("VEN-01", "Este veículo não está mais à venda.")
        contrato = contrato_da_venda.gerar(venda)
        hoje = _data_local(venda.filial, relogio.agora())
        contas = financeiro.criar_contas(
            _origem(venda),
            filial_id=venda.filial_id,
            cliente_id=cliente.pk,
            contas=[
                financeiro.NovaConta(
                    tipo=TipoConta.ENTRADA,
                    vencimento=hoje,
                    valor_centavos=venda.entrada_centavos or 0,
                    observacao=OBSERVACAO_A_VISTA if venda.forma == FormaVenda.A_VISTA else "",
                )
            ],
            aguarda_retirada=True,
        )
        with auditar(venda, "venda.preparar_assinatura", Categoria.OPERACAO, regra="VEN-15"):
            venda.contrato = contrato
            venda.conta_entrada = contas[0] if contas else None
            venda.ultimo_contato_em = relogio.agora()
            venda.save(
                update_fields=["contrato", "conta_entrada", "ultimo_contato_em", "atualizado_em"]
            )
    return venda


def cancelar_assinatura(venda: Venda, por: Any) -> Venda:
    """ "Cancelar a assinatura" (`VEN-19`): o contrato não assinado vai para `cancelado` e a
    conta da entrada em aberto para `cancelada`, nada se apaga, e a venda volta a se editar no
    estado em que estava. Entrada paga ou contrato assinado: 409 `VEN-06` (ADR 0042, item 6a)."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.contrato_id is None or venda.status not in NA_ASSINATURA:
            raise Conflito("transicao_venda", "Esta venda não tem assinatura para cancelar.")
        if venda.entrada_paga_em is not None or _entrada_paga(venda) is not None:
            raise Conflito("VEN-06", ENTRADA_JA_PAGA)
        contrato = Contrato.objects.select_for_update().get(pk=venda.contrato_id)
        if contrato.status == StatusContrato.ASSINADO or venda.contrato_assinado_em is not None:
            raise Conflito("VEN-06", CONTRATO_JA_ASSINADO)
        motivo = "Assinatura cancelada para mudar a proposta"
        if contrato.status != StatusContrato.CANCELADO:
            contratos_services.cancelar(contrato, motivo)
        if venda.conta_entrada_id is not None:
            financeiro.cancelar_conta(venda.conta_entrada_id, motivo=motivo, regra="VEN-19")
        with auditar(venda, "venda.cancelar_assinatura", Categoria.OPERACAO, regra="VEN-19"):
            venda.contrato = None
            venda.conta_entrada = None
            venda.ultimo_contato_em = relogio.agora()
            venda.save(
                update_fields=["contrato", "conta_entrada", "ultimo_contato_em", "atualizado_em"]
            )
    return venda


def _contrato_que_falta_assinar(venda: Venda) -> Contrato:
    contrato = contrato_da_venda.vigente(venda) if venda.status in NA_ASSINATURA else None
    if contrato is None or venda.contrato_id != contrato.pk:
        raise Conflito("sem_contrato", "Esta venda ainda não tem contrato. Prepare a assinatura.")
    return contrato


def copiar_link_do_contrato(venda: Venda, por: Any, ip: str | None) -> tuple[str, Contrato]:
    """ "Copiar link para assinar" (`VEN-15`), como na retirada (T-411): token novo agora; o
    link anterior deixa de valer. Devolve o link e o contrato."""
    _exigir_mexer(venda, por)
    contrato = _contrato_que_falta_assinar(venda)
    token, contrato = contratos_services.gerar_link(contrato, por, ip)
    host = contratos_selectors.marca_e_host()[1]
    return contratos_services.link_de_assinatura(host, token), contrato


def reenviar_contrato(venda: Venda, por: Any) -> Contrato:
    """Reenvia o contrato (novo link; o assinado manda o PDF assinado), como na retirada."""
    _exigir_mexer(venda, por)
    return contratos_services.reenviar(_contrato_que_falta_assinar(venda))


def _venda_da_fase(venda_id: int) -> Venda | None:
    if not Venda.objects.filter(pk=venda_id, origem=OrigemVenda.BALCAO).exists():
        return None
    return _travar(venda_id)


def registrar_contrato_assinado(
    venda_id: int, contrato_id: int | None, assinado_em: datetime | None
) -> None:
    """Assinante de `contratos.contrato_assinado` (ADR 0042, item 1): grava a data e tenta a
    conclusão, na transação da assinatura. Só o contrato vigente da venda conta; idempotente."""
    with transaction.atomic():
        venda = _venda_da_fase(venda_id)
        if venda is None or venda.contrato_assinado_em is not None:
            return
        if contrato_id is not None and venda.contrato_id != contrato_id:
            return
        with (
            usar_ator(ATOR_SISTEMA),
            auditar(venda, "venda.registrar_assinatura", Categoria.OPERACAO, regra="VEN-15"),
        ):
            venda.contrato_assinado_em = assinado_em or relogio.agora()
            venda.ultimo_contato_em = relogio.agora()
            venda.save(update_fields=["contrato_assinado_em", "ultimo_contato_em", "atualizado_em"])
        concluir_se_pronto(venda.pk)


def registrar_entrada_paga(venda_id: int, conta_id: int | None, pago_em: datetime | None) -> None:
    """Assinante de `financeiro.parcela_paga` com `tipo = entrada` (ADR 0042, item 1): grava a
    data e tenta a conclusão, na transação da baixa. Só a conta da entrada da venda conta."""
    with transaction.atomic():
        venda = _venda_da_fase(venda_id)
        if venda is None or venda.entrada_paga_em is not None:
            return
        if venda.conta_entrada_id is None or (
            conta_id is not None and venda.conta_entrada_id != conta_id
        ):
            return
        with auditar(venda, "venda.registrar_entrada", Categoria.OPERACAO, regra="VEN-15"):
            venda.entrada_paga_em = pago_em or relogio.agora()
            venda.ultimo_contato_em = relogio.agora()
            venda.save(update_fields=["entrada_paga_em", "ultimo_contato_em", "atualizado_em"])
        concluir_se_pronto(venda.pk)


def pronta_para_concluir(venda: Venda) -> bool:
    """O contrato assinado e a entrada paga (ou sem conta de entrada), em qualquer ordem, com a
    venda em `proposta` ou `negociacao` (`VEN-15`)."""
    return (
        venda.origem == OrigemVenda.BALCAO
        and venda.status in NA_ASSINATURA
        and venda.contrato_id is not None
        and venda.contrato_assinado_em is not None
        and (venda.conta_entrada_id is None or venda.entrada_paga_em is not None)
    )


def _titulo_da_transferencia(venda: Venda) -> str:
    """`VEN-17` (proposta do arquiteto, ADR 0042, item 7): "Fazer a transferência no Detran:
    RTA-2C55 para Diego Martins. VEN-0177 vendida em 07/10/2026."."""
    vendida = data_da_quitacao(venda).strftime("%d/%m/%Y")
    return (
        f"Fazer a transferência no Detran: {placa_com_hifen(venda.veiculo.placa)} para "
        f"{nome_do_comprador(venda)}. {venda.codigo} vendida em {vendida}."
    )


def _avisar_transferencia(venda_id: int) -> None:
    venda = Venda.objects.select_related("filial", "veiculo", "cliente").get(pk=venda_id)
    notificacoes.avisar(
        destinatarios_da_transferencia(venda.filial),
        tipo="transferencia_venda",
        titulo=_titulo_da_transferencia(venda),
        link=f"/vendas/{venda.pk}",
        urgente=False,
        chave=f"venda-transferencia-{venda.pk}",
        por_email=True,
    )


def _avisar_fora_do_estoque(venda: Venda) -> None:
    """ADR 0042, item 7: o veículo saiu do estoque antes da conclusão (a trava da `VEN-10`
    impede). A venda fica como está, a baixa e a assinatura gravam e os gerentes são avisados."""
    logger.error(
        "Venda %s pronta para concluir com o veículo %s fora de a_venda.",
        venda.codigo,
        venda.veiculo_id,
    )
    notificacoes.avisar(
        destinatarios_da_transferencia(venda.filial),
        tipo="venda_nao_concluida",
        titulo=(
            f"A {venda.codigo} tem o contrato assinado e a entrada paga, mas o veículo não está "
            "mais à venda. Confira o veículo."
        )[:200],
        link=f"/vendas/{venda.pk}",
        chave=f"venda-nao-concluida-{venda.pk}",
    )


def _criar_parcelas(venda: Venda, dia: date) -> int:
    """`VEN-04`: as parcelas em Contas a receber, a 1ª um mês depois do dia da venda, as outras
    no mesmo dia dos meses seguintes; a diferença de centavos na última. Nascem normais (régua,
    multa e juros da `FIN-03`)."""
    if venda.forma != FormaVenda.ENTRADA_PARCELAS or not venda.num_parcelas:
        return 0
    if venda.cliente_id is None:
        raise ValueError(f"{venda.codigo} sem cliente.")
    conta = calculo_da_venda(venda)
    n = venda.num_parcelas
    parcela = conta.parcela_centavos or 0
    ultima = conta.ultima_parcela_centavos or parcela
    novas = [
        financeiro.NovaConta(
            tipo=TipoConta.PARCELA,
            vencimento=vencimento,
            valor_centavos=ultima if numero == n else parcela,
            numero_parcela=numero,
            total_parcelas=n,
        )
        for numero, vencimento in enumerate(calculo.vencimentos(dia, n), start=1)
    ]
    criadas = financeiro.criar_contas(
        _origem(venda), filial_id=venda.filial_id, cliente_id=venda.cliente_id, contas=novas
    )
    return len(criadas)


def concluir_se_pronto(venda_id: int) -> bool:
    """`VEN-06`, `VEN-15` (ADR 0042, item 7), na transação do evento que completou a segunda
    condição; idempotente. A venda vira `vendida`; o veículo vai para `vendido` e os outros
    interessados dele, para `perdida` (`VEN-10`); as parcelas entram em Contas a receber; a
    comissão é recalculada e confirmada (`FIN-09`); a transferência no Detran vira tarefa
    (`VEN-17`). O ator é o Sistema. Com o veículo fora do estoque, não conclui e avisa."""
    with transaction.atomic():
        venda = _venda_da_fase(venda_id)
        if venda is None or not pronta_para_concluir(venda):
            return False
        veiculo = veiculos_services.travar(venda.veiculo)
        if veiculo.status != StatusVeiculo.A_VENDA:
            _avisar_fora_do_estoque(venda)
            return False
        agora = relogio.agora()
        with usar_ator(ATOR_SISTEMA):
            venda.vendida_em = agora
            venda.ultimo_contato_em = agora
            estados.transicionar(
                venda,
                StatusVenda.VENDIDA,
                acao="venda.concluir",
                regra="VEN-06",
                mais_campos=("vendida_em", "ultimo_contato_em"),
            )
            veiculos_services.transicionar(
                veiculo,
                StatusVeiculo.VENDIDO,
                origem=veiculos_services.OrigemDaMudanca(ORIGEM, venda.pk, venda.codigo),
                motivo=f"Venda {venda.codigo}",
            )
            _perder_interessados(veiculo.pk, venda.pk)
            dia = _data_local(venda.filial, agora)
            _criar_parcelas(venda, dia)
            financeiro.liberar_contas_da_retirada(_origem(venda), dia)
            _lancar_comissao_pendente(venda)
            financeiro.confirmar_comissao(_origem(venda))
        empresa = conexao().tenant

        def _depois() -> None:
            with tenant_context(empresa):
                _avisar_transferencia(venda.pk)

        transaction.on_commit(_depois)
        painel.renovar()  # a transferência pendente no Início, na hora
    return True


# --- Textos prontos da lista e do detalhe (a tela mostra como vêm) ---

SITUACAO = {
    StatusVenda.INTERESSADO: "Interessado",
    StatusVenda.PROPOSTA: "Proposta enviada",
    StatusVenda.NEGOCIACAO: "Em negociação",
    StatusVenda.AGUARDANDO_APROVACAO: "Aguardando gerente",
    StatusVenda.VENDIDA: "Vendida",
    StatusVenda.PERDIDA: "Perdida",
    StatusVenda.CANCELADA: "Cancelada",
}


def forma_texto(venda: Venda) -> str:
    """ "Pix à vista", "entrada + 12×" (ADR 0042, item 14)."""
    if venda.forma == FormaVenda.A_VISTA:
        return "Pix à vista"
    if venda.forma == FormaVenda.ENTRADA_PARCELAS and venda.num_parcelas:
        return f"entrada + {venda.num_parcelas}×"
    return ""


def situacao_texto(venda: Venda) -> str:
    """A situação da lista (`VEN-19`): "Vendida 06 out", "Perdida · proposta vencida" e, na
    etapa "Assinatura" (a venda ainda em `proposta` ou `negociacao`), "Aguardando assinatura" e
    "Aguardando entrada"."""
    if venda.origem == OrigemVenda.QUITACAO_LOCACAO:
        return OrigemVenda.QUITACAO_LOCACAO.label
    if venda.status == StatusVenda.VENDIDA and venda.vendida_em is not None:
        return f"Vendida {aprovacoes.dia_curto(_data_local(venda.filial, venda.vendida_em))}"
    if venda.status == StatusVenda.PERDIDA and venda.motivo_perda:
        return f"Perdida · {venda.motivo_perda}"
    if venda.status in NA_ASSINATURA and venda.contrato_id is not None:
        if venda.contrato_assinado_em is None:
            return "Aguardando assinatura"
        if venda.conta_entrada_id is not None and venda.entrada_paga_em is None:
            return "Aguardando entrada"
    return SITUACAO.get(StatusVenda(venda.status), "")


def vence_em(venda: Venda) -> date | None:
    """`VEN-13`: a proposta sem resposta vence 7 dias corridos depois do último envio."""
    if venda.status != StatusVenda.PROPOSTA or venda.proposta_enviada_em is None:
        return None
    return _data_local(venda.filial, venda.proposta_enviada_em) + timedelta(days=VENCE_EM_DIAS)


def textos_da_aprovacao(venda: Venda, gerentes: list[str]) -> str | None:
    """`VEN-19`, montados pela API: "Pedido de 8% enviado para Rodrigo Pinheiro. Você não edita a
    proposta até ele decidir." e "Desconto de 8% recusado por Rodrigo Pinheiro: margem baixa
    neste mês. Dê até 5% ou peça uma nova aprovação." Lê só o que a venda guarda (ADR 0019)."""
    if venda.desconto_pedido_pct is None:
        return None
    pct = f"{Decimal(venda.desconto_pedido_pct).normalize():f}".replace(".", ",") + "%"
    limite = f"{LIMITE_DESCONTO_PCT.normalize():f}%"
    if venda.aprovacao == SituacaoAprovacao.PENDENTE:
        para = gerentes[0] if len(gerentes) == 1 else "o gerente"
        return f"Pedido de {pct} enviado para {para}. Você não edita a proposta até ele decidir."
    if venda.aprovacao == SituacaoAprovacao.RECUSADO:
        decisor = venda.aprovacao_decidida_por
        quem = decisor.nome if decisor is not None else "o gerente"
        motivo = (venda.motivo_recusa or "").strip().rstrip(".")
        motivo = f"{motivo[:1].lower()}{motivo[1:]}" if motivo else ""
        return (
            f"Desconto de {pct} recusado por {quem}{': ' + motivo if motivo else ''}. "
            f"Dê até {limite} ou peça uma nova aprovação."
        )
    return None
