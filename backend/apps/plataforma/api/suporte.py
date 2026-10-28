"""Acesso de suporte (PLT-07; ADR 0013, item 2; contratos de plataforma e de contas).

- Host admin: `POST /api/plataforma/empresas/{id}/acessos-suporte/` abre o acesso e devolve a URL
  de entrada com o token no fragmento.
- Host da empresa: o administrador vê os acessos dos últimos 90 dias, bloqueia, libera e revoga.
  O próprio suporte nunca usa estas rotas (`suporte_proibido`).
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum import relogio
from comum.permissoes import com_padrao, exige_perfil

from .. import selectors, services
from ..models import AcessoSuporte, Empresa, PermissaoSuporte, StatusAcessoSuporte
from ..permissoes import exige_permissao

SO_ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil("administrador"))


class AbrirAcessoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=500)
    chamado_id = serializers.IntegerField(required=False, allow_null=True)
    duracao_minutos = serializers.ChoiceField(choices=[15, 30, 60])
    permissao = serializers.ChoiceField(choices=PermissaoSuporte.choices)


class AcessoAbertoSerializer(serializers.Serializer[Any]):
    acesso_suporte_id = serializers.IntegerField()
    fim = serializers.DateTimeField()
    url_entrada = serializers.CharField()


class AcoesDoAcessoSerializer(serializers.Serializer[Any]):
    revogar = serializers.BooleanField()


class AcessoDaListaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    motivo = serializers.CharField()
    permissao = serializers.ChoiceField(choices=PermissaoSuporte.choices)
    permissao_rotulo = serializers.CharField()
    inicio = serializers.DateTimeField()
    fim = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=StatusAcessoSuporte.choices)
    status_rotulo = serializers.CharField()
    acoes = AcoesDoAcessoSerializer()


class ContagensDoSuporteSerializer(serializers.Serializer[Any]):
    todos = serializers.IntegerField()
    ativos = serializers.IntegerField()
    encerrados = serializers.IntegerField()


class SuporteDaEmpresaSerializer(serializers.Serializer[Any]):
    bloqueado = serializers.BooleanField()
    situacao_rotulo = serializers.CharField()
    contagens = ContagensDoSuporteSerializer()
    acessos = AcessoDaListaSerializer(many=True)


class MotivoDoSuporteSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=500)


class BloqueioSerializer(serializers.Serializer[Any]):
    bloqueado = serializers.BooleanField()


# --- Host admin (public) ---


class AbrirAcessoSuporteView(APIView):
    permission_classes = [IsAuthenticated, exige_permissao("entrar_como_suporte")]

    @extend_schema(
        request=AbrirAcessoSerializer,
        responses={201: AcessoAbertoSerializer},
        summary="Entrar como suporte (PLT-07)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = AbrirAcessoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        empresa = get_object_or_404(Empresa.objects.exclude(schema_name="public"), pk=pk)
        acesso, token = services.abrir_acesso_suporte(
            empresa,
            request.user,
            motivo=dados.validated_data["motivo"],
            duracao_minutos=dados.validated_data["duracao_minutos"],
            permissao=dados.validated_data["permissao"],
        )
        return Response(
            {
                "acesso_suporte_id": acesso.pk,
                "fim": acesso.fim,
                "url_entrada": services.url_de_entrada_do_suporte(acesso, token),
            },
            status=status.HTTP_201_CREATED,
        )


# --- Host da empresa (administrador) ---


def _empresa(request: Request) -> Empresa:
    empresa: Empresa = request.tenant  # type: ignore[attr-defined]
    return empresa


class ControleDoSuporte(APIView):
    permission_classes = SO_ADMINISTRADOR
    suporte_proibido = True  # o suporte não se libera nem se esconde


class SuporteView(ControleDoSuporte):
    @extend_schema(
        parameters=[
            OpenApiParameter("situacao", str, enum=["todos", "ativos", "encerrados"]),
        ],
        responses=SuporteDaEmpresaSerializer,
        summary="Acessos do suporte (últimos 90 dias), com contagens e rótulos (PLT-07)",
    )
    def get(self, request: Request) -> Response:
        situacao = request.query_params.get("situacao")
        return Response(selectors.controle_do_suporte(_empresa(request), situacao))


class BloquearSuporteView(ControleDoSuporte):
    bloquear = True

    @extend_schema(
        request=MotivoDoSuporteSerializer,
        responses=BloqueioSerializer,
        summary="Bloquear o suporte (PLT-07)",
    )
    def post(self, request: Request) -> Response:
        dados = MotivoDoSuporteSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        bloqueado = services.definir_bloqueio_do_suporte(
            _empresa(request), bloquear=self.bloquear, motivo=dados.validated_data.get("motivo", "")
        )
        return Response({"bloqueado": bloqueado})


class LiberarSuporteView(BloquearSuporteView):
    bloquear = False

    @extend_schema(
        request=MotivoDoSuporteSerializer,
        responses=BloqueioSerializer,
        summary="Liberar o suporte (PLT-07)",
    )
    def post(self, request: Request) -> Response:
        return super().post(request)


class RevogarAcessoSuporteView(ControleDoSuporte):
    @extend_schema(
        request=MotivoDoSuporteSerializer,
        responses=AcessoDaListaSerializer,
        summary="Revogar um acesso do suporte (PLT-07)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = MotivoDoSuporteSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        with services.no_publico():
            acesso = get_object_or_404(AcessoSuporte, pk=pk, empresa_id=_empresa(request).pk)
        acesso = services.revogar_acesso_suporte(acesso, dados.validated_data.get("motivo", ""))
        with services.no_publico():
            return Response(selectors.item_do_acesso(acesso, relogio.agora()))
