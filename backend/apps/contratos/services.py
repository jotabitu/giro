"""Regras de contratos: modelos (S-09), contrato gerado, link de assinatura (S-15) e aditivo
(`LOC-08`). Interface para os outros apps em `docs/api/contratos.md`.

Quem chama (`locacoes`; `vendas` na fase 2) monta os valores dos marcadores e manda a origem
genérica: este app não conhece a locação. O PDF e o envio do link saem numa tarefa depois do
commit; o token é criado na tarefa e nunca passa pela fila.
"""

import hashlib
import secrets
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status

from comum import relogio
from comum.auditoria import Categoria, auditar, registrar_evento
from comum.erros import Conflito, ErroDeNegocio, ErroDeRegra, ErroDeValidacao
from comum.estados import transicionar
from comum.eventos import publicar
from comum.tarefas import ator_para_fila, schema_atual

from . import marcadores, pdf, prontos, sanitizacao, selectors
from .models import (
    Contrato,
    Finalidade,
    ModeloContrato,
    OrigemContrato,
    StatusContrato,
    TipoContrato,
)

S = StatusContrato
VALIDADE_DO_LINK = timedelta(days=7)  # S-15
LINK_MODELOS = "/admin/contratos"


# --- Erros ---


class LinkIndisponivel(ErroDeNegocio):
    status_http = status.HTTP_410_GONE


def link_expirado() -> LinkIndisponivel:
    return LinkIndisponivel("link_expirado", "Este link venceu. Peça um novo à locadora.")


def ja_assinado() -> LinkIndisponivel:
    return LinkIndisponivel("contrato_ja_assinado", "Este contrato já foi assinado.")


class NomeNaoConfere(ErroDeValidacao):
    def __init__(self) -> None:
        super().__init__({"nome_completo": ["O nome não confere com o cadastro."]})
        self.codigo = "nome_nao_confere"
        self.mensagem = "Digite seu nome completo como está no cadastro"


def sem_modelo_publicado() -> ErroDeRegra:
    return ErroDeRegra(
        "IMP-04",
        "Publique um modelo de contrato antes de concluir a locação",
        {"link": LINK_MODELOS},
    )


# --- Modelos (S-09, LOC-15, IMP-04) ---


def _texto_limpo(texto: str) -> str:
    if len(texto) > sanitizacao.TAMANHO_MAXIMO:
        raise ErroDeValidacao({"texto": ["O texto passa do tamanho máximo do modelo."]})
    limpo = sanitizacao.limpar(texto)
    marcadores.conferir(limpo)
    return limpo


def _versoes(grupo: Any, travar: bool = False) -> QuerySet[ModeloContrato]:
    consulta = ModeloContrato.objects.filter(grupo=grupo)
    if travar:
        consulta = consulta.select_for_update()
    return consulta.order_by("-versao")


def ultima_versao(modelo: ModeloContrato) -> ModeloContrato:
    return _versoes(modelo.grupo).first() or modelo


def criar_modelo(nome: str, finalidade: str, texto: str) -> ModeloContrato:
    """Rascunho, versão 1."""
    modelo = ModeloContrato(nome=nome, finalidade=finalidade, texto=_texto_limpo(texto))
    with auditar(modelo, "modelo_contrato.criar", Categoria.CONFIGURACOES):
        modelo.save()
    return modelo


def criar_de_pronto(nome: str | None, chave: str) -> ModeloContrato:
    pronto = prontos.POR_CHAVE.get(chave)
    if pronto is None:
        raise ErroDeValidacao({"a_partir_de": ["Modelo pronto desconhecido."]})
    return criar_modelo(nome or pronto.nome, Finalidade.LOCACAO, pronto.texto)


def editar_modelo(
    modelo: ModeloContrato, nome: str | None = None, texto: str | None = None
) -> ModeloContrato:
    """Rascunho muda no lugar. Publicado não muda: nasce o rascunho da versão seguinte (`LOC-15`:
    contrato assinado mantém o texto da versão dele)."""
    with transaction.atomic():
        ultima = _versoes(modelo.grupo, travar=True).first() or modelo
        if ultima.arquivado:
            raise Conflito("modelo_arquivado", "Este modelo está arquivado.")
        limpo = _texto_limpo(texto) if texto is not None else ultima.texto
        if ultima.publicado or ultima.publicado_em is not None:
            rascunho = ModeloContrato(
                grupo=ultima.grupo,
                finalidade=ultima.finalidade,
                versao=ultima.versao + 1,
                nome=nome or ultima.nome,
                texto=limpo,
            )
            with auditar(rascunho, "modelo_contrato.nova_versao", Categoria.CONFIGURACOES):
                rascunho.save()
            return rascunho
        with auditar(ultima, "modelo_contrato.editar", Categoria.CONFIGURACOES):
            ultima.nome = nome or ultima.nome
            ultima.texto = limpo
            ultima.save(update_fields=["nome", "texto", "atualizado_em"])
        return ultima


