"""Login da equipe da plataforma com 2 etapas e convite (PLT-08, PLT-09; ADR 0013).

Rotas em `admin.<dominio>/api/plataforma/` (schema public). As do lado da empresa (login,
sessões, convite da locadora) são da T-011, e usam os mesmos blocos.
"""

from typing import Any

from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.plataforma.permissoes import exige_permissao, pode
from comum.autenticacao import (
    AMR_SENHA_E_CODIGO,
    JWTPre2FA,
    apagar_cookie_refresh,
    emitir_pre_2fa,
    emitir_tokens,
    gravar_cookie_refresh,
    recusar_token_de_suporte,
    veio_do_frontend,
)
from comum.erros import Conflito, NaoAutenticado, SemPermissao
from comum.limites import LIMITES_DE_ENTRAR, AcessoPorIP

from .. import dois_fatores, sessoes
from ..models import StatusUsuario, Usuario
from ..services import (
    CONVITE_VENCIDO,
    aceitar_convite,
    ativar_depois_do_2fa,
    convite_aceito,
    convite_pelo_token,
    pode_configurar_2fa,
)

EMISSOR_DA_PLATAFORMA = "Giro"  # a equipe da plataforma usa a marca Giro

CREDENCIAIS_INVALIDAS = ("credenciais_invalidas", "E-mail, senha ou código incorretos")


def dados_do_usuario(usuario: Usuario) -> dict[str, Any]:
    return {
        "id": usuario.pk,
        "nome": usuario.nome,
        "email": usuario.email,
        "funcao": usuario.funcao_plataforma,
        "pode": pode(usuario.funcao_plataforma),
    }


def _credenciais_invalidas(
    request: Request, usuario: Usuario | None, motivo: str
) -> NaoAutenticado:
    dois_fatores.auditar_entrada(request, "usuario.entrar_falhou", usuario, motivo)
    return NaoAutenticado(*CREDENCIAIS_INVALIDAS)


def _entrou(request: Request, usuario: Usuario, extras: dict[str, Any] | None = None) -> Response:
    dois_fatores.auditar_entrada(request, "usuario.entrar", usuario)
    refresh = emitir_tokens(usuario, amr=AMR_SENHA_E_CODIGO)
    resposta = Response(
        {
            "access": str(refresh.access_token),
            "usuario": dados_do_usuario(usuario),
            **(extras or {}),
        }
    )
    gravar_cookie_refresh(resposta, refresh)
    return resposta


def _configurar_2fa(usuario: Usuario) -> Response:
    return Response({"etapa": "configurar_2fa", "token_pre_2fa": str(emitir_pre_2fa(usuario))})


def _falhou(request: Request, tentativa: dois_fatores.Tentativa) -> Exception:
    """401, ou 429 quando esta tentativa atingiu o limite (PLT-08). Os dois ficam auditados."""
    motivo = "código" if tentativa.falha == dois_fatores.Falha.CODIGO else "senha"
    erro = _credenciais_invalidas(request, tentativa.usuario, motivo)
    return tentativa.bloqueio or erro


class EntrarSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()
    senha = serializers.CharField(trim_whitespace=False)
    codigo = serializers.CharField(required=False, allow_blank=True, max_length=6)
    codigo_recuperacao = serializers.CharField(required=False, allow_blank=True, max_length=20)


class CodigoSerializer(serializers.Serializer[dict[str, str]]):
    codigo = serializers.RegexField(r"^\d{6}$")


class PodeSerializer(serializers.Serializer[Any]):
    ver_empresas = serializers.BooleanField()
    entrar_como_suporte = serializers.BooleanField()
    estender_teste_e_mudar_plano = serializers.BooleanField()
    cobranca_e_faturas = serializers.BooleanField()
    suspender_empresa = serializers.BooleanField()
    planos_e_precos = serializers.BooleanField()
    equipe_interna = serializers.BooleanField()


class UsuarioDaPlataformaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    email = serializers.EmailField()
    funcao = serializers.CharField()
    pode = PodeSerializer()


class EuSerializer(UsuarioDaPlataformaSerializer):
    dois_fatores_ativo = serializers.BooleanField()
    codigos_recuperacao_restantes = serializers.IntegerField()


class EntrouSerializer(serializers.Serializer[Any]):
    access = serializers.CharField()
    usuario = UsuarioDaPlataformaSerializer()
    codigos_recuperacao = serializers.ListField(child=serializers.CharField(), required=False)


class EtapaSerializer(serializers.Serializer[Any]):
    etapa = serializers.ChoiceField(choices=["configurar_2fa"])
    token_pre_2fa = serializers.CharField()


class AccessSerializer(serializers.Serializer[Any]):
    access = serializers.CharField()


class ConviteSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    nome = serializers.CharField()
    funcao = serializers.CharField()
    expira_em = serializers.DateTimeField()


ENTRAR_OU_CONFIGURAR = PolymorphicProxySerializer(
    component_name="EntrarResposta",
    serializers=[EntrouSerializer, EtapaSerializer],
    resource_type_field_name=None,
)


