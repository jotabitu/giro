"""Gera a carteira de outubro da Moto Rápida (T-056) e calcula os números da FIN-15.

Uso (na raiz do repositório):  python docs/qa/carteira-outubro/gerar.py
Grava locacoes.csv e parcelas.csv ao lado deste arquivo e imprime os números.
Só biblioteca padrão; determinístico (nenhum sorteio).
Dinheiro em centavos. Data de referência: 07 out 2026 (quarta-feira).
"""

import csv
from datetime import date, timedelta
from pathlib import Path

HOJE = date(2026, 10, 7)
INICIO_MES, FIM_MES = date(2026, 10, 1), date(2026, 10, 31)
PASTA = Path(__file__).parent

# (categoria, plano): valor da parcela em centavos (tabela de preços da Filial Centro, LOC-01)
PRECO = {
    ("urbana", "diaria"): 4490,
    ("urbana", "semanal"): 29940,
    ("urbana", "entregador"): 27900,
    ("urbana", "mensal"): 109000,
    ("street", "semanal"): 32900,
    ("street", "mensal"): 119000,
    ("scooter", "semanal"): 44900,
    ("scooter", "mensal"): 159000,
    ("carro", "semanal"): 64900,
    ("carro", "mensal"): 229000,
}

# Locações das telas. Parcelas dadas à mão: (vencimento, valor, situação).
# situação: paga | aberta  (a situação "atrasada" ou "vence hoje" sai da data, como na API).
NOMEADAS = [
    ("LOC-2790", "Rafael Sousa", "urbana", "semanal", [(date(2026, 9, 12), 134700, "aberta")]),
    ("LOC-2812", "Patrícia Gomes", "scooter", "mensal", [(date(2026, 9, 15), 159000, "paga")]),
    (
        "LOC-2836",
        "Juliana Rocha",
        "street",
        "semanal",
        [(date(2026, 9, 30), 32900, "paga"), (date(2026, 10, 7), 32900, "paga")],
    ),
    (
        "LOC-2841",
        "Carlos Menezes",
        "street",
        "semanal",
        [(date(2026, 9, 30) + timedelta(7 * k), 29940, "aberta") for k in range(5)],
    ),
    ("LOC-2848", "Diego Martins", "carro", "diaria", [(date(2026, 10, 6), 3 * 10900, "paga")]),
    ("LOC-2850", "Marcos Viana", "urbana", "mensal", [(date(2026, 10, 1), 109000, "paga")]),
    (
        "LOC-2856",
        "Lucas Ferreira",
        "street",
        "semanal",
        [(date(2026, 10, 7), 32900, "paga"), (date(2026, 10, 14), 32900, "aberta")],
    ),
]

# 35 locações geradas: 18 Urbana, 13 Street, 2 Scooter, 2 Carro.
SEMANAIS = (
    [("urbana", "semanal")] * 8
    + [("urbana", "entregador")] * 5
    + [("street", "semanal")] * 9
    + [("scooter", "semanal")]
    + [("carro", "semanal")]
)
DIA_DA_SEMANA = [0, 1, 2, 3, 4, 5]  # segunda a sábado, em rodízio
MENSAIS = (  # (categoria, dia do mês do vencimento)
    [("urbana", d) for d in (1, 5, 7, 18)]
    + [("street", d) for d in (2, 6, 12, 25)]
    + [("scooter", 9), ("carro", 20)]
)


def primeiro_dia_da_semana(dia_semana: int, a_partir_de: date) -> date:
    return a_partir_de + timedelta((dia_semana - a_partir_de.weekday()) % 7)


