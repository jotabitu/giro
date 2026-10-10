"""As 42 locações abertas da Moto Rápida em 07 out (carteira de outubro da T-056), no banco.

Lê `docs/qa/carteira-outubro/` e grava direto nos models, como a importação do seed (T-019) vai
fazer: as locações já ativas (LOC-2790 com a devolução atrasada), as parcelas pagas ou em aberto
e os clientes. Os veículos são os alugados da frota (`frota.py`), na mesma proporção.
"""

import csv
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from comum.codigos import ajustar_sequencia

from .frota import Frota

PASTA = Path(__file__).resolve().parents[3] / "docs" / "qa" / "carteira-outubro"
FUSO = ZoneInfo("America/Sao_Paulo")
CATEGORIAS = {
    "urbana": "Urbana 110–125",
    "street": "Street 150–160",
    "scooter": "Scooter premium",
    "carro": "Carro compacto",
}
PERIODICIDADE = {
    "semanal": "semanal",
    "entregador": "semanal",
    "mensal": "mensal",
    "diaria": "diaria",
}
# Placa das locações citadas nos critérios (frota.py).
PLACAS = {"LOC-2836": "PNB7C04", "LOC-2841": "QXA4B21"}
# Início e fim das locações das telas (regras, "Dados de referência para testes").
DATAS: dict[str, tuple[str, str]] = {
    "LOC-2790": ("2026-08-13 09:00", "2026-09-12 18:00"),
    "LOC-2812": ("2026-09-15 09:00", "2026-10-15 18:00"),
    "LOC-2841": ("2026-09-23 09:00", "2026-10-28 09:00"),
    "LOC-2848": ("2026-10-06 09:00", "2026-10-10 09:00"),
    "LOC-2850": ("2026-10-01 09:00", "2026-11-01 09:00"),
    "LOC-2856": ("2026-10-07 09:00", "2026-10-21 09:00"),
}
FIM_DAS_GERADAS = "2026-11-30 18:00"
# Locações que passam pela confirmação de verdade (LOC-15), no dia e com o início que as regras
# dão: o preço sai da tabela vigente na confirmação, e as parcelas e a caução nascem das contas
# (LOC-2836: início em 30 set, confirmada em 01 out, "Preço da LOC-2836"). Código → (confirmação,
# início, retirada). A parcela 1 vence em 30 set e é paga na retirada, sem multa (FIN-03, padrão A).
CONFIRMADAS = {"LOC-2836": ("2026-10-01 09:00", "2026-09-30 18:00", "2026-10-01 09:10")}


def momento(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=FUSO)


def cpf(semente: int) -> str:
    """CPF válido a partir de 9 dígitos (para os clientes gerados)."""
    base = [int(d) for d in f"{semente:09d}"]
    for _ in range(2):
        soma = sum(d * p for d, p in zip(base, range(len(base) + 1, 1, -1), strict=True))
        resto = soma % 11
        base.append(0 if resto < 2 else 11 - resto)
    return "".join(map(str, base))


def pessoa(nome: str, documento: str, celular: str, **extra: Any) -> dict[str, Any]:
    """Cadastro completo, com CNH AB (moto e carro) válida."""
    return {
        "tipo": "pf",
        "nome": nome,
        "documento": documento,
        "nascimento": "1995-05-10",
        "celular": celular,
        "cnh": {
            "numero": f"0{documento[:10]}",
            "categoria": "AB",
            "validade": "2030-01-10",
            "primeira_habilitacao": "2015-01-10",
        },
        "endereco": {
            "cep": "60325000",
            "logradouro": "Rua Padre Mororó",
            "numero": "145",
            "complemento": None,
            "bairro": "Centro",
            "cidade": "Fortaleza",
            "uf": "CE",
        },
        "referencia": {"nome": "Maria Rocha", "parentesco": "mãe", "telefone": "85999990000"},
        "consentimento": True,
        **extra,
    }


def _cliente(nome: str, numero: int) -> Cliente:
    existente = Cliente.objects.filter(nome=nome).first()
    if existente is not None:
        return existente
    return clientes_services.cadastrar(
        pessoa(nome, cpf(400000000 + numero * 7919), f"8599{numero:07d}")
    )