def publicar_modelo(modelo: ModeloContrato) -> ModeloContrato:
    """A última versão passa a valer para contratos novos; a anterior sai de uso (fica no
    histórico). Marcador fora da lista: 400. Publicar o primeiro de locação conclui o passo
    `contrato` da implantação (`IMP-04`)."""
    with transaction.atomic():
        versoes = list(_versoes(modelo.grupo, travar=True))
        ultima = versoes[0] if versoes else modelo
        if ultima.arquivado:
            raise Conflito("modelo_arquivado", "Este modelo está arquivado.")
        marcadores.conferir(ultima.texto)
        if ultima.publicado:
            return ultima
        for anterior in versoes[1:]:
            if anterior.publicado:
                anterior.publicado = False
                anterior.save(update_fields=["publicado", "atualizado_em"])
        with auditar(ultima, "modelo_contrato.publicar", Categoria.CONFIGURACOES, regra="IMP-04"):
            ultima.publicado = True
            ultima.publicado_em = relogio.agora()
            ultima.save(update_fields=["publicado", "publicado_em", "atualizado_em"])
        if ultima.finalidade == Finalidade.LOCACAO:
            from apps.plataforma.services import registrar_passo_implantacao

            registrar_passo_implantacao("contrato")
    return ultima


def arquivar_modelo(modelo: ModeloContrato) -> ModeloContrato:
    """Tira de uso, sem apagar. O último modelo de locação publicado não sai (`IMP-04`)."""
    with transaction.atomic():
        versoes = list(_versoes(modelo.grupo, travar=True))
        ultima = versoes[0] if versoes else modelo
        if ultima.arquivado:
            return ultima
        publicado = any(v.publicado for v in versoes)
        if publicado and ultima.finalidade == Finalidade.LOCACAO:
            outros = (
                ModeloContrato.objects.select_for_update()
                .filter(finalidade=Finalidade.LOCACAO, publicado=True, arquivado=False)
                .exclude(grupo=ultima.grupo)
            )
            if not outros.exists():
                raise ErroDeRegra(
                    "IMP-04", "A empresa precisa de ao menos um modelo de locação publicado"
                )
        for versao in versoes:
            with auditar(versao, "modelo_contrato.arquivar", Categoria.CONFIGURACOES):
                versao.arquivado = True
                versao.save(update_fields=["arquivado", "atualizado_em"])
    return ultima


def previa(modelo: ModeloContrato, valores: dict[str, str] | None = None) -> str:
    """ "Ver com dados reais": o HTML montado, sem PDF e sem gravar. Sem valores, os exemplos."""
    ultima = ultima_versao(modelo)
    return marcadores.substituir(ultima.texto, valores or marcadores.EXEMPLOS)


# --- Contrato de uma origem ---


@dataclass(frozen=True)
class DadosDoContrato:
    """O que a origem manda: quem, de onde e os valores já formatados dos marcadores."""

    origem_tipo: str
    origem_id: int
    origem_codigo: str
    filial_id: int
    cliente_id: int
    valores: dict[str, str] = field(default_factory=dict)


def _titulo(nome_do_modelo: str) -> str:
    return f"Contrato de {nome_do_modelo[:1].lower()}{nome_do_modelo[1:]}"


def _agendar_preparo(contrato: Contrato) -> None:
    from .tasks import contratos_preparar_e_enviar

    schema = schema_atual()
    ator = ator_para_fila()
    transaction.on_commit(lambda: contratos_preparar_e_enviar.delay(schema, contrato.pk, ator=ator))


def _criar(dados: DadosDoContrato, **campos: Any) -> Contrato:
    contrato = Contrato(
        origem_tipo=dados.origem_tipo,
        origem_id=dados.origem_id,
        origem_codigo=dados.origem_codigo,
        filial_id=dados.filial_id,
        cliente_id=dados.cliente_id,
        **campos,
    )
    try:
        with transaction.atomic(), auditar(contrato, "contrato.gerar", Categoria.OPERACAO):
            contrato.save()
    except IntegrityError as erro:
        raise contrato_existente() from erro
    _agendar_preparo(contrato)
    return contrato


def contrato_existente() -> Conflito:
    return Conflito(
        "contrato_existente", "Esta locação já tem contrato. Use reenviar para mandar de novo."
    )


