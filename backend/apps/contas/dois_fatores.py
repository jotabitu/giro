"""Verificação em 2 etapas e bloqueio por tentativas erradas (PLT-08, USR-06; ADR 0013, item 3).

Autenticador: `contas.Autenticador` (TOTP com a semente cifrada). Códigos de recuperação:
`contas.CodigoRecuperacao`, 8 de uso único, guardados só em hash (P-08 da T-057).

Bloqueio de 15 minutos, com evento de segurança na auditoria do schema:
- plataforma (`PLT-08`): 5 senhas ou 3 códigos errados seguidos;
- empresa (`USR-06`): 5 tentativas erradas somando senhas e códigos, e os administradores
  recebem um aviso.
A API e o Django Admin entram pelas mesmas funções.

Eventos de 2 etapas levam só o usuário como objeto: o autenticador e os códigos nunca vão para a
auditoria (R-06 da T-050).
"""

import secrets
from dataclasses import dataclass, replace
from datetime import timedelta
from enum import StrEnum

from django.db import transaction
from django.http import HttpRequest
from django_tenants.utils import get_public_schema_name

from comum import relogio
from comum.auditoria import Categoria, TipoAtor, registrar_evento, usar_ator
from comum.conexao import schema_atual
from comum.erros import MuitasTentativas
from comum.middleware import ator_da_requisicao

from .models import Autenticador, CodigoRecuperacao, Usuario, hash_do_codigo

CODIGOS_ERRADOS_PARA_BLOQUEAR = 3  # PLT-08
SENHAS_ERRADAS_PARA_BLOQUEAR = 5  # PLT-08 (decisão de 08/10, P-03 da T-057)
TENTATIVAS_ERRADAS_PARA_BLOQUEAR = 5  # USR-06: senhas e códigos somados
TEMPO_DE_BLOQUEIO = timedelta(minutes=15)
QUANTOS_CODIGOS_DE_RECUPERACAO = 8
NOME_AUTENTICADOR = "autenticador"


def na_plataforma() -> bool:
    return bool(schema_atual() == get_public_schema_name())


def regra_de_acesso() -> str:
    return "PLT-08" if na_plataforma() else "USR-06"


def auditar_entrada(
    request: HttpRequest, acao: str, usuario: Usuario | None, motivo: str = ""
) -> None:
    """`usuario.entrar` e `usuario.entrar_falhou`, com IP e aparelho (API e Django Admin)."""
    ator = ator_da_requisicao(request)
    if usuario is not None and acao == "usuario.entrar":
        ator = replace(ator, tipo=TipoAtor.USUARIO, id=usuario.pk, nome=usuario.nome)
    with usar_ator(ator):
        registrar_evento(
            acao, Categoria.SEGURANCA, objeto=usuario, motivo=motivo, regra=regra_de_acesso()
        )


def auditar_2fa(acao: str, usuario: Usuario, motivo: str = "") -> None:
    """Evento de 2 etapas com o usuário como objeto, sem o autenticador (R-06)."""
    registrar_evento(acao, Categoria.SEGURANCA, objeto=usuario, motivo=motivo, regra="USR-02")


# --- Autenticador e códigos de recuperação ---


def autenticador_confirmado(usuario: Usuario) -> Autenticador | None:
    return Autenticador.objects.filter(user=usuario, confirmed=True).first()


def tem_2fa(usuario: Usuario) -> bool:
    return bool(Autenticador.objects.filter(user=usuario, confirmed=True).exists())


def novo_autenticador(usuario: Usuario) -> Autenticador:
    """Troca a semente do autenticador ainda não confirmado."""
    Autenticador.objects.filter(user=usuario, confirmed=False).delete()
    dispositivo = Autenticador(user=usuario, name=NOME_AUTENTICADOR, confirmed=False)
    dispositivo.gerar_chave()
    dispositivo.save()
    return dispositivo


def _codigo_de_recuperacao() -> str:
    bruto = secrets.token_hex(4)
    return f"{bruto[:4]}-{bruto[4:]}"


def gerar_codigos_recuperacao(usuario: Usuario) -> list[str]:
    """8 códigos novos, mostrados uma vez só; os anteriores deixam de valer."""
    codigos = [_codigo_de_recuperacao() for _ in range(QUANTOS_CODIGOS_DE_RECUPERACAO)]
    with transaction.atomic():
        CodigoRecuperacao.objects.filter(usuario=usuario).delete()
        CodigoRecuperacao.objects.bulk_create(
            [CodigoRecuperacao(usuario=usuario, codigo_hash=hash_do_codigo(c)) for c in codigos]
        )
    return codigos


