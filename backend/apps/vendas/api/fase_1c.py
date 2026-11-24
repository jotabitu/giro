"""Rotas da fase 1c da T-502 (ADR 0042, itens 8, 13 e 14; `docs/api/vendas.md`): o link público
da proposta (`VEN-15`, S-15), o resumo das vendas (`VEN-08`, `VEN-09`, `VEN-12`, `VEN-16`) e as
metas (`VEN-09`). Num módulo à parte de `views.py` para não cruzar com a fase 1b.
"""

import re
from datetime import date
from typing import Any

from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contratos.selectors import marca_e_host
from apps.filiais.models import Filial
from apps.filiais.selectors import filtrar_por_filial
from apps.plataforma.models import Recurso
from comum import arquivos, relogio
from comum.empresa import nome_da_empresa
from comum.erros import ErroDeValidacao
from comum.limites import LIMITES_DA_PROPOSTA_PUBLICA, LIMITES_DO_LINK_PROPOSTA
from comum.permissoes import TODAS_AS_FILIAIS, com_padrao, exige_perfil, filial_pedida
from comum.rede import ip_do_cliente

from .. import envio, metas, resumo, services
from .views import LEEM, ViewDeAcao, ViewDeVendas, _venda

DEFINEM: list[type[BasePermission]] = com_padrao(exige_perfil("administrador", "gerente"))
SUPORTE_NAO_GERA_LINK = "No modo suporte você não gera link para o cliente."
MES = re.compile(r"^(\d{4})-(\d{2})$")


def _mes(texto: str | None) -> date:
    """`?mes=AAAA-MM`; sem ele, o mês de hoje. Fora do formato: 400 no campo."""
    if not texto:
        return relogio.hoje().replace(day=1)
    achado = MES.match(texto)
    if achado is None or not 1 <= int(achado[2]) <= 12:
        raise ErroDeValidacao({"mes": ["Use o mês no formato AAAA-MM."]})
    return date(int(achado[1]), int(achado[2]), 1)


def _filiais(request: Request) -> list[Filial]:
    """As filiais do `X-Filial` (USR-07); `?filial=` escolhe uma delas."""
    filiais = list(filtrar_por_filial(Filial.objects.all(), request, campo="pk").order_by("pk"))
    pedida = request.query_params.get("filial")
    if pedida:
        filiais = [f for f in filiais if str(f.pk) == str(pedida)]
        if not filiais:
            raise Http404
    return filiais


def _onde(request: Request, filiais: list[Filial]) -> str:
    if len(filiais) == 1 and not (
        filial_pedida(request) == TODAS_AS_FILIAIS and not request.query_params.get("filial")
    ):
        return filiais[0].nome
    return "Todas as filiais"


def _uma_filial(request: Request, corpo: dict[str, Any] | None = None) -> Filial:
    pedida = (corpo or {}).get("filial_id") or request.query_params.get("filial")
    filiais = filtrar_por_filial(Filial.objects.all(), request, campo="pk")
    if pedida:
        filial = filiais.filter(pk=pedida).first()
        if filial is None:
            raise Http404
        return filial  # type: ignore[no-any-return]
    if filial_pedida(request) == TODAS_AS_FILIAIS or filiais.count() != 1:
        raise ErroDeValidacao({"filial": ["Escolha a filial."]})
    return filiais.get()  # type: ignore[no-any-return]


# --- Serializers ---


class LinkDaPropostaSerializer(serializers.Serializer[Any]):
    link = serializers.CharField(help_text="/proposta#<token>; o token só aparece aqui")
    expira_em = serializers.DateTimeField()
    aviso = serializers.CharField()


class TokenDaPropostaSerializer(serializers.Serializer[Any]):
    token = serializers.CharField(max_length=200)


class EmpresaDaPropostaSerializer(serializers.Serializer[Any]):
    nome_exibicao = serializers.CharField()
    logo_url = serializers.CharField(allow_null=True)
    cor_marca = serializers.CharField(allow_null=True)


class PropostaPublicaSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    cliente_primeiro_nome = serializers.CharField()
    veiculo = serializers.CharField(help_text="marca e modelo, sem a placa")
    vence_em = serializers.DateField(allow_null=True)
    pdf_url = serializers.CharField(help_text="URL assinada de 15 minutos (AUD-05)")
    pdf_url_expira_em = serializers.DateTimeField()


