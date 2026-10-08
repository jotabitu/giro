"""Usuários da empresa (Administração) e convite (contrato de contas; USR-01, USR-03, USR-04,
PLT-03).

`usuarios/` é só do administrador (`pode.administracao`). `convites/consultar/` e
`convites/aceitar/` são públicos e recebem o token no corpo, nunca no caminho (P-09, T-072).
"""

from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, PolymorphicProxySerializer, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.autenticacao import AMR_SENHA
from comum.paginacao import PaginacaoPorCursor
from comum.permissoes import com_padrao, exige_perfil, resumo_das_filiais

from .. import selectors, services, sessoes
from ..models import MotivoRevogacao, Perfil, PermissaoExtra, TipoSessao, Usuario
from .acesso import (
    EtapaDoLoginSerializer,
    FilialResumoSerializer,
    ProntoSerializer,
    Publica,
    SessoesSerializer,
    _etapa,
    _pronto,
    _sessao_para_lista,
)

SO_ADMINISTRADOR: list[type[BasePermission]] = com_padrao(exige_perfil(Perfil.ADMINISTRADOR))


def _eu(request: Request) -> Usuario:
    usuario: Usuario = request.user  # type: ignore[assignment]
    return usuario


def _usuario(pk: int) -> Usuario:
    usuario: Usuario = get_object_or_404(Usuario.objects.exclude(perfil=""), pk=pk)
    return usuario


# --- Serializers ---


class PlanoDeUsuariosSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField(allow_null=True)
    aviso = serializers.BooleanField()
    bloqueado = serializers.BooleanField()


class ContagensDeUsuariosSerializer(serializers.Serializer[Any]):
    todos = serializers.IntegerField()
    ativos = serializers.IntegerField()
    convites = serializers.IntegerField()
    desativados = serializers.IntegerField()


class UsuarioItemSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    celular = serializers.CharField(allow_null=True)
    perfil = serializers.ChoiceField(choices=Perfil.choices)
    filiais = FilialResumoSerializer(many=True)
    todas_filiais = serializers.BooleanField()
    status = serializers.CharField()
    dois_fatores_ativo = serializers.BooleanField()
    ultimo_acesso_em = serializers.DateTimeField(allow_null=True)
    convite_expira_em = serializers.DateTimeField(allow_null=True)
    eu = serializers.BooleanField()


class ListaDeUsuariosSerializer(serializers.Serializer[Any]):
    plano = PlanoDeUsuariosSerializer()
    contagens = ContagensDeUsuariosSerializer()
    resultados = UsuarioItemSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class PermissaoExtraDoUsuarioSerializer(serializers.Serializer[Any]):
    chave = serializers.ChoiceField(choices=PermissaoExtra.choices)
    marcada = serializers.BooleanField()
    padrao_do_perfil = serializers.BooleanField()


class UsuarioDetalheSerializer(UsuarioItemSerializer):
    permissoes_extras = PermissaoExtraDoUsuarioSerializer(many=True)
    entrou_em = serializers.DateTimeField(allow_null=True)


class ConvidarSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    nome = serializers.CharField(required=False, allow_blank=True, max_length=150)
    celular = serializers.CharField(required=False, allow_blank=True, max_length=20)
    perfil = serializers.ChoiceField(choices=Perfil.choices)
    filiais = serializers.ListField(child=serializers.IntegerField(), required=False)
    permissoes_extras = serializers.ListField(
        child=serializers.ChoiceField(choices=PermissaoExtra.choices), required=False
    )


class AlterarUsuarioSerializer(serializers.Serializer[Any]):
    perfil = serializers.ChoiceField(choices=Perfil.choices, required=False)
    filiais = serializers.ListField(child=serializers.IntegerField(), required=False)
    permissoes_extras = serializers.ListField(
        child=serializers.ChoiceField(choices=PermissaoExtra.choices), required=False
    )


class MotivoOpcionalSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=500)


class MotivoDaRedefinicaoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(max_length=500)


class TokenSerializer(serializers.Serializer[Any]):
    token = serializers.CharField(max_length=100)


class AceitarConviteSerializer(TokenSerializer):
    nome = serializers.CharField(required=False, allow_blank=True, max_length=150)
    senha = serializers.CharField(trim_whitespace=False)
    aparelho = serializers.ChoiceField(choices=TipoSessao.choices, default=TipoSessao.DESKTOP)