def confirmar_autenticador(dispositivo: Autenticador) -> list[str]:
    """Confirma o autenticador e gera os 8 códigos de recuperação."""
    with transaction.atomic():
        Autenticador.objects.filter(user=dispositivo.user, confirmed=True).delete()
        dispositivo.confirmed = True
        dispositivo.save(update_fields=["confirmed"])
        return gerar_codigos_recuperacao(dispositivo.user)


def remover_2fa(usuario: Usuario) -> None:
    """Apaga autenticador e códigos (desligar ou redefinir as 2 etapas)."""
    with transaction.atomic():
        Autenticador.objects.filter(user=usuario).delete()
        CodigoRecuperacao.objects.filter(usuario=usuario).delete()


def codigos_restantes(usuario: Usuario) -> int:
    return int(CodigoRecuperacao.objects.filter(usuario=usuario, usado_em__isnull=True).count())


def _usar_codigo_de_recuperacao(usuario: Usuario, codigo: str) -> bool:
    """Marca o código como usado; o mesmo código não serve uma segunda vez."""
    usados = CodigoRecuperacao.objects.filter(
        usuario=usuario, codigo_hash=hash_do_codigo(codigo.strip()), usado_em__isnull=True
    ).update(usado_em=relogio.agora())
    return bool(usados)


def conferir_codigo(
    usuario: Usuario, *, codigo: str = "", codigo_recuperacao: str = "", confirmando: bool = False
) -> Autenticador | None:
    """O autenticador que aceitou o código, ou `None`. `confirmando` usa o ainda não confirmado."""
    if codigo_recuperacao and not confirmando:
        dispositivo = autenticador_confirmado(usuario)
        if dispositivo is not None and _usar_codigo_de_recuperacao(usuario, codigo_recuperacao):
            return dispositivo
        return None
    dispositivo = Autenticador.objects.filter(user=usuario, confirmed=not confirmando).first()
    if dispositivo is not None and codigo and dispositivo.verify_token(codigo):
        return dispositivo
    return None


# --- Bloqueio (PLT-08, USR-06) ---
#
# Bloqueio, verificação e contagem rodam numa transação só, que começa travando a linha do
# usuário (P-02 da T-057): tentativas simultâneas da mesma conta passam uma de cada vez, e
# nenhuma verifica senha ou código depois de o limite ser atingido.


class Falha(StrEnum):
    SENHA = "senha"
    CODIGO = "codigo"


@dataclass
class Tentativa:
    """Resultado de uma tentativa. Sem `falha`, a pessoa passou (com `dispositivo`, se tem 2FA)."""

    usuario: Usuario
    dispositivo: Autenticador | None = None
    falha: Falha | None = None
    bloqueio: MuitasTentativas | None = None


def _atingiu_o_limite(usuario: Usuario) -> bool:
    if na_plataforma():
        return (
            usuario.senhas_erradas >= SENHAS_ERRADAS_PARA_BLOQUEAR
            or usuario.tentativas_erradas >= CODIGOS_ERRADOS_PARA_BLOQUEAR
        )
    return usuario.senhas_erradas + usuario.tentativas_erradas >= TENTATIVAS_ERRADAS_PARA_BLOQUEAR


def _motivo_do_bloqueio(usuario: Usuario) -> str:
    if not na_plataforma():
        return "5 tentativas erradas"
    if usuario.senhas_erradas >= SENHAS_ERRADAS_PARA_BLOQUEAR:
        return "5 senhas erradas"
    return "3 códigos errados"


def _erro_de_bloqueio(usuario: Usuario) -> MuitasTentativas:
    if usuario.bloqueado_ate is None:
        raise ValueError("Usuário sem bloqueio.")
    return MuitasTentativas(
        regra_de_acesso(),
        f"Acesso bloqueado por 15 minutos depois de {_motivo_do_bloqueio(usuario)}",
        {"tentar_de_novo_em": usuario.bloqueado_ate},
    )


def conferir_bloqueio(usuario: Usuario) -> None:
    """429 enquanto o bloqueio vale, mesmo com o código certo. Use sobre a linha travada."""
    if usuario.bloqueado_ate is not None and usuario.bloqueado_ate > relogio.agora():
        raise _erro_de_bloqueio(usuario)


