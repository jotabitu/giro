"""Marca da locadora, pública (`docs/api/empresas.md`; ADR 0002 e 0004; S-12).

Sem login: o login, o convite, o primeiro acesso e o "esqueci a senha" leem a marca antes de
haver sessão, e a casca do app lê a mesma rota depois. A empresa é a do subdomínio. O logo sai
pela própria API (o storage continua privado), com os cabeçalhos que impedem um SVG de rodar
script mesmo aberto direto na barra de endereço (2ª barreira da S-12; a 1ª é a sanitização no
upload, `empresas/logo.py`, ADR 0022).

A escrita (`PATCH /api/marca/` e `POST /api/marca/simular/`, T-153) é só do administrador, com
login: o suporte não escreve nem com "ver e editar" (`suporte_proibido`), e a empresa sem
operação recebe o 403 de `EmpresaOperando`.
"""

from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.erros import ErroDeValidacao, NaoEncontrado
from comum.limites import MarcaPorIP, MarcaSalvarPorUsuario, MarcaSimularPorUsuario
from comum.permissoes import EmpresaOperando, EscopoDeFilial, com_padrao, exige_perfil

from .. import selectors, services
from ..logo import MENSAGEM_FORMATO, TAMANHO_MAXIMO
from .serializers import (
    MarcaSerializer,
    MarcaSimuladaSerializer,
    MudarRamoSerializer,
    RamoSerializer,
    SalvarMarcaSerializer,
    SimularMarcaSerializer,
)

CACHE_DA_MARCA = "public, max-age=300"
CACHE_DO_LOGO_ATUAL = "public, max-age=31536000, immutable"
CACHE_DO_LOGO_ANTIGO = "public, max-age=300"
CSP_DO_LOGO = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


class Publica(APIView):
    """Sem autenticação: com ou sem token (inclusive o do suporte), a resposta é a mesma."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny, EmpresaOperando, EscopoDeFilial]
    throttle_classes = [MarcaPorIP]


def _etag(versao: str) -> str:
    return f'"{versao}"'


def _pede_a_mesma(request: Request, versao: str) -> bool:
    pedidas = str(request.META.get("HTTP_IF_NONE_MATCH", ""))
    return any(
        parte.strip().removeprefix("W/") in (_etag(versao), "*") for parte in pedidas.split(",")
    )


SO_ADMINISTRADOR = com_padrao(exige_perfil("administrador"))


class MarcaView(Publica):
    """GET público; PATCH do administrador, com login e o limite por usuário."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    suporte_proibido = frozenset({"PATCH"})  # nem com "ver e editar" (PLT-07)

    def _escrita(self) -> bool:
        return getattr(self.request, "method", "GET") == "PATCH"

    def get_authenticators(self) -> list[Any]:
        if self._escrita():
            return [classe() for classe in APIView.authentication_classes]
        return super().get_authenticators()

    def get_permissions(self) -> list[Any]:
        if self._escrita():
            return [permissao() for permissao in SO_ADMINISTRADOR]
        return list(super().get_permissions())

    def get_throttles(self) -> list[Any]:
        if self._escrita():
            return [MarcaSalvarPorUsuario()]
        return super().get_throttles()

    @extend_schema(
        responses={200: MarcaSerializer, 304: OpenApiResponse(description="Sem mudança")},
        summary="Marca da empresa do subdomínio (nome, logo e cores)",
    )
    def get(self, request: Request) -> Response:
        dados = selectors.marca()
        cabecalhos = {"ETag": _etag(dados["versao"]), "Cache-Control": CACHE_DA_MARCA}
        if _pede_a_mesma(request, dados["versao"]):
            return Response(status=304, headers=cabecalhos)
        return Response(MarcaSerializer(dados).data, headers=cabecalhos)

    @extend_schema(
        request={
            "multipart/form-data": SalvarMarcaSerializer,
            "application/json": SimularMarcaSerializer,
        },
        responses={200: MarcaSerializer},
        summary="Salvar a marca: nome, cor e logo (só o administrador; S-12, ADR 0022)",
    )
    def patch(self, request: Request) -> Response:
        dados = SalvarMarcaSerializer(data=_campos_de_texto(request))
        dados.is_valid(raise_exception=True)
        services.salvar_marca(
            nome_exibicao=dados.validated_data.get("nome_exibicao"),
            cor=dados.validated_data.get("cor"),
            logo=_conteudo_do_logo(request),
            remover_logo=dados.validated_data["remover_logo"],
            por=request.user,
        )
        marca = selectors.marca()
        return Response(MarcaSerializer(marca).data, headers={"ETag": _etag(marca["versao"])})


