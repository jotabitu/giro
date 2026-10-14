"""Financeiro da Moto Rápida em 07 out 2026 (T-019): o que depende da T-017.

Roda depois da carteira, pelos serviços de domínio: preço do litro da Filial Centro, vistoria de
saída da LOC-2836, caução paga da LOC-2841, LOC-2812 e LOC-2856, o caixa de 07 out (caso "Caixa de
07 out", `FIN-07`) e as 6 despesas de outubro (`FIN-05`). O caixa fica aberto, como na tela.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from apps.aprovacoes import services as aprovacoes
from apps.aprovacoes.models import PedidoAprovacao
from apps.contas.models import Usuario
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro
from apps.financeiro.models import Caixa, ContaReceber, Despesa
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo
from apps.vistorias import services as vistorias
from apps.vistorias.models import Vistoria
from comum import relogio as relogio_do_giro

from .ator import como
from .relogio import RelogioDoSeed

FUSO = ZoneInfo("America/Sao_Paulo")
PRECO_DO_LITRO_CENTAVOS = 550  # DEV-01: "preço da bomba" da Filial Centro (R$ 5,50)
CAUCOES = {"LOC-2841": 30000, "LOC-2812": 50000}  # Street e Scooter premium (tabela de preços)


def _caucao_paga(locacao: Locacao, valor: int, quando: datetime) -> ContaReceber:
    """Caução já paga na retirada (`LOC-04`), gravada como a carteira grava as parcelas."""
    Locacao.objects.filter(pk=locacao.pk).update(caucao_centavos=valor)
    return ContaReceber.objects.create(
        filial=locacao.filial,
        cliente=locacao.cliente,
        origem_tipo="locacao",
        origem_id=locacao.pk,
        origem_codigo=locacao.codigo,
        tipo="caucao",
        vencimento=locacao.inicio.date(),
        valor_centavos=valor,
        status="paga",
        forma="pix",
        pago_em=quando,
    )


def _saida(locacao: Locacao, quando: datetime) -> None:
    """Vistoria de saída concluída: tanque cheio, no km do veículo (DEV-08)."""
    veiculo = Veiculo.objects.select_related("categoria").get(pk=locacao.veiculo_id)
    Vistoria.objects.create(
        locacao=locacao,
        veiculo=veiculo,
        tipo="saida",
        status="concluida",
        km=locacao.km_saida,
        combustivel="cheio",
        itens=[{**i, "ok": True} for i in vistorias.itens_iniciais(locacao, veiculo)],
        concluida_em=quando,
    )


def _entrada(caixa: Caixa, conta: ContaReceber, forma: str, usuario: Usuario | None) -> None:
    """Liga uma conta já paga (da carteira) ao movimento de entrada do caixa de 07 out."""
    movimento = financeiro._registrar_movimento(
        caixa,
        tipo="entrada",
        forma=forma,
        valor_centavos=conta.valor_centavos,
        descricao=financeiro.descricao_da_conta(conta),
        usuario=usuario.pk if usuario else None,
        origem=financeiro.Origem(conta.origem_tipo, conta.origem_id, conta.origem_codigo),
    )
    ContaReceber.objects.filter(pk=conta.pk).update(
        movimento_caixa=movimento, forma=forma, pago_em=relogio_do_giro.agora()
    )


def _conta(codigo: str, vencimento: str) -> ContaReceber:
    conta: ContaReceber = ContaReceber.objects.select_related("cliente").get(
        origem_codigo=codigo, tipo="parcela", vencimento=date.fromisoformat(vencimento)
    )
    return conta


def _caixa_de_07_out(centro: Filial, bruna: Usuario, relogio: RelogioDoSeed) -> None:
    relogio.em("2026-10-07 07:55")
    with como(bruna):
        caixa = financeiro.abrir_caixa(centro, bruna, 20000)
    relogio.em("2026-10-07 08:02")
    _entrada(caixa, _conta("LOC-2836", "2026-10-07"), "pix", None)  # webhook: "Sistema"
    relogio.em("2026-10-07 08:40")
    with como(bruna):
        _entrada(caixa, _conta("LOC-2848", "2026-10-07"), "cartao_credito", bruna)
    relogio.em("2026-10-07 09:15")
    lucas = Locacao.objects.get(codigo="LOC-2856")
    with como(bruna):
        _entrada(caixa, _conta("LOC-2856", "2026-10-07"), "dinheiro", bruna)
        _entrada(caixa, _caucao_paga(lucas, 30000, relogio.agora), "dinheiro", bruna)
    relogio.em("2026-10-07 10:30")
    with como(bruna):
        financeiro.sangria(caixa, bruna, valor_centavos=50000, descricao="Depósito no banco")
    relogio.em("2026-10-07 11:05")
    _entrada(caixa, _conta("LOC-2826", "2026-10-07"), "pix", None)
    relogio.em("2026-10-07 11:20")
    with como(bruna):
        financeiro.lancar_despesa(
            filial=centro,
            usuario=bruna,
            descricao="Óleo 1 litro",
            valor_centavos=4800,
            data=date(2026, 10, 7),
            vencimento=date(2026, 10, 7),
            categoria="manutencao",
            veiculo_id=Veiculo.objects.get(placa="QXA4B21").pk,
            pago_no_caixa=True,
        )


def _despesas_de_outubro(centro: Filial, pessoas: dict[str, Usuario], relogio: Any) -> None:
    """As outras 5 despesas da tabela (CA-019-23), cada uma no dia dela: só os pneus (acima de
    R$ 500) ficam aguardando o gerente; aluguel e rastreadores foram aprovados pelo Rodrigo e
    pagos no dia (boleto e cartão)."""
    lucia, joao = pessoas["Lúcia Freitas"], pessoas["João Silva"]
    rodrigo = pessoas["Rodrigo Pinheiro"]

    def lancar(
        quem: Usuario, descricao: str, valor: int, dia: str, vence: str, categoria: str, **mais: Any
    ) -> Despesa:
        relogio.em(f"{dia} 09:00")
        with como(quem):
            return financeiro.lancar_despesa(
                filial=centro,
                usuario=quem,
                descricao=descricao,
                valor_centavos=valor,
                data=date.fromisoformat(dia),
                vencimento=date.fromisoformat(vence),
                categoria=categoria,
                **mais,
            )

    def aprovar_e_pagar(despesa: Despesa, forma: str) -> None:
        despesa.refresh_from_db()
        pedido = PedidoAprovacao.objects.get(pk=despesa.pedido_aprovacao_id or 0)
        relogio.em(f"{despesa.data.isoformat()} 10:00")
        with como(rodrigo):
            aprovacoes.aprovar(pedido, rodrigo)
        despesa.refresh_from_db()
        relogio.em(f"{despesa.data.isoformat()} 11:00")
        with como(lucia):
            financeiro.pagar_despesa(despesa, lucia, forma=forma, pago_em=relogio.agora)

    pmz = Veiculo.objects.get(placa="PMZ3E17").pk
    rastreadores = lancar(
        lucia, "Rastreadores (86)", 172000, "2026-10-02", "2026-10-02", "rastreamento"
    )
    aprovar_e_pagar(rastreadores, "cartao")
    lancar(lucia, "IPVA ROE2A88", 18640, "2026-10-03", "2026-10-31", "impostos")
    aluguel = lancar(lucia, "Aluguel do ponto", 350000, "2026-10-05", "2026-10-05", "fixas")
    aprovar_e_pagar(aluguel, "boleto")
    lancar(lucia, "Conta de luz", 41230, "2026-10-06", "2026-10-10", "fixas")
    lancar(joao, "Pneus (2)", 120000, "2026-10-07", "2026-10-07", "manutencao", veiculo_id=pmz)


def _pedido_de_encerramento_da_loc_2812(pessoas: dict[str, Usuario], relogio: Any) -> None:
    """Bruna pede em 07 out o encerramento antecipado da Patrícia: `APR-02` pendente para o
    Rodrigo, sinal `cancelamento_pendente` (CA-019-17)."""
    relogio.em("2026-10-07 09:30")
    bruna = pessoas["Bruna Alves"]
    with como(bruna):
        locacoes_services.cancelar(
            Locacao.objects.get(codigo="LOC-2812"), bruna, motivo="Cliente vai mudar de cidade"
        )


def carregar(centro: Filial, pessoas: dict[str, Usuario], relogio: RelogioDoSeed) -> None:
    relogio.em("2026-10-01 09:00")
    filiais_services.editar_filial(centro, {"preco_litro_centavos": PRECO_DO_LITRO_CENTAVOS})
    _saida(Locacao.objects.get(codigo="LOC-2836"), datetime(2026, 10, 1, 9, 10, tzinfo=FUSO))
    relogio.em("2026-10-07 07:00")
    for codigo, valor in CAUCOES.items():
        locacao = Locacao.objects.get(codigo=codigo)
        _caucao_paga(locacao, valor, locacao.inicio)
        _saida(locacao, locacao.inicio)
    carlos = Locacao.objects.get(codigo="LOC-2841")
    Locacao.objects.filter(pk=carlos.pk).update(periodos=5)  # 5 semanas, de 23 set a 28 out
    # O km do QXA-4B21 é o lido na vistoria de saída de 23 set (CA-019-10).
    Veiculo.objects.filter(pk=carlos.veiculo_id).update(
        km_atualizado_em=datetime(2026, 9, 23, 9, 0, tzinfo=FUSO)
    )
    _despesas_de_outubro(centro, pessoas, relogio)
    _caixa_de_07_out(centro, pessoas["Bruna Alves"], relogio)
    _pedido_de_encerramento_da_loc_2812(pessoas, relogio)
    relogio.em("2026-10-07 12:00")