def gerar(dados: DadosDoContrato) -> Contrato:
    """O contrato com a versão publicada do modelo da finalidade. 422 `IMP-04` sem modelo; 409
    `contrato_existente` se já há um vigente. O PDF e o link saem depois do commit."""
    modelo = selectors.modelo_publicado(dados.origem_tipo)
    if modelo is None:
        raise sem_modelo_publicado()
    if selectors.contrato_vigente(dados.origem_tipo, dados.origem_id) is not None:
        raise contrato_existente()
    return _criar(
        dados,
        modelo=modelo,
        versao_modelo=modelo.versao,
        tipo=TipoContrato.CONTRATO,
        titulo=_titulo(modelo.nome),
        versao_texto_html=marcadores.substituir(modelo.texto, dados.valores),
        clausula_juros=marcadores.tem_clausula_juros(modelo.texto),
    )


def gerar_aditivo(dados: DadosDoContrato) -> Contrato:
    """`LOC-08`: aditivo da renovação, com o texto padrão do sistema. Não trava a renovação."""
    return _criar(
        dados,
        tipo=TipoContrato.ADITIVO,
        titulo="Aditivo de renovação",
        versao_texto_html=marcadores.substituir(prontos.TEXTO_ADITIVO, dados.valores),
    )


def cancelar(contrato: Contrato, motivo: str) -> Contrato:
    """O link deixa de valer na hora."""
    contrato.token_assinatura_hash = None
    contrato.token_assinatura_expira_em = None
    contrato.cancelado_em = relogio.agora()
    contrato.motivo_cancelamento = motivo[:200]
    transicionar(
        contrato,
        S.CANCELADO,
        motivo=motivo,
        mais_campos=(
            "token_assinatura_hash",
            "token_assinatura_expira_em",
            "cancelado_em",
            "motivo_cancelamento",
        ),
    )
    return contrato


# --- PDF, link e envio (rodam na tarefa) ---


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def link_de_assinatura(host: str, token: str) -> str:
    """O token vai no fragmento: não chega a logs de servidor nem ao `Referer` (S-15)."""
    return f"https://{host}/assinar#{token}"


def novo_token(contrato: Contrato) -> str:
    """Token de 32 bytes, 7 dias. O anterior deixa de valer. Devolve o token em claro uma vez."""
    token = secrets.token_urlsafe(32)
    contrato.token_assinatura_hash = hash_do_token(token)
    contrato.token_assinatura_expira_em = relogio.agora() + VALIDADE_DO_LINK
    contrato.save(
        update_fields=["token_assinatura_hash", "token_assinatura_expira_em", "atualizado_em"]
    )
    return token


def gravar_pdf(contrato: Contrato, marca: pdf.Marca) -> None:
    conteudo = pdf.gerar(contrato.versao_texto_html, marca)
    contrato.hash_pdf = pdf.sha256(conteudo)
    contrato.pdf.save(f"{contrato.origem_codigo}.pdf", ContentFile(conteudo), save=False)
    contrato.save(update_fields=["pdf", "hash_pdf", "atualizado_em"])


def marcar_enviado(contrato: Contrato) -> None:
    contrato.enviado_em = relogio.agora()
    if contrato.status == S.GERADO:
        transicionar(contrato, S.ENVIADO, mais_campos=("enviado_em",))
    else:
        contrato.save(update_fields=["enviado_em", "atualizado_em"])


def reenviar(contrato: Contrato) -> Contrato:
    """Novo link (o anterior deixa de valer agora) e novo envio. Assinado: reenvia o PDF
    assinado. Cancelado: 409."""
    from .tasks import contratos_preparar_e_enviar, contratos_reenviar

    if contrato.status == S.CANCELADO:
        raise Conflito("contrato_cancelado", "Este contrato foi cancelado.")
    schema = schema_atual()
    ator = ator_para_fila()
    with transaction.atomic():
        if contrato.status != S.ASSINADO:
            with auditar(contrato, "contrato.reenviar", Categoria.OPERACAO):
                contrato.token_assinatura_hash = None
                contrato.token_assinatura_expira_em = None
                contrato.save(
                    update_fields=[
                        "token_assinatura_hash",
                        "token_assinatura_expira_em",
                        "atualizado_em",
                    ]
                )
        else:
            registrar_evento("contrato.reenviar", Categoria.OPERACAO, objeto=contrato)
        tarefa = contratos_preparar_e_enviar if contrato.status == S.GERADO else contratos_reenviar
        transaction.on_commit(lambda: tarefa.delay(schema, contrato.pk, ator=ator))
    return contrato


# --- Assinatura pelo link (S-15) ---


