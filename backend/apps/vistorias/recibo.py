"""Recibo da devolução em PDF, com a marca da locadora e as fotos da chegada (DEV-06).

Texto para pessoas, no horário da filial e com as palavras das telas ("devolução", "caução").
Tudo o que vem do cadastro passa por `html.escape`; as fotos entram por endereço interno
(`giro-imagem:<id>`), lidas aqui do armazenamento privado (S-09).
"""

import html
from typing import Any
from zoneinfo import ZoneInfo

from apps.contratos import pdf
from apps.contratos import selectors as contratos_selectors
from comum.dinheiro import formatar_reais

from . import services
from .models import Combustivel, Devolucao, FotoVistoria, NaturezaItem, PosicaoFoto

NIVEL = dict(Combustivel.choices)
POSICAO = dict(PosicaoFoto.choices)


def _e(texto: Any) -> str:
    return html.escape(str(texto))


def _linhas(itens: list[tuple[str, int]]) -> str:
    return "".join(
        f"<tr><td>{_e(descricao)}</td><td>{formatar_reais(valor)}</td></tr>"
        for descricao, valor in itens
    )


def corpo(devolucao: Devolucao) -> tuple[str, pdf.Imagens]:
    """O HTML do recibo e as imagens que ele usa."""
    locacao = devolucao.locacao
    # O recibo é só da devolução encerrada, que sempre tem a chegada.
    chegada = services.chegada_vigente(devolucao) or devolucao.vistoria
    if chegada is None:
        raise services.vistoria_pendente()
    saida = services.saida_vigente(locacao.pk, chegada.veiculo_id)
    veiculo = chegada.veiculo
    fuso = ZoneInfo(locacao.filial.fuso)
    quando = devolucao.devolvida_em or chegada.concluida_em
    itens = list(devolucao.itens.order_by("id"))
    cobrancas = [
        (i.descricao, i.valor_centavos)
        for i in itens
        if i.natureza == NaturezaItem.COBRANCA and i.valor_centavos > 0
    ]
    creditos = [
        (i.descricao, i.valor_centavos) for i in itens if i.natureza == NaturezaItem.CREDITO
    ]
    total, _ = services.somas(itens)

    fotos = list(FotoVistoria.ativos.filter(vistoria=chegada).order_by("id"))
    imagens: pdf.Imagens = {}
    figuras = []
    for foto in fotos:
        endereco = f"giro-imagem:{foto.pk}"
        with foto.arquivo.open("rb") as arquivo:
            conteudo = arquivo.read()
        tipo = "image/png" if foto.arquivo.name.lower().endswith(".png") else "image/jpeg"
        imagens[endereco] = (conteudo, tipo)
        figuras.append(
            f'<figure><img src="{endereco}" alt="" style="width:150pt">'
            f"<figcaption>{_e(POSICAO[foto.posicao])}</figcaption></figure>"
        )

    km_saida = services.km_de_saida(locacao, chegada, saida)
    combustivel_saida = NIVEL.get(saida.combustivel, "-") if saida is not None else "-"
    partes = [
        f"<h1>Recibo de devolução · {_e(locacao.codigo)}</h1>",
        f"<p>Cliente: {_e(locacao.cliente.nome)}<br>",
        f"Veículo: {_e(veiculo.marca)} {_e(veiculo.modelo)} · {_e(veiculo.placa)}<br>",
        "Devolução em: "
        + (_e(quando.astimezone(fuso).strftime("%d/%m/%Y %H:%M")) if quando else "-")
        + "</p>",
        "<h2>Vistoria de chegada</h2>",
        f"<p>Km na saída: {km_saida if km_saida is not None else '-'} · "
        f"Km na chegada: {chegada.km if chegada.km is not None else '-'}<br>",
        f"Combustível na saída: {_e(combustivel_saida)} · "
        f"na chegada: {_e(NIVEL.get(chegada.combustivel, '-'))}</p>",
        "<h2>Acerto</h2>",
        "<table><tr><th>Cobrança</th><th>Valor</th></tr>",
        _linhas(cobrancas) or "<tr><td>Nenhuma cobrança</td><td>R$ 0,00</td></tr>",
        f"<tr><td><strong>Total das cobranças</strong></td><td>{formatar_reais(total)}</td></tr>",
        "</table>",
    ]
    if creditos:
        partes += ["<table><tr><th>Crédito</th><th>Valor</th></tr>", _linhas(creditos), "</table>"]
    partes += [
        f"<p>Caução: {formatar_reais(devolucao.caucao_centavos)}<br>",
        f"<strong>{_e(services.texto_do_saldo(devolucao))}</strong></p>",
    ]
    if figuras:
        partes += ["<h2>Fotos da devolução</h2>", "".join(figuras)]
    return "".join(partes), imagens


def pdf_do_recibo(devolucao: Devolucao) -> bytes:
    marca, _ = contratos_selectors.marca_e_host()
    html_do_corpo, imagens = corpo(devolucao)
    return pdf.gerar(html_do_corpo, marca, imagens=imagens)