class Publica(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes: list[Any] = [AcessoPorIP]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        recusar_token_de_suporte(request)  # nenhuma rota da plataforma aceita (PLT-07)
        super().initial(request, *args, **kwargs)


class EntrarView(Publica):
    throttle_classes = LIMITES_DE_ENTRAR

    @extend_schema(
        request=EntrarSerializer,
        responses=ENTRAR_OU_CONFIGURAR,
        summary="Entrar na plataforma (PLT-08)",
    )
    def post(self, request: Request) -> Response:
        dados = EntrarSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        email = dados.validated_data["email"].strip().lower()
        senha = dados.validated_data["senha"]
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            Usuario().set_password(senha)  # mesmo tempo de resposta de quem existe
            raise _credenciais_invalidas(request, None, "e-mail")
        tentativa = dois_fatores.tentar_entrar(
            usuario,
            senha=senha,
            codigo=dados.validated_data.get("codigo", ""),
            codigo_recuperacao=dados.validated_data.get("codigo_recuperacao", ""),
        )
        if tentativa.falha is not None:
            raise _falhou(request, tentativa)
        usuario = tentativa.usuario
        if usuario.status == StatusUsuario.DESATIVADO or (
            usuario.status == StatusUsuario.CONVITE_PENDENTE and not convite_aceito(usuario)
        ):
            raise SemPermissao(
                "usuario_inativo", "Seu acesso foi desativado. Fale com o administrador."
            )
        if tentativa.dispositivo is None:
            if not pode_configurar_2fa(usuario):  # P-05 da T-057
                raise SemPermissao("convite_expirado", CONVITE_VENCIDO)
            return _configurar_2fa(usuario)
        return _entrou(request, usuario)


class Configurar2FAView(APIView):
    authentication_classes = [JWTPre2FA]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AcessoPorIP]

    @extend_schema(
        request=None,
        responses=inline_serializer("Configurar2FA", {"otpauth_uri": serializers.CharField()}),
        summary="Novo autenticador (PLT-08)",
    )
    def post(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        if dois_fatores.tem_2fa(usuario):
            raise Conflito("2fa_ja_configurado", "O autenticador já está configurado.")
        if not pode_configurar_2fa(usuario):  # P-05 da T-057
            raise SemPermissao("convite_expirado", CONVITE_VENCIDO)
        dispositivo = dois_fatores.novo_autenticador(usuario)
        return Response({"otpauth_uri": dispositivo.config_url_para(EMISSOR_DA_PLATAFORMA)})


class Verificar2FAView(APIView):
    authentication_classes = [JWTPre2FA]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AcessoPorIP]

    @extend_schema(
        request=CodigoSerializer, responses=EntrouSerializer, summary="Confirmar o código (PLT-08)"
    )
    def post(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        dados = CodigoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        confirmando = not dois_fatores.tem_2fa(usuario)
        if confirmando and not pode_configurar_2fa(usuario):  # P-05 da T-057
            raise SemPermissao("convite_expirado", CONVITE_VENCIDO)
        tentativa = dois_fatores.verificar_codigo(
            usuario, codigo=dados.validated_data["codigo"], confirmando=confirmando
        )
        usuario, dispositivo = tentativa.usuario, tentativa.dispositivo
        if dispositivo is None:
            raise _falhou(request, tentativa)
        extras: dict[str, Any] = {}
        if confirmando:
            extras["codigos_recuperacao"] = dois_fatores.confirmar_autenticador(dispositivo)
            ativar_depois_do_2fa(usuario)
        return _entrou(request, usuario, extras)


class RenovarView(Publica):
    @extend_schema(request=None, responses=AccessSerializer, summary="Renovar o acesso pelo cookie")
    def post(self, request: Request) -> Response:
        if not veio_do_frontend(request):
            raise SemPermissao("permissao", "Requisição recusada.")
        _, novo = sessoes.renovar(request)  # rotação com a sessão travada (P-07)
        resposta = Response({"access": str(novo.access_token)})
        gravar_cookie_refresh(resposta, novo)
        return resposta


class SairView(Publica):
    @extend_schema(request=None, responses={204: None}, summary="Sair")
    def post(self, request: Request) -> Response:
        if not veio_do_frontend(request):
            raise SemPermissao("permissao", "Requisição recusada.")
        # Sair sempre apaga o cookie, mesmo com token vencido ou de outra empresa.
        sessoes.sair(request)
        resposta = Response(status=status.HTTP_204_NO_CONTENT)
        apagar_cookie_refresh(resposta)
        return resposta


class EuView(APIView):
    permission_classes = [IsAuthenticated, exige_permissao("ver_empresas")]

    @extend_schema(responses=EuSerializer, summary="Quem está na plataforma (PLT-09)")
    def get(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        return Response(
            {
                **dados_do_usuario(usuario),
                "dois_fatores_ativo": dois_fatores.tem_2fa(usuario),
                "codigos_recuperacao_restantes": dois_fatores.codigos_restantes(usuario),
            }
        )


class TokenDoConviteDaEquipeSerializer(serializers.Serializer[dict[str, str]]):
    token = serializers.CharField(max_length=100)


class AceitarConviteDaEquipeSerializer(TokenDoConviteDaEquipeSerializer):
    senha = serializers.CharField(trim_whitespace=False)


class ConsultarConviteView(Publica):
    """O token vem no corpo, nunca no caminho (P-09, T-072)."""

    @extend_schema(
        request=TokenDoConviteDaEquipeSerializer,
        responses=ConviteSerializer,
        summary="Ver convite da equipe",
    )
    def post(self, request: Request) -> Response:
        dados = TokenDoConviteDaEquipeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        convite = convite_pelo_token(dados.validated_data["token"])
        usuario = convite.usuario
        return Response(
            {
                "email": usuario.email,
                "nome": usuario.nome,
                "funcao": usuario.funcao_plataforma,
                "expira_em": convite.expira_em,
            }
        )


class AceitarConviteView(Publica):
    @extend_schema(
        request=AceitarConviteDaEquipeSerializer,
        responses=EtapaSerializer,
        summary="Aceitar convite da equipe",
    )
    def post(self, request: Request) -> Response:
        dados = AceitarConviteDaEquipeSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = aceitar_convite(dados.validated_data["token"], dados.validated_data["senha"])
        return _configurar_2fa(usuario)
