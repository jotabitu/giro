"""Acesso à empresa: login, 2 etapas, sessões, `eu` e senha (contrato de contas; USR-02, USR-03,
USR-06; ADRs 0013 e 0014).

Rotas em `<subdominio>.<dominio>/api/auth/`. Estas rotas não passam por `EmpresaOperando`: com a
empresa suspensa as pessoas ainda entram para ler e exportar, e trocar a senha, encerrar uma
sessão ou ativar as 2 etapas é segurança da conta, não operação (exceção registrada em
`tests/test_permissoes_das_rotas.py`).
"""

from typing import Any

from django.http import Http404
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import PolymorphicProxySerializer, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from comum.autenticacao import (
    AMR_SENHA,
    AMR_SENHA_E_CODIGO,
    CLAIM_APARELHO,
    AtorSuporte,
    JWTPre2FA,
    JWTPre2FAOuAcesso,
    apagar_cookie_refresh,
    emitir_pre_2fa,
    emitir_tokens,
    gravar_cookie_refresh,
    recusar_token_de_suporte,
    veio_do_frontend,
)
from comum.erros import (
    Conflito,
    ErroDeRegra,
    ErroDeValidacao,
    NaoAutenticado,
    SemPermissao,
)
from comum.limites import LIMITES_DE_ENTRAR, AcessoPorIP
from comum.permissoes import EscopoDeFilial

from .. import dois_fatores, selectors, services, sessoes
from ..models import MotivoRevogacao, StatusUsuario, TipoSessao, Usuario

CREDENCIAIS_INVALIDAS = ("credenciais_invalidas", "E-mail ou senha incorretos")
CODIGO_INVALIDO = (
    "codigo_invalido",
    "Código incorreto. Confira o horário do celular e tente de novo.",
)
SENHA_INCORRETA = "Senha incorreta."


def _usuario(request: Request) -> Usuario:
    usuario: Usuario = request.user  # type: ignore[assignment]
    return usuario


def _eu(request: Request, usuario: Usuario) -> dict[str, Any]:
    return selectors.dados_do_eu(usuario, getattr(request, "tenant", None))


def _recusar_frontend_ausente(request: Request) -> None:
    if not veio_do_frontend(request):
        raise SemPermissao("permissao", "Requisição recusada.")


def _falhou_entrada(request: Request, usuario: Usuario | None, motivo: str) -> None:
    dois_fatores.auditar_entrada(request, "usuario.entrar_falhou", usuario, motivo)


def _erro_da_tentativa(
    request: Request, tentativa: dois_fatores.Tentativa, erro: tuple[str, str]
) -> Exception:
    """401, ou 429 quando esta tentativa atingiu o limite (USR-06). Os dois ficam auditados."""
    motivo = "código" if tentativa.falha == dois_fatores.Falha.CODIGO else "senha"
    _falhou_entrada(request, tentativa.usuario, motivo)
    return tentativa.bloqueio or NaoAutenticado(*erro)


def _pronto(
    request: Request,
    usuario: Usuario,
    *,
    tipo: str,
    amr: tuple[str, ...],
    extras: dict[str, Any] | None = None,
) -> Response:
    """Login completo: abre a sessão, devolve o access e grava o refresh no cookie."""
    dois_fatores.auditar_entrada(request, "usuario.entrar", usuario)
    refresh = emitir_tokens(usuario, amr, tipo=tipo)
    resposta = Response(
        {
            "etapa": "pronto",
            "access": str(refresh.access_token),
            "usuario": _eu(request, usuario),
            **(extras or {}),
        }
    )
    gravar_cookie_refresh(resposta, refresh)
    return resposta


def _etapa(etapa: str, usuario: Usuario, aparelho: str) -> Response:
    return Response({"etapa": etapa, "token_pre_2fa": str(emitir_pre_2fa(usuario, aparelho))})


def _conferir_senha_de_quem_esta_logado(usuario: Usuario, senha: str, campo: str) -> None:
    """Senha errada: 400 no campo, ou 429 se bateu o limite (USR-06)."""
    tentativa = dois_fatores.conferir_senha(usuario, senha)
    if tentativa.bloqueio is not None:
        raise tentativa.bloqueio
    if tentativa.falha is not None:
        raise ErroDeValidacao({campo: [SENHA_INCORRETA]})


