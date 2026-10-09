"""Regras da locação (LOC-01 a LOC-05, LOC-14, LOC-15, APR-01, FIL-05, IMP-04, FIN-09). Único
lugar que grava nos models de `locacoes`.

Interface para os outros apps (`docs/api/locacoes.md`, "Interface interna"):
`registrar_vistoria_saida` (vistorias, T-016) e `verificar_ativacao`. Os assinantes de
`financeiro.parcela_paga`, `contratos.contrato_assinado` e `aprovacoes.pedido_decidido` ficam em
`eventos.py` e chamam as funções `registrar_*` e `aplicar_decisao_desconto` daqui.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction

from apps.clientes import selectors as clientes_selectors
from apps.clientes.models import Cliente
from apps.contratos import selectors as contratos_selectors
from apps.empresas import selectors as empresas_selectors
from apps.filiais.models import Filial
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.notificacoes.services import avisar
from apps.veiculos import selectors as veiculos_selectors
from apps.veiculos import services as veiculos
from apps.veiculos.models import Categoria as CategoriaVeiculo
from apps.veiculos.models import Extra, StatusVeiculo, Veiculo
from comum import aprovacoes, estados, relogio
from comum.auditoria import Categoria, auditar
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, TransicaoInvalida

from . import calculo
from .models import (
    ABERTAS,
    ExtraLocacao,
    Locacao,
    ParcelamentoMensal,
    Periodicidade,
    PlanoEspecial,
    StatusDesconto,
    StatusLocacao,
    TrechoLocacao,
)

S = StatusLocacao
ORIGEM = "locacao"
GESTAO = frozenset({"administrador", "gerente"})  # desconto acima do limite direto
LINK_MODELOS = "/admin/contratos"
HORAS_DO_RASCUNHO = 24
CAMPOS_DO_FORMULARIO = (
    "periodicidade",
    "plano_especial_id",
    "periodos",
    "inicio",
    "fim_previsto",
    "desconto_pct",
    "forma_pagamento",
    "parcelamento_mensal",
    "primeiro_vencimento",
    "valor_periodo_centavos",
    "diaria_centavos",
    "caucao_centavos",
    "extras_rascunho",
    "cliente_id",
    "veiculo_id",
    "usado_em",
)


def veiculo_indisponivel() -> Conflito:
    return Conflito("LOC-03", "Veículo indisponível no período")


def sem_modelo_de_contrato() -> ErroDeRegra:
    return ErroDeRegra(
        "IMP-04",
        "Publique um modelo de contrato antes de concluir a locação",
        {"link": LINK_MODELOS},
    )


def transicao_invalida(de: str, para: str) -> TransicaoInvalida:
    return TransicaoInvalida(
        "transicao_locacao",
        f"Não é possível passar de {S(de).label.lower()} para {S(para).label.lower()}.",
        {"de": de, "para": para},
    )


def fuso(filial: Filial) -> str:
    return filial.fuso


def data_local(momento: datetime, filial: Filial) -> date:
    return momento.astimezone(ZoneInfo(fuso(filial))).date()


# --- Montagem: entrada do formulário + preços + impedimentos ---


@dataclass
class Montagem:
    cliente: Cliente
    veiculo: Veiculo
    plano: PlanoEspecial | None
    extras: list[calculo.ItemExtra]
    calculo: calculo.Calculo
    diaria_centavos: int
    preco_periodo_centavos: int
    impedimentos: list[dict[str, Any]] = field(default_factory=list)
    avisos: list[dict[str, Any]] = field(default_factory=list)


def _cliente(cliente_id: Any) -> Cliente:
    cliente: Cliente | None = Cliente.objects.filter(pk=cliente_id).first()
    if cliente is None:
        raise ErroDeValidacao({"cliente_id": ["Cliente não encontrado."]})
    return cliente


def _veiculo(veiculo_id: Any) -> Veiculo:
    veiculo: Veiculo | None = (
        Veiculo.objects.select_related("categoria").filter(pk=veiculo_id).first()
    )
    if veiculo is None:
        raise ErroDeValidacao({"veiculo_id": ["Veículo não encontrado."]})
    return veiculo


def _plano(plano_id: Any, periodicidade: str, veiculo: Veiculo) -> PlanoEspecial | None:
    if not plano_id:
        return None
    plano: PlanoEspecial | None = PlanoEspecial.ativos.filter(pk=plano_id).first()
    if plano is None:
        raise ErroDeValidacao({"plano_especial_id": ["Plano especial não encontrado."]})
    if plano.periodicidade != periodicidade:
        rotulo = Periodicidade(plano.periodicidade).label.lower()
        raise ErroDeValidacao({"plano_especial_id": [f"O plano {plano.nome} é {rotulo}."]})
    categorias = set(plano.categorias.values_list("pk", flat=True))
    if categorias and veiculo.categoria_id not in categorias:
        raise ErroDeValidacao(
            {
                "plano_especial_id": [
                    f"O plano {plano.nome} não vale para a categoria {veiculo.categoria.nome}."
                ]
            }
        )
    return plano


def _extras(pedidos: list[dict[str, Any]]) -> list[calculo.ItemExtra]:
    ids = [p["extra_id"] for p in pedidos]
    cadastro = {e.pk: e for e in Extra.ativos.filter(pk__in=ids)}
    faltando = [i for i in ids if i not in cadastro]
    if faltando:
        raise ErroDeValidacao({"extras": ["Extra não encontrado ou desativado."]})
    return [
        calculo.ItemExtra(
            extra_id=e.pk,
            nome=e.nome,
            quantidade=int(p.get("quantidade") or 1),
            valor_centavos=e.valor_centavos,
            cobranca=e.cobranca,
        )
        for p in pedidos
        for e in [cadastro[p["extra_id"]]]
    ]


def _desconto_do_plano(plano: PlanoEspecial | None) -> calculo.DescontoDoPlano | None:
    if plano is None or plano.regra != PlanoEspecial.Regra.DESCONTO:
        return None
    return calculo.DescontoDoPlano(
        pct=Decimal(plano.desconto_pct or 0), a_partir_do_periodo=plano.a_partir_do_periodo or 1
    )


def _outra_locacao_aberta(veiculo: Veiculo, exceto: int | None) -> bool:
    return Locacao.objects.filter(veiculo=veiculo, status__in=ABERTAS).exclude(pk=exceto).exists()


def impedimentos(
    cliente: Cliente, veiculo: Veiculo, filial: Filial, exceto: int | None = None
) -> list[dict[str, Any]]:
    """O que impede confirmar (CLI-05, `cliente_inativo`, CLI-02, FIL-05, LOC-03)."""
    lista = clientes_selectors.impedimentos_para_nova_locacao(cliente)
    tipo = veiculo.categoria.tipo_veiculo
    if cliente.cnh_categoria not in clientes_selectors.CATEGORIA_POR_TIPO[tipo]:
        exigida = clientes_selectors.EXIGIDA_POR_TIPO[tipo]
        lista.append(
            {"codigo": "CLI-02", "mensagem": f"A CNH do cliente não tem a categoria {exigida}."}
        )
    if veiculo.filial_id != filial.pk:
        lista.append(
            {
                "codigo": "FIL-05",
                "mensagem": "O veículo é de outra filial. Transfira antes de alugar.",
            }
        )
    disponivel = veiculo.status in (StatusVeiculo.DISPONIVEL, StatusVeiculo.RESERVADO)
    if not disponivel or _outra_locacao_aberta(veiculo, exceto):
        lista.append(veiculo_indisponivel().como_dict() | {"detalhes": None})
    return [{"codigo": i["codigo"], "mensagem": i["mensagem"]} for i in lista]


def avisos(cliente: Cliente, filial: Filial) -> list[dict[str, Any]]:
    """O que não impede confirmar, mas impede a retirada (CLI-03, CLI-02 vencida, IMP-04)."""
    lista: list[dict[str, Any]] = []
    if cliente.status == clientes_selectors.S.INCOMPLETO:
        lista.append(
            {"codigo": "CLI-03", "mensagem": "Complete o cadastro do cliente antes da retirada."}
        )
    hoje = relogio.hoje()
    if clientes_selectors.situacao_da_cnh(cliente.cnh_validade, hoje) == "vencida_impede":
        lista.append(
            {"codigo": "CLI-02", "mensagem": "A CNH do cliente está vencida há mais de 30 dias."}
        )
    if contratos_selectors.modelo_publicado() is None:
        erro = sem_modelo_de_contrato()
        lista.append({"codigo": erro.codigo, "mensagem": erro.mensagem, "link": LINK_MODELOS})
    return lista


def montar(
    dados: dict[str, Any],
    filial: Filial,
    *,
    desconto_pct: Decimal | None = None,
    exceto: int | None = None,
) -> Montagem:
    """Preços de hoje (LOC-15) sobre o formulário. Não grava nada."""
    cliente = _cliente(dados.get("cliente_id"))
    veiculo = _veiculo(dados.get("veiculo_id"))
    periodicidade = dados["periodicidade"]
    plano = _plano(dados.get("plano_especial_id"), periodicidade, veiculo)
    extras = _extras(list(dados.get("extras") or []))
    preco = veiculos_selectors.preco_vigente(veiculo.categoria_id, relogio.hoje())
    if preco is None:
        raise ErroDeRegra("LOC-01", "A categoria do veículo não tem preço vigente.")
    tabela = {
        Periodicidade.DIARIA: preco.diaria_centavos,
        Periodicidade.SEMANAL: preco.semanal_centavos,
        Periodicidade.MENSAL: preco.mensal_centavos,
    }[Periodicidade(periodicidade)]
    preco_periodo = (
        plano.preco_centavos
        if plano is not None and plano.regra == PlanoEspecial.Regra.PRECO_FIXO
        else tabela
    )
    entrada = calculo.Entrada(
        periodicidade=periodicidade,
        inicio=dados["inicio"],
        fuso=fuso(filial),
        preco_periodo_centavos=int(preco_periodo or 0),
        diaria_centavos=preco.diaria_centavos,
        caucao_centavos=preco.caucao_centavos,
        periodos=dados.get("periodos"),
        fim_previsto=dados.get("fim_previsto"),
        desconto_do_plano=_desconto_do_plano(plano),
        extras=tuple(extras),
        desconto_pct=Decimal(
            desconto_pct if desconto_pct is not None else dados.get("desconto_pct") or 0
        ),
        parcelamento_mensal=_parcelamento(dados),
        primeiro_vencimento=dados.get("primeiro_vencimento"),
    )
    return Montagem(
        cliente=cliente,
        veiculo=veiculo,
        plano=plano,
        extras=extras,
        calculo=calculo.calcular(entrada),
        diaria_centavos=preco.diaria_centavos,
        preco_periodo_centavos=int(preco_periodo or 0),
        impedimentos=impedimentos(cliente, veiculo, filial, exceto),
        avisos=avisos(cliente, filial),
    )


def _parcelamento(dados: dict[str, Any]) -> str:
    if dados.get("periodicidade") != Periodicidade.MENSAL:
        return ""
    return str(dados.get("parcelamento_mensal") or ParcelamentoMensal.A_VISTA)


def limite_de_desconto() -> Decimal:
    return Decimal(empresas_selectors.configuracao().desconto_sem_aprovacao_pct)


def precisa_aprovacao_desconto(desconto_pct: Decimal, usuario: Any) -> bool:
    """LOC-03: acima do limite, só o vendedor pede (`APR-01`); gerente e administrador dão
    direto (decisão de 07 out 2026)."""
    return desconto_pct > limite_de_desconto() and getattr(usuario, "perfil", "") not in GESTAO


# --- Rascunho ---


def _preencher(locacao: Locacao, dados: dict[str, Any], montagem: Montagem) -> None:
    locacao.cliente = montagem.cliente
    locacao.veiculo = montagem.veiculo
    locacao.periodicidade = dados["periodicidade"]
    locacao.plano_especial = montagem.plano
    locacao.periodos = montagem.calculo.periodos
    locacao.inicio = dados["inicio"]
    locacao.fim_previsto = montagem.calculo.fim_previsto
    locacao.desconto_pct = Decimal(dados.get("desconto_pct") or 0)
    locacao.forma_pagamento = dados["forma_pagamento"]
    locacao.parcelamento_mensal = _parcelamento(dados)
    locacao.primeiro_vencimento = dados.get("primeiro_vencimento")
    locacao.valor_periodo_centavos = montagem.preco_periodo_centavos
    locacao.diaria_centavos = montagem.diaria_centavos
    locacao.caucao_centavos = montagem.calculo.caucao_centavos
    locacao.extras_rascunho = [
        {"extra_id": e.extra_id, "quantidade": e.quantidade} for e in montagem.extras
    ]
    locacao.usado_em = relogio.agora()


def criar_rascunho(dados: dict[str, Any], filial: Filial, vendedor: Any) -> Locacao:
    """O código já sai reservado (LOC-2856). Rascunho não ocupa o veículo."""
    montagem = montar(dados, filial)
    locacao = Locacao(filial=filial, vendedor=vendedor)
    _preencher(locacao, dados, montagem)
    with transaction.atomic(), auditar(locacao, "locacao.criar", Categoria.OPERACAO):
        locacao.save()
    return locacao


def _travar(locacao: Locacao | int) -> Locacao:
    pk = locacao if isinstance(locacao, int) else locacao.pk
    travada: Locacao = Locacao.objects.select_for_update().get(pk=pk)
    return travada


def _recarregar(locacao: Locacao) -> None:
    locacao.refresh_from_db()
    locacao._status_salvo = locacao.status


def editar_rascunho(locacao: Locacao, dados: dict[str, Any]) -> Locacao:
    with transaction.atomic():
        travada = _travar(locacao)
        if travada.status != S.RASCUNHO:
            raise transicao_invalida(travada.status, S.RASCUNHO)
        completos = {**_formulario(travada), **dados}
        montagem = montar(completos, travada.filial, exceto=travada.pk)
        with auditar(travada, "locacao.editar", Categoria.OPERACAO):
            _preencher(travada, completos, montagem)
            travada.save(update_fields=[*_campos_salvos(), "atualizado_em"])
    _recarregar(locacao)
    return locacao


def _campos_salvos() -> list[str]:
    return [
        c.replace("plano_especial_id", "plano_especial")
        .replace("cliente_id", "cliente")
        .replace("veiculo_id", "veiculo")
        for c in CAMPOS_DO_FORMULARIO
    ]


def _formulario(locacao: Locacao) -> dict[str, Any]:
    """O formulário guardado, no formato da entrada (para o PATCH parcial)."""
    return {
        "cliente_id": locacao.cliente_id,
        "veiculo_id": locacao.veiculo_id,
        "periodicidade": locacao.periodicidade,
        "plano_especial_id": locacao.plano_especial_id,
        "inicio": locacao.inicio,
        "periodos": locacao.periodos,
        "fim_previsto": None,
        "extras": list(locacao.extras_rascunho),
        "desconto_pct": locacao.desconto_pct,
        "forma_pagamento": locacao.forma_pagamento,
        "parcelamento_mensal": locacao.parcelamento_mensal or None,
        "primeiro_vencimento": locacao.primeiro_vencimento,
    }


def cancelar_rascunhos_sem_uso() -> int:
    """Rascunho sem uso por 24 h vai para `cancelada` (só o evento do cancelamento)."""
    limite = relogio.agora() - timedelta(hours=HORAS_DO_RASCUNHO)
    cancelados = 0
    for pk in Locacao.objects.filter(status=S.RASCUNHO, usado_em__lt=limite).values_list(
        "pk", flat=True
    ):
        with transaction.atomic():
            travada = _travar(pk)
            if travada.status != S.RASCUNHO or (travada.usado_em or limite) >= limite:
                continue
            travada.cancelada_em = relogio.agora()
            travada.motivo_cancelamento = "Rascunho sem uso por 24 horas"
            estados.transicionar(
                travada,
                S.CANCELADA,
                motivo=travada.motivo_cancelamento,
                acao="locacao.cancelar_rascunho",
                mais_campos=("cancelada_em", "motivo_cancelamento"),
            )
            cancelados += 1
    return cancelados


# --- Confirmação ---


def _primeiro_impedimento(lista: list[dict[str, Any]]) -> Exception | None:
    for item in lista:
        if item["codigo"] != "LOC-03":
            return ErroDeRegra(item["codigo"], item["mensagem"])
    if lista:
        return veiculo_indisponivel()
    return None


def _origem(locacao: Locacao) -> financeiro.Origem:
    return financeiro.Origem(ORIGEM, locacao.pk, locacao.codigo)


def _contas(locacao: Locacao, conta: calculo.Calculo) -> list[financeiro.NovaConta]:
    total = len(conta.parcelas)
    contas = [
        financeiro.NovaConta(
            tipo="parcela",
            vencimento=p.vencimento,
            valor_centavos=p.valor_centavos,
            numero_parcela=p.numero,
            total_parcelas=total,
        )
        for p in conta.parcelas
    ]
    contas.append(
        financeiro.NovaConta(
            tipo="caucao",
            vencimento=conta.parcelas[0].vencimento,
            valor_centavos=conta.caucao_centavos,
            observacao="Devolver na entrega",
        )
    )
    return contas


def confirmar(locacao: Locacao, usuario: Any, primeiro_vencimento: date | None = None) -> Locacao:
    """`rascunho` → `aguardando_retirada`. Na mesma transação: preços de hoje congelados
    (LOC-15), contas a receber (parcelas e caução), comissão `pendente` (FIN-09), reserva do
    veículo com início futuro e, com desconto acima do limite, o pedido `APR-01`."""
    with transaction.atomic():
        travada = _travar(locacao)
        if travada.status != S.RASCUNHO:
            raise transicao_invalida(travada.status, S.AGUARDANDO_RETIRADA)
        dados = _formulario(travada)
        if primeiro_vencimento is not None:
            dados["primeiro_vencimento"] = primeiro_vencimento
        pedido_pct = Decimal(travada.desconto_pct)
        pendente = precisa_aprovacao_desconto(pedido_pct, usuario)
        montagem = montar(
            dados,
            travada.filial,
            desconto_pct=Decimal("0.00") if pendente else pedido_pct,
            exceto=travada.pk,
        )
        erro = _primeiro_impedimento(montagem.impedimentos)
        if erro is not None and not isinstance(erro, Conflito):
            raise erro
        if contratos_selectors.modelo_publicado() is None:
            raise sem_modelo_de_contrato()
        if erro is not None:
            raise erro

        _preencher(travada, dados, montagem)
        travada.precos_de = relogio.hoje()
        travada.primeiro_vencimento = montagem.calculo.parcelas[0].vencimento
        if pendente:
            travada.desconto_pct = Decimal("0.00")
            travada.desconto_pedido_pct = pedido_pct
            travada.desconto_status = StatusDesconto.PENDENTE
        try:
            with transaction.atomic():
                estados.transicionar(
                    travada,
                    S.AGUARDANDO_RETIRADA,
                    acao="locacao.confirmar",
                    regra="LOC-15",
                    mais_campos=(
                        *_campos_salvos(),
                        "precos_de",
                        "desconto_pedido_pct",
                        "desconto_status",
                    ),
                )
        except IntegrityError as erro_banco:
            raise veiculo_indisponivel() from erro_banco

        for item in montagem.extras:
            ExtraLocacao.objects.create(
                locacao=travada,
                extra_id=item.extra_id,
                nome=item.nome,
                quantidade=item.quantidade,
                valor_centavos=item.valor_centavos,
                cobranca=item.cobranca,
            )
        TrechoLocacao.objects.create(
            locacao=travada,
            veiculo=travada.veiculo,
            inicio=travada.inicio,
            valor_periodo_centavos=travada.valor_periodo_centavos,
            diaria_centavos=travada.diaria_centavos,
        )
        financeiro.criar_contas(
            _origem(travada),
            filial_id=travada.filial_id,
            cliente_id=travada.cliente_id,
            contas=_contas(travada, montagem.calculo),
        )
        financeiro.lancar_comissao(
            _origem(travada),
            usuario_id=travada.vendedor_id,
            valor_centavos=empresas_selectors.configuracao().comissao_locacao_centavos,
        )
        if data_local(travada.inicio, travada.filial) > relogio.hoje():
            veiculo = travada.veiculo
            if veiculo.status == StatusVeiculo.DISPONIVEL:
                veiculos.transicionar(
                    veiculo,
                    StatusVeiculo.RESERVADO,
                    origem=veiculos.OrigemDaMudanca(ORIGEM, travada.pk, travada.codigo),
                    motivo=f"Reserva da {travada.codigo}",
                )
        if pendente:
            _pedir_desconto(travada, usuario, pedido_pct)
    _recarregar(locacao)
    return locacao


def _pedir_desconto(locacao: Locacao, usuario: Any, pct: Decimal) -> None:
    calculo_com_desconto = calculo.calcular(_entrada_congelada(locacao, pct))
    ref = aprovacoes.pedir(
        tipo="APR-01",
        origem_tipo=ORIGEM,
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        filial_id=locacao.filial_id,
        solicitante=usuario,
        titulo="Desconto acima do limite",
        detalhe=f"{locacao.codigo} · {locacao.cliente.nome} · desconto de {pct}%".replace(".", ","),
        pct=pct,
        valor_centavos=calculo_com_desconto.desconto_centavos,
        dados={"desconto_pct": str(pct)},
    )
    locacao.pedido_desconto_id = ref.id
    locacao.save(update_fields=["pedido_desconto_id", "atualizado_em"])


def _entrada_congelada(locacao: Locacao, desconto_pct: Decimal) -> calculo.Entrada:
    """Os preços congelados na confirmação, para refazer as parcelas (APR-01)."""
    extras = tuple(
        calculo.ItemExtra(e.extra_id, e.nome, e.quantidade, e.valor_centavos, e.cobranca)
        for e in locacao.extras.all()
    )
    return calculo.Entrada(
        periodicidade=locacao.periodicidade,
        inicio=locacao.inicio,
        fuso=fuso(locacao.filial),
        preco_periodo_centavos=locacao.valor_periodo_centavos,
        diaria_centavos=locacao.diaria_centavos,
        caucao_centavos=locacao.caucao_centavos,
        periodos=locacao.periodos,
        desconto_do_plano=_desconto_do_plano(locacao.plano_especial),
        extras=extras,
        desconto_pct=desconto_pct,
        parcelamento_mensal=locacao.parcelamento_mensal,
        primeiro_vencimento=locacao.primeiro_vencimento,
    )


def calculo_congelado(locacao: Locacao) -> calculo.Calculo:
    return calculo.calcular(_entrada_congelada(locacao, Decimal(locacao.desconto_pct)))


def aplicar_decisao_desconto(locacao_id: int, status: str, motivo: str) -> None:
    """Volta do `APR-01`. Aprovado: as parcelas em aberto são refeitas com o desconto. Recusado:
    o desconto fica 0 e o vendedor é avisado com o motivo. Cancelado: o desconto fica 0."""
    with transaction.atomic():
        if not Locacao.objects.filter(pk=locacao_id).exists():
            return
        travada = _travar(locacao_id)
        if travada.desconto_status != StatusDesconto.PENDENTE:
            return
        if status == "aprovado":
            pct = Decimal(travada.desconto_pedido_pct or 0)
            novo = calculo.calcular(_entrada_congelada(travada, pct))
            por_numero = {p.numero: p.valor_centavos for p in novo.parcelas}
            for conta in financeiro_selectors.contas_da_origem(ORIGEM, travada.pk).filter(
                tipo="parcela", status="aberta"
            ):
                if conta.numero_parcela in por_numero:
                    financeiro.ajustar_valor(
                        conta,
                        por_numero[conta.numero_parcela],
                        motivo=f"Desconto de {pct}% aprovado".replace(".", ","),
                        regra="APR-01",
                    )
            novo_status, acao = StatusDesconto.APROVADO, "locacao.aprovar_desconto"
            travada.desconto_pct = pct
        elif status == "recusado":
            novo_status, acao = StatusDesconto.RECUSADO, "locacao.recusar_desconto"
        else:
            novo_status, acao = StatusDesconto.CANCELADO, "locacao.cancelar_desconto"
        with auditar(travada, acao, Categoria.OPERACAO, motivo=motivo, regra="APR-01"):
            travada.desconto_status = novo_status
            travada.save(update_fields=["desconto_pct", "desconto_status", "atualizado_em"])
        if novo_status == StatusDesconto.RECUSADO:
            avisar(
                [travada.vendedor_id],
                tipo="desconto_recusado",
                titulo=f"Desconto da {travada.codigo} recusado: {motivo}"[:200],
                link=f"/locacoes/{travada.pk}",
            )


# --- Ativação: vistoria de saída + contrato assinado + 1º pagamento, em qualquer ordem ---


def verificar_ativacao(locacao: Locacao | int) -> bool:
    """Com as três condições, `aguardando_retirada` → `ativa`; na mesma transação o veículo vira
    `alugado` e a comissão fica `confirmada` (FIN-09)."""
    with transaction.atomic():
        travada = _travar(locacao)
        if travada.status != S.AGUARDANDO_RETIRADA:
            return False
        condicoes = (
            travada.vistoria_saida_ok_em,
            travada.contrato_assinado_em,
            travada.primeiro_pagamento_em,
        )
        if any(c is None for c in condicoes):
            return False
        estados.transicionar(
            travada,
            S.ATIVA,
            motivo="Vistoria de saída, contrato assinado e 1º pagamento",
            acao="locacao.ativar",
        )
        veiculos.transicionar(
            travada.veiculo,
            StatusVeiculo.ALUGADO,
            origem=veiculos.OrigemDaMudanca(ORIGEM, travada.pk, travada.codigo),
            motivo=f"Retirada da {travada.codigo}",
        )
        financeiro.confirmar_comissao(_origem(travada))
    if isinstance(locacao, Locacao):
        _recarregar(locacao)
    return True


def _registrar_condicao(locacao_id: int, campo: str, momento: datetime, acao: str) -> bool:
    with transaction.atomic():
        travada = _travar(locacao_id)
        if travada.status != S.AGUARDANDO_RETIRADA or getattr(travada, campo) is not None:
            return False
        with auditar(travada, acao, Categoria.OPERACAO):
            setattr(travada, campo, momento)
            travada.save(update_fields=[campo, "atualizado_em"])
        return verificar_ativacao(travada.pk)


def registrar_vistoria_saida(
    locacao: Locacao, *, km: int, concluida_em: datetime | None = None
) -> bool:
    """Chamado por `vistorias` ao concluir a saída (T-016). Fora de `aguardando_retirada`: 409."""
    with transaction.atomic():
        travada = _travar(locacao)
        if travada.status != S.AGUARDANDO_RETIRADA:
            raise transicao_invalida(travada.status, S.ATIVA)
        if travada.km_saida != km:
            travada.km_saida = km
            travada.save(update_fields=["km_saida", "atualizado_em"])
        ativou = _registrar_condicao(
            travada.pk,
            "vistoria_saida_ok_em",
            concluida_em or relogio.agora(),
            "locacao.vistoria_saida",
        )
    _recarregar(locacao)
    return ativou


def registrar_contrato_assinado(locacao_id: int, assinado_em: datetime | None) -> bool:
    """Assinante de `contratos.contrato_assinado` (o aditivo não conta)."""
    return _registrar_condicao(
        locacao_id,
        "contrato_assinado_em",
        assinado_em or relogio.agora(),
        "locacao.contrato_assinado",
    )


def registrar_pagamento(locacao_id: int) -> bool:
    """Assinante de `financeiro.parcela_paga`: 1ª parcela **e** caução pagas."""
    momento = financeiro_selectors.primeiro_pagamento_em(ORIGEM, locacao_id)
    if momento is None:
        return False
    return _registrar_condicao(
        locacao_id, "primeiro_pagamento_em", momento, "locacao.primeiro_pagamento"
    )


# --- Planos especiais (tela Precos; só administrador) ---


def _validar_plano(dados: dict[str, Any]) -> dict[str, Any]:
    regra = dados.get("regra")
    erros: dict[str, list[str]] = {}
    if regra == PlanoEspecial.Regra.PRECO_FIXO:
        if not dados.get("preco_centavos"):
            erros["preco_centavos"] = ["Informe o preço do plano."]
        dados["desconto_pct"] = None
        dados["a_partir_do_periodo"] = None
    elif regra == PlanoEspecial.Regra.DESCONTO:
        pct = dados.get("desconto_pct")
        if pct is None or not Decimal(0) < Decimal(pct) <= Decimal(100):
            erros["desconto_pct"] = ["Informe um desconto entre 0,01% e 100%."]
        dados["preco_centavos"] = None
        dados["a_partir_do_periodo"] = dados.get("a_partir_do_periodo") or 1
    categorias = dados.get("categorias") or []
    if CategoriaVeiculo.objects.filter(pk__in=categorias).count() != len(set(categorias)):
        erros["categorias"] = ["Categoria não encontrada."]
    if erros:
        raise ErroDeValidacao(erros)
    return dados


def _nome_do_plano_em_uso(nome: str, exceto: int | None = None) -> None:
    if PlanoEspecial.objects.filter(nome__iexact=nome).exclude(pk=exceto or 0).exists():
        raise Conflito("nome_em_uso", "Já existe um plano com este nome")


def _gravar_plano(plano: PlanoEspecial, dados: dict[str, Any], acao: str) -> PlanoEspecial:
    categorias = dados.pop("categorias", None)
    with transaction.atomic(), auditar(plano, acao, Categoria.CONFIGURACOES, regra="LOC-01"):
        for campo, valor in dados.items():
            setattr(plano, campo, valor)
        plano.save()
        if categorias is not None:
            plano.categorias.set(categorias)
    return plano


def criar_plano(dados: dict[str, Any]) -> PlanoEspecial:
    """Vale para locações novas (LOC-15)."""
    dados = _validar_plano(dict(dados))
    _nome_do_plano_em_uso(dados["nome"])
    return _gravar_plano(PlanoEspecial(), dados, "plano_especial.criar")


def editar_plano(plano: PlanoEspecial, dados: dict[str, Any]) -> PlanoEspecial:
    """A mudança vale para locações novas; quem já confirmou mantém o preço (LOC-15)."""
    completos = {
        "regra": plano.regra,
        "preco_centavos": plano.preco_centavos,
        "desconto_pct": plano.desconto_pct,
        "a_partir_do_periodo": plano.a_partir_do_periodo,
        **dados,
    }
    completos = _validar_plano(completos)
    if "nome" in dados:
        _nome_do_plano_em_uso(dados["nome"], exceto=plano.pk)
    return _gravar_plano(plano, completos, "plano_especial.editar")


def desativar_plano(plano: PlanoEspecial) -> PlanoEspecial:
    """Sai das locações novas; as que já usam o plano continuam."""
    if not plano.ativo:
        return plano
    return _gravar_plano(plano, {"ativo": False}, "plano_especial.desativar")
