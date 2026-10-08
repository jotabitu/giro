"""Login da equipe da plataforma com 2 etapas e convite (PLT-08, PLT-09; ADR 0013).

Rotas em `admin.<dominio>/api/plataforma/` (schema public). As do lado da empresa (login,
sessões, convite da locadora) são da T-011, e usam os mesmos blocos.
"""

import contextlib
from dataclasses import replace
from typing import Any

from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.plataforma.permissoes import exige_permissao, pode
from comum.auditoria import Categoria, TipoAtor, registrar_evento, usar_ator
from comum.autenticacao import (
    AMR_SENHA_E_CODIGO,
    JWTPre2FA,
    apagar_cookie_refresh,
    emitir_pre_2fa,
    emitir_tokens,
    gravar_cookie_refresh,
    refresh_do_cookie,
    veio_do_frontend,
)
from comum.erros import Conflito, ErroDeValidacao, NaoAutenticado, SemPermissao
from comum.middleware import ator_da_requisicao

from .. import dois_fatores
from ..models import StatusUsuario, Usuario
from ..services import aceitar_convite, ativar_depois_do_2fa, convite_aceito, convite_pelo_token

CREDENCIAIS_INVALIDAS = ("credenciais_invalidas", "E-mail, senha ou código incorretos")


def dados_do_usuario(usuario: Usuario) -> dict[str, Any]:
    return {
        "id": usuario.pk,
        "nome": usuario.nome,
        "email": usuario.email,
        "funcao": usuario.funcao_plataforma,
        "pode": pode(usuario.funcao_plataforma),
    }


def _registrar(request: Request, acao: str, usuario: Usuario | None, motivo: str = "") -> None:
    ator = ator_da_requisicao(request)
    if usuario is not None and acao == "usuario.entrar":
        ator = replace(ator, tipo=TipoAtor.USUARIO, id=usuario.pk, nome=usuario.nome)
    with usar_ator(ator):
        registrar_evento(acao, Categoria.SEGURANCA, objeto=usuario, motivo=motivo, regra="PLT-08")


def _credenciais_invalidas(
    request: Request, usuario: Usuario | None, motivo: str
) -> NaoAutenticado:
    _registrar(request, "usuario.entrar_falhou", usuario, motivo)
    return NaoAutenticado(*CREDENCIAIS_INVALIDAS)


def _entrou(request: Request, usuario: Usuario, extras: dict[str, Any] | None = None) -> Response:
    dois_fatores.zerar_tentativas(usuario)
    _registrar(request, "usuario.entrar", usuario)
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


def _codigo_errado(request: Request, usuario: Usuario) -> NaoAutenticado:
    erro = _credenciais_invalidas(request, usuario, "código")
    dois_fatores.registrar_codigo_errado(usuario)  # no 3º levanta 429 (PLT-08)
    return erro


class EntrarSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()
    senha = serializers.CharField(trim_whitespace=False)
    codigo = serializers.CharField(required=False, allow_blank=True, max_length=6)
    codigo_recuperacao = serializers.CharField(required=False, allow_blank=True, max_length=20)


class CodigoSerializer(serializers.Serializer[dict[str, str]]):
    codigo = serializers.RegexField(r"^\d{6}$")


class SenhaSerializer(serializers.Serializer[dict[str, str]]):
    senha = serializers.CharField(trim_whitespace=False)


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


class EntrarView(Publica):
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
        if not usuario.check_password(senha):
            raise _credenciais_invalidas(request, usuario, "senha")
        if usuario.status == StatusUsuario.DESATIVADO or (
            usuario.status == StatusUsuario.CONVITE_PENDENTE and not convite_aceito(usuario)
        ):
            raise SemPermissao(
                "usuario_inativo", "Seu acesso foi desativado. Fale com o administrador."
            )
        dois_fatores.conferir_bloqueio(usuario)
        if not dois_fatores.tem_2fa(usuario):
            return _configurar_2fa(usuario)

        codigo = dados.validated_data.get("codigo", "")
        recuperacao = dados.validated_data.get("codigo_recuperacao", "")
        if not codigo and not recuperacao:
            raise ErroDeValidacao({"codigo": ["Informe o código do autenticador."]})
        if (
            dois_fatores.conferir_codigo(usuario, codigo=codigo, codigo_recuperacao=recuperacao)
            is None
        ):
            raise _codigo_errado(request, usuario)
        return _entrou(request, usuario)


class Configurar2FAView(APIView):
    authentication_classes = [JWTPre2FA]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses=inline_serializer("Configurar2FA", {"otpauth_uri": serializers.CharField()}),
        summary="Novo autenticador (PLT-08)",
    )
    def post(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        if dois_fatores.tem_2fa(usuario):
            raise Conflito("2fa_ja_configurado", "O autenticador já está configurado.")
        dispositivo = dois_fatores.novo_autenticador(usuario)
        return Response({"otpauth_uri": dispositivo.config_url})


class Verificar2FAView(APIView):
    authentication_classes = [JWTPre2FA]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=CodigoSerializer, responses=EntrouSerializer, summary="Confirmar o código (PLT-08)"
    )
    def post(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        dados = CodigoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        dois_fatores.conferir_bloqueio(usuario)
        confirmando = not dois_fatores.tem_2fa(usuario)
        dispositivo = dois_fatores.conferir_codigo(
            usuario, codigo=dados.validated_data["codigo"], confirmando=confirmando
        )
        if dispositivo is None:
            raise _codigo_errado(request, usuario)
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
        refresh = refresh_do_cookie(request)
        usuario = Usuario.objects.filter(pk=refresh.get("user_id")).first()
        if usuario is None or not usuario.is_active:
            raise NaoAutenticado("nao_autenticado", "Entre de novo.")
        refresh.blacklist()
        novo = emitir_tokens(usuario, amr=refresh.get("amr", []))
        resposta = Response({"access": str(novo.access_token)})
        gravar_cookie_refresh(resposta, novo)
        return resposta


class SairView(Publica):
    @extend_schema(request=None, responses={204: None}, summary="Sair")
    def post(self, request: Request) -> Response:
        if not veio_do_frontend(request):
            raise SemPermissao("permissao", "Requisição recusada.")
        # Sair sempre apaga o cookie, mesmo com token vencido ou de outra empresa.
        with contextlib.suppress(Exception):
            refresh_do_cookie(request).blacklist()
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


class ConviteView(Publica):
    @extend_schema(responses=ConviteSerializer, summary="Ver convite da equipe")
    def get(self, request: Request, token: str) -> Response:
        convite = convite_pelo_token(token)
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
        request=SenhaSerializer, responses=EtapaSerializer, summary="Aceitar convite da equipe"
    )
    def post(self, request: Request, token: str) -> Response:
        dados = SenhaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = aceitar_convite(token, dados.validated_data["senha"])
        return _configurar_2fa(usuario)
