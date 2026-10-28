"""Rotas da assinatura do lado da empresa (`docs/api/assinatura.md`; T-185).

Só o administrador (tabela de perfis; PLT-04, PLT-06, PLT-13, PLT-15). O suporte Giro lê e
nunca escreve, nem com "ver e editar" (PLT-07, CA-ASS-19). Com a empresa `suspensa`, só as rotas
de pagar e a de cancelar escrevem (`escreve_na_suspensa`, PLT-13, CA-ASS-27, PLT-06); mudar de
plano e pausar respondem o 409 da regra (`recusa_na_suspensa`). Com a `pausada`, só cancelar e
voltar da pausa (`escreve_na_pausada`, `cancelamento.md`); o resto, 403 `empresa_sem_operacao`.
A `cancelada` não entra no sistema (`EmpresaCanceladaMiddleware`, AUD-08).
"""

from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.autenticacao import dois_fatores_recente, token_da_requisicao
from comum.erros import ErroDeValidacao, NaoEncontrado, SemPermissao
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..calendario import MESES_DE_PAUSA
from ..models import (
    Empresa,
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagaFatura,
    MotivoCancelamento,
    SituacaoNota,
    StatusFatura,
)
from .serializers import (
    AndamentoDoAssistenteSerializer,
    AssinaturaSerializer,
    DadosFiscaisSerializer,
    EnderecoDaNotaSerializer,
    FormaDePagamentoSerializer,
    SituacaoSerializer,
    representar_assinatura,
)

SO_O_ADMINISTRADOR = ("permissao", "Só o administrador mexe na assinatura")
SUPORTE_NA_ASSINATURA = ("PLT-07", "O suporte não mexe na assinatura da empresa")


class SoAdministrador(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if getattr(request.user, "perfil", None) != "administrador":
            raise SemPermissao(*SO_O_ADMINISTRADOR)
        return True


class LeituraDaAssinatura(APIView):
    permission_classes = com_padrao(SoAdministrador)
    suporte_somente_leitura = True


class EscritaDaAssinatura(APIView):
    """Nenhuma escrita da assinatura aceita o token de suporte (PLT-07, T-189)."""

    permission_classes = com_padrao(SoAdministrador)
    suporte_proibido: bool | frozenset[str] = True
    mensagem_suporte_proibido = SUPORTE_NA_ASSINATURA


def _empresa(request: Request) -> Empresa:
    empresa: Empresa = request.tenant  # type: ignore[attr-defined]
    return empresa


def _assinatura(request: Request) -> dict[str, Any]:
    with services.no_publico():
        return representar_assinatura(selectors.assinatura(_empresa(request), request.user))


# --- Planos e mudança de plano (PLT-04, PLT-05, PLT-11) ---


class LimiteExcedidoSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField()


class AbertoSerializer(serializers.Serializer[Any]):
    grupo = serializers.CharField()
    quantidade = serializers.IntegerField()
    texto = serializers.CharField()


class ExcedeSerializer(serializers.Serializer[Any]):
    veiculos = LimiteExcedidoSerializer(required=False)
    filiais = LimiteExcedidoSerializer(required=False)
    usuarios = LimiteExcedidoSerializer(required=False)
    abertos = AbertoSerializer(many=True, required=False)
    abertos_texto = serializers.CharField(required=False)


class PlanoParaMudarSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    ordem = serializers.IntegerField()
    atual = serializers.BooleanField()
    preco_mensal_centavos = serializers.IntegerField()
    preco_anual_centavos = serializers.IntegerField()
    preco_contratado_centavos = serializers.IntegerField(required=False)
    limite_veiculos = serializers.IntegerField(allow_null=True)
    limite_filiais = serializers.IntegerField(allow_null=True)
    limite_usuarios = serializers.IntegerField(allow_null=True)
    itens = serializers.ListField(child=serializers.CharField())
    mudanca = serializers.ChoiceField(choices=["upgrade", "downgrade"], allow_null=True)
    cabe = serializers.BooleanField()
    excede = ExcedeSerializer()


class PlanosParaMudarSerializer(serializers.Serializer[Any]):
    ciclo_atual = serializers.ChoiceField(choices=Empresa.Ciclo.choices)
    resultados = PlanoParaMudarSerializer(many=True)


class PedidoDeMudancaSerializer(serializers.Serializer[Any]):
    plano_id = serializers.IntegerField()
    ciclo = serializers.ChoiceField(choices=Empresa.Ciclo.choices)


class ConfirmarMudancaSerializer(PedidoDeMudancaSerializer):
    confirmar_valor_centavos = serializers.IntegerField(min_value=0)


class FaturaDaDiferencaSerializer(serializers.Serializer[Any]):
    valor_centavos = serializers.IntegerField()
    vencimento = serializers.DateField()
    descricao = serializers.CharField()


class ProximaFaturaDaMudancaSerializer(serializers.Serializer[Any]):
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    descricao = serializers.CharField()


class SimulacaoSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["upgrade", "downgrade"])
    vale_em = serializers.DateField()
    preco_novo_centavos = serializers.IntegerField()
    diferenca_centavos = serializers.IntegerField()
    fatura_diferenca = FaturaDaDiferencaSerializer(allow_null=True)
    proxima_fatura = ProximaFaturaDaMudancaSerializer(allow_null=True)
    mensagem = serializers.CharField()


