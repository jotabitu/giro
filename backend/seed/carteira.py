"""As 42 locações abertas da Moto Rápida em 07 out (carteira de outubro da T-056), no banco.

Lê `seed/dados/carteira-outubro/` (cópia de `docs/qa/carteira-outubro/`, conferida por teste) e
grava direto nos models, como a importação do seed (T-019) vai fazer: as locações já ativas
(LOC-2790 com a devolução atrasada), as parcelas pagas ou em aberto e os clientes. Os veículos são
os alugados da frota (`frota.py`), na mesma proporção.
"""

import csv
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente, DocumentoCliente, TipoDocumentoCliente
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import ContaReceber
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from comum.codigos import ajustar_sequencia

from .frota import PRECOS_SEED, Frota

PASTA = Path(__file__).resolve().parent / "dados" / "carteira-outubro"  # cópia de docs/qa/
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
# Placa das locações citadas nos critérios e nas telas (frota.py).
PLACAS = {"LOC-2836": "PNB7C04", "LOC-2841": "QXA4B21"}
# Só no seed de conferência (`conferencia=True`), que usa a frota do seed (T-138).
PLACAS_DA_CONFERENCIA = {
    "LOC-2790": "PQD6E21",
    "LOC-2812": "SBC0J44",
    "LOC-2848": "RKP3D26",
    "LOC-2850": "RJD5B38",
    "LOC-2856": "SAK1D39",
}
# A conta da LOC-2790 (R$ 1.347,00) é um valor dado do seed, e não da tabela ("Dados de
# referência": 30 diárias Urbana); o plano semanal dela vale o da tabela (LOC-01, D-05 da T-138).
VALOR_DO_PERIODO = {"LOC-2790": 29940}
# Quem vende: a Bruna as locações das telas e 2 de cada 3 das outras; o Rodrigo (gerente) o resto
# (D-24). A regra do seed pede 5 usuários (PLT-03), então não há um 2º vendedor.
VENDE_O_GERENTE = 3
HOJE_DO_SEED = date(2026, 10, 7)
# Retiradas futuras (dias úteis) das reservas: uma locação `aguardando_retirada` por veículo
# `reservado` (D-01). O Kwid RHT9F02 é a LOC-2857.
RETIRADAS_DAS_RESERVAS = (
    "2026-10-13",
    "2026-10-14",
    "2026-10-15",
    "2026-10-16",
    "2026-10-19",
    "2026-10-20",
    "2026-10-21",
    "2026-10-22",
    "2026-10-23",
)
RESERVADO_PRIMEIRO = "RHT9F02"
# Nomes fictícios no lugar de "Cliente NN" (os 35 primeiros) e dos clientes das 9 reservas.
NOMES = (
    "Anderson Lima",
    "Beatriz Moura",
    "Caio Barros",
    "Daniela Freire",
    "Eduardo Queiroz",
    "Fabiana Teles",
    "Gustavo Nobre",
    "Helena Pontes",
    "Igor Bezerra",
    "Jéssica Arruda",
    "Kleber Duarte",
    "Larissa Cavalcante",
    "Mateus Brandão",
    "Natália Sampaio",
    "Otávio Girão",
    "Priscila Farias",
    "Rodrigo Vasconcelos",
    "Sabrina Holanda",
    "Thiago Menezes",
    "Úrsula Lobo",
    "Vinícius Campos",
    "Waleska Aragão",
    "Yuri Albuquerque",
    "Zilda Maciel",
    "Alan Peixoto",
    "Bianca Rangel",
    "Cláudio Sena",
    "Débora Furtado",
    "Elton Mesquita",
    "Flávia Linhares",
    "Gabriel Paiva",
    "Heloísa Cunha",
    "Ícaro Montenegro",
    "Joana Veras",
    "Kauã Bastos",
    "Letícia Aguiar",
    "Murilo Façanha",
    "Nicole Fontenele",
    "Osvaldo Pimentel",
    "Paula Tavares",
    "Renan Colares",
    "Samara Frota",
    "Tales Gondim",
    "Vanessa Leitão",
)
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