def _travar(usuario: Usuario) -> Usuario:
    """A linha do usuário travada até o fim da transação; bloqueio vencido volta a zero."""
    atual: Usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
    if atual.bloqueado_ate is not None and atual.bloqueado_ate <= relogio.agora():
        atual.bloqueado_ate = None
        atual.tentativas_erradas = 0
        atual.senhas_erradas = 0
    conferir_bloqueio(atual)
    return atual


def _avisar_administradores(usuario: Usuario) -> None:
    """USR-06: o aviso sai depois do commit, com só os ids na fila."""
    from .tasks import contas_avisar_bloqueio

    schema = schema_atual()
    transaction.on_commit(lambda: contas_avisar_bloqueio.delay(schema, usuario.pk))


def _contar(atual: Usuario, falha: Falha | None) -> MuitasTentativas | None:
    """Grava a contagem na linha travada. No limite, bloqueia e grava o evento de segurança."""
    if falha is None:
        atual.tentativas_erradas = 0
        atual.senhas_erradas = 0
        atual.bloqueado_ate = None
    elif falha == Falha.SENHA:
        atual.senhas_erradas += 1
    else:
        atual.tentativas_erradas += 1
    bloqueou = falha is not None and _atingiu_o_limite(atual)
    if bloqueou:
        atual.bloqueado_ate = relogio.agora() + TEMPO_DE_BLOQUEIO
    atual.save(
        update_fields=["tentativas_erradas", "senhas_erradas", "bloqueado_ate", "atualizado_em"]
    )
    if not bloqueou:
        return None
    registrar_evento(
        "usuario.bloqueado",
        Categoria.SEGURANCA,
        objeto=atual,
        depois={"bloqueado_ate": atual.bloqueado_ate},
        motivo=_motivo_do_bloqueio(atual),
        regra=regra_de_acesso(),
    )
    if not na_plataforma():
        _avisar_administradores(atual)
    return _erro_de_bloqueio(atual)


def tentar_entrar(
    usuario: Usuario, *, senha: str, codigo: str = "", codigo_recuperacao: str = ""
) -> Tentativa:
    """Senha e código numa chamada só (login da plataforma e do Django Admin).

    Bloqueado: levanta 429 antes de olhar a senha. Quem tem autenticador e não mandou código
    falha como senha errada, para a resposta não dizer que a senha estava certa (P-03).
    """
    with transaction.atomic():
        atual = _travar(usuario)
        dispositivo = None
        if not atual.check_password(senha):
            falha: Falha | None = Falha.SENHA
        elif not tem_2fa(atual):
            falha = None
        elif not codigo and not codigo_recuperacao:
            falha = Falha.SENHA
        else:
            dispositivo = conferir_codigo(
                atual, codigo=codigo, codigo_recuperacao=codigo_recuperacao
            )
            falha = None if dispositivo is not None else Falha.CODIGO
        bloqueio = _contar(atual, falha)
    return Tentativa(atual, dispositivo, falha, bloqueio)


def tentar_senha(usuario: Usuario, senha: str) -> Tentativa:
    """Só a senha, com a mesma trava e contagem (1ª etapa do login da empresa).

    Senha certa de quem tem autenticador não zera a contagem: a etapa do código ainda falta
    (USR-06 soma senhas e códigos).
    """
    with transaction.atomic():
        atual = _travar(usuario)
        if not atual.check_password(senha):
            return Tentativa(atual, falha=Falha.SENHA, bloqueio=_contar(atual, Falha.SENHA))
        if not tem_2fa(atual):
            _contar(atual, None)
    return Tentativa(atual)


def conferir_senha(usuario: Usuario, senha: str) -> Tentativa:
    """Senha de quem já está logado (desligar 2 etapas, novos códigos, trocar a senha).

    Errar conta como tentativa errada; acertar não zera, porque não é um login.
    """
    with transaction.atomic():
        atual = _travar(usuario)
        if atual.check_password(senha):
            return Tentativa(atual)
        return Tentativa(atual, falha=Falha.SENHA, bloqueio=_contar(atual, Falha.SENHA))


def verificar_codigo(
    usuario: Usuario, *, codigo: str = "", codigo_recuperacao: str = "", confirmando: bool = False
) -> Tentativa:
    """Só o código (etapa `pre_2fa` ou ativação), com a mesma trava e a mesma contagem."""
    with transaction.atomic():
        atual = _travar(usuario)
        dispositivo = conferir_codigo(
            atual, codigo=codigo, codigo_recuperacao=codigo_recuperacao, confirmando=confirmando
        )
        falha = None if dispositivo is not None else Falha.CODIGO
        bloqueio = _contar(atual, falha)
    return Tentativa(atual, dispositivo, falha, bloqueio)