class ConviteDaEmpresaSerializer(serializers.Serializer[Any]):
    empresa = serializers.CharField()
    email = serializers.EmailField()
    nome = serializers.CharField()
    perfil = serializers.ChoiceField(choices=Perfil.choices)
    filiais = FilialResumoSerializer(many=True)
    convidado_por = serializers.CharField(allow_null=True)
    expira_em = serializers.DateTimeField()
    exige_2fa = serializers.BooleanField()


ACEITAR_RESPOSTA = PolymorphicProxySerializer(
    component_name="AceitarConviteResposta",
    serializers=[ProntoSerializer, EtapaDoLoginSerializer],
    resource_type_field_name=None,
)


# --- Usuários ---


class PaginacaoDeUsuarios(PaginacaoPorCursor):
    ordering = ("nome", "id")  # type: ignore[assignment]


def _detalhe(request: Request, usuario: Usuario, codigo: int = status.HTTP_200_OK) -> Response:
    return Response(selectors.detalhe_de_usuario(usuario, _eu(request)), status=codigo)


class UsuariosView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        parameters=[
            OpenApiParameter("situacao", str, enum=list(selectors.SITUACOES)),
            OpenApiParameter("perfil", str, enum=Perfil.values),
            OpenApiParameter("filial", int),
            OpenApiParameter("busca", str),
        ],
        responses=ListaDeUsuariosSerializer,
        operation_id="usuarios_list",
        summary="Usuários, com o plano e as contagens (USR-01, PLT-03)",
    )
    def get(self, request: Request) -> Response:
        from apps.plataforma.selectors import uso_do_plano

        consulta = selectors.usuarios(
            situacao=request.query_params.get("situacao"),
            perfil=request.query_params.get("perfil"),
            filial=request.query_params.get("filial"),
            busca=request.query_params.get("busca"),
        )
        paginador = PaginacaoDeUsuarios()
        pagina = paginador.paginate_queryset(consulta, request, view=self) or []
        return paginador.get_paginated_response(
            [selectors.item_de_usuario(u, _eu(request)) for u in pagina],
            extras={
                "plano": uso_do_plano()["usuarios"],
                "contagens": selectors.contagens_de_usuarios(),
            },
        )


class UsuarioView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(responses=UsuarioDetalheSerializer, summary="Usuário")
    def get(self, request: Request, pk: int) -> Response:
        return _detalhe(request, _usuario(pk))

    @extend_schema(
        request=AlterarUsuarioSerializer,
        responses=UsuarioDetalheSerializer,
        summary="Perfil, filiais e permissões extras (USR-03)",
    )
    def patch(self, request: Request, pk: int) -> Response:
        dados = AlterarUsuarioSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.alterar_usuario(
            _usuario(pk),
            por=_eu(request),
            perfil=dados.validated_data.get("perfil"),
            filiais=dados.validated_data.get("filiais"),
            permissoes_extras=dados.validated_data.get("permissoes_extras"),
        )
        return _detalhe(request, usuario)


class ConvidarView(APIView):
    permission_classes = SO_ADMINISTRADOR

    @extend_schema(
        request=ConvidarSerializer,
        responses={201: UsuarioDetalheSerializer},
        summary="Convidar (USR-01, PLT-03)",
    )
    def post(self, request: Request) -> Response:
        dados = ConvidarSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.convidar(
            email=dados.validated_data["email"],
            perfil=dados.validated_data["perfil"],
            filiais=dados.validated_data.get("filiais"),
            nome=dados.validated_data.get("nome", ""),
            celular=dados.validated_data.get("celular", ""),
            permissoes_extras=dados.validated_data.get("permissoes_extras"),
            por=_eu(request),
        )
        return _detalhe(request, usuario, status.HTTP_201_CREATED)


class AcaoSobreUsuario(APIView):
    permission_classes = SO_ADMINISTRADOR


class ReenviarConviteView(AcaoSobreUsuario):
    @extend_schema(request=None, responses=UsuarioDetalheSerializer, summary="Reenviar convite")
    def post(self, request: Request, pk: int) -> Response:
        return _detalhe(request, services.reenviar_convite(_usuario(pk), _eu(request)))