def _simulacao(simulacao: services.Simulacao) -> dict[str, Any]:
    avulsa, proxima = simulacao.fatura_diferenca, simulacao.proxima
    return {
        "tipo": simulacao.tipo,
        "vale_em": simulacao.vale_em,
        "preco_novo_centavos": simulacao.preco_novo_centavos,
        "diferenca_centavos": simulacao.diferenca_centavos,
        "fatura_diferenca": (
            {
                "valor_centavos": avulsa.valor_centavos,
                "vencimento": avulsa.vencimento,
                "descricao": avulsa.descricao,
            }
            if avulsa
            else None
        ),
        "proxima_fatura": (
            {
                "vencimento": proxima.vencimento,
                "valor_centavos": proxima.valor_centavos,
                "descricao": proxima.descricao,
            }
            if proxima
            else None
        ),
        "mensagem": simulacao.mensagem,
    }


class PlanosDaAssinaturaView(LeituraDaAssinatura):
    @extend_schema(
        responses=PlanosParaMudarSerializer,
        operation_id="assinatura_planos_list",
        summary="Planos para mudar e comparar (PLT-04, PLT-11)",
    )
    def get(self, request: Request) -> Response:
        with services.no_publico():
            dados = selectors.planos_da_assinatura(_empresa(request))
        return Response(PlanosParaMudarSerializer(dados).data)


class MudancaDePlano(EscritaDaAssinatura):
    recusa_na_suspensa = services.PAGUE_ANTES  # PLT-04, CA-ASS-17


class SimularMudancaPlanoView(MudancaDePlano):
    @extend_schema(
        request=PedidoDeMudancaSerializer,
        responses=SimulacaoSerializer,
        summary="Simular a mudança de plano, sem gravar (PLT-04)",
    )
    def post(self, request: Request) -> Response:
        pedido = PedidoDeMudancaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        empresa = _empresa(request)
        plano = services.plano_para_mudar(pedido.validated_data["plano_id"], empresa)
        simulacao = services.simular_mudanca_plano(empresa, plano, pedido.validated_data["ciclo"])
        return Response(SimulacaoSerializer(_simulacao(simulacao)).data)


class MudancaPlanoView(MudancaDePlano):
    @extend_schema(
        request=ConfirmarMudancaSerializer,
        responses=AssinaturaSerializer,
        summary="Mudar de plano (PLT-04, PLT-05)",
    )
    def post(self, request: Request) -> Response:
        pedido = ConfirmarMudancaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        empresa = _empresa(request)
        plano = services.plano_para_mudar(pedido.validated_data["plano_id"], empresa)
        services.mudar_plano(
            empresa,
            plano,
            pedido.validated_data["ciclo"],
            confirmar_valor_centavos=pedido.validated_data["confirmar_valor_centavos"],
        )
        return Response(_assinatura(request))

    @extend_schema(
        request=None,
        responses=AssinaturaSerializer,
        summary="Desfazer o downgrade agendado (PLT-04)",
    )
    def delete(self, request: Request) -> Response:
        services.desfazer_mudanca_plano(_empresa(request))
        return Response(_assinatura(request))


