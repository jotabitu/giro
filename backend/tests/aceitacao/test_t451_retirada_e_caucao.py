"""T-451 e T-452 · Retirada da locação e caução (`docs/qa/criterios/T-451-T-452.md`).

Regras: LOC-17 (retirada), FIN-18 (caução), FIN-15 (caução na lista do `Receber`, fora dos
números). Cenário da T-015/T-090: Moto Rápida em 07 out 2026, 10:00, Filial Centro. "A locação"
é a LOC-2856 do Lucas, confirmada pela Bruna: semanal Street R$ 329,00 no SAK-1D39, 2 semanas a
partir de hoje, com caução de R$ 300,00. Sem contrato enviado, sem vistoria, nada pago.
"""

from datetime import date
from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro.models import ContaReceber, MovimentoCaixa
from apps.locacoes.models import Locacao
from apps.veiculos.models import DocumentoVeiculo, Veiculo
from comum import relogio as relogio_do_giro

from .test_t015_locacoes import LISTA, Cenario, _vistoriar
from .test_t016_vistorias import _completar
from .test_t017_financeiro import (
    CONTAS,
    _abrir,
    _pix_no_caixa,
    _receber,
    recebimentos,  # noqa: F401 - fixture
)
from .test_t090_contratos import _assinar, _gerar, _token
from .test_t090_contratos import moto as cenario  # noqa: F401 - fixture

PRAZO_07_OUT = "Retire até 10 out. Sem retirada, a locação é cancelada em 11 out."


def _confirmada(cenario: Cenario, **campos: Any) -> Locacao:  # noqa: F811
    criada = cenario.confirmada(periodos=2, **campos)
    return Locacao.objects.get(pk=criada["id"])


@pytest.fixture
def locacao(cenario: Cenario) -> Locacao:  # noqa: F811
    """Com o cadastro do Lucas completo, como na preparação dos critérios."""
    _completar(cenario.clientes["Lucas"])
    return _confirmada(cenario)


def _conta(locacao: Locacao, tipo: str = "parcela", numero: int = 1) -> ContaReceber:
    contas = ContaReceber.objects.filter(origem_tipo="locacao", origem_id=locacao.pk, tipo=tipo)
    conta: ContaReceber = contas.get(numero_parcela=numero) if tipo == "parcela" else contas.get()
    return conta


def _bloco(cenario: Cenario, locacao: Locacao, quem: str = "Bruna") -> dict[str, Any]:  # noqa: F811
    bloco = cenario.detalhe(locacao.pk, quem)["para_retirar"]
    assert bloco is not None
    return dict(bloco)


def _passos(bloco: dict[str, Any]) -> list[tuple[str, bool, str, list[str]]]:
    return [
        (p["codigo"], p["feito"], p["texto"], [a["rotulo"] for a in p["acoes"]])
        for p in bloco["passos"]
    ]


def _status(locacao: Locacao) -> str:
    return Locacao.objects.get(pk=locacao.pk).status


def _retirada(locacao: Locacao) -> EventoAuditoria:
    evento: EventoAuditoria = EventoAuditoria.objects.get(
        objeto_tipo="locacao", objeto_id=locacao.pk, acao="locacao.retirada"
    )
    return evento


# --- Caução (T-452, FIN-18) ---


def test_fin_18_ca_452_01_caucao_na_secao_pagamentos(cenario, locacao) -> None:  # noqa: F811
    """A ficha lista a parcela 1 e a caução, cada uma com o rótulo, o valor de hoje, a conta e
    "Registrar pagamento" para a Bruna."""
    parcelas = cenario.detalhe(locacao.pk)["parcelas"]
    primeiras = [p for p in parcelas if p["rotulo"] in ("Parcela 1", "Caução")]
    assert [
        (p["rotulo"], p["valor_centavos"], p["valor_hoje_centavos"], p["status"], p["acoes"])
        for p in primeiras
    ] == [
        ("Parcela 1", 32900, 32900, "aberta", {"receber": True}),
        ("Caução", 30000, 30000, "aberta", {"receber": True}),
    ]
    caucao = primeiras[1]
    assert caucao["conta_id"] == _conta(locacao, "caucao").pk
    assert [p["rotulo"] for p in parcelas] == ["Parcela 1", "Parcela 2", "Caução"]


