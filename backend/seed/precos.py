"""Preços por veículo da Moto Rápida (T-495, ADR 0041): os casos de `docs/regras/dados-de-teste.md`
"Locação com compra da Pop 110i TBC-5H21" e "Locação com compra da CG QXA-4B21".

- **TBC-5H21**, Honda Pop 110i, Urbana, Filial Centro, `disponivel`: compra R$ 13.490,00 e
  R$ 310,00 de despesas ligadas (pago na moto R$ 13.800,00, `VEI-13`), venda R$ 15.900,00 e a
  locação com compra ligada: semanal, 104 parcelas, entrada R$ 1.000,00, juros de 1,00% ao mês,
  modo calcular e R$ 29,77 de adicional por semana (R$ 129,00 por mês) → parcela da moto
  R$ 161,24 e do cliente R$ 191,01 (`VEI-16`, `LOC-16`). Os planos de aluguel são os da tabela da
  Urbana. Ocupa o lugar de uma Urbana genérica disponível (`frota.SUBSTITUIDOS_PELA_COMPRA`): a
  frota segue com 86 veículos.
- **QXA-4B21**, a CG 160 da LOC-2841: venda R$ 12.480,00, pago na moto R$ 13.900,00 (a compra de
  R$ 13.852,00 mais o óleo de R$ 48,00 de outubro, `FIN-17`) e a locação com compra desligada:
  semanal, 104 parcelas, sem entrada, juros de 1,00% ao mês → parcela R$ 135,05, recebe no
  contrato R$ 14.045,20, lucro R$ 145,20 e o alerta da venda abaixo do pago (`VEI-16`).

Tudo pelos serviços de domínio (`cadastrar`, `lancar_despesa`, `salvar_precos`), como a Mariana
faria na tela de preços. A caução da compra da Pop é a da Urbana (R$ 300,00), o valor que a
migração daria (ADR 0041, item 3, passo 4); a do QXA-4B21, que não tem compra ligada, fica R$ 0,00.
Idempotente: o veículo que já tem plano de compra fica como está.
"""

from datetime import date
from typing import Any

from apps.contas.models import Usuario
from apps.filiais.models import Filial
from apps.plataforma.models import Empresa
from apps.plataforma.services import recalcular_uso
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import PlanoCompraVeiculo, Veiculo

from .ator import administradora, como
from .estoque import _lancar_e_pagar
from .frota import PRECOS_SEED, cadastrar_veiculo
from .relogio import RelogioDoSeed

URBANA = "Urbana 110–125"
POP = "TBC5H21"
QXA = "QXA4B21"
NUMERO_DA_POP = 950  # só para o km e a cor padrão; placa e chassi vêm daqui
POP_COMPRA_EM = "2026-07-20"
POP_DESPESA = ("Revisão e kit de relação", 31000, "2026-08-12")
QXA_COMPRA_CENTAVOS = 1385200  # + óleo de R$ 48,00 (07 out) = pago na moto R$ 13.900,00

COMPRA_DA_POP: dict[str, Any] = {
    "ligado": True,
    "periodicidade": "semanal",
    "parcelas": 104,
    "entrada_centavos": 100000,
    "juros_mes_pct": "1.00",
    "modo": "calcular",
    "adicional_centavos": 2977,
    "caucao_centavos": 30000,
}
COMPRA_DO_QXA: dict[str, Any] = {
    "ligado": False,
    "periodicidade": "semanal",
    "parcelas": 104,
    "entrada_centavos": 0,
    "juros_mes_pct": "1.00",
    "modo": "calcular",
    "adicional_centavos": 0,
    "caucao_centavos": 0,
}


def _planos_da_tabela(categoria: str) -> list[dict[str, Any]]:
    """Os planos diária, semanal e mensal ligados, com os valores da tabela do seed."""
    _, diaria, semanal, mensal, caucao = PRECOS_SEED[categoria]
    return [
        {
            "tipo": tipo,
            "valor_centavos": valor,
            "caucao_centavos": caucao,
            "ligado": True,
            "agendado": None,
        }
        for tipo, valor in (("diaria", diaria), ("semanal", semanal), ("mensal", mensal))
    ]


def _pop(centro: Filial, lucia: Usuario, relogio: RelogioDoSeed) -> bool:
    if Veiculo.objects.filter(placa=POP).exists():
        return False
    relogio.em(f"{POP_COMPRA_EM} 09:00")
    pop = cadastrar_veiculo(
        NUMERO_DA_POP,
        URBANA,
        centro,
        "disponivel",
        com_precos=False,
        placa=POP,
        chassi="9C2JC7110RR000950",
        marca="Honda",
        modelo="Pop 110i",
        ano_fabricacao=2024,
        ano_modelo=2024,
        cor="branca",
        km_atual=6420,
        valor_compra_centavos=1349000,
        data_compra=date.fromisoformat(POP_COMPRA_EM),
        entrou_na_frota_em=date.fromisoformat(POP_COMPRA_EM),
    )
    descricao, valor, dia = POP_DESPESA
    _lancar_e_pagar(pop, lucia, lucia, centro, relogio, descricao, valor, dia)
    # A tabela da Urbana vale desde 01 out: a Mariana preenche os preços da moto em 07 out.
    relogio.em("2026-10-07 07:30")
    with como(administradora()):
        veiculos_services.salvar_precos(
            pop,
            {
                "valor_venda_centavos": 1590000,
                "planos": _planos_da_tabela(URBANA),
                "custos": {"revenda_estimada_centavos": 890000},
                "plano_compra": COMPRA_DA_POP,
            },
        )
    return True


def _qxa(relogio: RelogioDoSeed) -> bool:
    qxa = Veiculo.objects.filter(placa=QXA).first()
    if qxa is None or PlanoCompraVeiculo.objects.filter(veiculo=qxa).exists():
        return False
    relogio.em("2026-10-07 07:30")
    with como(administradora()):
        if qxa.valor_compra_centavos is None:
            veiculos_services.editar(qxa, {"valor_compra_centavos": QXA_COMPRA_CENTAVOS})
        veiculos_services.salvar_precos(
            qxa, {"valor_venda_centavos": 1248000, "plano_compra": COMPRA_DO_QXA}
        )
    return True


def garantir_precos_dos_veiculos(
    empresa: Empresa,
    centro: Filial,
    pessoas: dict[str, Usuario],
    relogio: RelogioDoSeed,
) -> bool:
    """A Pop TBC-5H21 com a locação com compra ligada e o plano de compra do QXA-4B21 (T-495).
    Devolve se criou algo."""
    criou = _pop(centro, pessoas["Lúcia Freitas"], relogio)
    criou = _qxa(relogio) or criou
    if criou:
        recalcular_uso(empresa)
        relogio.em("2026-10-07 10:00")
    return criou