def _pelo_token(token: str, travar: bool = False) -> Contrato:
    """404 para token desconhecido; 410 se já assinado ou vencido."""
    if not token:
        raise Http404
    consulta = Contrato.objects.select_related("cliente").filter(
        token_assinatura_hash=hash_do_token(token)
    )
    if travar:
        consulta = consulta.select_for_update(of=("self",))
    contrato: Contrato | None = consulta.first()
    if contrato is None or contrato.status in (S.CANCELADO, S.GERADO):
        raise Http404
    if contrato.status == S.ASSINADO:
        raise ja_assinado()
    expira = contrato.token_assinatura_expira_em
    if expira is None or expira <= relogio.agora():
        raise link_expirado()
    return contrato


def consultar(token: str) -> Contrato:
    return _pelo_token(token)


def _normalizar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome)
    letras = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(letras.casefold().split())


def assinar(token: str, nome_completo: str, ip: str | None, aparelho: str) -> Contrato:
    """O nome tem que conferir com o cadastro, sem diferenciar maiúsculas e acentos. Grava o
    momento, o IP, o aparelho e publica `contratos.contrato_assinado`."""
    with transaction.atomic():
        contrato = _pelo_token(token, travar=True)
        if _normalizar_nome(nome_completo) != _normalizar_nome(contrato.cliente.nome):
            raise NomeNaoConfere()
        contrato.assinado_em = relogio.agora()
        contrato.assinado_ip = ip
        contrato.assinatura_aparelho = (aparelho or "")[:200]
        transicionar(
            contrato,
            S.ASSINADO,
            mais_campos=("assinado_em", "assinado_ip", "assinatura_aparelho"),
        )
        publicar(
            "contratos.contrato_assinado",
            contrato_id=contrato.pk,
            origem_tipo=contrato.origem_tipo,
            origem_id=contrato.origem_id,
            tipo=contrato.tipo,
            assinado_em=contrato.assinado_em,
        )
        from .tasks import contratos_registrar_assinatura

        schema = schema_atual()
        transaction.on_commit(lambda: contratos_registrar_assinatura.delay(schema, contrato.pk))
    return contrato


def gravar_pdf_assinado(contrato: Contrato, marca: pdf.Marca, quando: str) -> None:
    """O PDF final ganha a página de registro: data e hora, IP /24, aparelho e o hash do PDF
    que foi assinado."""
    from comum.classificacao import mascarar_ip

    registro = [
        ("Documento", f"{contrato.titulo} · {contrato.origem_codigo}"),
        ("Assinado por", contrato.cliente.nome),
        ("Data e hora", quando),
        ("IP", mascarar_ip(contrato.assinado_ip) if contrato.assinado_ip else "não informado"),
        ("Aparelho", contrato.assinatura_aparelho or "não informado"),
        ("Hash do PDF assinado (SHA-256)", contrato.hash_pdf),
    ]
    conteudo = pdf.gerar(contrato.versao_texto_html, marca, registro)
    contrato.hash_pdf_assinado = pdf.sha256(conteudo)
    contrato.pdf_assinado.save(
        f"{contrato.origem_codigo}-assinado.pdf", ContentFile(conteudo), save=False
    )
    contrato.save(update_fields=["pdf_assinado", "hash_pdf_assinado", "atualizado_em"])


# --- LOC-08: aditivo sem assinatura em 7 dias vira tarefa para os gerentes da filial ---

LINK_DA_ORIGEM = {OrigemContrato.LOCACAO: "/locacoes/{id}", OrigemContrato.VENDA: "/vendas/{id}"}


def avisar_aditivos_sem_assinatura(agora: datetime | None = None) -> int:
    """Aditivo enviado há 7 dias (o prazo do link) e não assinado. Idempotente: cada aditivo
    avisa uma vez (`lembrete_aditivo_em` e a chave do aviso)."""
    from apps.filiais.selectors import gerentes
    from apps.notificacoes.services import avisar

    agora = agora or relogio.agora()
    avisados = 0
    pendentes = Contrato.objects.select_related("filial").filter(
        tipo=TipoContrato.ADITIVO,
        status=S.ENVIADO,
        enviado_em__lte=agora - VALIDADE_DO_LINK,
        lembrete_aditivo_em__isnull=True,
    )
    for contrato in pendentes:
        with transaction.atomic():
            avisar(
                [g["id"] for g in gerentes(contrato.filial)],
                tipo="aditivo_sem_assinatura",
                titulo=f"Aditivo da {contrato.origem_codigo} sem assinatura há 7 dias",
                link=LINK_DA_ORIGEM[OrigemContrato(contrato.origem_tipo)].format(
                    id=contrato.origem_id
                ),
                chave=f"aditivo-{contrato.pk}",
            )
            Contrato.objects.filter(pk=contrato.pk).update(
                lembrete_aditivo_em=agora, atualizado_em=agora
            )
        avisados += 1
    return avisados