def test_fin_18_ca_452_02_caucao_na_lista_do_receber_fora_dos_numeros(
    cenario,  # noqa: F811
    locacao,
) -> None:
    """FIN-15: a caução aparece na lista, na aba da situação dela, com "Registrar pagamento";
    as contagens, os indicadores e o contador do menu só contam as parcelas."""
    api = cenario.moto.api("Lúcia")
    lista = api.get(CONTAS).json()
    caucao = _conta(locacao, "caucao")
    linha = next(c for c in lista["resultados"] if c["id"] == caucao.pk)
    assert (linha["tipo"], linha["cliente"]["nome"], linha["origem"]["codigo"]) == (
        "caucao",
        "Lucas Ferreira",
        locacao.codigo,
    )
    assert linha["acoes"]["receber"] is True
    a_vencer = api.get(CONTAS, {"situacao": "a_vencer"}).json()["resultados"]
    assert caucao.pk in [c["id"] for c in a_vencer]

    sem_caucao = [c for c in lista["resultados"] if c["tipo"] != "caucao"]
    assert lista["contagens"]["todas"] == len(sem_caucao)
    assert lista["contagens"]["a_vencer"] == len([c for c in a_vencer if c["tipo"] != "caucao"])
    indicadores = lista["indicadores"]
    assert (
        indicadores["previsto_mes_parcelas"]
        == ContaReceber.objects.filter(tipo="parcela", vencimento__month=10).count()
    )
    assert indicadores["previsto_mes_centavos"] == 32900 * 2
    contador = api.get("/api/painel/contadores/").json()["contadores"]["receber"]
    assert contador == 0


def test_fin_18_busca_do_caixa_acha_a_caucao(cenario, locacao) -> None:  # noqa: F811
    """A busca do `Caixa` por cliente ou locação traz a parcela e a caução."""
    for termo in ("Lucas", locacao.codigo):
        achadas = cenario.moto.api("Bruna").get(CONTAS, {"busca": termo}).json()["resultados"]
        tipos = {(c["tipo"], c["numero"]) for c in achadas}
        assert {("parcela", 1), ("caucao", None)} <= tipos, termo


def test_fin_18_ca_452_03_baixa_da_caucao_em_dinheiro(cenario, locacao) -> None:  # noqa: F811
    """A caução fica paga na ficha e em `Receber`, o caixa ganha R$ 300,00 em dinheiro, a
    receita e os números de `Receber` não mudam, e a locação segue aguardando a retirada."""
    api = cenario.moto.api("Lúcia")
    antes = api.get(CONTAS).json()
    filiais = [cenario.frota.centro.pk]
    dia = relogio_do_giro.agora().replace(hour=0, minute=0)
    fim = dia.replace(hour=23, minute=59)
    receita_antes = financeiro_selectors.receita_de_locacao(filiais, dia, fim)
    assert _abrir(cenario).status_code == 201

    resposta = _receber(cenario, _conta(locacao, "caucao"), 30000)
    assert resposta.status_code == 200, resposta.json()

    caucao = next(p for p in cenario.detalhe(locacao.pk)["parcelas"] if p["rotulo"] == "Caução")
    assert (caucao["status"], caucao["forma"], caucao["acoes"]) == (
        "paga",
        "dinheiro",
        {"receber": False},
    )
    entrada = MovimentoCaixa.objects.get(valor_centavos=30000)
    assert (entrada.tipo, entrada.forma) == ("entrada", "dinheiro")
    assert financeiro_selectors.receita_de_locacao(filiais, dia, fim) == receita_antes
    depois = api.get(CONTAS).json()
    assert depois["indicadores"] == antes["indicadores"]
    assert depois["contagens"] == antes["contagens"]
    pagas = api.get(CONTAS, {"situacao": "pagas"}).json()["resultados"]
    assert _conta(locacao, "caucao").pk in [c["id"] for c in pagas]
    assert _status(locacao) == "aguardando_retirada"


