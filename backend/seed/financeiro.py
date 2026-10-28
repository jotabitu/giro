"""Financeiro da Moto Rápida em 07 out 2026 (T-019): o que depende da T-017.

Roda depois da carteira, pelos serviços de domínio: preço do litro da Filial Centro, vistoria de
saída da LOC-2836, caução paga da LOC-2841, LOC-2812 e LOC-2856, o caixa de 07 out (caso "Caixa de
07 out", `FIN-07`) e as 6 despesas de outubro (`FIN-05`), cada uma com a nota (`FIN-06`, um PDF
pequeno de exemplo). O caixa fica aberto, como na tela.
"""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.core.files.base import ContentFile

from apps.aprovacoes import services as aprovacoes
from apps.aprovacoes.models import PedidoAprovacao
from apps.contas.models import Usuario
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import (
    Caixa,
    CobrancaExterna,
    ContaReceber,
    Despesa,
    PendenciaPagamento,
    Reembolso,
)
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
# Nota de exemplo das despesas (FIN-06): um PDF de uma página em branco.
PDF_DA_NOTA = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _nota() -> "ContentFile[bytes]":
    return ContentFile(PDF_DA_NOTA, name="nota.pdf")


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
            nota=_nota(),
            pago_no_caixa=True,
        )


def _despesas_de_outubro(centro: Filial, pessoas: dict[str, Usuario], relogio: Any) -> None:
    """As outras 5 despesas da tabela (CA-019-23), cada uma no dia dela: só os pneus (acima de
    R$ 500) ficam aguardando o gerente; aluguel e rastreadores foram aprovados pelo Rodrigo e
    pagos no dia (boleto e cartão)."""
    lucia, joao = pessoas["Lúcia Freitas"], pessoas["João Silva"]
    rodrigo = pessoas["Rodrigo Pinheiro"]

    def lancar(
        quem: Usuario,
        descricao: str,
        valor: int,
        dia: str,
        vence: str,
        categoria: str,
        hora: str = "09:00",
        **mais: Any,
    ) -> Despesa:
        relogio.em(f"{dia} {hora}")
        with como(quem):
            return financeiro.lancar_despesa(
                filial=centro,
                usuario=quem,
                descricao=descricao,
                valor_centavos=valor,
                data=date.fromisoformat(dia),
                vencimento=date.fromisoformat(vence),
                categoria=categoria,
                nota=_nota(),
                **mais,
            )

    def aprovar_e_pagar(despesa: Despesa, forma: str, aprovada: str, paga: str) -> None:
        despesa.refresh_from_db()
        pedido = PedidoAprovacao.objects.get(pk=despesa.pedido_aprovacao_id or 0)
        relogio.em(f"{despesa.data.isoformat()} {aprovada}")
        with como(rodrigo):
            aprovacoes.aprovar(pedido, rodrigo)
        despesa.refresh_from_db()
        relogio.em(f"{despesa.data.isoformat()} {paga}")
        with como(lucia):
            financeiro.pagar_despesa(despesa, lucia, forma=forma, pago_em=relogio.agora)

    pmz = Veiculo.objects.get(placa="PMZ3E17").pk
    # Horas do caso "Números da tela Aprovações em 07 out" (APR-12): 40 min e 2 h 20 min.
    rastreadores = lancar(
        lucia, "Rastreadores (86)", 172000, "2026-10-02", "2026-10-02", "rastreamento", "10:00"
    )
    aprovar_e_pagar(rastreadores, "cartao", "12:20", "12:30")
    lancar(lucia, "IPVA ROE2A88", 18640, "2026-10-03", "2026-10-31", "impostos")
    aluguel = lancar(
        lucia, "Aluguel do ponto", 350000, "2026-10-05", "2026-10-05", "fixas", "08:30"
    )
    aprovar_e_pagar(aluguel, "boleto", "09:10", "09:30")
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


def garantir_reembolso_e_pendencia(centro: Filial, relogio: RelogioDoSeed) -> bool:
    """Um reembolso a fazer e uma pendência do pagamento aberta, para as telas `Reembolsos` e
    `Pendências do pagamento` (T-375), sem mexer nos casos de referência.

    - Reembolso: Patrícia (LOC-2812), Pix de R$ 286,20 = 1 semana inteira R$ 371,00 menos a multa
      R$ 84,80 (`LOC-13`, `DEV-02`). Fica `a_fazer`; o pedido de encerramento da locação segue
      pendente para o Rodrigo (`APR-02`), então o estado da locação não muda.
    - Pendência: Carlos (LOC-2841), parcela 2 de 30 set. O Pix gerado em 07 out era de R$ 306,09
      (299,40 + multa 5,99 + juros 0,70, `FIN-03`) e o parceiro avisou R$ 299,40: `valor_diferente`
      (`AUT-05`). A conta segue aberta e atrasada: o "em aberto" de Carlos continua R$ 299,40.

    Gravados direto, como as cobranças de teste da T-380: o caminho pelos serviços avisaria o
    financeiro no sino e moveria os contadores que o seed já fixa."""
    relogio.em("2026-10-07 11:00")
    patricia = Locacao.objects.select_related("cliente").get(codigo="LOC-2812")
    _, reembolso_novo = Reembolso.objects.get_or_create(
        origem_tipo="locacao",
        origem_id=patricia.pk,
        origem_codigo=patricia.codigo,
        defaults={
            "filial": centro,
            "cliente": patricia.cliente,
            "valor_centavos": 28620,
            "forma": "pix",
            "motivo": "Cancelamento: 1 semana inteira R$ 371,00 menos multa R$ 84,80",
        },
    )
    conta = _conta("LOC-2841", "2026-09-30")
    hoje = relogio_do_giro.hoje()
    devido = financeiro_selectors.valor_hoje(conta, hoje)["total_centavos"]
    cobranca, _ = CobrancaExterna.objects.get_or_create(
        externo_id="pay_88192",
        defaults={
            "conta_receber": conta,
            "tipo": "pix",
            "valor_centavos": devido,
            "vence_em": date(2026, 10, 8),
            "gerada_no_dia": hoje,
            "status": "divergente",
        },
    )
    _, pendencia_nova = PendenciaPagamento.objects.get_or_create(
        cobranca=cobranca,
        defaults={"motivo": "valor_diferente", "valor_pago_centavos": conta.valor_centavos},
    )
    return reembolso_novo or pendencia_nova
