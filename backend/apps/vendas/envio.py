"""Envio da proposta de venda (`VEN-15`, `VEN-19`; ADR 0042, item 8; T-502, fase 1c).

- O PDF da proposta: texto fixo do sistema, com a marca da locadora, pelo `contratos.pdf.gerar`.
  Fica no armazenamento privado (AUD-05), sem versão: cada envio grava o PDF de novo.
- O e-mail ao cliente com o PDF anexo sai depois do commit, numa tarefa (`vendas_enviar_proposta`).
  Nada vai pelo WhatsApp do sistema na fase 1. Sem e-mail no cadastro, a venda muda de estado do
  mesmo jeito e a resposta traz `email_enviado: false`, para a tela mostrar "Copiar link".
- O link público ("Copiar link", S-15, como o recibo da devolução da T-411): token de 32 bytes,
  o banco guarda só o hash, vale 7 dias, um vivo por venda (o novo anula o anterior). O token vai
  no fragmento do link (`/proposta#<token>`) e a página o manda no corpo de um POST: não chega a
  log de servidor nem ao `Referer`. A consulta devolve só o código, o primeiro nome do cliente, o
  veículo e uma URL assinada de 15 minutos do PDF. Fica desligado por `GIRO_PROPOSTA_PUBLICA`
  até a revisão da Segurança.

Este módulo não muda o status da venda: o estado e as datas continuam em `services`.
"""

import hashlib
import html
import ipaddress
import secrets
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import Http404

from apps.contratos import pdf
from apps.contratos import selectors as contratos_selectors
from apps.financeiro.services import remetente
from comum import aprovacoes, enderecos, relogio
from comum.auditoria import ATOR_SISTEMA, Categoria, registrar_evento, usar_ator
from comum.conexao import schema_atual
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen
from comum.erros import Conflito

from . import services
from .models import FormaVenda, StatusVenda, Venda

VALIDADE_DO_LINK = timedelta(days=7)  # S-15, como o contrato, o recibo e o convite
FUSO_DO_DIA = ZoneInfo("America/Sao_Paulo")
# Onde a proposta já foi enviada e ainda vale para o cliente (VEN-13).
COM_PROPOSTA = (StatusVenda.PROPOSTA, StatusVenda.NEGOCIACAO)
SEM_EMAIL = (
    "A proposta foi salva, mas este cliente não tem e-mail cadastrado. "
    "Copie o link e envie para ele."
)


def _e(texto: Any) -> str:
    return html.escape(str(texto))


def _dia(venda: Venda, momento: datetime) -> date:
    return momento.astimezone(ZoneInfo(venda.filial.fuso)).date()


def _pct(valor: Any) -> str:
    return f"{valor:.2f}".replace(".", ",") + "%"


def _veiculo(venda: Venda) -> str:
    veiculo = venda.veiculo
    return f"{veiculo.marca} {veiculo.modelo} · {placa_com_hifen(veiculo.placa)}"


# --- O PDF ---


def corpo(venda: Venda) -> str:
    """O HTML da proposta (`VEN-15`): veículo, preço de tabela, desconto, preço final, forma,
    entrada e parcelas. A troca entra na fase 2. Tudo do cadastro passa por `html.escape`."""
    conta = services.calculo_da_venda(venda)
    cliente = venda.cliente
    linhas = [
        ("Preço de tabela", formatar_reais(conta.preco_tabela_centavos)),
        (
            "Desconto",
            f"{_pct(conta.desconto_pct)} · {formatar_reais(conta.desconto_centavos)}"
            if conta.desconto_centavos
            else "Sem desconto",
        ),
        ("Preço final", formatar_reais(conta.preco_final_centavos)),
    ]
    if conta.forma == FormaVenda.A_VISTA:
        linhas.append(("Forma de pagamento", "À vista, por Pix ou TED"))
    elif conta.forma == FormaVenda.ENTRADA_PARCELAS and conta.num_parcelas:
        linhas += [
            ("Forma de pagamento", "Entrada e parcelas mensais, por boleto ou Pix"),
            ("Entrada", formatar_reais(conta.entrada_centavos or 0)),
            ("Parcelas", _texto_das_parcelas(conta)),
        ]
        if conta.juros_pct:
            linhas.append(("Juros", f"{_pct(conta.juros_pct)} ao mês"))
    tabela = "".join(f"<tr><td>{_e(r)}</td><td>{_e(v)}</td></tr>" for r, v in linhas)
    partes = [
        f"<h1>Proposta de venda · {_e(venda.codigo)}</h1>",
        f"<p>Cliente: {_e(cliente.nome if cliente else venda.interessado_nome)}<br>",
        f"Veículo: {_e(_veiculo(venda))}<br>",
        f"Ano: {_e(venda.veiculo.ano_fabricacao)}/{_e(venda.veiculo.ano_modelo)}</p>",
        f"<table>{tabela}</table>",
    ]
    vence = services.vence_em(venda)
    if vence is not None:
        partes.append(
            f"<p>Esta proposta vale até {vence:%d/%m/%Y}. "
            "Depois disso, fale com a loja para uma nova proposta.</p>"
        )
    partes.append(
        "<p>As parcelas começam um mês depois da conclusão da venda, com o contrato assinado e "
        "a entrada paga.</p>"
        if conta.forma == FormaVenda.ENTRADA_PARCELAS
        else "<p>A venda se conclui com o contrato assinado e o pagamento feito.</p>"
    )
    vendedor = venda.vendedor
    partes.append(
        f"<p>Atendimento: {_e(vendedor.nome if vendedor else '')} · {_e(venda.filial.nome)}</p>"
    )
    return "".join(partes)