def montar():
    geradas = []
    for i, (cat, plano) in enumerate(SEMANAIS):
        inicio = primeiro_dia_da_semana(DIA_DA_SEMANA[i % 6], date(2026, 9, 1) + timedelta(7 * (i % 3)))
        valor, parcelas, v = PRECO[(cat, plano)], [], inicio
        while v <= date(2026, 11, 3):  # fim previsto depois de 31 out
            if v >= INICIO_MES:
                parcelas.append((v, valor, "paga" if v < HOJE else "aberta"))
            v += timedelta(7)
        geradas.append((cat, plano, inicio, parcelas))
    for cat, dia in MENSAIS:
        venc = date(2026, 10, dia)
        geradas.append(
            (cat, "mensal", date(2026, 9, dia), [(venc, PRECO[(cat, "mensal")], "paga" if venc < HOJE else "aberta")])
        )
    geradas.append(("urbana", "diaria", HOJE, [(HOJE, PRECO[("urbana", "diaria")], "paga")]))
    geradas.sort(key=lambda g: (g[2], g[0], g[1]))
    usados = {int(n[0][4:]) for n in NOMEADAS}
    livres = (n for n in range(2791, 2856) if n not in usados)
    return [
        (f"LOC-{next(livres)}", f"Cliente {i + 1:02d}", c, p, parc)
        for i, (c, p, _, parc) in enumerate(geradas)
    ]


def situacao(venc: date, base: str) -> str:
    if base == "paga":
        return "paga"
    return "atrasada" if venc < HOJE else ("vence_hoje" if venc == HOJE else "aberta")


def numeros(parcelas):
    mes = [p for p in parcelas if INICIO_MES <= p["vencimento"] <= FIM_MES]
    pagas = [p for p in mes if p["situacao"] == "paga"]
    hoje = [p for p in mes if p["situacao"] == "vence_hoje"]
    atrasadas = [p for p in parcelas if p["situacao"] == "atrasada"]
    soma = lambda ps: sum(p["valor_centavos"] for p in ps)  # noqa: E731
    faixa = lambda ps, a, b: [p for p in ps if a <= (HOJE - p["vencimento"]).days <= b]  # noqa: E731
    a_vencer = [p for p in mes if p["situacao"] == "aberta"]
    return {
        "previsto_centavos": soma(mes),
        "previsto_parcelas": len(mes),
        "recebido_centavos": soma(pagas),
        "recebido_parcelas": len(pagas),
        "recebido_percentual": round(soma(pagas) * 10000 / soma(mes)) / 100,
        "vence_hoje_centavos": soma(hoje),
        "vence_hoje_parcelas": len(hoje),
        "atraso_centavos": soma(atrasadas),
        "atraso_parcelas": len(atrasadas),
        "atraso_clientes": len({p["codigo"] for p in atrasadas}),
        "atraso_1_7_centavos": soma(faixa(atrasadas, 1, 7)),
        "atraso_8_30_centavos": soma(faixa(atrasadas, 8, 30)),
        "atraso_mais_30_centavos": soma(faixa(atrasadas, 31, 9999)),
        "aba_em_atraso": len(atrasadas),
        "aba_vencem_hoje": len(hoje),
        "aba_a_vencer": len(a_vencer),
        "aba_pagas": len(pagas),
        "aba_todas": len(atrasadas) + len(hoje) + len(a_vencer) + len(pagas),
        "a_vencer_centavos": soma(a_vencer),
    }


def carteira():
    locacoes = NOMEADAS + montar()
    assert len(locacoes) == 42
    parcelas = []
    for codigo, _, cat, plano, parc in locacoes:
        for n, (venc, valor, base) in enumerate(sorted(parc), 1):
            parcelas.append(
                {
                    "codigo": codigo,
                    "vencimento": venc,
                    "valor_centavos": valor,
                    "situacao": situacao(venc, base),
                }
            )
    return locacoes, parcelas


if __name__ == "__main__":
    locacoes, parcelas = carteira()
    with open(PASTA / "locacoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["codigo", "cliente", "categoria", "plano"])
        for codigo, cliente, cat, plano, _ in locacoes:
            w.writerow([codigo, cliente, cat, plano])
    with open(PASTA / "parcelas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["codigo", "vencimento", "valor_centavos", "situacao"])
        for p in sorted(parcelas, key=lambda p: (p["vencimento"], p["codigo"])):
            w.writerow([p["codigo"], p["vencimento"].isoformat(), p["valor_centavos"], p["situacao"]])
    for k, v in numeros(parcelas).items():
        print(k, v)