def nome_exibido(nome: str) -> str:
    """ "Cliente 07" da carteira vira um nome fictício; os das telas (Rafael etc.) ficam."""
    if nome.startswith("Cliente "):
        return NOMES[int(nome.split()[1]) - 1]
    return nome


def _completar(cliente: Cliente) -> None:
    """CLI-03: os 4 documentos enviados (só o registro, sem arquivo) e o cadastro sai de
    `incompleto`. O Rafael é o único que fica sem (D-07)."""
    for tipo in TipoDocumentoCliente.values:
        DocumentoCliente.objects.get_or_create(cliente=cliente, tipo=tipo)
    clientes_services.acertar_cadastro(cliente)


def _cliente(nome: str, numero: int, conferencia: bool = False) -> Cliente:
    if conferencia:
        nome = nome_exibido(nome)
    existente: Cliente | None = Cliente.objects.filter(nome=nome).first()
    if existente is not None:
        return existente
    novo: Cliente = clientes_services.cadastrar(
        pessoa(nome, cpf(400000000 + numero * 7919), f"8599{numero:07d}")
    )
    if conferencia and nome != "Rafael Sousa":
        _completar(novo)
    return novo


def _ler(arquivo: str) -> list[dict[str, str]]:
    with open(PASTA / arquivo, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _confirmar(
    codigo: str,
    linha: dict[str, str],
    numero: int,
    frota: Frota,
    vendedor: Any,
    relogio: Any,
    conferencia: bool = False,
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
            "cliente_id": _cliente(linha["cliente"], numero, conferencia).pk,
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
    if locacao.codigo != codigo:
        raise RuntimeError(f"A sequência deu {locacao.codigo}, e o seed esperava {codigo}")
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


def carregar(
    frota: Frota, vendedor: Any, relogio: Any, *, gerente: Any = None, conferencia: bool = False
) -> dict[str, Locacao]:
    """`conferencia=True` é o seed de desenvolvimento (T-138): placas das telas, clientes com
    nome e documentos, vendas divididas com o gerente, 1ª parcela paga na retirada e uma reserva
    por veículo `reservado`. Sem ele, é a carteira crua da T-056, que os testes usam."""
    placas = {**PLACAS, **(PLACAS_DA_CONFERENCIA if conferencia else {})}
    parcelas: dict[str, list[dict[str, str]]] = defaultdict(list)
    for linha in _ler("parcelas.csv"):
        parcelas[linha["codigo"]].append(linha)
    livres: dict[str, list[Veiculo]] = {
        nome: list(
            Veiculo.objects.filter(categoria=categoria, status="alugado")
            .exclude(placa__in=placas.values())
            .order_by("placa")
        )
        for nome, categoria in frota.categorias.items()
    }
    locacoes = {}
    for numero, linha in enumerate(_ler("locacoes.csv"), start=1):
        codigo = linha["codigo"]
        quem = gerente if conferencia and numero > 7 and numero % VENDE_O_GERENTE == 0 else vendedor
        categoria = CATEGORIAS[linha["categoria"]]
        veiculo = frota.veiculos[placas[codigo]] if codigo in placas else livres[categoria].pop(0)
        if codigo in CONFIRMADAS:
            locacoes[codigo] = _confirmar(codigo, linha, numero, frota, quem, relogio, conferencia)
            continue
        contas = sorted(parcelas[codigo], key=lambda p: p["vencimento"])
        primeira = date.fromisoformat(contas[0]["vencimento"]) if contas else date(2026, 10, 1)
        # A locação já está ativa em 07 out: a retirada não é depois do dia (D-21).
        inicio, fim = DATAS.get(
            codigo,
            (
                datetime.combine(
                    min(primeira, HOJE_DO_SEED) if conferencia else primeira, time(9)
                ).isoformat(" "),
                FIM_DAS_GERADAS,
            ),
        )
        locacao = Locacao(
            numero=int(codigo.split("-")[1]),
            codigo=codigo,
            filial=frota.centro,
            cliente=_cliente(linha["cliente"], numero, conferencia),
            veiculo=veiculo,
            vendedor=quem,
            periodicidade=PERIODICIDADE[linha["plano"]],
            inicio=momento(inicio),
            fim_previsto=momento(fim),
            valor_periodo_centavos=(VALOR_DO_PERIODO if conferencia else {}).get(
                codigo, int(contas[0]["valor_centavos"]) if contas else 0
            ),
            diaria_centavos=PRECOS_SEED[categoria][1] if conferencia else 0,
            caucao_centavos=0,
            precos_de=momento(inicio).date(),
            forma_pagamento="pix",
            status="devolucao_atrasada" if codigo == "LOC-2790" else "ativa",
        )
        locacao.save()
        for posicao, conta in enumerate(contas, start=1):
            vencimento = date.fromisoformat(conta["vencimento"])
            # LOC-05: a parcela 1 é paga na retirada, então não nasce em aberto nem atrasada
            # (D-21); a conta atrasada dada da LOC-2790 é a exceção.
            paga = conta["situacao"] == "paga" or (
                conferencia and posicao == 1 and codigo != "LOC-2790"
            )
            pago_em = datetime.combine(min(vencimento, HOJE_DO_SEED), time(10), tzinfo=FUSO)
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
                pago_em=pago_em if paga else None,
            )
        # As parcelas nasceram com a locação, e não hoje: o atraso da FIN-03 conta do vencimento.
        ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk).update(
            criado_em=momento(inicio)
        )
        locacoes[codigo] = locacao
    ajustar_sequencia("LOC", 2856 if conferencia else 2855)  # 2857: a reserva do Kwid
    if conferencia:
        locacoes.update(_reservas(frota, vendedor, gerente))
    return locacoes


