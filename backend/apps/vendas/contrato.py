"""O contrato de compra e venda (`VEN-15`; ADR 0042, item 6; T-502, fase 1b).

`vendas` monta os valores dos marcadores e chama `contratos`, que não conhece a venda, como a
locação faz (`apps/locacoes/contrato.py`). Os de empresa, filial, cliente e veículo seguem os da
locação; os `venda.*` são só da finalidade `venda`. Os valores saem prontos para ler: dinheiro em
reais, datas no fuso da filial.
"""

from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db import connection

from apps.contratos import origens
from apps.contratos import selectors as contratos_selectors
from apps.contratos import services as contratos
from apps.contratos.models import Contrato, Finalidade
from apps.empresas.selectors import configuracao
from apps.locacoes import contrato as contrato_da_locacao
from comum import relogio
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen
from comum.empresa import nome_da_empresa

from . import calculo
from .models import FormaVenda, Venda

ORIGEM = "venda"
# O dia só existe quando a venda vira `vendida` (VEN-04): o contrato diz a regra.
PRIMEIRO_VENCIMENTO = "um mês depois da conclusão da venda"

_cpf_ou_cnpj = contrato_da_locacao._cpf_ou_cnpj
_telefone = contrato_da_locacao._telefone
_endereco = contrato_da_locacao._endereco
_data = contrato_da_locacao._data
_pct = contrato_da_locacao._pct


def _parcelas(conta: calculo.Calculo) -> str:
    """ "12 parcelas mensais de R$ 1.339,00"; com a diferença de centavos na última, ela
    aparece à parte. À vista: sem parcelas."""
    n = conta.num_parcelas or 0
    if conta.forma != FormaVenda.ENTRADA_PARCELAS or not n or conta.parcela_centavos is None:
        return "sem parcelas"
    parcela = formatar_reais(conta.parcela_centavos)
    ultima = conta.ultima_parcela_centavos
    if ultima is None or ultima == conta.parcela_centavos:
        return f"{n} parcelas mensais de {parcela}"
    return f"{n} parcelas mensais, {n - 1} de {parcela} e a última de {formatar_reais(ultima)}"


def valores(venda: Venda) -> dict[str, str]:
    """Os marcadores da lista fechada para esta venda (os `locacao.*` ficam vazios)."""
    empresa: Any = getattr(connection, "tenant", None)
    filial, cliente, veiculo = venda.filial, venda.cliente, venda.veiculo
    config = configuracao()
    conta = calculo.calcular(
        calculo.Entrada(
            preco_tabela_centavos=venda.preco_tabela_centavos or 0,
            desconto_pct=Decimal(venda.desconto_pct or 0),
            forma=venda.forma,
            entrada_centavos=venda.entrada_centavos,
            num_parcelas=venda.num_parcelas,
            juros_pct=Decimal(venda.juros_pct or 0),
            desconto_aprovado_pct=venda.desconto_aprovado_pct,
        )
    )
    cidade_da_empresa = getattr(empresa, "cidade", "") or filial.cidade
    uf_da_empresa = getattr(empresa, "uf", "") or filial.uf
    parcelada = venda.forma == FormaVenda.ENTRADA_PARCELAS
    comprador: dict[str, str] = {}
    if cliente is not None:
        comprador = {
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
        }
    return {
        "empresa.nome": nome_da_empresa(),
        "empresa.razao_social": str(getattr(empresa, "razao_social", "") or ""),
        "empresa.cnpj": _cpf_ou_cnpj(str(getattr(empresa, "cnpj", "") or "")),
        "empresa.endereco": _endereco(filial),
        "empresa.cidade": f"{cidade_da_empresa}/{uf_da_empresa}",
        "filial.nome": filial.nome,
        "filial.cnpj": _cpf_ou_cnpj(filial.cnpj),
        "filial.endereco": _endereco(filial),
        "filial.telefone": _telefone(filial.telefone),
        **comprador,
        "veiculo.marca": veiculo.marca,
        "veiculo.modelo": veiculo.modelo,
        "veiculo.placa": placa_com_hifen(veiculo.placa),
        "veiculo.chassi": veiculo.chassi,
        "veiculo.renavam": veiculo.renavam,
        "veiculo.ano": f"{veiculo.ano_fabricacao}/{veiculo.ano_modelo}",
        "veiculo.cor": veiculo.cor,
        "veiculo.km_saida": f"{veiculo.km_atual:,}".replace(",", "."),
        "venda.codigo": venda.codigo,
        "venda.preco_tabela": formatar_reais(venda.preco_tabela_centavos or 0),
        "venda.desconto": (
            f"{formatar_reais(venda.desconto_centavos)} ({_pct(Decimal(venda.desconto_pct))})"
        ),
        "venda.preco_final": formatar_reais(venda.preco_final_centavos),
        "venda.forma": str(FormaVenda(venda.forma).label).lower() if venda.forma else "",
        "venda.entrada": formatar_reais(venda.entrada_centavos or 0),
        "venda.parcelas": _parcelas(conta),
        "venda.juros_mes": _pct(Decimal(venda.juros_pct or 0)),
        "venda.primeiro_vencimento": PRIMEIRO_VENCIMENTO if parcelada else "sem parcelas",
        "cobranca.multa_atraso_pct": _pct(config.multa_atraso_pct),
        "cobranca.juros_mes_pct": _pct(config.juros_mes_pct),
        "contrato.data": relogio.agora().astimezone(ZoneInfo(filial.fuso)).strftime("%d/%m/%Y"),
        "contrato.cidade_assinatura": f"{filial.cidade}/{filial.uf}",
    }


def _com_relacoes(venda_id: int) -> Venda | None:
    return (
        Venda.objects.select_related("filial", "cliente", "veiculo")
        .filter(pk=venda_id, origem="balcao")
        .first()
    )


def _valores_por_id(venda_id: int) -> dict[str, str] | None:
    venda = _com_relacoes(venda_id)
    return valores(venda) if venda else None


def registrar() -> None:
    """A prévia do modelo de compra e venda com dados reais lê por aqui (no `ready()`)."""
    origens.registrar(ORIGEM, _valores_por_id)


def gerar(venda: Venda) -> Contrato:
    """O contrato com o modelo publicado de compra e venda: 422 `IMP-04` sem ele. O PDF e o
    envio saem depois do commit, como na retirada."""
    if venda.cliente_id is None:
        raise ValueError(f"{venda.codigo} sem cliente.")
    completa = _com_relacoes(venda.pk) or venda
    return contratos.gerar(
        contratos.DadosDoContrato(
            origem_tipo=ORIGEM,
            origem_id=completa.pk,
            origem_codigo=completa.codigo,
            filial_id=completa.filial_id,
            cliente_id=venda.cliente_id,
            valores=valores(completa),
            finalidade=Finalidade.VENDA,
        )
    )


def vigente(venda: Venda) -> Contrato | None:
    return contratos_selectors.contrato_vigente(ORIGEM, venda.pk)