def _texto_das_parcelas(conta: Any) -> str:
    """ "12 parcelas mensais de R$ 1.339,00", e a última à parte quando muda."""
    n = conta.num_parcelas
    texto = f"{n} parcelas mensais de {formatar_reais(conta.parcela_centavos or 0)}"
    ultima = conta.ultima_parcela_centavos
    if ultima is not None and ultima != conta.parcela_centavos:
        texto = (
            f"{n - 1} parcelas mensais de {formatar_reais(conta.parcela_centavos or 0)} "
            f"e a última de {formatar_reais(ultima)}"
        )
    return texto


def pdf_da_proposta(venda: Venda) -> bytes:
    marca, _ = contratos_selectors.marca_e_host()
    return pdf.gerar(corpo(venda), marca)


def gravar_pdf(venda: Venda) -> None:
    """Grava o PDF da proposta enviada; o envio novo aponta para o arquivo novo (o antigo fica no
    armazenamento: arquivo de negócio não se apaga, ADR 0009). Chamado com a venda travada."""
    conteudo = pdf_da_proposta(venda)
    venda.proposta_pdf.save(f"proposta-{venda.codigo}.pdf", ContentFile(conteudo), save=False)
    venda.save(update_fields=["proposta_pdf", "atualizado_em"])


# --- O e-mail ---


def tem_email(venda: Venda) -> bool:
    return bool(venda.cliente is not None and venda.cliente.email)


def agendar_envio(venda: Venda) -> bool:
    """Depois do commit, a tarefa grava o PDF e manda o e-mail (com o PDF anexo). Devolve
    `email_enviado`: se o cliente tem e-mail para receber. Sem e-mail, só o PDF é gravado (o
    "Copiar link" precisa dele). A tarefa leva a data do envio: um envio mais novo vence."""
    from .tasks import vendas_enviar_proposta

    schema = schema_atual()
    pk, enviada = venda.pk, venda.proposta_enviada_em
    momento = enviada.isoformat() if enviada else ""
    transaction.on_commit(lambda: vendas_enviar_proposta.delay(schema, pk, momento))
    return tem_email(venda)


def enviar(venda_id: int, momento: str) -> None:
    """O corpo da tarefa: idempotente pela data do envio (a tarefa de um envio antigo não manda
    o PDF de uma proposta que mudou depois)."""
    with transaction.atomic():
        venda = (
            Venda.objects.select_for_update(of=("self",))
            .select_related("filial", "cliente", "veiculo", "vendedor")
            .filter(pk=venda_id)
            .first()
        )
        if venda is None or venda.status not in COM_PROPOSTA:
            return
        enviada = venda.proposta_enviada_em
        if momento and (enviada is None or enviada != datetime.fromisoformat(momento)):
            return
        gravar_pdf(venda)
        cliente = venda.cliente
        if cliente is None or not cliente.email:
            return
        marca, _ = contratos_selectors.marca_e_host()
        with venda.proposta_pdf.open("rb") as aberto:
            conteudo = aberto.read()
        mensagem = EmailMessage(
            subject=f"{marca.nome}: proposta da {venda.codigo}",
            body=texto_do_email(venda, marca.nome),
            from_email=remetente(),
            to=[cliente.email],
        )
        mensagem.attach(f"proposta-{venda.codigo}.pdf", conteudo, "application/pdf")
        mensagem.send()


def texto_do_email(venda: Venda, nome_da_marca: str) -> str:
    nome = venda.cliente.nome if venda.cliente is not None else venda.interessado_nome
    veiculo = f"{venda.veiculo.marca} {venda.veiculo.modelo}"
    texto = (
        f"Olá, {nome}.\n"
        f"{nome_da_marca}: proposta de venda da {veiculo} ({venda.codigo}), por "
        f"{formatar_reais(venda.preco_final_centavos)}. A proposta segue anexa, em PDF."
    )
    vence = services.vence_em(venda)
    if vence is not None:
        texto += f" Ela vale até {vence:%d/%m/%Y}."
    return texto


def texto_do_envio(venda: Venda) -> str:
    """`VEN-19`: "Proposta enviada para diego@exemplo.com em 07 out. Sem resposta do cliente,
    ela vence em 14 out." Sem e-mail: "A proposta foi salva, mas este cliente não tem e-mail
    cadastrado. Copie o link e envie para ele." Em `negociacao`, a proposta não vence."""
    cliente = venda.cliente
    if cliente is None or not cliente.email or venda.proposta_enviada_em is None:
        return SEM_EMAIL
    dia = aprovacoes.dia_curto(_dia(venda, venda.proposta_enviada_em))
    texto = f"Proposta enviada para {cliente.email} em {dia}."
    vence = services.vence_em(venda)
    if vence is not None:
        texto += f" Sem resposta do cliente, ela vence em {aprovacoes.dia_curto(vence)}."
    return texto