def test_fin_18_ca_452_04_sem_multa_antes_da_retirada(
    cenario,  # noqa: F811
    relogio,
    relogio_jwt,
) -> None:
    """Confirmada em 05 nov com início em 05 nov, a caução paga em 07 nov, antes da retirada,
    sai por R$ 300,00, sem multa nem juros (FIN-03, LOC-05)."""
    relogio.em("2026-11-05 09:00")
    cenario.moto._tokens.clear()
    criada = cenario.confirmada(inicio="2026-11-05T13:00:00Z", periodos=2)
    locacao = Locacao.objects.get(pk=criada["id"])
    relogio.em("2026-11-07 09:00")
    cenario.moto._tokens.clear()
    caucao = next(p for p in cenario.detalhe(locacao.pk)["parcelas"] if p["rotulo"] == "Caução")
    assert (caucao["valor_hoje_centavos"], caucao["status"]) == (30000, "aberta")
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    paga = _conta(locacao, "caucao")
    assert (paga.multa_centavos, paga.juros_centavos) == (0, 0)


def test_fin_18_ca_452_05_baixa_pelo_pix(
    cenario,  # noqa: F811
    locacao,
    recebimentos,  # noqa: F811
    django_capture_on_commit_callbacks,
) -> None:
    """O webhook do Pix baixa a caução sozinho, como numa parcela (FIN-04)."""
    assert _abrir(cenario).status_code == 201
    _pix_no_caixa(cenario, _conta(locacao, "caucao"), django_capture_on_commit_callbacks)
    caucao = next(p for p in cenario.detalhe(locacao.pk)["parcelas"] if p["rotulo"] == "Caução")
    assert (caucao["status"], caucao["forma"]) == ("paga", "pix")
    assert _status(locacao) == "aguardando_retirada"  # falta a parcela 1


# --- Retirada (T-451, LOC-17) ---


def test_loc_17_ca_451_01_para_retirar_com_tudo_faltando(cenario, locacao) -> None:  # noqa: F811
    bloco = _bloco(cenario, locacao)
    assert _passos(bloco) == [
        ("vistoria_saida", False, "Falta a vistoria de saída", ["Fazer vistoria de saída"]),
        ("contrato", False, "Falta enviar o contrato", ["Enviar contrato"]),
        (
            "pagamento",
            False,
            "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00",
            [],
        ),
    ]
    assert [a["codigo"] for p in bloco["passos"] for a in p["acoes"]] == [
        "continuar_vistoria",
        "gerar_contrato",
    ]
    assert bloco["prazo"] == PRAZO_07_OUT


def test_loc_17_ca_451_02_cada_passo_feito_muda_o_bloco(
    cenario,  # noqa: F811
    locacao,
    relogio,
    django_capture_on_commit_callbacks,
) -> None:
    relogio.em("2026-10-07 09:20")
    _vistoriar(locacao.pk)
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    assert _passos(_bloco(cenario, locacao)) == [
        ("vistoria_saida", True, "Feita em 07 out, 09:20", []),
        (
            "contrato",
            False,
            "Falta a assinatura do cliente",
            ["Reenviar", "Copiar link para assinar"],
        ),
        ("pagamento", False, "Falta receber R$ 329,00: 1ª semana R$ 329,00", []),
    ]
    assert cenario.detalhe(locacao.pk)["situacao"]["rotulo"] == "Aguardando assinatura"


def test_loc_17_ca_451_03_ativa_sozinha_com_a_assinatura_por_ultimo(
    cenario,  # noqa: F811
    locacao,
    django_capture_on_commit_callbacks,
) -> None:
    """Vistoria, 1ª semana, caução e, por último, a assinatura do cliente: a locação vira
    `ativa` na hora, o veículo `alugado`, o bloco some, e a "Retirada" é do Sistema."""
    _vistoriar(locacao.pk)
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    assert _status(locacao) == "aguardando_retirada"
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assinatura = _assinar(_token(), capturar=django_capture_on_commit_callbacks)
    assert assinatura.status_code == 200, assinatura.json()

    assert _status(locacao) == "ativa"
    assert Veiculo.objects.get(pk=locacao.veiculo_id).status == "alugado"
    detalhe = cenario.detalhe(locacao.pk)
    assert detalhe["para_retirar"] is None
    evento = _retirada(locacao)
    assert (evento.ator_tipo, evento.motivo) == (
        "sistema",
        "Retirada. Último passo: assinatura do contrato",
    )
    linha_do_tempo = cenario.moto.api("Bruna").get(f"{LISTA}{locacao.pk}/historico/").json()
    assert "Retirada" in [item["rotulo"] for item in linha_do_tempo["resultados"]]


