"""Regras da locação (LOC-01 a LOC-05, LOC-08, LOC-10 a LOC-15, APR-01, APR-02, FIL-05, IMP-04,
FIN-09). Único lugar que grava nos models de `locacoes`.

Interface para os outros apps (`docs/api/locacoes.md`, "Interface interna"):
`registrar_vistoria_saida` e `encerrar` (vistorias, T-016), `calcular_atraso`,
`calcular_encerramento` e `verificar_ativacao`. Os assinantes de `financeiro.parcela_paga`,
`contratos.contrato_assinado` e `aprovacoes.pedido_decidido` ficam em `eventos.py` e chamam as
funções `registrar_*`, `aplicar_decisao_desconto` e `aplicar_decisao_cancelamento` daqui.
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
from comum.dinheiro import aplicar_percentual, dividir_em_parcelas, formatar_reais
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, SemPermissao, TransicaoInvalida
from comum.eventos import publicar
from comum.permissoes import pode

from . import calculo, contrato, fim
from .models import (
    ABERTAS,
    ExtraLocacao,
    Locacao,
    ParcelamentoMensal,
    Periodicidade,
    PlanoEspecial,
    StatusDesconto,
    StatusLocacao,
    StatusTroca,
    TrechoLocacao,
    TrocaVeiculo,
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


# --- Atraso (LOC-10, LOC-11, FIL-03) ---


def _tolerancia() -> timedelta:
    return timedelta(minutes=empresas_selectors.configuracao().tolerancia_atraso_minutos)


def _feriados(filial: Filial, de: datetime, ate: datetime) -> set[date]:
    return set(
        filial.feriados.filter(
            ativo=True,
            data__gte=data_local(de, filial) - timedelta(days=1),
            data__lte=data_local(ate, filial) + timedelta(days=400),
        ).values_list("data", flat=True)
    )


def atraso_desde(locacao: Locacao, fim_previsto: datetime, momento: datetime) -> fim.Atraso:
    filial = locacao.filial
    return fim.calcular_atraso(
        fim_previsto,
        momento,
        tolerancia=_tolerancia(),
        horario=filial.horario or {},
        feriados=_feriados(filial, min(fim_previsto, momento), max(fim_previsto, momento)),
        fuso=fuso(filial),
        diaria_centavos=locacao.diaria_centavos,
    )


def calcular_atraso(locacao: Locacao, momento: datetime | None = None) -> dict[str, Any]:
    """`{dias, valor_centavos}` se a devolução for em `momento` (padrão agora), usado no acerto
    (T-016). Soma o atraso que já corria quando a locação atrasada foi renovada (LOC-08)."""
    atual = atraso_desde(locacao, locacao.fim_previsto, momento or relogio.agora())
    return {
        "dias": atual.dias + locacao.atraso_anterior_dias,
        "valor_centavos": atual.valor_centavos + locacao.atraso_anterior_centavos,
        "devolucao_considerada_em": atual.devolucao_considerada_em,
    }


def marcar_devolucoes_atrasadas(agora: datetime | None = None) -> int:
    """AUT-02 (de hora em hora): `ativa` → `devolucao_atrasada` no dia seguinte ao fim
    previsto, quando a devolução feita agora já teria atraso (LOC-10, LOC-11). Idempotente."""
    agora = agora or relogio.agora()
    marcadas = 0
    candidatas = Locacao.objects.filter(
        status=S.ATIVA, fim_previsto__lt=agora - _tolerancia()
    ).values_list("pk", flat=True)
    for pk in candidatas:
        with transaction.atomic():
            travada = _travar(pk)
            if travada.status != S.ATIVA:
                continue
            if data_local(agora, travada.filial) <= data_local(
                travada.fim_previsto, travada.filial
            ):
                continue
            atraso = atraso_desde(travada, travada.fim_previsto, agora)
            if atraso.dias == 0:
                continue
            estados.transicionar(
                travada,
                S.DEVOLUCAO_ATRASADA,
                motivo="Passou do fim previsto e da tolerância sem devolução",
                acao="locacao.marcar_atraso",
                regra="LOC-10",
            )
            marcadas += 1
    return marcadas


# --- Renovação (LOC-08, LOC-15) ---


def _sem_cancelamento_em_curso(locacao: Locacao) -> None:
    if locacao.cancelamento_status in (StatusDesconto.PENDENTE, StatusDesconto.APROVADO):
        raise Conflito(
            "cancelamento_em_andamento",
            "Esta locação tem um cancelamento pedido ou aprovado.",
            {"cancelamento": locacao.cancelamento_status},
        )


@dataclass(frozen=True)
class Renovacao:
    calculo: calculo.Calculo
    preco_periodo_centavos: int  # sem descontos, como o congelado na confirmação (base do LOC-12)
    diaria_centavos: int
    inicio: datetime  # onde começa o período novo
    atraso: fim.Atraso  # o atraso até a renovação, que continua cobrado no acerto (LOC-08)
    extras_centavos: dict[int, int]  # extra_id → valor de hoje


def _inicio_da_renovacao(locacao: Locacao, agora: datetime) -> tuple[datetime, fim.Atraso]:
    """LOC-08: dentro do prazo (fim previsto mais a tolerância, LOC-10, LOC-11), o período novo
    começa no fim previsto antigo. Depois do prazo, mesmo com a locação ainda `ativa`, começa na
    hora da renovação, e o atraso até ali fica guardado para o acerto: nenhum dia é pago duas
    vezes."""
    atraso = atraso_desde(locacao, locacao.fim_previsto, agora)
    if atraso.dias == 0:
        return locacao.fim_previsto, atraso
    return agora, atraso


def montar_renovacao(locacao: Locacao, dados: dict[str, Any]) -> Renovacao:
    """As parcelas novas com o preço de hoje (LOC-08, LOC-15): a tabela, ou o preço do plano
    especial ativo; o plano de desconto conta os períodos desde o começo da locação. O mesmo
    percentual de desconto continua, sem novo `APR-01`, e os extras por período vão pelo valor
    de hoje do cadastro; a caução não se cobra de novo. Não grava nada."""
    if locacao.status not in (S.ATIVA, S.DEVOLUCAO_ATRASADA):
        raise Conflito(
            "transicao_locacao",
            "Só dá para renovar uma locação ativa ou com a devolução atrasada.",
            {"de": locacao.status},
        )
    _sem_cancelamento_em_curso(locacao)
    preco = veiculos_selectors.preco_vigente(locacao.veiculo.categoria_id, relogio.hoje())
    if preco is None:
        raise ErroDeRegra("LOC-01", "A categoria do veículo não tem preço vigente.")
    plano = locacao.plano_especial
    if plano is not None and not plano.ativo:
        plano = None  # plano desativado: a renovação usa a tabela
    preco_periodo = {
        Periodicidade.DIARIA: preco.diaria_centavos,
        Periodicidade.SEMANAL: preco.semanal_centavos,
        Periodicidade.MENSAL: preco.mensal_centavos,
    }[Periodicidade(locacao.periodicidade)]
    if plano is not None and plano.regra == PlanoEspecial.Regra.PRECO_FIXO:
        preco_periodo = int(plano.preco_centavos or 0)
    desconto_do_plano = _desconto_do_plano(plano)
    if desconto_do_plano is not None:
        desconto_do_plano = calculo.DescontoDoPlano(
            pct=desconto_do_plano.pct,
            a_partir_do_periodo=max(1, desconto_do_plano.a_partir_do_periodo - locacao.periodos),
        )
    por_periodo = [e for e in locacao.extras.select_related("extra") if e.cobranca == "por_periodo"]
    valores_de_hoje = {e.extra_id: e.extra.valor_centavos for e in por_periodo}
    extras = tuple(
        calculo.ItemExtra(e.extra_id, e.nome, e.quantidade, valores_de_hoje[e.extra_id], e.cobranca)
        for e in por_periodo
    )
    inicio, atraso = _inicio_da_renovacao(locacao, relogio.agora())
    novo_fim = dados.get("fim_previsto")
    if novo_fim is not None and novo_fim <= max(locacao.fim_previsto, inicio):
        raise ErroDeValidacao(
            {"fim_previsto": ["O novo fim previsto precisa ser depois do fim atual."]}
        )
    conta = calculo.calcular(
        calculo.Entrada(
            periodicidade=locacao.periodicidade,
            inicio=inicio,
            fuso=fuso(locacao.filial),
            preco_periodo_centavos=preco_periodo,
            diaria_centavos=preco.diaria_centavos,
            caucao_centavos=0,
            periodos=dados.get("periodos"),
            fim_previsto=novo_fim,
            desconto_do_plano=desconto_do_plano,
            extras=extras,
            desconto_pct=Decimal(locacao.desconto_pct),
            parcelamento_mensal=locacao.parcelamento_mensal,
        )
    )
    return Renovacao(conta, preco_periodo, preco.diaria_centavos, inicio, atraso, valores_de_hoje)


def _ultima_parcela(locacao: Locacao) -> int:
    numeros = [
        c.numero_parcela or 0
        for c in financeiro_selectors.contas_da_origem(ORIGEM, locacao.pk)
        if c.tipo == "parcela"
    ]
    return max(numeros, default=0)


def renovar(locacao: Locacao, dados: dict[str, Any], usuario: Any) -> Locacao:
    """LOC-08: estende o fim previsto e cria as parcelas novas na mesma locação, com o preço de
    hoje (períodos e extras). O aditivo sai para assinatura sem travar a renovação. Sem comissão
    (FIN-09). Depois do prazo, o período novo começa agora e o atraso já corrido fica guardado
    para o acerto; a `devolucao_atrasada` volta a `ativa` se o novo fim for futuro."""
    with transaction.atomic():
        travada = _travar(locacao)
        renovacao = montar_renovacao(travada, dados)
        conta = renovacao.calculo
        agora = relogio.agora()
        mais_campos = [
            "fim_previsto",
            "periodos",
            "renovacoes",
            "valor_periodo_centavos",
            "diaria_centavos",
        ]
        if renovacao.atraso.dias:
            travada.atraso_anterior_dias += renovacao.atraso.dias
            travada.atraso_anterior_centavos += renovacao.atraso.valor_centavos
            mais_campos += ["atraso_anterior_dias", "atraso_anterior_centavos"]
        for extra in travada.extras.filter(extra_id__in=renovacao.extras_centavos):
            novo = renovacao.extras_centavos[extra.extra_id]
            if extra.valor_centavos != novo:
                with auditar(extra, "locacao.renovar_extra", Categoria.OPERACAO, regra="LOC-08"):
                    extra.valor_centavos = novo
                    extra.save(update_fields=["valor_centavos", "atualizado_em"])
        ultima = _ultima_parcela(travada)
        total = ultima + len(conta.parcelas)
        financeiro.criar_contas(
            _origem(travada),
            filial_id=travada.filial_id,
            cliente_id=travada.cliente_id,
            contas=[
                financeiro.NovaConta(
                    tipo="parcela",
                    vencimento=p.vencimento,
                    valor_centavos=p.valor_centavos,
                    numero_parcela=ultima + p.numero,
                    total_parcelas=total,
                    observacao=f"Renovação {travada.renovacoes + 1}",
                )
                for p in conta.parcelas
            ],
        )
        travada.fim_previsto = conta.fim_previsto
        travada.periodos += conta.periodos
        travada.renovacoes += 1
        travada.valor_periodo_centavos = renovacao.preco_periodo_centavos
        travada.diaria_centavos = renovacao.diaria_centavos
        motivo = f"Renovação por {conta.periodos} {_unidade(travada, conta.periodos)}"
        if travada.status == S.DEVOLUCAO_ATRASADA and conta.fim_previsto > agora:
            estados.transicionar(
                travada,
                S.ATIVA,
                motivo=motivo,
                acao="locacao.renovar",
                regra="LOC-08",
                mais_campos=tuple(mais_campos),
            )
        else:
            with auditar(
                travada, "locacao.renovar", Categoria.OPERACAO, motivo=motivo, regra="LOC-08"
            ):
                travada.save(update_fields=[*mais_campos, "atualizado_em"])
        TrechoLocacao.objects.filter(locacao=travada, fim__isnull=True).update(
            valor_periodo_centavos=travada.valor_periodo_centavos,
            diaria_centavos=travada.diaria_centavos,
            atualizado_em=agora,
        )
        contrato.gerar_aditivo(travada)
    _recarregar(locacao)
    return locacao


def _unidade(locacao: Locacao, n: int) -> str:
    singular, plural = calculo.UNIDADE[Periodicidade(locacao.periodicidade)]
    return singular if n == 1 else plural


# --- Troca de veículo (LOC-09) ---


def troca_pendente(locacao: Locacao | int) -> TrocaVeiculo | None:
    locacao_id = locacao.pk if isinstance(locacao, Locacao) else locacao
    troca: TrocaVeiculo | None = (
        TrocaVeiculo.objects.select_related("veiculo_antigo", "veiculo_novo")
        .filter(locacao_id=locacao_id, status=StatusTroca.PENDENTE)
        .first()
    )
    return troca


@dataclass(frozen=True)
class PrecoDaTroca:
    periodo_centavos: int  # sem descontos, como o congelado na confirmação (base do LOC-12)
    diaria_centavos: int
    caucao_centavos: int


def preco_da_troca(locacao: Locacao, veiculo: Veiculo) -> PrecoDaTroca:
    """LOC-09: o preço de hoje da nova categoria, como na renovação (LOC-15). O plano especial
    de preço fixo continua se valer para a nova categoria; senão, vale a tabela."""
    preco = veiculos_selectors.preco_vigente(veiculo.categoria_id, relogio.hoje())
    if preco is None:
        raise ErroDeRegra("LOC-01", "A categoria do veículo novo não tem preço vigente.")
    periodo = {
        Periodicidade.DIARIA: preco.diaria_centavos,
        Periodicidade.SEMANAL: preco.semanal_centavos,
        Periodicidade.MENSAL: preco.mensal_centavos,
    }[Periodicidade(locacao.periodicidade)]
    plano = locacao.plano_especial
    if plano is not None and plano.ativo and plano.regra == PlanoEspecial.Regra.PRECO_FIXO:
        categorias = set(plano.categorias.values_list("pk", flat=True))
        if not categorias or veiculo.categoria_id in categorias:
            periodo = int(plano.preco_centavos or 0)
    return PrecoDaTroca(int(periodo or 0), preco.diaria_centavos, preco.caucao_centavos)


def _impedimento_da_troca(locacao: Locacao, veiculo: Veiculo) -> ErroDeRegra | None:
    """422 `CLI-02` (CNH sem a categoria), `FIL-05` (de outra filial) e `LOC-03` (indisponível)."""
    tipo = veiculo.categoria.tipo_veiculo
    if locacao.cliente.cnh_categoria not in clientes_selectors.CATEGORIA_POR_TIPO[tipo]:
        exigida = clientes_selectors.EXIGIDA_POR_TIPO[tipo]
        return ErroDeRegra("CLI-02", f"A CNH do cliente não tem a categoria {exigida}.")
    if veiculo.filial_id != locacao.filial_id:
        return ErroDeRegra("FIL-05", "O veículo é de outra filial. Transfira antes de alugar.")
    livre = veiculo.status == StatusVeiculo.DISPONIVEL and not _outra_locacao_aberta(veiculo, None)
    if not livre or veiculo.pk == locacao.veiculo_id:
        erro = veiculo_indisponivel()
        return ErroDeRegra(erro.codigo, erro.mensagem)
    return None


def pedir_troca(locacao: Locacao, veiculo_novo_id: Any, motivo: str, usuario: Any) -> TrocaVeiculo:
    """Só em `ativa`. Reserva o veículo novo e, se a caução da nova categoria for maior, cobra a
    diferença na hora (`tipo = caucao`): o veículo novo só sai depois de paga. Caução menor fica
    para o acerto final, que desconta da caução total paga. `vistorias` abre as duas vistorias
    na mesma transação."""
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo da troca."]})
    with transaction.atomic():
        travada = _travar(locacao)
        if travada.status != S.ATIVA:
            raise Conflito(
                "transicao_locacao",
                "Só dá para trocar o veículo de uma locação ativa.",
                {"de": travada.status},
            )
        _sem_cancelamento_em_curso(travada)
        if troca_pendente(travada) is not None:
            raise Conflito("troca_pendente", "Esta locação já tem uma troca de veículo pendente.")
        veiculo = _veiculo(veiculo_novo_id)
        erro = _impedimento_da_troca(travada, veiculo)
        if erro is not None:
            raise erro
        preco = preco_da_troca(travada, veiculo)
        troca = TrocaVeiculo(
            locacao=travada,
            veiculo_antigo_id=travada.veiculo_id,
            veiculo_novo=veiculo,
            motivo=texto,
            pedida_por_id=getattr(usuario, "pk", None),
        )
        try:
            with (
                transaction.atomic(),
                auditar(troca, "locacao.pedir_troca", Categoria.OPERACAO, regra="LOC-09"),
            ):
                troca.save()
        except IntegrityError as erro_banco:  # outra pessoa pediu a troca ao mesmo tempo
            raise Conflito(
                "troca_pendente", "Esta locação já tem uma troca de veículo pendente."
            ) from erro_banco
        veiculos.transicionar(
            veiculo,
            StatusVeiculo.RESERVADO,
            origem=veiculos.OrigemDaMudanca(ORIGEM, travada.pk, travada.codigo),
            motivo=f"Troca de veículo da {travada.codigo}",
        )
        diferenca = preco.caucao_centavos - travada.caucao_centavos
        if diferenca > 0:
            (conta,) = financeiro.criar_contas(
                _origem(travada),
                filial_id=travada.filial_id,
                cliente_id=travada.cliente_id,
                contas=[
                    financeiro.NovaConta(
                        tipo="caucao",
                        vencimento=relogio.hoje(),
                        valor_centavos=diferenca,
                        observacao="Diferença de caução da troca de veículo",
                    )
                ],
            )
            troca.conta_caucao_id = conta.pk
            troca.save(update_fields=["conta_caucao_id", "atualizado_em"])
    return troca


def vincular_vistorias_da_troca(troca: TrocaVeiculo, *, devolucao_id: int, saida_id: int) -> None:
    """Chamado por `vistorias` ao abrir as duas vistorias da troca."""
    troca.vistoria_devolucao_id = devolucao_id
    troca.vistoria_saida_id = saida_id
    troca.save(update_fields=["vistoria_devolucao_id", "vistoria_saida_id", "atualizado_em"])


def caucao_da_troca_paga(troca: TrocaVeiculo) -> bool:
    """LOC-09: sem diferença de caução, ou com ela paga."""
    if troca.conta_caucao_id is None:
        return True
    return (
        financeiro_selectors.contas_da_origem(ORIGEM, troca.locacao_id)
        .filter(pk=troca.conta_caucao_id, status="paga")
        .exists()
    )


def _com_descontos(locacao: Locacao, preco_periodo: int) -> int:
    return preco_periodo - aplicar_percentual(preco_periodo, Decimal(locacao.desconto_pct))


def _parcela_refeita(locacao: Locacao, conta: Any, antigo: int, novo: int) -> int:
    """A parte do período sai pelo preço novo; os extras e o resto da parcela ficam. No mensal em
    4 semanais, cada parcela é a sua quarta parte do mês."""
    if locacao.parcelamento_mensal == ParcelamentoMensal.QUATRO_SEMANAIS:
        semana = ((conta.numero_parcela or 1) - 1) % 4
        antigo = dividir_em_parcelas(antigo, 4)[semana]
        novo = dividir_em_parcelas(novo, 4)[semana]
    return max(0, int(conta.valor_centavos) - antigo + novo)


def concluir_troca(troca: TrocaVeiculo, *, km_saida: int, momento: datetime) -> TrocaVeiculo:
    """Chamado por `vistorias` quando as duas vistorias da troca estão concluídas. Na mesma
    transação: o trecho atual fecha e o novo começa, a locação passa ao veículo novo (que vira
    `alugado`) com o preço, a diária e a caução da nova categoria, e as parcelas em aberto que
    vencem depois do dia da troca são refeitas pelo preço novo (LOC-09). O veículo antigo segue
    a regra da devolução (DEV-04), pela própria `vistorias`."""
    with transaction.atomic():
        travada = _travar(troca.locacao_id)
        troca = TrocaVeiculo.objects.select_for_update(of=("self",)).get(pk=troca.pk)
        if troca.status != StatusTroca.PENDENTE:
            return troca
        veiculo = Veiculo.objects.select_related("categoria").get(pk=troca.veiculo_novo_id)
        preco = preco_da_troca(travada, veiculo)
        antigo = _com_descontos(travada, travada.valor_periodo_centavos)
        novo = _com_descontos(travada, preco.periodo_centavos)
        dia = data_local(momento, travada.filial)
        motivo = f"Troca de veículo: {troca.motivo}"[:200]
        for conta in financeiro_selectors.abertas_vencendo_depois(ORIGEM, travada.pk, dia):
            if conta.tipo == "parcela":
                financeiro.ajustar_valor(
                    conta,
                    _parcela_refeita(travada, conta, antigo, novo),
                    motivo=motivo,
                    regra="LOC-09",
                )
        TrechoLocacao.objects.filter(locacao=travada, fim__isnull=True).update(
            fim=momento, atualizado_em=relogio.agora()
        )
        TrechoLocacao.objects.create(
            locacao=travada,
            veiculo=veiculo,
            inicio=momento,
            valor_periodo_centavos=preco.periodo_centavos,
            diaria_centavos=preco.diaria_centavos,
        )
        with auditar(
            travada, "locacao.trocar_veiculo", Categoria.OPERACAO, motivo=motivo, regra="LOC-09"
        ):
            travada.veiculo = veiculo
            travada.valor_periodo_centavos = preco.periodo_centavos
            travada.diaria_centavos = preco.diaria_centavos
            travada.caucao_centavos = preco.caucao_centavos
            travada.km_saida = km_saida
            travada.save(
                update_fields=[
                    "veiculo",
                    "valor_periodo_centavos",
                    "diaria_centavos",
                    "caucao_centavos",
                    "km_saida",
                    "atualizado_em",
                ]
            )
        if veiculo.status != StatusVeiculo.ALUGADO:
            veiculos.transicionar(
                veiculo,
                StatusVeiculo.ALUGADO,
                origem=veiculos.OrigemDaMudanca(ORIGEM, travada.pk, travada.codigo),
                motivo=f"Troca de veículo da {travada.codigo}",
            )
        troca.concluida_em = momento
        estados.transicionar(
            troca,
            StatusTroca.CONCLUIDA,
            motivo=motivo,
            acao="locacao.concluir_troca",
            regra="LOC-09",
            mais_campos=("concluida_em",),
        )
    return troca


# --- Cancelamento e encerramento antecipado (LOC-12, LOC-13, APR-02) ---

ANTES_DA_RETIRADA = (S.RASCUNHO, S.AGUARDANDO_RETIRADA)


def _sem_dias_restantes() -> Conflito:
    return Conflito(
        "sem_dias_restantes",
        "A locação já chegou ao fim previsto. Registre a devolução.",
    )


def _pode_cancelar(locacao: Locacao) -> None:
    if locacao.status in (S.ENCERRADA, S.CANCELADA):
        raise transicao_invalida(locacao.status, S.CANCELADA)
    if locacao.cancelamento_status == StatusDesconto.APROVADO:
        raise Conflito(
            "cancelamento_aprovado",
            "O encerramento antecipado já foi aprovado. Registre a devolução.",
        )


def calcular_encerramento(
    locacao: Locacao, dia: date | None = None, *, momento: datetime | None = None
) -> fim.Encerramento:
    """LOC-12 e LOC-13 em `dia` (padrão hoje); o mesmo cálculo de `cancelamento/simular`. 409
    `sem_dias_restantes` depois da retirada, quando não sobra nenhum dia do fim previsto. Na
    diária, `momento` é a hora da devolução (o acerto, T-016); sem ele, vale a hora do início."""
    if momento is not None:
        dia = data_local(momento, locacao.filial)
    dia = dia or relogio.hoje()
    if locacao.status in ANTES_DA_RETIRADA:
        return fim.antes_da_retirada(
            financeiro_selectors.pago_da_origem_centavos(ORIGEM, locacao.pk)
        )
    entrada = _entrada_congelada(locacao, Decimal(locacao.desconto_pct))
    canceladas = sum(c.valor_centavos for c in _parcelas_do_mes_a_cancelar(locacao, dia))
    resultado = fim.depois_da_retirada(
        periodicidade=locacao.periodicidade,
        inicio=locacao.inicio,
        fim_previsto=locacao.fim_previsto,
        periodos=locacao.periodos,
        fuso=fuso(locacao.filial),
        dia=dia,
        preco_do_periodo=lambda k: calculo.preco_com_descontos(entrada, k),
        diaria_centavos=locacao.diaria_centavos,
        momento=momento,
        parcelas_canceladas_centavos=canceladas,
    )
    if resultado is None:
        raise _sem_dias_restantes()
    return resultado


def _parcelas_do_mes_a_cancelar(locacao: Locacao, dia: date) -> list[Any]:
    """LOC-13, mensal em 4 semanais: as parcelas em aberto do mês em curso que vencem depois de
    `dia` e que o encerramento cancela (saem do crédito das semanas)."""
    if locacao.parcelamento_mensal != ParcelamentoMensal.QUATRO_SEMANAIS:
        return []
    achado = fim.periodo_em(
        locacao.periodicidade,
        locacao.inicio.astimezone(ZoneInfo(fuso(locacao.filial))),
        locacao.periodos,
        dia,
    )
    if achado is None:
        return []
    return sorted(
        (
            c
            for c in financeiro_selectors.abertas_vencendo_depois(ORIGEM, locacao.pk, dia)
            if c.vencimento < achado[2]
        ),
        key=lambda c: (c.vencimento, c.pk),
    )


def _dia_do_cancelamento(dia: date | None) -> date:
    hoje = relogio.hoje()
    if dia is not None and dia < hoje:
        raise ErroDeValidacao({"data": ["O cancelamento vale de hoje em diante."]})
    return dia or hoje


def cancelar(
    locacao: Locacao,
    usuario: Any,
    *,
    motivo: str,
    dia: date | None = None,
    forma_devolucao: str = "pix",
) -> aprovacoes.PedidoRef | None:
    """LOC-12. Administrador, gerente ou quem tem `cancelar_contrato`: vale na hora (devolve
    `None`). Vendedor: abre o pedido `APR-02` e acende `cancelamento_pendente`."""
    nivel = pode(usuario, "locacoes_cancelar")
    if nivel not in ("sim", "aprova", "pede"):
        raise SemPermissao("APR-02", "Você não pode cancelar locações")
    dia = _dia_do_cancelamento(dia)
    with transaction.atomic():
        travada = _travar(locacao)
        _pode_cancelar(travada)
        encerramento = calcular_encerramento(travada, dia)
        if nivel == "pede":
            ref = _pedir_cancelamento(travada, usuario, motivo, dia, forma_devolucao, encerramento)
        else:
            ref = None
            _aplicar_cancelamento(travada, motivo, dia, forma_devolucao)
    _recarregar(locacao)
    return ref


def _pedir_cancelamento(
    locacao: Locacao,
    usuario: Any,
    motivo: str,
    dia: date,
    forma: str,
    encerramento: fim.Encerramento,
) -> aprovacoes.PedidoRef:
    if encerramento.antes_da_retirada:
        detalhe = f"{locacao.codigo} · {locacao.cliente.nome} · antes da retirada, sem multa"
    else:
        multa = formatar_reais(encerramento.multa_centavos)
        detalhe = f"{locacao.codigo} · {locacao.cliente.nome} · multa {multa}"
    ref = aprovacoes.pedir(
        tipo="APR-02",
        origem_tipo=ORIGEM,
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        filial_id=locacao.filial_id,
        solicitante=usuario,
        titulo="Cancelamento de locação",
        detalhe=detalhe,
        motivo=motivo,
        valor_centavos=encerramento.multa_centavos or None,
        dados={
            "data": dia.isoformat(),
            "forma_devolucao": forma,
            "solicitante_id": getattr(usuario, "pk", None),
        },
    )
    with auditar(
        locacao, "locacao.pedir_cancelamento", Categoria.OPERACAO, motivo=motivo, regra="APR-02"
    ):
        locacao.cancelamento_status = StatusDesconto.PENDENTE
        locacao.pedido_cancelamento_id = ref.id
        locacao.cancelamento_data = dia
        locacao.cancelamento_forma = forma
        locacao.motivo_cancelamento = motivo
        locacao.multa_encerramento_centavos = encerramento.multa_centavos
        locacao.credito_encerramento_centavos = _credito(encerramento)
        locacao.save(update_fields=[*CAMPOS_DO_CANCELAMENTO, "atualizado_em"])
    return ref


CAMPOS_DO_CANCELAMENTO = (
    "cancelamento_status",
    "pedido_cancelamento_id",
    "cancelamento_data",
    "cancelamento_forma",
    "motivo_cancelamento",
    "multa_encerramento_centavos",
    "credito_encerramento_centavos",
)


def _credito(encerramento: fim.Encerramento) -> int:
    """O que volta ao cliente antes da multa: tudo o que pagou antes da retirada; depois, as
    semanas (LOC-13) ou as diárias não usadas. No mensal em 4 semanais, menos as parcelas que o
    encerramento cancela, e pode ser negativo (LOC-13)."""
    return encerramento.credito_liquido_centavos


@dataclass(frozen=True)
class EncerramentoNaDevolucao:
    multa_centavos: int
    credito_centavos: int  # negativo no mensal em 4 semanais com mais parcelas canceladas (LOC-13)
    descricao_do_credito: str


def encerramento_na_devolucao(locacao: Locacao, momento: datetime) -> EncerramentoNaDevolucao:
    """O encerramento antecipado aprovado no acerto da devolução (T-016), recalculado pelo dia
    da devolução com o mesmo cálculo de `cancelamento/simular` (LOC-12, LOC-13, DEV-07). O que
    a aprovação gravou é só a estimativa do dia pedido (T-116). Na diária, os dias não usados
    contam pela hora real da devolução. No mensal em 4 semanais, o crédito das semanas sai menos
    as parcelas do mês que o encerramento cancela. No fim previsto ou depois, não há multa nem
    crédito: é uma devolução comum."""
    try:
        encerramento = calcular_encerramento(locacao, momento=momento)
    except Conflito:  # sem dias restantes
        return EncerramentoNaDevolucao(0, 0, "")
    liquido = encerramento.credito_liquido_centavos
    if locacao.periodicidade == Periodicidade.DIARIA:
        return EncerramentoNaDevolucao(encerramento.multa_centavos, liquido, "Diárias não usadas")
    canceladas = _parcelas_do_mes_a_cancelar(locacao, data_local(momento, locacao.filial))
    if not canceladas:
        return EncerramentoNaDevolucao(encerramento.multa_centavos, liquido, "Semanas não usadas")
    soma = sum(c.valor_centavos for c in canceladas)
    semanas = encerramento.credito_semanas["semanas"]
    n = len(canceladas)
    descricao = (
        f"{semanas} {'semana não usada' if semanas == 1 else 'semanas não usadas'} "
        f"({formatar_reais(liquido + soma)}) − {n} "
        f"{'parcela cancelada' if n == 1 else 'parcelas canceladas'} ({formatar_reais(soma)})"
    )
    return EncerramentoNaDevolucao(encerramento.multa_centavos, liquido, descricao)


def _aplicar_cancelamento(locacao: Locacao, motivo: str, dia: date, forma: str) -> None:
    """O efeito do cancelamento, direto ou aprovado, na transação de quem chama.

    Antes da retirada: `cancelada` na hora, sem multa; as contas abertas são canceladas, o que
    foi pago vira um `Reembolso` a fazer, o veículo reservado volta a `disponivel`, a comissão é
    estornada (FIN-09) e o link do contrato deixa de valer. Depois da retirada: a locação fica
    com o encerramento antecipado aprovado e segue para a devolução. A multa e o crédito gravados
    aqui são a estimativa para `dia`; o acerto os recalcula pelo dia da devolução, e é o
    encerramento da devolução que cancela as parcelas (T-116, DEV-07). Nenhuma parcela muda aqui,
    e a comissão fica."""
    encerramento = calcular_encerramento(locacao, dia)
    aprovacoes.cancelar_pendentes(
        origem_tipo=ORIGEM, origem_id=locacao.pk, motivo=f"Locação cancelada: {motivo}"[:200]
    )
    origem = _origem(locacao)
    locacao.cancelamento_status = StatusDesconto.APROVADO
    locacao.cancelamento_data = dia
    locacao.cancelamento_forma = forma
    locacao.motivo_cancelamento = motivo
    locacao.multa_encerramento_centavos = encerramento.multa_centavos
    locacao.credito_encerramento_centavos = _credito(encerramento)
    if encerramento.antes_da_retirada:
        locacao.cancelada_em = relogio.agora()
        estados.transicionar(
            locacao,
            S.CANCELADA,
            motivo=motivo,
            acao="locacao.cancelar",
            regra="LOC-12",
            mais_campos=(*CAMPOS_DO_CANCELAMENTO, "cancelada_em"),
        )
        financeiro.cancelar_abertas(origem, motivo=motivo, regra="LOC-12")
        financeiro.devolver_ao_cliente(
            origem,
            filial_id=locacao.filial_id,
            cliente_id=locacao.cliente_id,
            valor_centavos=encerramento.devolver_centavos,
            forma=forma,
            motivo=f"Cancelamento da {locacao.codigo}",
            regra="LOC-12",
        )
        financeiro.estornar_comissao(origem, motivo=f"{locacao.codigo} cancelada antes da retirada")
        veiculo = locacao.veiculo
        if veiculo.status == StatusVeiculo.RESERVADO:
            veiculos.transicionar(
                veiculo,
                StatusVeiculo.DISPONIVEL,
                origem=veiculos.OrigemDaMudanca(ORIGEM, locacao.pk, locacao.codigo),
                motivo=f"Cancelamento da {locacao.codigo}",
            )
        contrato.cancelar_nao_assinados(locacao, f"Locação cancelada: {motivo}")
        return
    locacao.encerramento_antecipado_aprovado_em = relogio.agora()
    with auditar(
        locacao, "locacao.aprovar_encerramento", Categoria.OPERACAO, motivo=motivo, regra="LOC-12"
    ):
        locacao.save(
            update_fields=[
                *CAMPOS_DO_CANCELAMENTO,
                "encerramento_antecipado_aprovado_em",
                "atualizado_em",
            ]
        )


def aplicar_decisao_cancelamento(
    locacao_id: int, status: str, motivo: str, dados: dict[str, Any] | None = None
) -> None:
    """Volta do `APR-02`. Aprovado: o cancelamento vale (multa e acerto). Recusado: o sinal
    apaga e quem pediu é avisado com o motivo. Cancelado: o sinal apaga."""
    with transaction.atomic():
        if not Locacao.objects.filter(pk=locacao_id).exists():
            return
        travada = _travar(locacao_id)
        if travada.cancelamento_status != StatusDesconto.PENDENTE:
            return
        if status == "aprovado":
            _pode_cancelar(travada)
            _aplicar_cancelamento(
                travada,
                travada.motivo_cancelamento,
                travada.cancelamento_data or relogio.hoje(),
                travada.cancelamento_forma or "pix",
            )
            return
        novo, acao = (
            (StatusDesconto.RECUSADO, "locacao.recusar_cancelamento")
            if status == "recusado"
            else (StatusDesconto.CANCELADO, "locacao.cancelar_pedido_cancelamento")
        )
        with auditar(travada, acao, Categoria.OPERACAO, motivo=motivo, regra="APR-02"):
            travada.cancelamento_status = novo
            travada.save(update_fields=["cancelamento_status", "atualizado_em"])
        if novo == StatusDesconto.RECUSADO:
            solicitante = (dados or {}).get("solicitante_id") or travada.vendedor_id
            avisar(
                [solicitante],
                tipo="cancelamento_recusado",
                titulo=f"Cancelamento da {travada.codigo} recusado: {motivo}"[:200],
                link=f"/locacoes/{travada.pk}",
            )


# --- Encerramento (chamado por `vistorias` ao concluir a devolução, T-016) ---


def encerramento_antecipado_vale(locacao: Locacao, momento: datetime) -> bool:
    """DEV-07 (T-118): o encerramento antecipado aprovado só vale com a devolução antes do dia
    do fim previsto, no fuso da filial. No dia do fim ou depois, a devolução é comum: sem multa
    nem crédito da LOC-12, e o pedido aprovado fica registrado, sem efeito."""
    if locacao.encerramento_antecipado_aprovado_em is None:
        return False
    fim_previsto = data_local(locacao.fim_previsto, locacao.filial)
    return data_local(momento, locacao.filial) < fim_previsto


def encerrar(locacao: Locacao, *, devolvida_em: datetime | None = None) -> Locacao:
    """DEV-06: `encerrada`, ou `cancelada` no encerramento antecipado aprovado com a devolução
    antes do dia do fim previsto (LOC-12, DEV-07). Grava `devolvida_em`, fecha o trecho aberto e
    publica `locacoes.locacao_encerrada`. A comissão não muda (o encerramento antecipado não a
    estorna, FIN-09). O veículo segue a regra da devolução (DEV-04), pela própria `vistorias`."""
    with transaction.atomic():
        travada = _travar(locacao)
        devolvida_em = devolvida_em or relogio.agora()
        antecipado = encerramento_antecipado_vale(travada, devolvida_em)
        destino = S.CANCELADA if antecipado else S.ENCERRADA
        if travada.status not in (S.ATIVA, S.DEVOLUCAO_ATRASADA):
            raise transicao_invalida(travada.status, destino)
        travada.devolvida_em = devolvida_em
        mais: tuple[str, ...] = ("devolvida_em",)
        if antecipado:
            travada.cancelada_em = devolvida_em
            mais = (*mais, "cancelada_em")
        estados.transicionar(
            travada,
            destino,
            motivo=(
                f"Encerramento antecipado: {travada.motivo_cancelamento}"
                if antecipado
                else "Devolução concluída"
            ),
            acao="locacao.encerrar",
            regra="LOC-12" if antecipado else "",
            mais_campos=mais,
        )
        TrechoLocacao.objects.filter(locacao=travada, fim__isnull=True).update(
            fim=devolvida_em, atualizado_em=relogio.agora()
        )
        publicar(
            "locacoes.locacao_encerrada",
            locacao_id=travada.pk,
            veiculo_id=travada.veiculo_id,
            status=destino,
            devolvida_em=devolvida_em,
        )
    _recarregar(locacao)
    return locacao


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