# --- Dados fiscais (PLT-15) ---


class PedidoDeDadosFiscaisSerializer(serializers.Serializer[Any]):
    """Parcial. `endereco` vem inteiro (nulo é recusado); o CNPJ não muda por aqui."""

    razao_social = serializers.CharField(required=False, max_length=150)
    endereco = EnderecoDaNotaSerializer(required=False)
    email_cobranca = serializers.EmailField(required=False)


class RespostaDosDadosFiscaisSerializer(serializers.Serializer[Any]):
    dados_fiscais = DadosFiscaisSerializer()


class DadosFiscaisView(EscritaDaAssinatura):
    escreve_na_suspensa = frozenset({"PATCH"})  # a suspensa paga (PLT-13, CA-ASS-27)

    @extend_schema(
        request=PedidoDeDadosFiscaisSerializer,
        responses=RespostaDosDadosFiscaisSerializer,
        summary="Dados da nota fiscal da assinatura (PLT-15)",
    )
    def patch(self, request: Request) -> Response:
        dados = request.data if isinstance(request.data, dict) else {}
        empresa = services.atualizar_dados_fiscais(_empresa(request), dados)
        with services.no_publico():
            resposta = {"dados_fiscais": selectors.dados_fiscais(empresa)}
        return Response(RespostaDosDadosFiscaisSerializer(resposta).data)


# --- Forma de pagamento (PLT-13; ADR 0023) ---


class PedidoDeFormaSerializer(serializers.Serializer[Any]):
    """Sem campo de cartão: o cartão é digitado só na página do parceiro (ADR 0023)."""

    forma = serializers.ChoiceField(choices=FormaAssinatura.choices)


class ProximoPassoSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["autorizar_pix", "pagina_parceiro"])
    pix_copia_e_cola = serializers.CharField(required=False)
    expira_em = serializers.DateTimeField(required=False)
    url = serializers.CharField(required=False)
    fatura = serializers.CharField(required=False)


class RespostaDaFormaSerializer(serializers.Serializer[Any]):
    forma_pagamento = FormaDePagamentoSerializer()
    proximo_passo = ProximoPassoSerializer(allow_null=True)


class FormaPagamentoView(EscritaDaAssinatura):
    escreve_na_suspensa = frozenset({"PUT"})  # a suspensa escolhe a forma e paga (CA-ASS-27)

    @extend_schema(
        request=PedidoDeFormaSerializer,
        responses=RespostaDaFormaSerializer,
        summary="Escolher a forma de pagamento da assinatura (PLT-13)",
    )
    def put(self, request: Request) -> Response:
        pedido = PedidoDeFormaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        empresa = _empresa(request)
        proximo = services.escolher_forma_pagamento(empresa, pedido.validated_data["forma"])
        with services.no_publico():
            forma = selectors.forma_de_pagamento(Empresa.objects.get(pk=empresa.pk))
        resposta = {"forma_pagamento": forma, "proximo_passo": proximo}
        return Response(RespostaDaFormaSerializer(resposta).data)


# --- Faturas (PLT-14) ---


class PeriodoDaFaturaSerializer(serializers.Serializer[Any]):
    inicio = serializers.DateField()
    fim = serializers.DateField()


class AcoesDaFaturaSerializer(serializers.Serializer[Any]):
    pagar = serializers.BooleanField()
    recibo = serializers.BooleanField()
    nota_fiscal = serializers.BooleanField()


class FaturaDaListaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["fatura", "teste"])
    codigo = serializers.CharField(allow_null=True)
    vencimento = serializers.DateField()
    descricao = serializers.CharField()
    periodo = PeriodoDaFaturaSerializer()
    valor_centavos = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusFatura.choices, allow_null=True)
    forma = serializers.ChoiceField(choices=FormaPagaFatura.choices, allow_null=True)
    pago_em = serializers.DateTimeField(allow_null=True)
    situacao = SituacaoSerializer()
    acoes = AcoesDaFaturaSerializer()


class ListaDeFaturasSerializer(serializers.Serializer[Any]):
    resultados = FaturaDaListaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class CobrancaDaFaturaSerializer(serializers.Serializer[Any]):
    forma = serializers.ChoiceField(choices=["cartao", "pix", "boleto"], allow_null=True)
    linha_digitavel = serializers.CharField(allow_null=True)
    url_boleto = serializers.CharField(allow_null=True)
    pix_copia_e_cola = serializers.CharField(allow_null=True)
    url_pagina = serializers.CharField(allow_null=True)
    vencimento = serializers.DateField()


class NotaFiscalSerializer(serializers.Serializer[Any]):
    situacao = serializers.ChoiceField(choices=SituacaoNota.choices)
    numero = serializers.CharField(allow_null=True)
    url = serializers.CharField(allow_null=True)


class FaturaDetalheSerializer(FaturaDaListaSerializer):
    cobranca = CobrancaDaFaturaSerializer(allow_null=True)
    recibo_url = serializers.CharField(allow_null=True)
    nota_fiscal = NotaFiscalSerializer(allow_null=True)


class PedidoDePagarSerializer(serializers.Serializer[Any]):
    """Sem `meio`, pela forma cadastrada; com ele, por outro meio, sem trocar a forma."""

    meio = serializers.ChoiceField(choices=["cartao", "pix", "boleto"], required=False)


def _fatura(empresa: Empresa, codigo: str) -> FaturaAssinatura:
    fatura = selectors.faturas_da_empresa(empresa).filter(codigo=codigo).first()
    if fatura is None:
        raise NaoEncontrado("nao_encontrado", "Fatura não encontrada.")
    return fatura


class FaturasView(LeituraDaAssinatura):
    @extend_schema(
        responses=ListaDeFaturasSerializer,
        operation_id="assinatura_faturas_list",
        parameters=[OpenApiParameter("status", enum=list(StatusFatura.values))],
        summary="Faturas da assinatura (PLT-14)",
    )
    def get(self, request: Request) -> Response:
        status = request.query_params.get("status") or None
        if status is not None and status not in StatusFatura.values:
            raise ErroDeValidacao({"status": ["Use aberta, paga, atrasada ou cancelada."]})
        with services.no_publico():
            empresa = Empresa.objects.get(pk=_empresa(request).pk)
            contexto = selectors.contexto_das_faturas(empresa, request.user)
            paginacao = PaginacaoPorCursor()
            paginacao.ordering = ("-vencimento", "-numero")  # type: ignore[assignment]
            faturas = selectors.faturas_da_empresa(empresa, status)
            pagina = paginacao.paginate_queryset(faturas, request, view=self) or []
            itens = [selectors.item_da_fatura(f, contexto) for f in pagina]
            teste = selectors.linha_do_teste(empresa)
            # A linha do teste vai no fim da última página, sem filtro de status.
            if teste is not None and status is None and not paginacao.has_next:
                itens.append(teste)
        return paginacao.get_paginated_response(FaturaDaListaSerializer(itens, many=True).data)


class FaturaView(LeituraDaAssinatura):
    @extend_schema(responses=FaturaDetalheSerializer, summary="Fatura da assinatura (PLT-14)")
    def get(self, request: Request, codigo: str) -> Response:
        with services.no_publico():
            empresa = Empresa.objects.get(pk=_empresa(request).pk)
            contexto = selectors.contexto_das_faturas(empresa, request.user)
            detalhe = selectors.detalhe_da_fatura(_fatura(empresa, codigo), contexto)
        return Response(FaturaDetalheSerializer(detalhe).data)