def test_loc_17_ca_451_03_ativa_sozinha_com_o_pagamento_por_ultimo(
    cenario,  # noqa: F811
    locacao,
    django_capture_on_commit_callbacks,
) -> None:
    """Com a vistoria e a assinatura feitas, o "Registrar pagamento" da caução pela Bruna é o
    último passo: a locação vira `ativa` nele, e a "Retirada" é da Bruna."""
    _vistoriar(locacao.pk)
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assinatura = _assinar(_token(), capturar=django_capture_on_commit_callbacks)
    assert assinatura.status_code == 200, assinatura.json()
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _status(locacao) == "aguardando_retirada"  # só a parcela não conta

    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    assert _status(locacao) == "ativa"
    evento = _retirada(locacao)
    assert (evento.ator_nome, evento.motivo) == ("Bruna", "Retirada. Último passo: 1º pagamento")


MOTIVO = "Cliente paga amanhã, combinado com a gerência"


def _registrar(cenario: Cenario, locacao: Locacao, quem: str = "Rodrigo", motivo: str = MOTIVO):  # noqa: F811
    return cenario.moto.api(quem).post(
        f"{LISTA}{locacao.pk}/retirada/", {"motivo": motivo}, format="json"
    )


def _no_dia(cenario: Cenario, relogio: Any, quando: str) -> None:  # noqa: F811
    relogio.em(quando)
    cenario.moto._tokens.clear()  # o token do dia anterior venceu


def test_loc_17_ca_451_04_09_10_registrar_retirada_quem_e_quando(cenario, locacao) -> None:  # noqa: F811
    """Decisão do dono de 11 nov: o botão é do administrador e do gerente da filial, só com a
    locação `aguardando_retirada`, e exige a vistoria de saída (409 `vistoria_saida_pendente`)."""
    for quem in ("Bruna", "João", "Lúcia"):
        assert cenario.detalhe(locacao.pk, quem)["acoes"]["registrar_retirada"] is False
        assert _bloco(cenario, locacao, quem)["registrar_retirada"] is None
        assert _registrar(cenario, locacao, quem).status_code == 403
    for quem in ("Mariana", "Rodrigo"):
        assert cenario.detalhe(locacao.pk, quem)["acoes"]["registrar_retirada"] is True
    botao = _bloco(cenario, locacao, "Rodrigo")["registrar_retirada"]
    assert botao == {
        "rotulo": "Registrar retirada",
        "disponivel": False,
        "aviso": "Faça a vistoria de saída antes da retirada.",
        "titulo": "Registrar retirada?",
        "faltas": [
            "Falta a vistoria de saída",
            "Falta enviar o contrato",
            "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00",
        ],
        "motivo_obrigatorio": "Informe o motivo.",
    }
    sem_vistoria = _registrar(cenario, locacao)
    assert (sem_vistoria.status_code, sem_vistoria.json()["codigo"]) == (
        409,
        "vistoria_saida_pendente",
    )
    assert sem_vistoria.json()["mensagem"] == "Faça a vistoria de saída antes da retirada."

    _vistoriar(locacao.pk)
    botao = _bloco(cenario, locacao, "Rodrigo")["registrar_retirada"]
    assert (botao["disponivel"], botao["aviso"]) == (True, None)
    assert botao["faltas"] == [
        "Falta enviar o contrato",
        "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00",
    ]
    sem_motivo = _registrar(cenario, locacao, motivo="  ")
    assert sem_motivo.status_code == 400
    assert sem_motivo.json()["campos"]["motivo"] == ["Informe o motivo."]
    assert _status(locacao) == "aguardando_retirada"

    assert _registrar(cenario, locacao).status_code == 200
    de_novo = _registrar(cenario, locacao)
    assert (de_novo.status_code, de_novo.json()["codigo"]) == (409, "transicao_locacao")


