"""Views finas da auditoria da empresa e da exportação (docs/api/auditoria.md).

Só o administrador (CA-018-08). O token de suporte recebe 403 `PLT-07`: o suporte não lê o
rastro de quem audita o próprio suporte. Não existe escrita de evento: `POST`, `PUT`, `PATCH` e
`DELETE` respondem 405 (CA-018-01).
"""

from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.auditoria import Categoria, TipoAtor
from comum.conexao import schema_atual
from comum.paginacao import PaginacaoPorCursor, envelope_sem_paginas
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..models import EventoAuditoria, Exportacao
from .serializers import (
    EventoDetalheSerializer,
    EventoSerializer,
    ExportacaoCriadaSerializer,
    ExportacaoEntradaSerializer,
    ExportacaoSerializer,
    ListaDeEventosSerializer,
    ListaDeExportacoesSerializer,
    ListaDePessoasSerializer,
    PessoaDaAuditoriaSerializer,
)

ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))

PERIODO = [
    OpenApiParameter("periodo", enum=list(selectors.PERIODOS), description="padrão 7d"),
    OpenApiParameter("de", str, description="data no fuso da empresa (2026-10-01)"),
    OpenApiParameter("ate", str, description="data no fuso da empresa (2026-10-07)"),
]
FILTROS = [
    OpenApiParameter("categoria", enum=list(Categoria.values)),
    OpenApiParameter("ator", int, description="id do usuário"),
    OpenApiParameter("ator_tipo", enum=list(TipoAtor.values)),
    *PERIODO,
    OpenApiParameter("objeto_tipo", str),
    OpenApiParameter("objeto_id", int),
    OpenApiParameter("objeto_codigo", str, description="LOC-2856"),
    OpenApiParameter("filial", int),
]


def token_da_requisicao(request: Request) -> dict[str, Any]:
    return dict(getattr(request.auth, "payload", None) or {})


def listar_eventos(
    view: APIView, request: Request
) -> tuple[PaginacaoPorCursor, list[dict[str, Any]]]:
    """Página de eventos (do mais novo para o mais velho), já representados."""
    qs = selectors.filtrar(request.query_params)
    paginacao = PaginacaoPorCursor()
    paginacao.ordering = ("-ocorrido_em", "-id")  # type: ignore[assignment]
    pagina = paginacao.paginate_queryset(qs, request, view=view) or []
    return paginacao, selectors.representar(pagina)


class SoAdministrador(APIView):
    permission_classes = ADMINISTRADOR
    suporte_proibido = True  # 403 PLT-07, mesmo com "ver e editar"


class EventosView(SoAdministrador):
    @extend_schema(
        responses=ListaDeEventosSerializer,
        operation_id="auditoria_eventos_list",
        parameters=FILTROS,
        summary="Auditoria da empresa (AUD-02, AUD-03)",
    )
    def get(self, request: Request) -> Response:
        paginacao, dados = listar_eventos(self, request)
        return paginacao.get_paginated_response(EventoSerializer(dados, many=True).data)


class EventoView(SoAdministrador):
    @extend_schema(
        responses=EventoDetalheSerializer,
        summary="Evento com antes e depois já classificados (AUD-01, ADR 0014)",
    )
    def get(self, request: Request, pk: int) -> Response:
        evento = get_object_or_404(EventoAuditoria, pk=pk)
        return Response(EventoDetalheSerializer(selectors.detalhar(evento)).data)


class PessoasView(SoAdministrador):
    @extend_schema(
        responses=ListaDePessoasSerializer,
        operation_id="auditoria_pessoas_list",
        parameters=PERIODO,
        summary="Pessoas para o filtro da auditoria",
    )
    def get(self, request: Request) -> Response:
        pessoas = selectors.pessoas(request.query_params)
        return envelope_sem_paginas(PessoaDaAuditoriaSerializer(pessoas, many=True).data)


# --- Exportação (AUD-07, S-15) ---


def _exportacao(exportacao: Exportacao) -> dict[str, Any]:
    return {
        "id": exportacao.pk,
        "solicitada_em": exportacao.criado_em,
        "solicitada_por": exportacao.solicitada_por_nome or "Automático",
        "conteudo": services.conteudo_rotulo(exportacao),
        "formato": exportacao.formato,
        "tamanho_bytes": exportacao.tamanho_bytes,
        "status": exportacao.status,
        "expira_em": exportacao.expira_em,
    }


class ExportacoesView(SoAdministrador):
    @extend_schema(
        responses=ListaDeExportacoesSerializer,
        operation_id="exportacoes_list",
        summary="Exportações recentes (AUD-07)",
    )
    def get(self, request: Request) -> Response:
        paginacao = PaginacaoPorCursor()
        paginacao.ordering = ("-criado_em", "-id")  # type: ignore[assignment]
        pagina = paginacao.paginate_queryset(Exportacao.objects.all(), request, view=self) or []
        dados = [_exportacao(e) for e in pagina]
        return paginacao.get_paginated_response(ExportacaoSerializer(dados, many=True).data)

    @extend_schema(
        request=ExportacaoEntradaSerializer,
        responses={202: ExportacaoCriadaSerializer},
        summary="Pedir exportação (AUD-07); backup completo pede 2 etapas recentes (S-15)",
    )
    def post(self, request: Request) -> Response:
        entrada = ExportacaoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        periodo = dados.get("periodo")
        exportacao = services.solicitar(
            itens=list(dados["itens"]),
            formato=dados["formato"],
            periodo={"de": str(periodo["de"]), "ate": str(periodo["ate"])} if periodo else None,
            token=token_da_requisicao(request),
        )
        from ..tasks import auditoria_exportar

        schema, id_exportacao = schema_atual(), exportacao.pk
        link = request.build_absolute_uri(f"/api/exportacoes/{id_exportacao}/baixar/")
        transaction.on_commit(lambda: auditoria_exportar.delay(schema, id_exportacao, link))
        return Response(
            ExportacaoCriadaSerializer({"id": exportacao.pk, "status": exportacao.status}).data,
            status=status.HTTP_202_ACCEPTED,
        )


class BaixarExportacaoView(SoAdministrador):
    @extend_schema(
        responses={
            302: OpenApiResponse(description="Redireciona para a URL assinada de 15 minutos"),
            410: OpenApiResponse(description="exportacao_expirada"),
        },
        summary="Baixar a exportação (S-15)",
    )
    def get(self, request: Request, pk: int) -> Response:
        exportacao = get_object_or_404(Exportacao, pk=pk)
        if services.vencida(exportacao):
            services.expirar(exportacao)
            exportacao.refresh_from_db()
        url = services.baixar(exportacao, token_da_requisicao(request))
        return Response(status=status.HTTP_302_FOUND, headers={"Location": url})
