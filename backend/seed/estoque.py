"""Estoque à venda parado da Moto Rápida (T-499): os casos das T-486 e T-487 de
`docs/regras/dados-de-teste.md` ("Dias em estoque em 07 out" e "Estoque à venda em 07 out").

Três veículos da Filial Centro postos à venda em 15 ago, 06 set e 07 set de 2026, pelo serviço de
domínio com o relógio do seed nessas datas (`VEI-18`), com valor de compra, valor de venda e as
despesas ligadas ao veículo (`FIN-17`). Os outros 9 `a_venda` do seed entram em 07 out às 07:00,
na montagem da frota. As vendas concluídas de setembro e outubro (`VEN-12`) ficam fora: ainda não
há fluxo de venda (`VEN-01` a `VEN-09`).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from apps.aprovacoes import services as aprovacoes
from apps.aprovacoes.models import PedidoAprovacao
from apps.contas.models import Usuario
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro
from apps.plataforma.models import Empresa
from apps.plataforma.services import recalcular_uso
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Categoria, Veiculo

from .ator import administradora, como
from .financeiro import _nota
from .frota import cadastrar_veiculo
from .relogio import RelogioDoSeed


@dataclass(frozen=True)
class Parado:
    placa: str
    categoria: str
    marca: str
    modelo: str
    chassi: str
    cor: str
    km: int
    entrada_em: str  # dia em que o veículo vai à venda (VEI-18)
    compra_em: str
    compra_centavos: int
    venda_centavos: int
    # (descrição, valor, dia) das despesas ligadas ao veículo que contam no custo.
    despesas: tuple[tuple[str, int, str], ...] = ()


URBANA = "Urbana 110–125"
STREET = "Street 150–160"

PARADOS: tuple[Parado, ...] = (
    Parado(
        "PVE1A07",
        URBANA,
        "Honda",
        "Biz 125",
        "9C2JC4810PR200107",
        "vermelha",
        9120,
        "2026-08-15",
        "2026-08-03",
        1120000,
        1290000,
        (("Revisão e pneu traseiro", 45000, "2026-08-10"),),
    ),
    Parado(
        "PVF2B18",
        STREET,
        "Honda",
        "CG 160 Fan",
        "9C2KC2210PR200218",
        "preta",
        12480,
        "2026-09-06",
        "2026-08-28",
        1390000,
        1550000,
    ),
    Parado(
        "PVG3C29",
        STREET,
        "Yamaha",
        "Factor 150",
        "9C6RG3110PR200329",
        "azul",
        15360,
        "2026-09-07",
        "2026-08-25",
        1280000,
        1320000,
        (
            ("Troca de kit de transmissão", 50000, "2026-08-27"),
            ("Pintura do tanque", 40000, "2026-08-29"),
            ("Revisão geral", 25000, "2026-08-30"),
        ),
    ),
)
# Despesa que o gerente recusou no PVG-3C29 e que não entra no custo (`VEI-20`).
RECUSADA = ("PVG3C29", "Carenagem lateral", 30000, "2026-08-31")
# A partir daqui, só o que o seed usa para gerar os números dos veículos extras (placa e chassi
# vêm da tabela acima; o número só serve ao km e à cor padrão).
NUMERO_BASE = 900


def _lancar_e_pagar(
    veiculo: Veiculo,
    quem: Usuario,
    pagador: Usuario,
    centro: Filial,
    relogio: RelogioDoSeed,
    descricao: str,
    valor: int,
    dia: str,
) -> None:
    """Despesa ligada ao veículo (`FIN-17`). Até R$ 500,00 nasce `a_pagar`; o financeiro paga no
    dia, pelo boleto, e a despesa não fica pendente nas telas de outubro."""
    relogio.em(f"{dia} 09:00")
    with como(quem):
        despesa = financeiro.lancar_despesa(
            filial=centro,
            usuario=quem,
            descricao=descricao,
            valor_centavos=valor,
            data=date.fromisoformat(dia),
            vencimento=date.fromisoformat(dia),
            categoria="manutencao",
            veiculo_id=veiculo.pk,
            nota=_nota(),
        )
    relogio.em(f"{dia} 15:00")
    with como(pagador):
        financeiro.pagar_despesa(despesa, pagador, forma="boleto", pago_em=relogio.agora)


def _despesa_recusada(
    veiculo: Veiculo,
    lucia: Usuario,
    rodrigo: Usuario,
    centro: Filial,
    relogio: RelogioDoSeed,
) -> None:
    """A despesa de R$ 300,00 que o gerente recusou. A recusa só existe para quem passou pelo
    pedido de aprovação (`APR-03`, acima do limite sem aprovação); o seed baixa o limite só pelo
    tempo do lançamento, para o pedido nascer, e o gerente recusa pelo serviço, com o motivo."""
    _, descricao, valor, dia = RECUSADA
    relogio.em(f"{dia} 09:00")
    limite = financeiro.LIMITE_SEM_APROVACAO
    financeiro.LIMITE_SEM_APROVACAO = 0
    try:
        with como(lucia):
            despesa = financeiro.lancar_despesa(
                filial=centro,
                usuario=lucia,
                descricao=descricao,
                valor_centavos=valor,
                data=date.fromisoformat(dia),
                vencimento=date.fromisoformat(dia),
                categoria="manutencao",
                veiculo_id=veiculo.pk,
                nota=_nota(),
            )
    finally:
        financeiro.LIMITE_SEM_APROVACAO = limite
    despesa.refresh_from_db()
    pedido = PedidoAprovacao.objects.get(pk=despesa.pedido_aprovacao_id or 0)
    relogio.em(f"{dia} 11:00")
    with como(rodrigo):
        aprovacoes.recusar(pedido, rodrigo, "Peça já coberta pela garantia da revenda.")


def garantir_estoque_parado(
    empresa: Empresa,
    centro: Filial,
    categorias: dict[str, Categoria],
    pessoas: dict[str, Usuario],
    relogio: RelogioDoSeed,
) -> bool:
    """Põe à venda PVE-1A07, PVF-2B18 e PVG-3C29 com as despesas dos casos das T-486 e T-487.
    Idempotente: quem já existe fica como está. Devolve se criou algo."""
    lucia, rodrigo = pessoas["Lúcia Freitas"], pessoas["Rodrigo Pinheiro"]
    criou = False
    for posicao, dados in enumerate(PARADOS):
        if Veiculo.objects.filter(placa=dados.placa).exists():
            continue
        criou = True
        extras: dict[str, Any] = {}
        if dados.categoria == STREET:
            extras["capacidade_tanque_litros"] = Decimal("16.0")
        relogio.em(f"{dados.compra_em} 09:00")
        veiculo = cadastrar_veiculo(
            NUMERO_BASE + posicao,
            categorias[dados.categoria],
            centro,
            "disponivel",
            placa=dados.placa,
            chassi=dados.chassi,
            marca=dados.marca,
            modelo=dados.modelo,
            ano_fabricacao=2023,
            ano_modelo=2023,
            cor=dados.cor,
            km_atual=dados.km,
            valor_compra_centavos=dados.compra_centavos,
            data_compra=date.fromisoformat(dados.compra_em),
            entrou_na_frota_em=date.fromisoformat(dados.compra_em),
            **extras,
        )
        for descricao, valor, dia in dados.despesas:
            _lancar_e_pagar(veiculo, lucia, lucia, centro, relogio, descricao, valor, dia)
        if dados.placa == RECUSADA[0]:
            _despesa_recusada(veiculo, lucia, rodrigo, centro, relogio)
        relogio.em(f"{dados.entrada_em} 10:00")
        with como(administradora()):
            veiculos_services.colocar_a_venda(veiculo, dados.venda_centavos)
    if criou:
        recalcular_uso(empresa)
        relogio.em("2026-10-07 10:00")
    return criou