def test_loc_17_ca_451_11_12_13_retirada_a_mao_exemplo_da_regra(
    cenario,  # noqa: F811
    relogio,
    relogio_jwt,
) -> None:
    """O exemplo da LOC-17: semanal Street de 05 nov 10:00, vistoria feita, sem assinatura nem
    pagamento, retirada pelo gerente em 07 nov. A parcela 1 e a caução vencem em 07 nov
    (`vence_hoje`), atrasam em 08 nov com o atraso contado de 08 nov; a parcela 2 continua em
    12 nov e o fim previsto em 19 nov 10:00."""
    _completar(cenario.clientes["Lucas"])
    _no_dia(cenario, relogio, "2026-11-05 09:00")
    criada = cenario.confirmada(inicio="2026-11-05T13:00:00Z", periodos=2)
    locacao = Locacao.objects.get(pk=criada["id"])
    _vistoriar(locacao.pk)
    _no_dia(cenario, relogio, "2026-11-07 09:00")

    resposta = _registrar(cenario, locacao)
    assert resposta.status_code == 200, resposta.json()
    detalhe = resposta.json()
    assert detalhe["status"] == "ativa"
    assert detalhe["para_retirar"] is None
    assert Veiculo.objects.get(pk=locacao.veiculo_id).status == "alugado"
    evento = _retirada(locacao)
    assert evento.ator_nome == "Rodrigo"
    assert evento.motivo == (
        f"Retirada registrada à mão. Motivo: {MOTIVO}. "
        "Faltava: assinatura do contrato e 1º pagamento"
    )
    assert evento.depois["retirada_a_mao"] is True

    contas = {p["rotulo"]: p for p in detalhe["parcelas"]}
    assert (contas["Parcela 1"]["vencimento"], contas["Parcela 1"]["status"]) == (
        "2026-11-07",
        "vence_hoje",
    )
    assert (contas["Caução"]["vencimento"], contas["Caução"]["status"]) == (
        "2026-11-07",
        "vence_hoje",
    )
    assert contas["Parcela 2"]["vencimento"] == "2026-11-12"
    assert (
        Locacao.objects.get(pk=locacao.pk).fim_previsto.isoformat() == "2026-11-19T13:00:00+00:00"
    )

    assert detalhe["situacao"]["codigo"] == "pendencia_retirada"
    assert detalhe["situacao"]["rotulo"] == "Faltam assinatura e pagamento"
    assert _passos(detalhe["pendencias_retirada"]) == [
        ("contrato", False, "Falta enviar o contrato", ["Enviar contrato"]),
        (
            "pagamento",
            False,
            "Falta receber R$ 629,00: 1ª semana R$ 329,00 e caução R$ 300,00",
            [],
        ),
    ]
    precisam = cenario.moto.api("Rodrigo").get(LISTA, {"aba": "precisam_acao"}).json()
    assert locacao.pk in [linha["id"] for linha in precisam["resultados"]]

    _no_dia(cenario, relogio, "2026-11-08 09:00")
    no_receber = cenario.moto.api("Rodrigo").get(f"{CONTAS}{contas['Parcela 1']['id']}/").json()
    assert (no_receber["status"], no_receber["dias_atraso"]) == ("atrasada", 1)  # não de 05 nov
    linha = cenario.detalhe(locacao.pk, "Rodrigo")
    assert {p["rotulo"]: p["status"] for p in linha["parcelas"]}["Parcela 1"] == "atrasada"


def test_loc_17_ca_451_14_pago_e_assinado_depois_so_tira_a_pendencia(
    cenario,  # noqa: F811
    locacao,
    django_capture_on_commit_callbacks,
) -> None:
    """Depois do botão, a retirada sozinha não roda de novo: pagar e assinar só tiram a
    pendência, sem outra "Retirada" e sem mexer nas contas."""
    _vistoriar(locacao.pk)
    assert _registrar(cenario, locacao).status_code == 200
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    detalhe = cenario.detalhe(locacao.pk, "Rodrigo")
    assert [p["codigo"] for p in detalhe["pendencias_retirada"]["passos"]] == ["contrato"]
    assert detalhe["situacao"]["rotulo"] == "Falta a assinatura"
    assert Locacao.objects.get(pk=locacao.pk).primeiro_pagamento_em is not None

    # "Enviar contrato" continua na locação ativa, e o cliente assina como antes.
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assinatura = _assinar(_token(), capturar=django_capture_on_commit_callbacks)
    assert assinatura.status_code == 200, assinatura.json()
    detalhe = cenario.detalhe(locacao.pk, "Rodrigo")
    assert detalhe["pendencias_retirada"] is None
    assert detalhe["situacao"]["codigo"] != "pendencia_retirada"
    assert detalhe["status"] == "ativa"
    assert (
        EventoAuditoria.objects.filter(
            objeto_tipo="locacao", objeto_id=locacao.pk, acao="locacao.retirada"
        ).count()
        == 1
    )