class PagarFaturaView(EscritaDaAssinatura):
    escreve_na_suspensa = frozenset({"POST"})  # a suspensa paga e volta a ativa (CA-ASS-27)

    @extend_schema(
        request=PedidoDePagarSerializer,
        responses=CobrancaDaFaturaSerializer,
        summary="Pagar a fatura agora (PLT-14)",
    )
    def post(self, request: Request, codigo: str) -> Response:
        pedido = PedidoDePagarSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        meio = pedido.validated_data.get("meio")
        fatura = services.pagar_fatura(_empresa(request), codigo, meio)
        with services.no_publico():
            cobranca = selectors.cobranca_da_fatura(fatura)
        return Response(CobrancaDaFaturaSerializer(cobranca).data)


# --- Cancelar e pausar (PLT-06, AUD-08; cancelamento.md, T-195) ---


class EscolhaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()


class AlternativaPausarSerializer(serializers.Serializer[Any]):
    meses = serializers.ListField(child=serializers.IntegerField())
    inicio = serializers.DateField()
    texto = serializers.CharField()


class PlanoDaAlternativaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    preco_mensal_centavos = serializers.IntegerField()


class AlternativaEssencialSerializer(serializers.Serializer[Any]):
    plano = PlanoDaAlternativaSerializer()
    resumo = serializers.CharField()
    cabe = serializers.BooleanField()
    excede = ExcedeSerializer()


class AlternativasSerializer(serializers.Serializer[Any]):
    pausar = AlternativaPausarSerializer(allow_null=True)
    mudar_para_essencial = AlternativaEssencialSerializer(allow_null=True)


class LinhaDoQueAconteceSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()  # acesso, cobrancas, dados, apagamento, contratos
    rotulo = serializers.CharField()
    valor = serializers.CharField()


class ConfirmacaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()


class ExportarSerializer(serializers.Serializer[Any]):
    texto = serializers.CharField()


class TelaDoCancelamentoSerializer(serializers.Serializer[Any]):
    empresa = serializers.CharField()
    plano_resumo = serializers.CharField()
    motivos = EscolhaSerializer(many=True)
    alternativas = AlternativasSerializer()
    o_que_acontece = LinhaDoQueAconteceSerializer(many=True)
    acesso_ate = serializers.DateField(allow_null=True)
    cancelada_em = serializers.DateField()
    apagar_em = serializers.DateField()
    confirmacao = ConfirmacaoSerializer()
    exportar = ExportarSerializer()


ESCOLHA_O_MOTIVO = "Escolha o motivo."
ESCOLHA_OS_MESES = "Escolha de 1 a 3 meses."


class PedidoDeCancelamentoSerializer(serializers.Serializer[Any]):
    motivo = serializers.ChoiceField(
        choices=MotivoCancelamento.choices,
        error_messages={
            "required": ESCOLHA_O_MOTIVO,
            "null": ESCOLHA_O_MOTIVO,
            "invalid_choice": ESCOLHA_O_MOTIVO,
        },
    )
    nome_confirmacao = serializers.CharField(allow_blank=True, trim_whitespace=False)


class PedidoDePausaSerializer(serializers.Serializer[Any]):
    meses = serializers.IntegerField(
        error_messages={
            "required": ESCOLHA_OS_MESES,
            "null": ESCOLHA_OS_MESES,
            "invalid": ESCOLHA_OS_MESES,
        },
    )

    def validate_meses(self, valor: int) -> int:
        if valor not in MESES_DE_PAUSA:  # CA-ASS-35: 4 meses é recusado
            raise serializers.ValidationError(ESCOLHA_OS_MESES)
        return valor


class AcaoDoCancelamento(EscritaDaAssinatura):
    """Só o administrador; o suporte lê e nunca escreve (PLT-07). Na lista explícita de exceções
    da `suspensa` e da `pausada` (`cancelamento.md`, com teste): cancelar, para as duas."""

    suporte_proibido = frozenset({"POST", "PUT", "PATCH", "DELETE"})
    suporte_somente_leitura = True
    escreve_na_suspensa = frozenset({"POST"})  # a suspensa cancela (PLT-06)
    escreve_na_pausada = frozenset({"POST"})  # a pausada cancela (PLT-06)


