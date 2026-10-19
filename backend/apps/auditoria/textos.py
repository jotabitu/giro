"""`resumo` e `detalhe` dos eventos, prontos para a tela (docs/api/auditoria.md).

Primeiro vale o formatador que o app dono registrou em `comum.auditoria.registrar_formatador`;
depois, os daqui, que só leem o próprio evento (valores em `depois`, `motivo`); por fim, o
texto genérico "<verbo> <objeto> <código>" (`Criou a locação LOC-2856`).

O texto sai do evento como foi gravado: `antes` e `depois` já vêm classificados (ADR 0014), e
nada aqui lê dado pessoal completo.
"""

from typing import Any

from django.db.models import Q
from django_tenants.utils import get_public_schema_name

from comum import auditoria
from comum.auditoria import Texto
from comum.conexao import schema_atual
from comum.dinheiro import formatar_reais

from .models import EventoAuditoria

# objeto (prefixo da ação) → (artigo, nome)
OBJETOS: dict[str, tuple[str, str]] = {
    "acesso_suporte": ("o", "acesso de suporte"),
    "caixa": ("o", "caixa"),
    "categoria": ("a", "categoria"),
    "cliente": ("o", "cliente"),
    "cobranca": ("a", "cobrança"),
    "comissao": ("a", "comissão"),
    "configuracao": ("as", "configurações"),
    "conta_receber": ("a", "conta a receber"),
    "contrato": ("o", "contrato"),
    "credencial": ("a", "credencial"),
    "despesa": ("a", "despesa"),
    "devolucao": ("a", "devolução"),
    "empresa": ("a", "empresa"),
    "exportacao": ("a", "exportação"),
    "filial": ("a", "filial"),
    "implantacao": ("a", "implantação"),
    "locacao": ("a", "locação"),
    "movimento_caixa": ("o", "movimento do caixa"),
    "pedido_aprovacao": ("o", "pedido de aprovação"),
    "pendencia_pagamento": ("a", "pendência de pagamento"),
    "plano": ("o", "plano"),
    "reembolso": ("o", "reembolso"),
    "renegociacao": ("a", "renegociação"),
    "sessao": ("a", "sessão"),
    "suporte": ("o", "suporte"),
    "usuario": ("o", "usuário"),
    "veiculo": ("o", "veículo"),
    "vistoria": ("a", "vistoria"),
}

VERBOS: dict[str, str] = {
    "abrir": "Abriu",
    "aceitar_convite": "Aceitou o convite d",
    "alterar_filiais": "Alterou as filiais d",
    "alterar_perfil": "Alterou o perfil d",
    "alterar_permissoes": "Alterou as permissões d",
    "aprovar": "Aprovou",
    "ativar": "Ativou",
    "bloquear": "Bloqueou",
    "cadastrar": "Cadastrou",
    "cancelar": "Cancelou",
    "cobrar": "Cobrou",
    "concluir": "Concluiu",
    "confirmar": "Confirmou",
    "convidar": "Convidou",
    "corrigir": "Corrigiu",
    "criar": "Criou",
    "desativar": "Desativou",
    "desbloquear": "Desbloqueou",
    "descartar": "Descartou",
    "editar": "Editou",
    "encerrar": "Encerrou",
    "estornar": "Estornou",
    "fechar": "Fechou",
    "inativar": "Inativou",
    "iniciar": "Iniciou",
    "lancar": "Lançou",
    "liberar": "Liberou",
    "pagar": "Registrou o pagamento d",
    "pedir": "Pediu",
    "reabrir": "Reabriu",
    "reativar": "Reativou",
    "recusar": "Recusou",
    "reenviar": "Reenviou",
    "renegociar": "Renegociou",
    "renovar": "Renovou",
    "revogar": "Revogou",
    "substituir": "Substituiu",
    "transferir": "Transferiu",
}

PERFIS = {
    "administrador": "Administrador",
    "gerente": "Gerente",
    "vendedor": "Vendedor",
    "vistoriador": "Vistoriador",
    "financeiro": "Financeiro",
}
PERMISSOES_DO_SUPORTE = {"ver": "só ver", "ver_editar": "ver e editar"}
STATUS_DA_DESPESA = {
    "aguardando_aprovacao": "aguardando gerente",
    "a_pagar": "a pagar",
    "paga": "pago no caixa",
}


def _objeto(prefixo: str) -> tuple[str, str]:
    return OBJETOS.get(prefixo, ("o", prefixo.replace("_", " ")))