def test_loc_17_situacao_falta_o_1o_pagamento_depois_da_retirada_a_mao(
    cenario,  # noqa: F811
    locacao,
    django_capture_on_commit_callbacks,
) -> None:
    """PR #541: com o contrato assinado antes do botão e o pagamento faltando, a situação diz
    "Falta o 1º pagamento" (o código continua `pendencia_retirada`)."""
    _vistoriar(locacao.pk)
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assinatura = _assinar(_token(), capturar=django_capture_on_commit_callbacks)
    assert assinatura.status_code == 200, assinatura.json()
    assert _registrar(cenario, locacao).status_code == 200
    situacao = cenario.detalhe(locacao.pk, "Rodrigo")["situacao"]
    assert situacao["codigo"] == "pendencia_retirada"
    assert situacao["rotulo"] == "Falta o 1º pagamento"


def _pagamento_na_lista(cenario: Cenario, locacao: Locacao) -> dict[str, Any]:  # noqa: F811
    todas = cenario.moto.api("Rodrigo").get(LISTA).json()["resultados"]
    pagamento: dict[str, Any] = next(x for x in todas if x["id"] == locacao.pk)["pagamento"]
    return pagamento


def test_loc_17_fin_01_coluna_pagamento_da_retirada_a_mao_sem_nada_pago(
    cenario,  # noqa: F811
    locacao,
) -> None:
    """T-466 (achado A1 de 12 nov, LOC-2871): retirada à mão com a parcela 1 e a caução vencendo
    hoje e nada pago. Nada está atrasado (FIN-01), mas a coluna não pode dizer "Pago": diz o que
    falta, como na `aguardando_retirada`. Com a LOC-17 do PR #554 (T-456), a caução paga não vira
    "R$ 300,00 pago": some do "Falta" e fica no texto dela."""
    _vistoriar(locacao.pk)
    assert _registrar(cenario, locacao).status_code == 200
    pagamento = _pagamento_na_lista(cenario, locacao)
    assert (pagamento["rotulo"], pagamento["tom"]) == (
        "Falta R$ 629,00 · 1ª semana e caução",
        "alerta",
    )
    assert (pagamento["em_aberto_centavos"], pagamento["pago_centavos"]) == (0, 0)

    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    pagamento = _pagamento_na_lista(cenario, locacao)
    assert (pagamento["rotulo"], pagamento["caucao"]["rotulo"]) == (
        "Falta R$ 329,00 · 1ª semana",
        "Caução R$ 300,00 · paga",
    )

    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _pagamento_na_lista(cenario, locacao)["rotulo"] == "Pix"  # parcela 2 por vencer


def test_loc_17_retirada_sozinha_nao_tem_pendencia(
    cenario,  # noqa: F811
    locacao,
    django_capture_on_commit_callbacks,
) -> None:
    _vistoriar(locacao.pk)
    assert _abrir(cenario).status_code == 201
    assert _receber(cenario, _conta(locacao), 32900).status_code == 200
    assert _receber(cenario, _conta(locacao, "caucao"), 30000).status_code == 200
    assert _gerar(cenario, django_capture_on_commit_callbacks, locacao.pk).status_code == 202
    assert _assinar(_token(), capturar=django_capture_on_commit_callbacks).status_code == 200
    salva = Locacao.objects.get(pk=locacao.pk)
    assert (salva.status, salva.retirada_a_mao) == ("ativa", False)
    assert salva.retirada_em is not None
    assert cenario.detalhe(locacao.pk)["pendencias_retirada"] is None


def test_loc_17_contrato_sem_assinatura_7_dias_depois_avisa_os_gerentes(
    cenario,  # noqa: F811
    locacao,
    relogio,
) -> None:
    from apps.locacoes import services as locacoes_services
    from apps.notificacoes.models import Notificacao

    _vistoriar(locacao.pk)
    assert _registrar(cenario, locacao).status_code == 200  # 07 out, 10:00
    relogio.em("2026-10-14 09:59")
    assert locacoes_services.avisar_assinaturas_pendentes_da_retirada() == 0
    relogio.em("2026-10-14 10:00")
    assert locacoes_services.avisar_assinaturas_pendentes_da_retirada() == 1
    assert locacoes_services.avisar_assinaturas_pendentes_da_retirada() == 0  # idempotente
    aviso = Notificacao.objects.get(tipo="retirada_sem_assinatura")
    assert aviso.destinatario_id == cenario.pessoas["Rodrigo"].pk
    assert aviso.titulo == "Contrato da LOC-2856 sem assinatura 7 dias depois da retirada"
    assert aviso.link == f"/locacoes/{locacao.pk}"