class CancelamentoView(AcaoDoCancelamento):
    @extend_schema(
        responses=TelaDoCancelamentoSerializer,
        summary="O que a tela de cancelar mostra hoje (PLT-06, AUD-08)",
    )
    def get(self, request: Request) -> Response:
        with services.no_publico():
            empresa = Empresa.objects.get(pk=_empresa(request).pk)
            if services.cancelamento_marcado(empresa):
                raise services.ja_cancelada(empresa)
            tela = selectors.tela_do_cancelamento(empresa)
        return Response(TelaDoCancelamentoSerializer(tela).data)

    @extend_schema(
        request=PedidoDeCancelamentoSerializer,
        responses=AssinaturaSerializer,
        summary="Cancelar a assinatura (PLT-06)",
    )
    def post(self, request: Request) -> Response:
        # T-199, M-01: 2 etapas recentes antes de qualquer outra conferência (sem volta na
        # `inadimplente`, na `suspensa` e na `pausada`).
        if not dois_fatores_recente(token_da_requisicao(request)):
            raise SemPermissao(*services.CANCELAR_PEDE_2_ETAPAS)
        pedido = PedidoDeCancelamentoSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        services.cancelar_assinatura(
            _empresa(request),
            pedido.validated_data["motivo"],
            nome_confirmacao=pedido.validated_data["nome_confirmacao"],
        )
        return Response(_assinatura(request))

    @extend_schema(
        request=None,
        responses=AssinaturaSerializer,
        summary="Desfazer o cancelamento até o último dia de acesso (PLT-06)",
    )
    def delete(self, request: Request) -> Response:
        services.desfazer_cancelamento(_empresa(request))
        return Response(_assinatura(request))


class PausaView(AcaoDoCancelamento):
    """Voltar da pausa e desistir da pausa agendada são a mesma rota (`DELETE`): a `pausada`
    volta, a `ativa` com a pausa agendada desiste. Só o `DELETE` está na exceção da `pausada`."""

    escreve_na_suspensa = frozenset()
    escreve_na_pausada = frozenset({"DELETE"})
    recusa_na_suspensa = {"POST": services.PAGUE_ANTES_DE_PAUSAR}

    @extend_schema(
        request=PedidoDePausaSerializer,
        responses=AssinaturaSerializer,
        summary="Pausar a assinatura de 1 a 3 meses (PLT-06)",
    )
    def post(self, request: Request) -> Response:
        pedido = PedidoDePausaSerializer(data=request.data)
        pedido.is_valid(raise_exception=True)
        services.pausar_assinatura(_empresa(request), pedido.validated_data["meses"])
        return Response(_assinatura(request))

    @extend_schema(
        request=None,
        responses=AssinaturaSerializer,
        summary="Voltar da pausa ou desistir da pausa agendada (PLT-06)",
    )
    def delete(self, request: Request) -> Response:
        empresa = _empresa(request)
        if empresa.status == Empresa.Status.PAUSADA:
            services.voltar_da_pausa(empresa)
        else:
            services.desistir_da_pausa(empresa)
        return Response(_assinatura(request))


# --- Andamento do assistente (`GET /api/implantacao/`, T-201, T-202) ---


class ImplantacaoView(APIView):
    """A moldura do assistente marca os passos pelo que a API manda (T-190, proposta 9).
    Administrador e token de suporte (só leitura); os demais, 403."""

    permission_classes = com_padrao(exige_perfil("administrador"))
    suporte_somente_leitura = True

    @extend_schema(
        responses=AndamentoDoAssistenteSerializer,
        summary="Andamento do assistente de implantação (IMP-05)",
    )
    def get(self, request: Request) -> Response:
        # IMP-07: o preço agendado que chegou à data marca o passo na primeira leitura.
        services.conferir_passos_na_leitura(_empresa(request))
        with services.no_publico():
            dados = selectors.andamento_do_assistente(_empresa(request))
        return Response(AndamentoDoAssistenteSerializer(dados).data)