class EsquemaPre2FAOuAcesso(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """`2fa/configurar`: Bearer JWT com o `token_pre_2fa` ou com o access."""

    target_class = "comum.autenticacao.JWTPre2FAOuAcesso"
    name = "jwtPre2faOuAccess"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}


# --- Serializers ---


class EntrarEmpresaSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()
    senha = serializers.CharField(trim_whitespace=False)
    aparelho = serializers.ChoiceField(choices=TipoSessao.choices, default=TipoSessao.DESKTOP)


class Verificar2FASerializer(serializers.Serializer[dict[str, str]]):
    codigo = serializers.RegexField(r"^\d{6}$", required=False)
    codigo_recuperacao = serializers.CharField(required=False, max_length=20)

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if bool(attrs.get("codigo")) == bool(attrs.get("codigo_recuperacao")):
            raise serializers.ValidationError("Informe o código ou um código de recuperação.")
        return attrs


class CodigoDoAutenticadorSerializer(serializers.Serializer[dict[str, str]]):
    codigo = serializers.RegexField(r"^\d{6}$")


class ConfirmarSenhaSerializer(serializers.Serializer[dict[str, str]]):
    senha = serializers.CharField(trim_whitespace=False)


class TrocarSenhaSerializer(serializers.Serializer[dict[str, str]]):
    senha_atual = serializers.CharField(trim_whitespace=False)
    senha_nova = serializers.CharField(trim_whitespace=False)


class EmailSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()


class RedefinirSenhaSerializer(serializers.Serializer[dict[str, str]]):
    token = serializers.CharField(max_length=100)
    senha_nova = serializers.CharField(trim_whitespace=False)


class EditarEuSerializer(serializers.Serializer[dict[str, str]]):
    nome = serializers.CharField(required=False, max_length=150)
    celular = serializers.CharField(required=False, allow_blank=True, max_length=20)


class FilialResumoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class DoisFatoresSerializer(serializers.Serializer[Any]):
    ativo = serializers.BooleanField()
    obrigatorio = serializers.BooleanField()
    codigos_recuperacao_restantes = serializers.IntegerField()


# Escala de quem cancela ou dá desconto acima do limite (contrato de contas, "pode").
NIVEL_DE_APROVACAO = ["sim", "aprova", "pede", "nao"]


class PodeDaEmpresaSerializer(serializers.Serializer[Any]):
    painel = serializers.ChoiceField(choices=["todas_filiais", "filial", "proprios", "nao"])
    veiculos = serializers.ChoiceField(choices=["editar", "km_e_avarias", "nao"])
    clientes_cadastrar = serializers.BooleanField()
    locacoes_criar = serializers.BooleanField()
    vistorias_fazer = serializers.BooleanField()
    locacoes_cancelar = serializers.ChoiceField(choices=NIVEL_DE_APROVACAO)
    desconto_acima_limite = serializers.ChoiceField(choices=NIVEL_DE_APROVACAO)
    vendas_criar = serializers.BooleanField()
    caixa_receber = serializers.BooleanField()
    caixa_abrir_fechar = serializers.BooleanField()
    despesas_lancar = serializers.ChoiceField(choices=["todas", "manutencao", "nao"])
    despesas_aprovar = serializers.BooleanField()
    financeiro_pagar = serializers.BooleanField()
    os_abrir = serializers.BooleanField()
    administracao = serializers.BooleanField()


class EmpresaDoEuSerializer(serializers.Serializer[Any]):
    nome_exibicao = serializers.CharField()
    status = serializers.CharField()
    somente_leitura = serializers.BooleanField()


class SuporteDoEuSerializer(serializers.Serializer[Any]):
    acesso_suporte_id = serializers.IntegerField()
    nome = serializers.CharField()
    permissao = serializers.ChoiceField(choices=["ver", "ver_editar"])
    fim = serializers.DateTimeField()
    motivo = serializers.CharField()


class EuDaEmpresaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField(allow_null=True)  # `null` no modo suporte
    nome = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    celular = serializers.CharField(allow_null=True)
    perfil = serializers.CharField()
    permissoes_extras = serializers.ListField(child=serializers.CharField())
    filiais = FilialResumoSerializer(many=True)
    dois_fatores = DoisFatoresSerializer()
    pode = PodeDaEmpresaSerializer()
    suporte = SuporteDoEuSerializer(allow_null=True)
    empresa = EmpresaDoEuSerializer()


class ProntoSerializer(serializers.Serializer[Any]):
    etapa = serializers.ChoiceField(choices=["pronto"])
    access = serializers.CharField()
    usuario = EuDaEmpresaSerializer()
    codigos_recuperacao = serializers.ListField(child=serializers.CharField(), required=False)


class EtapaDoLoginSerializer(serializers.Serializer[Any]):
    etapa = serializers.ChoiceField(choices=["verificar_2fa", "configurar_2fa"])
    token_pre_2fa = serializers.CharField()


class ConfigurarSerializer(serializers.Serializer[Any]):
    otpauth_uri = serializers.CharField()
    chave = serializers.CharField()


class CodigosSerializer(serializers.Serializer[Any]):
    codigos_recuperacao = serializers.ListField(child=serializers.CharField())


class AtivadoSerializer(CodigosSerializer):
    access = serializers.CharField()


class AccessDaEmpresaSerializer(serializers.Serializer[Any]):
    access = serializers.CharField()


class SessaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoSessao.choices)
    aparelho = serializers.CharField()
    ip = serializers.CharField(allow_null=True)
    criada_em = serializers.DateTimeField()
    ultimo_uso = serializers.DateTimeField()
    atual = serializers.BooleanField()


class SessoesSerializer(serializers.Serializer[Any]):
    resultados = SessaoSerializer(many=True)


class MensagemSerializer(serializers.Serializer[Any]):
    mensagem = serializers.CharField()


ENTRAR_RESPOSTA = PolymorphicProxySerializer(
    component_name="EntrarEmpresaResposta",
    serializers=[ProntoSerializer, EtapaDoLoginSerializer],
    resource_type_field_name=None,
)


# --- Bases ---