def _ler(arquivo: str) -> list[dict[str, str]]:
    with open(PASTA / arquivo, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _confirmar(
    codigo: str, linha: dict[str, str], numero: int, frota: Frota, vendedor: Any, relogio: Any
) -> Locacao:
    """Rascunho e confirmação pelos serviços, com o relógio no dia da confirmação; a retirada
    (vistoria, contrato, parcela 1 e caução) no dia seguinte, e a parcela 2 no vencimento."""
    confirmacao, inicio, retirada = CONFIRMADAS[codigo]
    agora = relogio.agora
    veiculo = frota.veiculos[PLACAS[codigo]]
    # A frota já o traz alugado; a confirmação pede o veículo livre, e a retirada o aluga.
    veiculos_services.transicionar(
        veiculo,
        "disponivel",
        origem=veiculos_services.OrigemDaMudanca("seed", 0, "seed"),
        motivo="Antes da retirada da LOC-2836",
    )
    ultimo = int(codigo.split("-")[1])
    ajustar_sequencia("LOC", ultimo - 1)
    relogio.em(confirmacao)
    locacao = locacoes_services.criar_rascunho(
        {
            "cliente_id": _cliente(linha["cliente"], numero).pk,
            "veiculo_id": veiculo.pk,
            "periodicidade": PERIODICIDADE[linha["plano"]],
            "plano_especial_id": None,
            "inicio": momento(inicio),
            "periodos": 2,  # 2 semanas: fim em 14 out 18:00 pela LOC-01 (LOC-06)
            "extras": [],
            "desconto_pct": "0.00",
            "forma_pagamento": "pix",
        },
        frota.centro,
        vendedor,
    )
    assert locacao.codigo == codigo
    locacoes_services.confirmar(locacao, vendedor)
    relogio.em(retirada)
    locacoes_services.registrar_vistoria_saida(locacao, km=veiculo.km_atual)
    locacoes_services.registrar_contrato_assinado(locacao.pk, relogio.agora)
    for conta in financeiro_selectors.contas_da_origem("locacao", locacao.pk):
        if conta.tipo == "caucao" or conta.numero_parcela == 1:
            financeiro.marcar_paga(conta, forma="pix")
    segunda = next(
        c
        for c in financeiro_selectors.contas_da_origem("locacao", locacao.pk)
        if c.numero_parcela == 2
    )
    financeiro.marcar_paga(
        segunda,
        forma="pix",
        pago_em=datetime.combine(segunda.vencimento, time(10), tzinfo=FUSO),
    )
    relogio.em(agora.strftime("%Y-%m-%d %H:%M"))
    locacao.refresh_from_db()
    return locacao


def carregar(frota: Frota, vendedor: Any, relogio: Any) -> dict[str, Locacao]:
    parcelas: dict[str, list[dict[str, str]]] = defaultdict(list)
    for linha in _ler("parcelas.csv"):
        parcelas[linha["codigo"]].append(linha)
    livres: dict[str, list[Veiculo]] = {
        nome: list(
            Veiculo.objects.filter(categoria=categoria, status="alugado")
            .exclude(placa__in=PLACAS.values())
            .order_by("placa")
        )
        for nome, categoria in frota.categorias.items()
    }
    locacoes = {}
    for numero, linha in enumerate(_ler("locacoes.csv"), start=1):
        codigo = linha["codigo"]
        categoria = CATEGORIAS[linha["categoria"]]
        veiculo = frota.veiculos[PLACAS[codigo]] if codigo in PLACAS else livres[categoria].pop(0)
        if codigo in CONFIRMADAS:
            locacoes[codigo] = _confirmar(codigo, linha, numero, frota, vendedor, relogio)
            continue
        contas = sorted(parcelas[codigo], key=lambda p: p["vencimento"])
        primeira = date.fromisoformat(contas[0]["vencimento"]) if contas else date(2026, 10, 1)
        inicio, fim = DATAS.get(
            codigo, (datetime.combine(primeira, time(9)).isoformat(" "), FIM_DAS_GERADAS)
        )
        locacao = Locacao(
            numero=int(codigo.split("-")[1]),
            codigo=codigo,
            filial=frota.centro,
            cliente=_cliente(linha["cliente"], numero),
            veiculo=veiculo,
            vendedor=vendedor,
            periodicidade=PERIODICIDADE[linha["plano"]],
            inicio=momento(inicio),
            fim_previsto=momento(fim),
            valor_periodo_centavos=int(contas[0]["valor_centavos"]) if contas else 0,
            diaria_centavos=0,
            caucao_centavos=0,
            precos_de=momento(inicio).date(),
            forma_pagamento="pix",
            status="devolucao_atrasada" if codigo == "LOC-2790" else "ativa",
        )
        locacao.save()
        for posicao, conta in enumerate(contas, start=1):
            vencimento = date.fromisoformat(conta["vencimento"])
            paga = conta["situacao"] == "paga"
            ContaReceber.objects.create(
                filial=frota.centro,
                cliente=locacao.cliente,
                origem_tipo="locacao",
                origem_id=locacao.pk,
                origem_codigo=codigo,
                tipo="parcela",
                numero_parcela=posicao,
                total_parcelas=len(contas),
                vencimento=vencimento,
                valor_centavos=int(conta["valor_centavos"]),
                status="paga" if paga else "aberta",
                forma="pix" if paga else "",
                pago_em=datetime.combine(vencimento, time(10), tzinfo=FUSO) if paga else None,
            )
        locacoes[codigo] = locacao
    ajustar_sequencia("LOC", 2855)  # a próxima locação é a LOC-2856
    return locacoes
