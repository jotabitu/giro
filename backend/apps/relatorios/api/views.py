"""Views finas do painel (`docs/api/painel.md`, "Rotas, perfis e o que entra no MVP").

Todos os perfis; a variante é a do `eu` (`contas.navegacao`), nunca da query. A filial vem só de
`filtrar_por_filial` (USR-07). O suporte só lê (`suporte_somente_leitura`), com a variante e o
escopo do administrador. Cache por empresa, pessoa, filial, rota e variante: 5 minutos no início, 60
segundos nos contadores; nunca compartilhado entre pessoas (escopo e APR-09 dependem de quem pede).
"""

from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contas import selectors as contas_selectors
from apps.filiais.models import Filial
from apps.filiais.selectors import filtrar_por_filial
from comum import relogio
from comum.conexao import schema_atual
from comum.erros import ErroDeValidacao
from comum.permissoes import TODAS_AS_FILIAIS, com_padrao, filial_pedida

from .. import selectors
from .serializers import (
    INICIO_RESPOSTA,
    SERIALIZER_DA_VARIANTE,
    ConfiguracoesSerializer,
    ContadoresSerializer,
)

PRAZO_DO_INICIO = 5 * 60
PRAZO_DOS_CONTADORES = 60


def _escopo(request: Request) -> selectors.Escopo:
    filiais = filtrar_por_filial(Filial.objects.all(), request, campo="pk")
    return selectors.Escopo(
        filiais=frozenset(filiais.values_list("pk", flat=True)),
        todas=filial_pedida(request) == TODAS_AS_FILIAIS,
    )


def _quem(usuario: Any) -> str:
    return str(usuario.pk) if usuario.pk is not None else f"suporte-{usuario.acesso_suporte_id}"


def _em_cache(chave: str, prazo: int, montar: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    dados = cache.get(chave)
    if dados is None:
        dados = montar()
        cache.set(chave, dados, prazo)
    return dict(dados)


class _Painel(APIView):
    escopo_de_relatorio = True  # "Todas as filiais" com a extra `relatorios_todas_filiais`
    suporte_somente_leitura = True

    def _chave(
        self, request: Request, escopo: selectors.Escopo, rota: str, nav: dict[str, Any]
    ) -> str:
        # A variante na chave: com a 1ª locação (IMP-01) o administrador sai da implantação na
        # hora, sem esperar o cache vencer.
        variante = nav["inicio"]["variante"]
        return f"painel:{schema_atual()}:{_quem(request.user)}:{escopo.chave}:{rota}:{variante}"


class ContadoresView(_Painel):
    @extend_schema(
        responses=ContadoresSerializer,
        summary="Contadores do menu (USR-05, APR-09, FIN-15)",
    )
    def get(self, request: Request) -> Response:
        escopo = _escopo(request)
        nav = contas_selectors.navegacao_de(request.user, request.tenant)  # type: ignore[attr-defined]

        def montar() -> dict[str, Any]:
            chaves = contas_selectors.chaves_de_contador(nav)
            return {
                "atualizado_em": relogio.agora(),
                "contadores": selectors.contadores(request.user, escopo, chaves),
            }

        chave = self._chave(request, escopo, "contadores", nav)
        return Response(_em_cache(chave, PRAZO_DOS_CONTADORES, montar))


class InicioView(_Painel):
    @extend_schema(
        responses=INICIO_RESPOSTA,
        parameters=[
            OpenApiParameter("periodo", enum=list(selectors.PERIODOS), default="7d"),
        ],
        summary="Início por perfil (USR-08, IMP-01, VEI-06, FIN-13, FIN-15)",
    )
    def get(self, request: Request) -> Response:
        periodo = request.query_params.get("periodo") or selectors.PERIODO_PADRAO
        if periodo not in selectors.PERIODOS:
            raise ErroDeValidacao({"periodo": ["Use hoje, 7d ou 30d."]})
        escopo = _escopo(request)
        empresa = request.tenant  # type: ignore[attr-defined]

        nav = contas_selectors.navegacao_de(request.user, empresa)
        variante = nav["inicio"]["variante"]

        def montar() -> dict[str, Any]:
            dados = selectors.inicio(request.user, variante, escopo, periodo, empresa)
            return dict(SERIALIZER_DA_VARIANTE[variante](dados).data)

        chave = f"{self._chave(request, escopo, 'inicio', nav)}:{periodo}"
        return Response(_em_cache(chave, PRAZO_DO_INICIO, montar))


# --- Configurações (`docs/api/configuracoes.md`) ---


class Administracao(BasePermission):
    """Quem tem `pode.administracao` (administrador e o suporte, que entra como ele)."""

    message = "Seu perfil não tem acesso a esta página"

    def has_permission(self, request: Request, view: Any) -> bool:
        return bool(contas_selectors.pode(request.user, "administracao"))


class ConfiguracoesView(APIView):
    """Os cartões de Configurações. Sem cache: voltar de Filiais ou de Usuários mostra o número
    novo. Responde com a empresa sem operação (é leitura) e sem depender de `configuracoes` em
    `GIRO_MODULOS_ATIVOS`, que só liga o item do menu."""

    permission_classes = com_padrao(Administracao)
    suporte_somente_leitura = True

    @extend_schema(
        responses=ConfiguracoesSerializer,
        summary="Resumo de Configurações (USR-05, PLT-03, PLT-07, IMP-01, IMP-04, IMP-05)",
    )
    def get(self, request: Request) -> Response:
        suporte = bool(getattr(request.user, "e_suporte", False))
        dados = selectors.configuracoes(request.user, suporte)
        return Response(ConfiguracoesSerializer(dados).data)