# --- O link público (S-15) ---


def proposta_publica_ligada() -> bool:
    """`GIRO_PROPOSTA_PUBLICA`: desligado até a revisão da Segurança (T-502, fase 1c)."""
    return bool(getattr(settings, "GIRO_PROPOSTA_PUBLICA", False))


def proposta_publica_desligada() -> Conflito:
    return Conflito(
        "proposta_publica_desligada",
        "O link da proposta ainda não está disponível. Use Enviar para mandar a proposta.",
    )


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def link(host: str, token: str) -> str:
    """O token vai no fragmento: não chega a log de servidor nem ao `Referer` (S-15)."""
    return enderecos.link(host, f"/proposta#{token}")


def gerar_link(venda: Venda, por: Any) -> tuple[str, Venda]:
    """ "Copiar link" (`VEN-15`, `VEN-19`): só a venda com a proposta enviada (`proposta` ou
    `negociacao`); grava o PDF de novo (o do link é sempre o da proposta de agora: S-15, revisão
    da Segurança no #650); token novo, o anterior deixa de valer. Não
    envia nada e não muda o estado nem o vencimento. Devolve o token em claro uma vez."""
    if not proposta_publica_ligada():
        raise proposta_publica_desligada()
    services._exigir_mexer(venda, por)
    with transaction.atomic():
        travada = services._travar(venda)
        if travada.status not in COM_PROPOSTA:
            raise Conflito(
                "transicao_venda", "O link existe só para a proposta enviada e ainda aberta."
            )
        if travada.cliente is not None and travada.cliente.anonimizado_em is not None:
            raise Conflito("titular_anonimizado", "Os dados deste cliente foram anonimizados.")
        gravar_pdf(travada)
        token = secrets.token_urlsafe(32)
        travada.token_proposta_hash = hash_do_token(token)
        travada.token_proposta_expira_em = relogio.agora() + VALIDADE_DO_LINK
        travada.save(
            update_fields=["token_proposta_hash", "token_proposta_expira_em", "atualizado_em"]
        )
        registrar_evento(
            "venda.copiar_link_proposta",
            Categoria.SEGURANCA,
            objeto=travada,
            depois={"token_proposta_expira_em": travada.token_proposta_expira_em.isoformat()},
            regra="S-15",
            filial_id=travada.filial_id,
        )
    return token, travada


def consultar(token: str, ip: str | None, aparelho: str) -> Venda:
    """A página pública `/proposta`: só a proposta daquele token, no schema do host. 404 para
    token desconhecido ou anulado (sem dizer qual) e com o link desligado; 410 `link_expirado`
    depois dos 7 dias ou com a venda fora de `proposta`/`negociacao` (vendida, perdida). Não é de
    uso único. Cada abertura grava `venda.proposta_aberta`, no máximo uma por token por dia."""
    from apps.contratos.services import link_expirado

    if not token or not proposta_publica_ligada():
        raise Http404
    venda: Venda | None = (
        Venda.objects.select_related("filial", "cliente", "veiculo")
        .filter(token_proposta_hash=hash_do_token(token))
        .first()
    )
    if venda is None or venda.token_proposta_expira_em is None or not venda.proposta_pdf:
        raise Http404
    if venda.cliente is not None and venda.cliente.anonimizado_em is not None:
        raise Http404
    if venda.token_proposta_expira_em <= relogio.agora() or venda.status not in COM_PROPOSTA:
        raise link_expirado()
    _registrar_abertura(venda, venda.token_proposta_expira_em, ip, aparelho)
    return venda


def _registrar_abertura(venda: Venda, expira: datetime, ip: str | None, aparelho: str) -> None:
    from apps.auditoria.models import EventoAuditoria
    from comum.classificacao import mascarar_ip

    gerado = expira - VALIDADE_DO_LINK
    inicio_do_dia = datetime.combine(relogio.hoje(), time.min, tzinfo=FUSO_DO_DIA)
    if EventoAuditoria.objects.filter(
        acao="venda.proposta_aberta",
        objeto_tipo="venda",
        objeto_id=venda.pk,
        ocorrido_em__gte=max(gerado, inicio_do_dia),
    ).exists():
        return
    rede = None
    if ip:
        rede = str(ipaddress.ip_network(mascarar_ip(ip), strict=False).network_address)
    ator = replace(ATOR_SISTEMA, ip=rede, aparelho=(aparelho or "")[:200], regra="VEN-15")
    with usar_ator(ator):
        registrar_evento(
            "venda.proposta_aberta", Categoria.SEGURANCA, objeto=venda, filial_id=venda.filial_id
        )


def primeiro_nome(venda: Venda) -> str:
    nome = (venda.cliente.nome if venda.cliente else venda.interessado_nome).split()
    return nome[0] if nome else ""