def generico(evento: EventoAuditoria) -> Texto:
    prefixo, _, verbo = evento.acao.partition(".")
    artigo, nome = _objeto(prefixo)
    codigo = f" {evento.objeto_codigo}" if evento.objeto_codigo else ""
    texto_verbo = VERBOS.get(verbo)
    if texto_verbo is None:
        # Transição sem ação própria (`locacao.ativa`): o objeto e o novo estado.
        resumo = f"{nome[0].upper()}{nome[1:]}{codigo}: {verbo.replace('_', ' ')}"
    elif texto_verbo.endswith(" d"):  # "Alterou o perfil d" + "o usuário"
        resumo = f"{texto_verbo}{artigo} {nome}{codigo}"
    else:
        resumo = f"{texto_verbo} {artigo} {nome}{codigo}"
    return Texto(resumo, evento.motivo)


def _valor(evento: EventoAuditoria, campo: str = "valor_centavos") -> str:
    valor = evento.depois.get(campo)
    return formatar_reais(valor) if isinstance(valor, int) else ""


def _juntar(*partes: str) -> str:
    return " · ".join(p for p in partes if p)


# --- Financeiro (as ações da T-017; o app pode registrar as próprias) ---


def _sangria(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto:
    """FIN-07: o detalhe é o caixa de onde saiu o dinheiro (T-150)."""
    filiais = apoio.setdefault("filiais", {})
    if evento.filial_id is not None and evento.filial_id not in filiais:
        filiais.update(auditoria.consultar("filiais", {evento.filial_id}))
    nome = filiais.get(evento.filial_id) if evento.filial_id is not None else None
    detalhe = f"Caixa da {nome}" if nome else str(evento.depois.get("descricao", ""))
    return Texto(f"Fez sangria de {_valor(evento)}", detalhe)


def _movimento(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    tipo = evento.acao.partition(".")[2]
    rotulo = {"entrada": "entrada", "saida": "saída", "estornar": "estorno"}.get(tipo, tipo)
    return Texto(
        f"Registrou {rotulo} de {_valor(evento)} no caixa",
        str(evento.depois.get("descricao", "")),
    )


def _abrir_caixa(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    troco = _valor(evento, "troco_centavos")
    return Texto(f"Abriu o caixa com troco de {troco}" if troco else "Abriu o caixa")


def _despesa(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    status = STATUS_DA_DESPESA.get(str(evento.depois.get("status", "")), "")
    return Texto(
        f"Lançou despesa de {_valor(evento)}",
        _juntar(str(evento.depois.get("descricao", "")), status),
    )


# --- Pessoas e acesso ---


def _convidar(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    nome = str(evento.depois.get("nome", "")) or "uma pessoa"
    return Texto(f"Convidou {nome}", PERFIS.get(str(evento.depois.get("perfil", "")), ""))


def _copiar_link_convite(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    """USR-01 (T-250): o evento não tem o link nem o token."""
    return Texto("Copiou o link do convite")


def _bloqueio(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto:
    motivo = evento.motivo or "tentativas erradas"
    emails = apoio.setdefault("emails", {})
    if evento.objeto_id is not None and evento.objeto_id not in emails:
        emails.update(auditoria.consultar("emails_de_usuarios", {evento.objeto_id}))
    email = emails.get(evento.objeto_id, "") if evento.objeto_id is not None else ""
    de_quem = f" de {email}" if email else ""
    ip = mascarar_ip_curto(evento.ip) if evento.ip else ""
    return Texto(f"Login bloqueado após {motivo}{de_quem}", _juntar(evento.regra, ip))


def mascarar_ip_curto(ip: str) -> str:
    """`177.84.10.22` vira `177.84.x.x`, como a tela da plataforma mostra."""
    partes = ip.split(".")
    if len(partes) == 4:
        return f"{partes[0]}.{partes[1]}.x.x"
    return ip.split(":")[0] + ":…"


# --- Suporte (AUD-03, PLT-07) ---


def _id_do_acesso(evento: EventoAuditoria) -> int | None:
    if evento.objeto_tipo == "acessosuporte":
        return evento.objeto_id
    return evento.acesso_suporte_id


def _acesso(evento: EventoAuditoria, apoio: dict[str, Any]) -> dict[str, Any]:
    id_acesso = _id_do_acesso(evento)
    if id_acesso is None:
        return {}
    acessos = apoio.setdefault("acessos_suporte", {})
    if id_acesso not in acessos:
        acessos.update(auditoria.consultar("acessos_suporte", {id_acesso}))
    return dict(acessos.get(id_acesso) or {})


def _entrar(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto:
    acesso = _acesso(evento, apoio)
    permissao = PERMISSOES_DO_SUPORTE.get(str(evento.depois.get("permissao", "")), "")
    return Texto(
        "Entrou como suporte", _juntar(evento.motivo or acesso.get("motivo", ""), permissao)
    )


def _alteracoes(evento: EventoAuditoria) -> str:
    """Escritas feitas durante o acesso. Só a empresa tem esse rastro (ADR 0010, item 6)."""
    id_acesso = _id_do_acesso(evento)
    if schema_atual() == get_public_schema_name() or id_acesso is None:
        return ""
    quantas = (
        EventoAuditoria.objects.filter(acesso_suporte_id=id_acesso)
        .filter(~Q(categoria=auditoria.Categoria.SUPORTE))
        .count()
    )
    if quantas == 0:
        return "nenhuma alteração"
    return "1 alteração" if quantas == 1 else f"{quantas} alterações"


def _duracao(acesso: dict[str, Any], evento: EventoAuditoria) -> str:
    inicio = acesso.get("inicio")
    if inicio is None:
        return ""
    minutos = max(0, int((evento.ocorrido_em - inicio).total_seconds() // 60))
    return f"{minutos} min"


def _terminar(resumo: str) -> auditoria.Formatador:
    def formatar(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto:
        acesso = _acesso(evento, apoio)
        permissao = PERMISSOES_DO_SUPORTE.get(str(acesso.get("permissao", "")), "")
        return Texto(resumo, _juntar(_duracao(acesso, evento), permissao, _alteracoes(evento)))

    return formatar


def _bloqueio_do_suporte(evento: EventoAuditoria, _: dict[str, Any]) -> Texto:
    bloqueou = bool(evento.depois.get("suporte_bloqueado"))
    resumo = "Bloqueou o acesso do suporte" if bloqueou else "Liberou o acesso do suporte"
    return Texto(resumo, evento.motivo)


def _decisao_do_pedido(evento: EventoAuditoria, _: dict[str, Any]) -> Texto | None:
    """APR-09 e APR-10 (T-250): o administrador decidiu o próprio pedido. Sem a marca, o texto
    genérico ("Aprovou o pedido de aprovação")."""
    if not evento.depois.get("decidido_pelo_solicitante"):
        return None
    aprovou = evento.acao.endswith(".aprovar")
    return Texto(
        "Aprovou o próprio pedido" if aprovou else "Recusou o próprio pedido", evento.motivo
    )



def _editar_filial(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto | None:
    """DEV-01 (T-201): "Mudou o preço do litro", "Filial Centro · R$ 5,50 → R$ 5,90"."""
    if "preco_litro_centavos" not in evento.depois:
        return None
    filiais = apoio.setdefault("filiais", {})
    if evento.objeto_id is not None and evento.objeto_id not in filiais:
        filiais.update(auditoria.consultar("filiais", {evento.objeto_id}))
    nome = filiais.get(evento.objeto_id, "")
    antes, depois = evento.antes.get("preco_litro_centavos"), evento.depois["preco_litro_centavos"]
    valores = " → ".join(formatar_reais(v) if isinstance(v, int) else "sem preço" for v in (antes, depois))
    return Texto("Mudou o preço do litro", _juntar(str(nome), valores))


DESTE_APP: dict[str, auditoria.Formatador] = {
    "filial.editar": _editar_filial,
    "movimento_caixa.sangria": _sangria,
    "movimento_caixa.entrada": _movimento,
    "movimento_caixa.saida": _movimento,
    "movimento_caixa.estornar": _movimento,
    "caixa.abrir": _abrir_caixa,
    "despesa.lancar": _despesa,
    "usuario.convidar": _convidar,
    "usuario.copiar_link_convite": _copiar_link_convite,
    "pedido_aprovacao.aprovar": _decisao_do_pedido,
    "pedido_aprovacao.recusar": _decisao_do_pedido,
    "usuario.bloqueado": _bloqueio,
    "suporte.entrar": _entrar,
    "suporte.sair": _terminar("Saiu do modo suporte"),
    "suporte.encerrar": _terminar("O acesso de suporte terminou no prazo"),
    "suporte.revogar": _terminar("Revogou o acesso do suporte"),
    "suporte.bloquear": _bloqueio_do_suporte,
    "suporte.liberar": _bloqueio_do_suporte,
}


def texto(evento: EventoAuditoria, apoio: dict[str, Any]) -> Texto:
    funcao = auditoria.formatador(evento.acao) or DESTE_APP.get(evento.acao)
    if funcao is not None:
        pronto = funcao(evento, apoio)
        if pronto is not None:
            return pronto
    return generico(evento)


# --- Tom da linha (T-201, `auditoria.md`) ---

# Ações que pedem o selo de perigo. No MVP, só o login bloqueado (USR-06, PLT-08).
ACOES_PERIGO = frozenset({"usuario.bloqueado"})
CATEGORIAS_INFO = frozenset({"configuracoes", "seguranca"})


def tom(evento: EventoAuditoria) -> str | None:
    """`alerta` no que o suporte fez (AUD-03), `perigo` nas `ACOES_PERIGO`, `info` no resto de
    configurações e segurança, `null` no resto. A tela não escolhe tom."""
    if evento.acesso_suporte_id is not None or evento.ator_tipo == "suporte":
        return "alerta"
    if evento.acao in ACOES_PERIGO:
        return "perigo"
    if evento.categoria in CATEGORIAS_INFO:
        return "info"
    return None