class CancelarConviteView(AcaoSobreUsuario):
    @extend_schema(request=None, responses=UsuarioDetalheSerializer, summary="Cancelar convite")
    def post(self, request: Request, pk: int) -> Response:
        return _detalhe(request, services.cancelar_convite(_usuario(pk), _eu(request)))


class DesativarUsuarioView(AcaoSobreUsuario):
    @extend_schema(
        request=MotivoOpcionalSerializer,
        responses=UsuarioDetalheSerializer,
        summary="Desativar (USR-04)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = MotivoOpcionalSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.desativar_usuario(
            _usuario(pk), por=_eu(request), motivo=dados.validated_data.get("motivo", "")
        )
        return _detalhe(request, usuario)


class ReativarUsuarioView(AcaoSobreUsuario):
    @extend_schema(request=None, responses=UsuarioDetalheSerializer, summary="Reativar (PLT-03)")
    def post(self, request: Request, pk: int) -> Response:
        return _detalhe(request, services.reativar_usuario(_usuario(pk), por=_eu(request)))


class Redefinir2FAView(AcaoSobreUsuario):
    @extend_schema(
        request=MotivoDaRedefinicaoSerializer,
        responses=UsuarioDetalheSerializer,
        summary="Redefinir as 2 etapas (USR-02)",
    )
    def post(self, request: Request, pk: int) -> Response:
        dados = MotivoDaRedefinicaoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.redefinir_2fa(
            _usuario(pk), por=_eu(request), motivo=dados.validated_data["motivo"]
        )
        return _detalhe(request, usuario)


class SessoesDoUsuarioView(AcaoSobreUsuario):
    @extend_schema(responses=SessoesSerializer, summary="Sessões de um usuário")
    def get(self, request: Request, pk: int) -> Response:
        atual = sessoes.sid_da_requisicao(request)
        lista = sessoes.ativas(_usuario(pk))
        return Response({"resultados": [_sessao_para_lista(s, atual) for s in lista]})


class EncerrarSessaoDoUsuarioView(AcaoSobreUsuario):
    @extend_schema(request=None, responses={204: None}, summary="Encerrar sessão de um usuário")
    def post(self, request: Request, pk: int, sid: int) -> Response:
        sessao = get_object_or_404(sessoes.ativas(_usuario(pk)), pk=sid)
        sessoes.revogar(sessao, MotivoRevogacao.REVOGADA_PELO_ADMINISTRADOR, por=_eu(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Convite (público; o token no corpo, P-09) ---


class ConsultarConviteView(Publica):
    @extend_schema(
        request=TokenSerializer,
        responses=ConviteDaEmpresaSerializer,
        summary="Ler o convite para a tela (USR-01)",
    )
    def post(self, request: Request) -> Response:
        dados = TokenSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        convite = services.convite_pelo_token(dados.validated_data["token"])
        usuario = convite.usuario
        return Response(
            {
                "empresa": str(getattr(request.tenant, "nome_exibicao", "")),  # type: ignore[attr-defined]
                "email": usuario.email,
                "nome": usuario.nome,
                "perfil": usuario.perfil,
                "filiais": resumo_das_filiais(usuario),
                "convidado_por": convite.enviado_por.nome if convite.enviado_por else None,
                "expira_em": convite.expira_em,
                "exige_2fa": usuario.exige_2fa_pela_regra,
            }
        )


class AceitarConviteView(Publica):
    @extend_schema(
        request=AceitarConviteSerializer,
        responses=ACEITAR_RESPOSTA,
        summary="Aceitar o convite (USR-01)",
    )
    def post(self, request: Request) -> Response:
        dados = AceitarConviteSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.aceitar_convite(
            dados.validated_data["token"],
            dados.validated_data["senha"],
            nome=dados.validated_data.get("nome"),
        )
        aparelho = dados.validated_data["aparelho"]
        if usuario.exige_2fa:
            # Ativa ao confirmar o código em `2fa/verificar/` (USR-02).
            return _etapa("configurar_2fa", usuario, aparelho)
        services.ativar_depois_do_2fa(usuario)
        usuario.refresh_from_db()
        return _pronto(request, usuario, tipo=aparelho, amr=AMR_SENHA)


# Públicas, de segurança da conta (ver `acesso.VIEWS_DE_ACESSO`): sem `EmpresaOperando`.
VIEWS_DE_CONVITE: tuple[type[APIView], ...] = (ConsultarConviteView, AceitarConviteView)