def _campos_de_texto(request: Request) -> dict[str, Any]:
    """Nome, cor e `remover_logo`; o logo é lido à parte, só como arquivo enviado."""
    return {
        chave: request.data.get(chave)
        for chave in ("nome_exibicao", "cor", "remover_logo")
        if chave in request.data
    }


def _conteudo_do_logo(request: Request) -> bytes | None:
    """O arquivo em `logo`, lido até 2 MB + 1 byte (o serviço recusa acima de 2 MB). Nenhuma
    rota de escrita aceita URL de logo: texto em `logo` é formato desconhecido."""
    if "logo" not in request.data:
        return None
    arquivo = request.data.get("logo")
    if not isinstance(arquivo, UploadedFile):
        raise ErroDeValidacao({"logo": [MENSAGEM_FORMATO]})
    arquivo.seek(0)
    return bytes(arquivo.read(TAMANHO_MAXIMO + 1))


class SimularMarcaView(APIView):
    """Prévia das cores (ADR 0005): a tela nunca calcula cor."""

    permission_classes = SO_ADMINISTRADOR
    throttle_classes = [MarcaSimularPorUsuario]
    suporte_proibido = True

    @extend_schema(
        request=SimularMarcaSerializer,
        responses={200: MarcaSimuladaSerializer},
        summary="Prévia da marca sem gravar (nome, iniciais e cores)",
    )
    def post(self, request: Request) -> Response:
        dados = SimularMarcaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        simulada = services.simular_marca(
            nome_exibicao=dados.validated_data.get("nome_exibicao"),
            cor=dados.validated_data.get("cor"),
        )
        return Response(MarcaSimuladaSerializer(simulada).data)


class LogoView(Publica):
    @extend_schema(
        parameters=[OpenApiParameter("v", str, description="Versão da marca (`versao`).")],
        responses={
            (200, "image/svg+xml"): OpenApiTypes.BINARY,
            (200, "image/png"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="Sem logo (`nao_encontrado`)"),
        },
        summary="Arquivo do logo da empresa (S-12)",
    )
    def get(self, request: Request) -> HttpResponse:
        arquivo = selectors.logo()
        if arquivo is None:
            raise NaoEncontrado("nao_encontrado", "Esta empresa não tem logo.")
        conteudo, tipo, extensao = arquivo
        atual = request.query_params.get("v") == selectors.marca()["versao"]
        resposta = HttpResponse(conteudo, content_type=tipo)
        resposta["Cache-Control"] = CACHE_DO_LOGO_ATUAL if atual else CACHE_DO_LOGO_ANTIGO
        resposta["X-Content-Type-Options"] = "nosniff"
        resposta["Content-Security-Policy"] = CSP_DO_LOGO
        resposta["Content-Disposition"] = f'inline; filename="logo.{extensao}"'
        return resposta


class RamoView(APIView):
    """O que a empresa faz (PLT-12): passo 7 da implantação e `/admin/ramo` (T-224, T-262).
    Sem cache: o plano pode ter mudado no pedido anterior."""

    permission_classes = com_padrao(exige_perfil("administrador"))
    suporte_somente_leitura = True  # o suporte lê o GET (PLT-07)
    suporte_proibido = frozenset({"PUT"})  # e nunca troca o ramo

    @extend_schema(responses=RamoSerializer, summary="Ramo da empresa e as opções do plano")
    def get(self, request: Request) -> Response:
        return Response(RamoSerializer(selectors.ramo()).data)

    @extend_schema(
        request=MudarRamoSerializer,
        responses={
            200: RamoSerializer,
            422: OpenApiResponse(description="`PLT-12`: o plano não aceita, ou algo aberto"),
        },
        summary="Trocar o ramo (PLT-12)",
    )
    def put(self, request: Request) -> Response:
        dados = MudarRamoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        services.mudar_ramo(
            dados.validated_data["atividade"], dados.validated_data["trabalha_com"], request.user
        )
        return Response(RamoSerializer(selectors.ramo()).data)