class Publica(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes: list[Any] = [AcessoPorIP]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        # Entrar, renovar, sair, senha e convite não aceitam o token de suporte (PLT-07).
        recusar_token_de_suporte(request)
        super().initial(request, *args, **kwargs)


class Logada(APIView):
    """Rotas da própria conta (sessões, senha, 2 etapas): o suporte não usa (PLT-07)."""

    permission_classes = [IsAuthenticated, EscopoDeFilial]
    throttle_classes: list[Any] = [AcessoPorIP]
    suporte_proibido: bool | frozenset[str] = True


class EtapaDe2FA(APIView):
    authentication_classes = [JWTPre2FA]
    permission_classes = [IsAuthenticated]
    throttle_classes: list[Any] = [AcessoPorIP]


# --- Login ---


class EntrarView(Publica):
    throttle_classes = LIMITES_DE_ENTRAR

    @extend_schema(
        request=EntrarEmpresaSerializer,
        responses=ENTRAR_RESPOSTA,
        summary="Entrar (USR-02, USR-06)",
    )
    def post(self, request: Request) -> Response:
        dados = EntrarEmpresaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        email = dados.validated_data["email"].strip().lower()
        senha = dados.validated_data["senha"]
        aparelho = dados.validated_data["aparelho"]
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            Usuario().set_password(senha)  # mesmo tempo de resposta de quem existe
            _falhou_entrada(request, None, "e-mail")
            raise NaoAutenticado(*CREDENCIAIS_INVALIDAS)
        if usuario.status == StatusUsuario.CONVITE_PENDENTE and not services.convite_aceito(
            usuario
        ):
            _falhou_entrada(request, usuario, "convite pendente")
            raise SemPermissao("convite_pendente", "Use o link do convite para criar seu acesso")
        tentativa = dois_fatores.tentar_senha(usuario, senha)
        if tentativa.falha is not None:
            raise _erro_da_tentativa(request, tentativa, CREDENCIAIS_INVALIDAS)
        usuario = tentativa.usuario
        if usuario.status == StatusUsuario.DESATIVADO:
            _falhou_entrada(request, usuario, "desativado")
            raise SemPermissao(
                "usuario_inativo", "Seu acesso foi desativado. Fale com o administrador."
            )
        if dois_fatores.tem_2fa(usuario):
            return _etapa("verificar_2fa", usuario, aparelho)
        if usuario.status == StatusUsuario.CONVITE_PENDENTE or usuario.exige_2fa:
            if not services.pode_configurar_2fa(usuario):
                _falhou_entrada(request, usuario, "convite vencido")
                raise SemPermissao("convite_expirado", services.CONVITE_VENCIDO)
            return _etapa("configurar_2fa", usuario, aparelho)
        return _pronto(request, usuario, tipo=aparelho, amr=AMR_SENHA)


class Verificar2FAView(EtapaDe2FA):
    @extend_schema(
        request=Verificar2FASerializer,
        responses=ProntoSerializer,
        summary="Confirmar o código (USR-02)",
    )
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        dados = Verificar2FASerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        confirmando = not dois_fatores.tem_2fa(usuario)
        if confirmando and not services.pode_configurar_2fa(usuario):
            raise SemPermissao("convite_expirado", services.CONVITE_VENCIDO)
        tentativa = dois_fatores.verificar_codigo(
            usuario,
            codigo=dados.validated_data.get("codigo", ""),
            codigo_recuperacao=dados.validated_data.get("codigo_recuperacao", ""),
            confirmando=confirmando,
        )
        usuario, dispositivo = tentativa.usuario, tentativa.dispositivo
        if dispositivo is None:
            raise _erro_da_tentativa(request, tentativa, CODIGO_INVALIDO)
        extras: dict[str, Any] = {}
        if confirmando:
            extras["codigos_recuperacao"] = dois_fatores.confirmar_autenticador(dispositivo)
            dois_fatores.auditar_2fa("usuario.ativar_2fa", usuario)
            services.ativar_depois_do_2fa(usuario)
        if dados.validated_data.get("codigo_recuperacao"):
            dois_fatores.auditar_2fa("usuario.usar_codigo_recuperacao", usuario)
        tipo = str(request.auth.get(CLAIM_APARELHO, TipoSessao.DESKTOP))  # type: ignore[union-attr]
        return _pronto(request, usuario, tipo=tipo, amr=AMR_SENHA_E_CODIGO, extras=extras)


class Configurar2FAView(APIView):
    """Com o `token_pre_2fa` (1º acesso ou 2 etapas que passaram a ser exigidas) ou com o access
    de quem quer ativar por conta própria."""

    authentication_classes = [JWTPre2FAOuAcesso]
    permission_classes = [IsAuthenticated]
    throttle_classes = [AcessoPorIP]
    suporte_proibido = True

    @extend_schema(
        request=None,
        responses=ConfigurarSerializer,
        summary="Novo autenticador",
    )
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        if dois_fatores.tem_2fa(usuario):
            raise Conflito("2fa_ja_configurado", "O autenticador já está configurado.")
        if not services.pode_configurar_2fa(usuario):
            raise SemPermissao("convite_expirado", services.CONVITE_VENCIDO)
        dispositivo = dois_fatores.novo_autenticador(usuario)
        marca = str(getattr(request.tenant, "nome_exibicao", ""))  # type: ignore[attr-defined]
        return Response(
            {
                "otpauth_uri": dispositivo.config_url_para(marca),
                "chave": dispositivo.chave_legivel(),
            }
        )


class Ativar2FAView(Logada):
    @extend_schema(
        request=CodigoDoAutenticadorSerializer,
        responses=AtivadoSerializer,
        summary="Ativar as 2 etapas por conta própria (USR-02)",
    )
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        dados = CodigoDoAutenticadorSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        if dois_fatores.tem_2fa(usuario):
            raise Conflito("2fa_ja_configurado", "O autenticador já está configurado.")
        tentativa = dois_fatores.verificar_codigo(
            usuario, codigo=dados.validated_data["codigo"], confirmando=True
        )
        if tentativa.dispositivo is None:
            raise tentativa.bloqueio or NaoAutenticado(*CODIGO_INVALIDO)
        codigos = dois_fatores.confirmar_autenticador(tentativa.dispositivo)
        dois_fatores.auditar_2fa("usuario.ativar_2fa", tentativa.usuario)
        # A sessão continua, agora com `otp`: sem isto o próximo uso daria `2fa_obrigatorio`.
        sid = sessoes.sid_da_requisicao(request)
        refresh = emitir_tokens(tentativa.usuario, AMR_SENHA_E_CODIGO, sid=sid)
        resposta = Response({"codigos_recuperacao": codigos, "access": str(refresh.access_token)})
        gravar_cookie_refresh(resposta, refresh)
        return resposta


class Desativar2FAView(Logada):
    @extend_schema(
        request=ConfirmarSenhaSerializer,
        responses={204: None},
        summary="Desligar as 2 etapas (USR-02)",
    )
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        dados = ConfirmarSenhaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        if usuario.exige_2fa_pela_regra:
            raise ErroDeRegra("USR-02", "Seu perfil exige a verificação em 2 etapas")
        _conferir_senha_de_quem_esta_logado(usuario, dados.validated_data["senha"], "senha")
        dois_fatores.remover_2fa(usuario)
        dois_fatores.auditar_2fa("usuario.desativar_2fa", usuario)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodigosRecuperacaoView(Logada):
    @extend_schema(
        request=ConfirmarSenhaSerializer,
        responses=CodigosSerializer,
        summary="Novos códigos de recuperação",
    )
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        dados = ConfirmarSenhaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        if not dois_fatores.tem_2fa(usuario):
            raise Conflito("2fa_inativo", "Ative a verificação em 2 etapas primeiro.")
        _conferir_senha_de_quem_esta_logado(usuario, dados.validated_data["senha"], "senha")
        codigos = dois_fatores.gerar_codigos_recuperacao(usuario)
        dois_fatores.auditar_2fa("usuario.novos_codigos_recuperacao", usuario)
        return Response({"codigos_recuperacao": codigos})


# --- Renovar e sair (cookie + X-Requested-With) ---


class RenovarView(Publica):
    @extend_schema(
        request=None, responses=AccessDaEmpresaSerializer, summary="Renovar o acesso (USR-06)"
    )
    def post(self, request: Request) -> Response:
        _recusar_frontend_ausente(request)
        _, novo = sessoes.renovar(request)
        resposta = Response({"access": str(novo.access_token)})
        gravar_cookie_refresh(resposta, novo)
        return resposta


class SairView(Publica):
    @extend_schema(request=None, responses={204: None}, summary="Sair")
    def post(self, request: Request) -> Response:
        _recusar_frontend_ausente(request)
        sessoes.sair(request)
        resposta = Response(status=status.HTTP_204_NO_CONTENT)
        apagar_cookie_refresh(resposta)
        return resposta


# --- Eu ---


class EuView(Logada):
    # O suporte lê o `eu` (faixa "Modo suporte") e não edita dados de ninguém (PLT-07).
    suporte_proibido = frozenset({"PATCH"})
    suporte_somente_leitura = True

    @extend_schema(responses=EuDaEmpresaSerializer, summary="Quem está logado (USR-03, USR-05)")
    def get(self, request: Request) -> Response:
        if isinstance(request.user, AtorSuporte):
            return Response(selectors.dados_do_eu_suporte(request.user, request.tenant))  # type: ignore[attr-defined]
        return Response(_eu(request, _usuario(request)))

    @extend_schema(
        request=EditarEuSerializer, responses=EuDaEmpresaSerializer, summary="Meus dados"
    )
    def patch(self, request: Request) -> Response:
        dados = EditarEuSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        usuario = services.editar_meus_dados(
            _usuario(request),
            nome=dados.validated_data.get("nome"),
            celular=dados.validated_data.get("celular"),
        )
        return Response(_eu(request, usuario))


# --- Sessões (ADR 0014) ---


def _sessao_para_lista(sessao: Any, atual: int | None) -> dict[str, Any]:
    return {
        "id": sessao.pk,
        "tipo": sessao.tipo,
        "aparelho": sessao.aparelho,
        "ip": sessoes.mascarar_ip(sessao.ip),
        "criada_em": sessao.criado_em,
        "ultimo_uso": sessao.ultimo_uso,
        "atual": sessao.pk == atual,
    }


class SessoesView(Logada):
    @extend_schema(responses=SessoesSerializer, summary="Minhas sessões ativas")
    def get(self, request: Request) -> Response:
        atual = sessoes.sid_da_requisicao(request)
        return Response(
            {
                "resultados": [
                    _sessao_para_lista(s, atual) for s in sessoes.ativas(_usuario(request))
                ]
            }
        )


class EncerrarSessaoView(Logada):
    @extend_schema(request=None, responses={204: None}, summary="Encerrar uma sessão minha")
    def post(self, request: Request, id: int) -> Response:
        sessao = sessoes.ativas(_usuario(request)).filter(pk=id).first()
        if sessao is None:
            raise Http404
        sessoes.revogar(sessao, MotivoRevogacao.REVOGADA_PELO_USUARIO, por=_usuario(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class EncerrarOutrasSessoesView(Logada):
    @extend_schema(request=None, responses={204: None}, summary="Encerrar as outras sessões")
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        sessoes.revogar_todas(
            usuario,
            MotivoRevogacao.REVOGADA_PELO_USUARIO,
            por=usuario,
            exceto=sessoes.sid_da_requisicao(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Senha ---


class TrocarSenhaView(Logada):
    @extend_schema(request=TrocarSenhaSerializer, responses={204: None}, summary="Trocar a senha")
    def post(self, request: Request) -> Response:
        usuario = _usuario(request)
        dados = TrocarSenhaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        _conferir_senha_de_quem_esta_logado(
            usuario, dados.validated_data["senha_atual"], "senha_atual"
        )
        services.trocar_senha(
            usuario,
            dados.validated_data["senha_nova"],
            sessao_atual=sessoes.sid_da_requisicao(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class EsqueciSenhaView(Publica):
    throttle_classes = [AcessoPorIP]

    @extend_schema(
        request=EmailSerializer,
        responses={202: MensagemSerializer},
        summary="Esqueci a senha (não revela quem tem conta)",
    )
    def post(self, request: Request) -> Response:
        dados = EmailSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        services.pedir_redefinicao(dados.validated_data["email"])
        return Response(
            {
                "mensagem": (
                    "Se houver uma conta com este e-mail, enviamos um link para criar uma "
                    "senha nova. Ele vale por 1 hora."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class RedefinirSenhaView(Publica):
    @extend_schema(
        request=RedefinirSenhaSerializer, responses={204: None}, summary="Criar a senha nova"
    )
    def post(self, request: Request) -> Response:
        dados = RedefinirSenhaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        services.redefinir_senha(dados.validated_data["token"], dados.validated_data["senha_nova"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Modo suporte (PLT-07) ---


class SuporteSairView(APIView):
    """O suporte encerra o próprio acesso (`encerrado`), com evento nas duas auditorias."""

    permission_classes = [IsAuthenticated]
    throttle_classes: list[Any] = [AcessoPorIP]
    so_suporte = True

    @extend_schema(request=None, responses={204: None}, summary="Sair do modo suporte (PLT-07)")
    def post(self, request: Request) -> Response:
        from apps.plataforma.services import sair_do_suporte

        if not isinstance(request.user, AtorSuporte):
            raise SemPermissao("PLT-07", "Só o suporte usa esta ação")
        sair_do_suporte(request.user.acesso_suporte_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# Sem `EmpresaOperando` de propósito (ver o docstring do módulo).
VIEWS_DE_ACESSO: tuple[type[APIView], ...] = (
    SuporteSairView,
    EntrarView,
    Verificar2FAView,
    Configurar2FAView,
    Ativar2FAView,
    Desativar2FAView,
    CodigosRecuperacaoView,
    RenovarView,
    SairView,
    EuView,
    SessoesView,
    EncerrarSessaoView,
    EncerrarOutrasSessoesView,
    TrocarSenhaView,
    EsqueciSenhaView,
    RedefinirSenhaView,
)