def test_loc_17_aut_17_nao_cancela_a_retirada_a_mao(cenario, locacao, relogio) -> None:  # noqa: F811
    from apps.locacoes import services as locacoes_services

    _vistoriar(locacao.pk)
    assert _registrar(cenario, locacao).status_code == 200
    relogio.em("2026-10-12 00:10")
    assert locacoes_services.cancelar_nao_retiradas() == 0
    assert _status(locacao) == "ativa"


def test_loc_17_beat_tem_o_aviso_da_assinatura() -> None:
    from django.conf import settings

    tarefa = settings.CELERY_BEAT_SCHEDULE["loc_17_avisar_assinaturas_pendentes"]
    assert tarefa["task"] == "loc_17_avisar_assinaturas_pendentes_de_todas"


def test_loc_17_ca_451_05_impedimento_aparece_como_motivo(cenario) -> None:  # noqa: F811
    """O cadastro incompleto (CLI-03), a CNH vencida há mais de 30 dias (CLI-02) e o CRLV
    vencido (VEI-03) aparecem no passo da vistoria, com a frase de cada um."""
    locacao = _confirmada(cenario)  # o Lucas do cenário está sem endereço
    assert _passos(_bloco(cenario, locacao))[0][2] == (
        "Complete o cadastro do cliente antes da retirada."
    )
    _completar(cenario.clientes["Lucas"])
    Cliente.objects.filter(pk=locacao.cliente_id).update(cnh_validade=date(2026, 8, 1))
    assert _passos(_bloco(cenario, locacao))[0][2] == (
        "A CNH do cliente está vencida há mais de 30 dias."
    )
    Cliente.objects.filter(pk=locacao.cliente_id).update(cnh_validade=date(2030, 1, 1))
    DocumentoVeiculo.objects.create(
        veiculo_id=locacao.veiculo_id, tipo="crlv", validade=date(2026, 10, 6)
    )
    texto = _passos(_bloco(cenario, locacao))[0][2]
    assert texto.startswith("Renove o ") and texto.endswith("antes da retirada.")


def test_loc_17_ca_451_06_quem_nao_pode_nao_ve_a_acao(cenario, locacao) -> None:  # noqa: F811
    """Vistoriador: só "Fazer vistoria de saída", sem valores. Bruna: as três. Financeiro:
    "Registrar pagamento", sem "Enviar contrato"."""
    joao = _bloco(cenario, locacao, "João")
    assert _passos(joao) == [
        ("vistoria_saida", False, "Falta a vistoria de saída", ["Fazer vistoria de saída"]),
        ("contrato", False, "Falta enviar o contrato", []),
        ("pagamento", False, "Falta o 1º pagamento", []),
    ]
    assert "parcelas" not in cenario.detalhe(locacao.pk, "João")

    bruna = cenario.detalhe(locacao.pk, "Bruna")
    assert [a["rotulo"] for p in bruna["para_retirar"]["passos"] for a in p["acoes"]] == [
        "Fazer vistoria de saída",
        "Enviar contrato",
    ]
    assert all(p["acoes"]["receber"] for p in bruna["parcelas"])

    lucia = cenario.detalhe(locacao.pk, "Lúcia")
    assert [a["rotulo"] for p in lucia["para_retirar"]["passos"] for a in p["acoes"]] == []
    assert all(p["acoes"]["receber"] for p in lucia["parcelas"])


def test_loc_17_situacao_da_linha_segue_a_ordem_dos_passos(cenario, locacao) -> None:  # noqa: F811
    """O texto da linha é o primeiro passo que falta: vistoria, assinatura, pagamento."""
    assert cenario.detalhe(locacao.pk)["situacao"]["rotulo"] == "Aguardando vistoria"
    _vistoriar(locacao.pk)
    assert cenario.detalhe(locacao.pk)["situacao"]["rotulo"] == "Aguardando assinatura"


def test_loc_17_fora_de_aguardando_retirada_sem_bloco(cenario) -> None:  # noqa: F811
    """O rascunho não tem "Para retirar"."""
    rascunho = cenario.criar()
    assert cenario.detalhe(rascunho["id"])["para_retirar"] is None
