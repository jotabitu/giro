"""O contrato da locação (fluxo da retirada, passo 3; `docs/api/contratos.md`).

`locacoes` monta os valores dos marcadores e chama `contratos`, que não conhece a locação. Os
valores saem prontos para ler: dinheiro em reais, datas no fuso da filial.
"""

import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.db import connection

from apps.contratos import origens
from apps.contratos import selectors as contratos_selectors
from apps.contratos import services as contratos
from apps.contratos.models import Contrato
from apps.empresas.selectors import configuracao
from apps.financeiro import selectors as financeiro_selectors
from comum import relogio
from comum.dinheiro import aplicar_percentual, formatar_reais
from comum.erros import Conflito

from .models import FormaPagamento, Locacao, Periodicidade, StatusDesconto, StatusLocacao

ORIGEM = "locacao"
S = StatusLocacao


# --- Formatos ---


def _cpf_ou_cnpj(digitos: str) -> str:
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    return digitos


def _telefone(digitos: str) -> str:
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return digitos


def _data(valor: Any) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def _momento(valor: datetime | None, fuso: str) -> str:
    return valor.astimezone(ZoneInfo(fuso)).strftime("%d/%m/%Y %H:%M") if valor else ""


def _pct(valor: Any) -> str:
    return f"{valor:.2f}%".replace(".", ",")


def _endereco(objeto: Any) -> str:
    partes = [f"{objeto.logradouro}, {objeto.numero}".strip(", ")]
    if objeto.complemento:
        partes.append(objeto.complemento)
    if objeto.bairro:
        partes.append(objeto.bairro)
    if objeto.cidade:
        partes.append(f"{objeto.cidade}/{objeto.uf}")
    return ", ".join(p for p in partes if p)


def _tabela_de_parcelas(locacao: Locacao) -> str:
    """HTML montado aqui, com os valores escapados; entra no texto como está."""
    linhas = "".join(
        f"<tr><td>{conta.numero_parcela}ª parcela</td><td>{_data(conta.vencimento)}</td>"
        f"<td>{html.escape(formatar_reais(conta.valor_centavos))}</td></tr>"
        for conta in financeiro_selectors.contas_da_origem(ORIGEM, locacao.pk)
        if conta.tipo == "parcela"
    )
    return (
        "<table><thead><tr><th>Parcela</th><th>Vencimento</th><th>Valor</th></tr></thead>"
        f"<tbody>{linhas}</tbody></table>"
    )


