"""Auditoria da plataforma (Plat-Auditoria; docs/api/auditoria.md).

Só os eventos do `public`: equipe interna, acessos de suporte, cobrança, planos e segurança do
login da plataforma. Não lê os schemas das empresas (CA-018-16). Só o dono (CA-018-15), e não
existe escrita (405, CA-018-01).
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria import selectors as auditoria_selectors
from apps.auditoria.api.serializers import EventoDetalheSerializer, EventoSerializer
from apps.auditoria.api.views import FILTROS
from apps.auditoria.models import EventoAuditoria
from comum.erros import ErroDeValidacao
from comum.paginacao import PaginacaoPorCursor

from .. import auditoria
from ..permissoes import SoDono


class EmpresaDoEventoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome_exibicao = serializers.CharField()


class EventoDaPlataformaSerializer(EventoSerializer):
    empresa = EmpresaDoEventoSerializer(allow_null=True)


class IndicadoresDaAuditoriaSerializer(serializers.Serializer[Any]):
    acessos_suporte_30d = serializers.IntegerField()
    acessos_suporte_com_edicao_30d = serializers.IntegerField()
    logins_bloqueados_hoje = serializers.IntegerField()
    mudancas_de_preco_7d = serializers.IntegerField()


class ListaDeEventosDaPlataformaSerializer(serializers.Serializer[Any]):
    indicadores = IndicadoresDaAuditoriaSerializer()
    resultados = EventoDaPlataformaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class EventoDetalheDaPlataformaSerializer(EventoDetalheSerializer):
    empresa = EmpresaDoEventoSerializer(allow_null=True)


def _empresa_pedida(request: Request) -> int | None:
    valor = request.query_params.get("empresa")
    if not valor:
        return None
    if not valor.isdigit():
        raise ErroDeValidacao({"empresa": ["Informe um número."]})
    return int(valor)


class EventosDaPlataformaView(APIView):
    permission_classes = [IsAuthenticated, SoDono]

    @extend_schema(
        responses=ListaDeEventosDaPlataformaSerializer,
        operation_id="plataforma_auditoria_eventos_list",
        parameters=[*FILTROS, OpenApiParameter("empresa", int)],
        summary="Auditoria da plataforma (AUD-03, PLT-07, PLT-08)",
    )
    def get(self, request: Request) -> Response:
        qs = auditoria_selectors.filtrar(request.query_params)
        empresa = _empresa_pedida(request)
        if empresa is not None:
            qs = auditoria.de_empresa(qs, empresa)
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("-ocorrido_em", "-id")  # type: ignore[assignment]
        pagina = list(paginacao.paginate_queryset(qs, request, view=self) or [])
        empresas = auditoria.empresas_dos_eventos(pagina)
        dados = [
            {**item, "empresa": empresas[evento.pk]}
            for evento, item in zip(pagina, auditoria_selectors.representar(pagina), strict=True)
        ]
        return paginacao.get_paginated_response(
            EventoDaPlataformaSerializer(dados, many=True).data,
            extras={"indicadores": auditoria.indicadores()},
        )


class EventoDaPlataformaView(APIView):
    permission_classes = [IsAuthenticated, SoDono]

    @extend_schema(
        responses=EventoDetalheDaPlataformaSerializer,
        operation_id="plataforma_auditoria_evento_retrieve",
        summary="Evento da plataforma com antes e depois já classificados",
    )
    def get(self, request: Request, pk: int) -> Response:
        evento = get_object_or_404(EventoAuditoria, pk=pk)
        dados = {
            **auditoria_selectors.detalhar(evento),
            "empresa": auditoria.empresas_dos_eventos([evento])[evento.pk],
        }
        return Response(EventoDetalheDaPlataformaSerializer(dados).data)