class ConsultaDaPropostaSerializer(serializers.Serializer[Any]):
    empresa = EmpresaDaPropostaSerializer()
    proposta = PropostaPublicaSerializer()


class FunilSerializer(serializers.Serializer[Any]):
    interessados = serializers.IntegerField()
    proposta = serializers.IntegerField()
    negociacao = serializers.IntegerField()
    vendido = serializers.IntegerField()


class ConversaoSerializer(serializers.Serializer[Any]):
    vendidas = serializers.IntegerField()
    criadas = serializers.IntegerField()
    pct = serializers.IntegerField(allow_null=True, help_text="últimos 30 dias, para baixo")


class VendidasDoMesSerializer(serializers.Serializer[Any]):
    quantidade = serializers.IntegerField()
    soma_centavos = serializers.IntegerField()
    ticket_centavos = serializers.IntegerField(allow_null=True)


class VendidoSerializer(VendidasDoMesSerializer):
    vazio = serializers.CharField(allow_null=True, help_text='"Sem vendas em outubro."')
    mes_anterior = VendidasDoMesSerializer()


class EmNegociacaoSerializer(serializers.Serializer[Any]):
    quantidade = serializers.IntegerField()
    soma_centavos = serializers.IntegerField()
    aguardando_aprovacao = serializers.IntegerField()


class MetaDoResumoSerializer(serializers.Serializer[Any]):
    valor_centavos = serializers.IntegerField(allow_null=True)
    vendido_centavos = serializers.IntegerField()
    pct = serializers.IntegerField(allow_null=True)
    faltam_dias = serializers.IntegerField(allow_null=True)
    texto = serializers.CharField()


class PropostaParaRetornarSerializer(serializers.Serializer[Any]):
    venda_id = serializers.IntegerField()
    codigo = serializers.CharField()
    comprador_nome = serializers.CharField()
    celular = serializers.CharField()
    veiculo = serializers.CharField()
    valor_centavos = serializers.IntegerField(allow_null=True)
    situacao_texto = serializers.CharField()
    ultimo_contato_em = serializers.DateTimeField(allow_null=True)


class ResumoDeVendasSerializer(serializers.Serializer[Any]):
    mes = serializers.DateField()
    subtitulo = serializers.CharField()
    funil = FunilSerializer()
    conversao = ConversaoSerializer()
    vendido = VendidoSerializer()
    em_negociacao = EmNegociacaoSerializer()
    a_venda = serializers.IntegerField()
    meta = MetaDoResumoSerializer()
    transferencias_pendentes = serializers.IntegerField()
    propostas_para_retornar = PropostaParaRetornarSerializer(many=True)
    propostas_vazio = serializers.CharField(allow_null=True)


class RefDaMetaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class MetaDoVendedorSerializer(serializers.Serializer[Any]):
    vendedor = RefDaMetaSerializer()
    valor_centavos = serializers.IntegerField(allow_null=True)


class QuadroDeMetasSerializer(serializers.Serializer[Any]):
    filial = RefDaMetaSerializer()
    mes = serializers.DateField()
    vendedores = MetaDoVendedorSerializer(many=True)
    soma_centavos = serializers.IntegerField(allow_null=True)
    texto = serializers.CharField()
    ajuda = serializers.CharField()


class MetaPedidaSerializer(serializers.Serializer[Any]):
    vendedor_id = serializers.IntegerField()
    valor_centavos = serializers.IntegerField(allow_null=True, min_value=1)


class DefinirMetasSerializer(serializers.Serializer[Any]):
    filial_id = serializers.IntegerField()
    mes = serializers.RegexField(r"^\d{4}-\d{2}$", help_text="AAAA-MM")
    metas = MetaPedidaSerializer(many=True)


# --- Views ---


