"""Regras das vendas: o único lugar que cria venda e muda o status dela (ADR 0009).

- Venda da quitação da locação com intenção de compra (`VEN-11`, `LOC-16`, ADR 0037, itens 4 a
  6): igual à da T-420.
- Venda de balcão, fase 1a da T-502 (ADR 0042, itens 2, 5, 9 e 11): `simular`, `criar`,
  `editar`, `enviar_proposta` (só o estado e a data; o e-mail é da 1c), `registrar_resposta`,
  `pedir_desconto`, `aplicar_decisao_desconto`, `perder` e `vencer_propostas` (`AUT-19`). A
  assinatura, a conclusão em `vendida` e a perda com a entrada paga são da 1b.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django_tenants.utils import tenant_context

from apps.clientes.models import Cliente
from apps.contas import selectors as contas_selectors
from apps.empresas import selectors as empresas_selectors
from apps.filiais import selectors as filiais_selectors
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro
from apps.financeiro.models import RegraComissao
from apps.notificacoes import services as notificacoes
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import StatusVeiculo, Veiculo
from comum import aprovacoes, estados, painel, relogio
from comum.auditoria import ATOR_SISTEMA, Categoria, auditar, usar_ator
from comum.conexao import conexao
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen, so_digitos
from comum.erros import Conflito, ErroDeValidacao, SemPermissao
from comum.permissoes import filiais_permitidas

from . import calculo
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
            raise Conflito("VEN-06", "Cancele a assinatura para mudar a proposta.")
        cliente = venda.cliente
        nome, celular = venda.interessado_nome, venda.interessado_celular
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
            venda.save(
                update_fields=[
                    "cliente",
                    "interessado_nome",
                    "interessado_celular",
                    *CAMPOS_DO_CALCULO,
                    "motivo_recusa",
                    "ultimo_contato_em",
                    "atualizado_em",
                ]
            )
        _recalcular_comissao(venda)
    return venda


def _marcar_envio(venda: Venda) -> tuple[str, ...]:
    """O último envio (o vencimento conta dele) e a primeira entrada em `proposta` (funil)."""
    agora = relogio.agora()
    venda.proposta_enviada_em = agora
    venda.ultimo_contato_em = agora
    if venda.entrou_proposta_em is None:
        venda.entrou_proposta_em = agora
    return ("proposta_enviada_em", "entrou_proposta_em", "ultimo_contato_em")


def enviar_proposta(venda: Venda, por: Any) -> tuple[Venda, bool]:
    """ "Salvar proposta e enviar ao cliente" (`VEN-15`): `interessado` → `proposta`, ou o
    reenvio em `proposta` e `negociacao` (o estado não muda). Nesta fase só o estado e a data:
    o PDF e o e-mail entram na 1c, e a resposta traz `email_enviado: false`."""
    _exigir_mexer(venda, por)
    with transaction.atomic():
        venda = _travar(venda)
        if venda.status == StatusVenda.AGUARDANDO_APROVACAO:
            raise Conflito("APR-01", EM_APROVACAO)
        if venda.status in (StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO):
            with auditar(venda, "venda.reenviar_proposta", Categoria.OPERACAO, regra="VEN-15"):
                campos = _marcar_envio(venda)
                venda.save(update_fields=[*campos, "atualizado_em"])
            return venda, False
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
    return venda, False


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
            raise Conflito("VEN-06", "Cancele a assinatura para mudar a proposta.")
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
        if status == "recusado" and venda.vendedor_id is not None:
            notificacoes.avisar(
                [venda.vendedor_id],
                tipo="desconto_recusado",
                titulo=f"Desconto da {venda.codigo} recusado: {motivo}"[:200],
                link=f"/vendas/{venda.pk}",
            )


def _perder(venda: Venda, motivo: str, *, regra: str, acao: str) -> None:
    """Qualquer estado em andamento → `perdida` (`VEN-13`), na transação de quem chama: cancela o
    pedido de desconto pendente (o pedido vai para `cancelado`) e estorna a comissão pendente
    (`FIN-09`). A `aprovacao` muda antes do cancelamento, para o evento de volta não fazer nada."""
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
    financeiro.estornar_comissao(_origem(venda), motivo=f"Venda perdida: {motivo}"[:200])


def perder(venda: Venda, motivo: str, por: Any) -> Venda:
    """ "Marcar como perdida" (`VEN-13`), motivo obrigatório. O vendedor perde as próprias vendas;
    gerente e administrador, as da filial (decisão do dono de 18 nov 2026). A venda com a entrada
    paga é da fase 1b."""
    _exigir_mexer(venda, por)
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with transaction.atomic():
        venda = _travar(venda)
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
    """A situação da lista (`VEN-19`): "Vendida 06 out", "Perdida · proposta vencida". As da
    etapa "Assinatura" ("Aguardando assinatura", "Aguardando entrada") entram na fase 1b."""
    if venda.origem == OrigemVenda.QUITACAO_LOCACAO:
        return OrigemVenda.QUITACAO_LOCACAO.label
    if venda.status == StatusVenda.VENDIDA and venda.vendida_em is not None:
        return f"Vendida {aprovacoes.dia_curto(_data_local(venda.filial, venda.vendida_em))}"
    if venda.status == StatusVenda.PERDIDA and venda.motivo_perda:
        return f"Perdida · {venda.motivo_perda}"
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