def valores(locacao: Locacao) -> dict[str, str]:
    """Todos os marcadores da lista fechada, para esta locação."""
    empresa: Any = getattr(connection, "tenant", None)
    filial, cliente, veiculo = locacao.filial, locacao.cliente, locacao.veiculo
    fuso = filial.fuso
    config = configuracao()
    efetivo = locacao.valor_periodo_centavos - aplicar_percentual(
        locacao.valor_periodo_centavos, locacao.desconto_pct
    )
    extras = [f"{e.nome} ({e.quantidade})" for e in locacao.extras.all()]
    cidade_da_empresa = getattr(empresa, "cidade", "") or filial.cidade
    uf_da_empresa = getattr(empresa, "uf", "") or filial.uf
    return {
        "empresa.nome": str(getattr(empresa, "nome_exibicao", "")),
        "empresa.razao_social": str(getattr(empresa, "razao_social", "") or ""),
        "empresa.cnpj": _cpf_ou_cnpj(str(getattr(empresa, "cnpj", "") or "")),
        "empresa.endereco": _endereco(filial),
        "empresa.cidade": f"{cidade_da_empresa}/{uf_da_empresa}",
        "filial.nome": filial.nome,
        "filial.cnpj": _cpf_ou_cnpj(filial.cnpj),
        "filial.endereco": _endereco(filial),
        "filial.telefone": _telefone(filial.telefone),
        "cliente.nome": cliente.nome,
        "cliente.cpf": _cpf_ou_cnpj(cliente.documento or ""),
        "cliente.nascimento": _data(cliente.nascimento),
        "cliente.endereco": _endereco(cliente),
        "cliente.celular": _telefone(cliente.celular),
        "cliente.email": cliente.email,
        "cliente.cnh_numero": cliente.cnh_numero or "",
        "cliente.cnh_categoria": cliente.cnh_categoria or "",
        "cliente.cnh_validade": _data(cliente.cnh_validade),
        "cliente.responsavel_nome": cliente.responsavel_nome,
        "cliente.responsavel_cpf": _cpf_ou_cnpj(cliente.responsavel_cpf or ""),
        "veiculo.marca": veiculo.marca,
        "veiculo.modelo": veiculo.modelo,
        "veiculo.placa": veiculo.placa,
        "veiculo.chassi": veiculo.chassi,
        "veiculo.renavam": veiculo.renavam,
        "veiculo.ano": f"{veiculo.ano_fabricacao}/{veiculo.ano_modelo}",
        "veiculo.cor": veiculo.cor,
        "veiculo.km_saida": f"{locacao.km_saida or veiculo.km_atual:,}".replace(",", "."),
        "locacao.codigo": locacao.codigo,
        "locacao.inicio": _momento(locacao.inicio, fuso),
        "locacao.fim_previsto": _momento(locacao.fim_previsto, fuso),
        "locacao.periodicidade": str(Periodicidade(locacao.periodicidade).label).lower(),
        "locacao.plano": locacao.plano_especial.nome if locacao.plano_especial else "Tabela",
        "locacao.valor": formatar_reais(efetivo),
        "locacao.caucao": formatar_reais(locacao.caucao_centavos),
        "locacao.diaria_atraso": formatar_reais(locacao.diaria_centavos),
        "locacao.extras": ", ".join(extras) or "nenhum",
        "locacao.forma_pagamento": str(FormaPagamento(locacao.forma_pagamento).label),
        "locacao.parcelas": _tabela_de_parcelas(locacao),
        "locacao.tolerancia_atraso": f"{config.tolerancia_atraso_minutos} minutos",
        "cobranca.multa_atraso_pct": _pct(config.multa_atraso_pct),
        "cobranca.juros_mes_pct": _pct(config.juros_mes_pct),
        "contrato.data": relogio.agora().astimezone(ZoneInfo(fuso)).strftime("%d/%m/%Y"),
        "contrato.cidade_assinatura": f"{filial.cidade}/{filial.uf}",
    }


def _com_relacoes(locacao_id: int) -> Locacao | None:
    return (
        Locacao.objects.select_related("filial", "cliente", "veiculo", "plano_especial")
        .filter(pk=locacao_id)
        .first()
    )


def _valores_por_id(locacao_id: int) -> dict[str, str] | None:
    locacao = _com_relacoes(locacao_id)
    return valores(locacao) if locacao else None


def registrar() -> None:
    """A prévia do modelo com dados reais lê os valores por aqui (chamado no `ready()`)."""
    origens.registrar(ORIGEM, _valores_por_id)


def _dados(locacao: Locacao) -> contratos.DadosDoContrato:
    completa = _com_relacoes(locacao.pk) or locacao
    return contratos.DadosDoContrato(
        origem_tipo=ORIGEM,
        origem_id=completa.pk,
        origem_codigo=completa.codigo,
        filial_id=completa.filial_id,
        cliente_id=completa.cliente_id,
        valores=valores(completa),
    )


# --- Ações ---


def gerar(locacao: Locacao) -> Contrato:
    """Locação `aguardando_retirada`, sem pedido de desconto pendente (o contrato sai com o
    preço decidido). 422 `IMP-04` sem modelo publicado; 409 `contrato_existente`."""
    if locacao.status != S.AGUARDANDO_RETIRADA:
        raise Conflito(
            "contrato_fora_de_hora",
            "O contrato sai quando a locação está aguardando retirada.",
            {"status": locacao.status},
        )
    if locacao.desconto_status == StatusDesconto.PENDENTE:
        raise Conflito(
            "desconto_pendente",
            "O contrato sai depois da decisão do pedido de desconto.",
            {"pedido_aprovacao_id": locacao.pedido_desconto_id},
        )
    return contratos.gerar(_dados(locacao))


def gerar_aditivo(locacao: Locacao) -> Contrato:
    """`LOC-08`: chamado pela renovação (T-091). Não trava a renovação."""
    return contratos.gerar_aditivo(_dados(locacao))


def vigente(locacao: Locacao) -> Contrato | None:
    return contratos_selectors.contrato_vigente(ORIGEM, locacao.pk)


def reenviar(locacao: Locacao) -> Contrato:
    contrato = vigente(locacao)
    if contrato is None:
        raise Conflito("sem_contrato", "Esta locação ainda não tem contrato. Gere o contrato.")
    return contratos.reenviar(contrato)