class LinkDaPropostaView(ViewDeAcao):
    """ "Copiar link" (`VEN-15`, `VEN-19`): o link sai só nesta resposta. Ordem da T-252:
    permissão e 403 `PLT-07`, depois o limite, depois o serviço."""

    throttle_classes = LIMITES_DO_LINK_PROPOSTA
    suporte_proibido = True
    mensagem_suporte_proibido = SUPORTE_NAO_GERA_LINK

    @extend_schema(
        request=None,
        responses=LinkDaPropostaSerializer,
        summary="Copiar link da proposta (VEN-15, S-15)",
    )
    def post(self, request: Request, pk: int) -> Response:
        token, venda = envio.gerar_link(_venda(request, pk), request.user)
        corpo = {
            "link": envio.link(marca_e_host()[1], token),
            "expira_em": venda.token_proposta_expira_em,
            "aviso": "O link anterior deixa de valer.",
        }
        return Response(LinkDaPropostaSerializer(corpo).data, headers={"Cache-Control": "no-store"})


class ConsultarPropostaView(APIView):
    """Página pública `/proposta` (VEN-15): sem login, no host da empresa, com limites próprios
    por IP e por token, como o recibo da devolução (T-411)."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes = LIMITES_DA_PROPOSTA_PUBLICA
    recurso_do_plano = Recurso.VENDAS_COMISSOES

    @extend_schema(
        request=TokenDaPropostaSerializer,
        responses=ConsultaDaPropostaSerializer,
        summary="Ler a proposta do link (VEN-15, S-15)",
    )
    def post(self, request: Request) -> Response:
        entrada = TokenDaPropostaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        venda = envio.consultar(
            entrada.validated_data["token"],
            ip_do_cliente(request),
            request.META.get("HTTP_USER_AGENT", ""),
        )
        assinada = arquivos.url_assinada(venda.proposta_pdf.name)
        corpo = {
            "empresa": {"nome_exibicao": nome_da_empresa(), "logo_url": None, "cor_marca": None},
            "proposta": {
                "codigo": venda.codigo,
                "cliente_primeiro_nome": envio.primeiro_nome(venda),
                "veiculo": f"{venda.veiculo.marca} {venda.veiculo.modelo}".strip(),
                "vence_em": services.vence_em(venda),
                "pdf_url": assinada.url,
                "pdf_url_expira_em": assinada.expira_em,
            },
        }
        return Response(
            ConsultaDaPropostaSerializer(corpo).data,
            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"},
        )


class ResumoView(ViewDeVendas):
    permission_classes = LEEM

    @extend_schema(
        responses=ResumoDeVendasSerializer,
        parameters=[
            OpenApiParameter("filial", int),
            OpenApiParameter("mes", str, description="AAAA-MM; sem ele, o mês de hoje"),
        ],
        summary="Resumo das vendas: funil, conversão, vendido, ticket, meta (VEN-08, VEN-09,"
        " VEN-12, VEN-16)",
    )
    def get(self, request: Request) -> Response:
        filiais = _filiais(request)
        dados = resumo.resumo(
            request.user,
            [f.pk for f in filiais],
            _mes(request.query_params.get("mes")),
            _onde(request, filiais),
        )
        return Response(ResumoDeVendasSerializer(dados).data)


class MetasView(ViewDeVendas):
    permission_classes = DEFINEM

    @extend_schema(
        responses=QuadroDeMetasSerializer,
        parameters=[
            OpenApiParameter("filial", int),
            OpenApiParameter("mes", str, description="AAAA-MM; sem ele, o mês de hoje"),
        ],
        summary="Metas dos vendedores da filial no mês (VEN-09)",
    )
    def get(self, request: Request) -> Response:
        filial = _uma_filial(request)
        quadro = metas.quadro(filial, _mes(request.query_params.get("mes")))
        return Response(QuadroDeMetasSerializer(quadro).data)

    @extend_schema(
        request=DefinirMetasSerializer,
        responses=QuadroDeMetasSerializer,
        summary="Definir as metas dos vendedores da filial (VEN-09); valor nulo tira a meta",
    )
    def put(self, request: Request) -> Response:
        entrada = DefinirMetasSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        filial = _uma_filial(request, {"filial_id": dados["filial_id"]})
        mes = _mes(dados["mes"])
        pedidas = [
            metas.MetaPedida(m["vendedor_id"], m.get("valor_centavos")) for m in dados["metas"]
        ]
        metas.definir_metas(filial, mes, pedidas, request.user)
        return Response(QuadroDeMetasSerializer(metas.quadro(filial, mes)).data)