def _reservas(frota: Frota, vendedora: Any, gerente: Any) -> dict[str, Locacao]:
    """Uma locação `aguardando_retirada` para cada veículo `reservado`, pelos serviços: rascunho e
    confirmação (LOC-15), com a retirada em dia útil depois de 07 out. O veículo volta a
    `disponivel` antes, porque é a confirmação que o reserva. Sem vistoria de saída, contrato nem
    1º pagamento: a tela de vistoria de saída abre (D-01)."""
    reservados = sorted(
        Veiculo.objects.filter(status="reservado"),
        key=lambda v: (v.placa != RESERVADO_PRIMEIRO, v.placa),
    )
    nomes_das_categorias = {c.pk: n for n, c in frota.categorias.items()}
    reservas = {}
    for posicao, veiculo in enumerate(reservados):
        veiculos_services.transicionar(
            veiculo,
            "disponivel",
            origem=veiculos_services.OrigemDaMudanca("seed", 0, "seed"),
            motivo="Antes da confirmação da reserva",
        )
        scooter = nomes_das_categorias[veiculo.categoria_id] == "Scooter premium"
        vendedor = gerente if posicao % VENDE_O_GERENTE == 0 else vendedora
        locacao = locacoes_services.criar_rascunho(
            {
                "cliente_id": _cliente(NOMES[35 + posicao], 100 + posicao, True).pk,
                "veiculo_id": veiculo.pk,
                "periodicidade": "mensal" if scooter else "semanal",
                "plano_especial_id": None,
                "inicio": momento(f"{RETIRADAS_DAS_RESERVAS[posicao]} 09:00"),
                "periodos": 1 if scooter else 2,
                "extras": [],
                "desconto_pct": "0.00",
                "forma_pagamento": "pix",
            },
            frota.centro,
            vendedor,
        )
        locacoes_services.confirmar(locacao, vendedor)
        locacao.refresh_from_db()
        reservas[locacao.codigo] = locacao
    return reservas
