"""Frota e tabela de preços da Moto Rápida (seed de T-013): seed de desenvolvimento e testes.

86 veículos na Filial Centro, nos 4 grupos da tabela (42/32/6/6), com as contagens de
`CONTAGENS_FROTA_SEED` e os alugados na proporção da carteira de outubro (Urbana 20, Street 16,
Scooter 3, Carro 3; `docs/qa/carteira-outubro/`). Os veículos citados nos critérios têm os dados
do seed; os outros levam placa e chassi gerados.

Sem categorias (ADR 0043): o grupo da tabela (Urbana, Street, Scooter, Carro) só organiza o seed.
Cada veículo nasce com o tipo (`tipo_veiculo`) e recebe os planos do grupo pela tela de preços
(`salvar_precos`, ADR 0041), com os mesmos valores de sempre (`dados-de-teste.md`).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from apps.filiais.models import Filial
from apps.plataforma.services import recalcular_uso
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo

from .ator import administradora, como
from .relogio import RelogioDoSeed

# Tabela de preços da Filial Centro (T-013), por grupo da tabela:
# grupo → (veículos, diária, semanal, mensal, caução).
PRECOS_SEED = {
    "Urbana 110–125": (42, 4490, 29940, 109000, 30000),
    "Street 150–160": (32, 5490, 32900, 119000, 30000),
    "Scooter premium": (6, 7990, 44900, 159000, 50000),
    "Carro compacto": (6, 10900, 64900, 229000, 80000),
}
ORIGEM = veiculos_services.OrigemDaMudanca("seed", 0, "seed")

VIGENTE_DESDE = date(2026, 10, 1)
STREET_ANTES = date(2026, 9, 1)  # até 30 set, semanal 29940 (LOC-15, LOC-2841)
STREET_SEMANAL_ANTES = 29940

# grupo → (tipo do veículo, modelos [(marca, modelo)], {status: quantos}).
DISTRIBUICAO: dict[str, tuple[str, list[tuple[str, str]], dict[str, int]]] = {
    "Urbana 110–125": (
        "moto",
        [("Honda", "Pop 110i"), ("Honda", "Biz 125")],
        {"disponivel": 8, "reservado": 4, "alugado": 20, "em_manutencao": 4, "a_venda": 6},
    ),
    "Street 150–160": (
        "moto",
        [("Honda", "CG 160 Fan"), ("Yamaha", "Factor 150")],
        {"disponivel": 6, "reservado": 3, "alugado": 16, "em_manutencao": 2, "a_venda": 5},
    ),
    "Scooter premium": (
        "moto",
        [("Yamaha", "NMax 160")],
        {"disponivel": 1, "reservado": 1, "alugado": 3, "a_venda": 1},
    ),
    "Carro compacto": (
        "carro",
        [("Renault", "Kwid"), ("Fiat", "Mobi")],
        {"disponivel": 1, "reservado": 1, "alugado": 3, "em_manutencao": 1},
    ),
}

# Os veículos citados nos critérios (docs/qa/criterios/T-013.md).
NOMEADOS: dict[str, dict[str, Any]] = {
    "SAK1D39": {
        "categoria": "Street 150–160",
        "status": "disponivel",
        "chassi": "9C2KC2210RR004417",
        "renavam": "01289934410",
        "marca": "Honda",
        "modelo": "CG 160 Fan",
        "ano_fabricacao": 2025,
        "ano_modelo": 2025,
        "cor": "vermelha",
        "km_atual": 3120,
        "capacidade_tanque_litros": Decimal("16.0"),
        "valor_compra_centavos": 1390000,
        "data_compra": date(2025, 3, 10),
        "entrou_na_frota_em": date(2025, 3, 12),
    },
    "QXA4B21": {
        "categoria": "Street 150–160",
        "status": "alugado",  # LOC-2841, Carlos Menezes
        "chassi": "9C2KC2210PR004401",
        "marca": "Honda",
        "modelo": "CG 160 Fan",
        "ano_fabricacao": 2023,
        "ano_modelo": 2023,
        "cor": "vermelha",
        "km_atual": 18950,
        # "Dados do CRLV-e do QXA-4B21" (VEI-09, T-421), fictícios. Os outros 85 ficam sem.
        "combustivel": "flex",
        "documento": {
            "potencia_cv": 15,
            "cilindrada_cc": 162,
            "especie": "passageiro",
            "tipo": "Motocicleta",
            "carroceria": None,
            "lotacao": 2,
            "peso_bruto_kg": 290,
            "numero_motor": "KC22E1P004401",
            "observacoes": "ALIENACAO FIDUCIARIA",
        },
        "rastreador": {"numero": "356938035643809", "empresa": "Rastreia Fácil"},
        "anotacoes": "Risco no tanque, lado esquerdo",
    },
    "PNB7C04": {
        "categoria": "Street 150–160",
        "status": "alugado",  # LOC-2836, Juliana Rocha
        "chassi": "9C6RG3110PR003302",
        "marca": "Yamaha",
        "modelo": "Factor 150",
        "ano_fabricacao": 2023,
        "ano_modelo": 2023,
        "cor": "preta",
        "km_atual": 21870,
        "capacidade_tanque_litros": Decimal("16.0"),
    },
    "PMZ3E17": {
        "categoria": "Urbana 110–125",
        "status": "em_manutencao",
        "chassi": "9C2JC7510RR110233",
        "marca": "Honda",
        "modelo": "Pop 110i",
        "ano_fabricacao": 2024,
        "ano_modelo": 2024,
        "cor": "branca",
        "km_atual": 9884,
    },
    "RHT9F02": {
        "categoria": "Carro compacto",
        "status": "reservado",
        "chassi": "93YRBB005NJ441907",
        "marca": "Renault",
        "modelo": "Kwid",
        "ano_fabricacao": 2022,
        "ano_modelo": 2022,
        "cor": "cinza",
        "km_atual": 52310,
    },
}


# Tanque por categoria (litros): a CG 160 e a Factor levam 16 L; a NMax, 8 L (DEV-01, troca da
# LOC-2836).
TANQUE = {"Street 150–160": Decimal("16.0"), "Scooter premium": Decimal("8.0")}

# Só no seed de conferência (T-138): os veículos das locações das telas, com as placas delas. O
# SAK1D39 fica alugado (LOC-2856, Lucas). Os testes de aceitação usam `NOMEADOS` como estava.
NOMEADOS_DA_CONFERENCIA: dict[str, dict[str, Any]] = {
    **NOMEADOS,
    "SAK1D39": {**NOMEADOS["SAK1D39"], "status": "alugado"},
    "PQD6E21": {
        "categoria": "Urbana 110–125",
        "status": "alugado",  # LOC-2790, Rafael Sousa
        "chassi": "9C2JC7510PR100621",
        "marca": "Honda",
        "modelo": "Pop 110i",
        "ano_fabricacao": 2023,
        "ano_modelo": 2023,
        "cor": "preta",
        "km_atual": 24380,
    },
    "RJD5B38": {
        "categoria": "Urbana 110–125",
        "status": "alugado",  # LOC-2850, Marcos Viana
        "chassi": "9C2JC4810PR103875",
        "marca": "Honda",
        "modelo": "Biz 125",
        "ano_fabricacao": 2024,
        "ano_modelo": 2024,
        "cor": "vermelha",
        "km_atual": 11260,
    },
    "SBC0J44": {
        "categoria": "Scooter premium",
        "status": "alugado",  # LOC-2812, Patrícia Gomes
        "chassi": "9C6SG5010PR004404",
        "marca": "Yamaha",
        "modelo": "NMax 160",
        "ano_fabricacao": 2024,
        "ano_modelo": 2024,
        "cor": "azul",
        "km_atual": 8740,
        "capacidade_tanque_litros": Decimal("8.0"),
    },
    "RKP3D26": {
        "categoria": "Carro compacto",
        "status": "alugado",  # LOC-2848, Diego Martins
        "chassi": "93YRBB005PJ226126",
        "marca": "Renault",
        "modelo": "Kwid",
        "ano_fabricacao": 2023,
        "ano_modelo": 2023,
        "cor": "branca",
        "km_atual": 33470,
    },
}

# `a_venda` genéricos que dão lugar aos veículos do estoque parado (T-499): a frota segue com 86
# veículos e 12 à venda (9 genéricos, colocados à venda em 07 out, e os 3 de `seed/estoque.py`).
SUBSTITUIDOS_PELO_ESTOQUE_PARADO = {"Urbana 110–125": 1, "Street 150–160": 2}
# `disponivel` genérico que dá lugar à Pop TBC-5H21 da locação com compra (T-495,
# `seed/precos.py`): a frota segue com 86 veículos.
SUBSTITUIDOS_PELA_COMPRA = {"Urbana 110–125": 1}

CORES = ("preta", "vermelha", "branca", "azul", "prata", "cinza")
ANOS = (2023, 2024, 2025, 2024, 2023)
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # sem I e O


def placa_do_seed(numero: int) -> str:
    """Placa Mercosul fictícia e fixa por número (AAA1A11), fora das placas dos veículos citados."""
    n = (numero * 7919 + 4421) % (len(LETRAS) ** 3 * 10)
    letras, digito = divmod(n, 10)
    a, resto = divmod(letras, len(LETRAS) ** 2)
    b, c = divmod(resto, len(LETRAS))
    fim = f"{LETRAS[numero % 24]}{numero % 10}{(numero // 10) % 10}"
    return f"{LETRAS[a]}{LETRAS[b]}{LETRAS[c]}{digito}{fim}"


def chassi_do_seed(numero: int) -> str:
    return f"9C2JC{numero:05d}RR{100000 + numero * 17:06d}"[:17]


@dataclass
class Frota:
    centro: Filial
    veiculos: dict[str, Veiculo] = field(default_factory=dict)
    grupos: dict[int, str] = field(default_factory=dict)  # id do veículo → grupo da tabela

    def veiculo(self, placa: str) -> Veiculo:
        return Veiculo.objects.get(placa=placa)


def planos_do_grupo(grupo: str) -> dict[str, Any]:
    """O documento da tela de preços (ADR 0041) com os planos diária, semanal e mensal ligados,
    nos valores do grupo, e o dia de atraso e a multa mínima iguais à diária (VEI-14), como a
    tabela da Filial Centro dava antes da ADR 0043."""
    _, diaria, semanal, mensal, caucao = PRECOS_SEED[grupo]
    return {
        "planos": [
            {
                "tipo": tipo,
                "valor_centavos": valor,
                "caucao_centavos": caucao,
                "ligado": True,
                "agendado": None,
            }
            for tipo, valor in (("diaria", diaria), ("semanal", semanal), ("mensal", mensal))
        ],
        "regras": {"dia_atraso_centavos": diaria, "multa_minima_centavos": diaria},
    }


def cadastrar_veiculo(
    numero: int,
    grupo: str,
    filial: Filial,
    status: str = "disponivel",
    *,
    com_precos: bool = True,
    **dados: Any,
) -> Veiculo:
    """Veículo pelo serviço de cadastro, com o tipo do grupo (nasce `indisponivel` "sem preço",
    VEI-15); com `com_precos`, a Mariana preenche os planos do grupo na tela de preços (o
    veículo fica `disponivel`) e, se for o caso, vem a transição de status com a origem `seed`.
    Sem `com_precos`, quem chama preenche os preços depois (estoque parado, Pop da compra)."""
    ano = ANOS[numero % len(ANOS)]
    padrao: dict[str, Any] = {
        "placa": placa_do_seed(numero),
        "chassi": chassi_do_seed(numero),
        "marca": "Honda",
        "modelo": "Pop 110i",
        "ano_fabricacao": ano,
        "ano_modelo": ano,
        "cor": CORES[numero % len(CORES)],
        "km_atual": 1500 + (numero * 1373) % 28000,
        "entrou_na_frota_em": date(ano + 1 if ano < 2025 else ano, 1 + numero % 9, 10),
    }
    tipo = DISTRIBUICAO[grupo][0]
    veiculo = veiculos_services.cadastrar(
        {**padrao, **dados, "tipo_veiculo": tipo, "filial_id": filial.pk}
    )
    if not com_precos:
        return veiculo
    with como(administradora()):
        veiculos_services.salvar_precos(veiculo, planos_do_grupo(grupo))
    if status != "disponivel":
        veiculos_services.transicionar(veiculo, status, origem=ORIGEM, motivo="Importação do seed")
    return veiculo


CAMPOS_DO_CRLV_DO_SEED = ("combustivel", "documento", "rastreador", "anotacoes")


def garantir_dados_do_crlv() -> bool:
    """O banco que já tinha a frota antes da T-421 ganha os dados do CRLV-e do QXA-4B21 (VEI-09),
    pelo editar, como a Mariana faria. Já preenchido (ou sem o QXA-4B21): nada muda."""
    qxa = Veiculo.objects.filter(placa="QXA4B21").first()
    if qxa is None or qxa.numero_motor or qxa.potencia_cv is not None:
        return False
    dados = {campo: NOMEADOS["QXA4B21"][campo] for campo in CAMPOS_DO_CRLV_DO_SEED}
    with como(administradora()):
        veiculos_services.editar(qxa, dados)
    return True


def montar_frota(centro: Filial, empresa: Any, relogio: RelogioDoSeed) -> Frota:
    """Os 86 veículos da Filial Centro e os preços de cada um, tudo pelos serviços de domínio."""
    frota = Frota(centro=centro)
    relogio.em("2026-10-07 07:00")
    numero = 0
    for nome, (_, modelos, por_status) in DISTRIBUICAO.items():
        nomeados = [p for p, d in NOMEADOS_DA_CONFERENCIA.items() if d["categoria"] == nome]
        faltam = dict(por_status)
        for placa in nomeados:
            dados = {k: v for k, v in NOMEADOS_DA_CONFERENCIA[placa].items() if k != "categoria"}
            faltam[dados["status"]] -= 1
            status = dados.pop("status")
            frota.veiculos[placa] = cadastrar_veiculo(0, nome, centro, status, placa=placa, **dados)
            frota.grupos[frota.veiculos[placa].pk] = nome
        # O estoque parado (T-499, `seed/estoque.py`) ocupa parte dos `a_venda` da categoria: os
        # últimos números ficam sem veículo, para os outros manterem a placa de sempre.
        trocados = {
            "a_venda": SUBSTITUIDOS_PELO_ESTOQUE_PARADO.get(nome, 0),
            "disponivel": SUBSTITUIDOS_PELA_COMPRA.get(nome, 0),
        }
        for status, quantos in faltam.items():
            for posicao in range(quantos):
                numero += 1
                if posicao >= quantos - trocados.get(status, 0):
                    continue
                marca, modelo = modelos[numero % len(modelos)]
                tanque: dict[str, Any] = (
                    {"capacidade_tanque_litros": TANQUE[nome]} if nome in TANQUE else {}
                )
                veiculo = cadastrar_veiculo(
                    numero, nome, centro, status, marca=marca, modelo=modelo, **tanque
                )
                frota.grupos[veiculo.pk] = nome
    recalcular_uso(empresa)
    return frota
