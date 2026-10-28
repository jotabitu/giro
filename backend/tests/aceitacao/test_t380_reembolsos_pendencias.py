"""T-380 · Listas de reembolsos e de pendências do pagamento (`financeiro.md`, telas da T-360).

Cenário da T-015 com a carteira de outubro, em 07 out 2026: Juliana com R$ 183,00 de caução a
devolver por Pix (DEV-02), três reembolsos feitos no mês e um em setembro. Nas pendências, o Pix
do Carlos (LOC-2841, 29940 vencida em 30 set, com juros no contrato: 30609 em 07 out) pago com
R$ 299,40 (AUT-05).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import connection

from apps.financeiro import selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import CobrancaExterna, ContaReceber, PendenciaPagamento, Reembolso
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from comum import estados
from comum.documentos import placa_com_hifen

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _contrato_com_juros, _jpg
from .test_t017_financeiro import com_carteira  # noqa: F401 - fixture
from .test_t317_varredura_suporte import _suporte

REEMBOLSOS = "/api/financeiro/reembolsos/"
PENDENCIAS = "/api/financeiro/pendencias-pagamento/"
FUSO = ZoneInfo("America/Sao_Paulo")


def _em(dia: date) -> datetime:
    return datetime(dia.year, dia.month, dia.day, 15, 0, tzinfo=FUSO)


def _reembolso(cenario, locacao: Locacao, cliente: str, valor: int, **campos) -> Reembolso:  # noqa: F811
    feito_em = campos.pop("feito_em", None)
    return Reembolso.objects.create(
        filial=locacao.filial,
        cliente=cenario.cliente(cliente),
        valor_centavos=valor,
        forma=campos.pop("forma", "pix"),
        status="feito" if feito_em else "a_fazer",
        feito_em=feito_em,
        origem_tipo=campos.pop("origem_tipo", "devolucao"),
        origem_id=campos.pop("origem_id", 1),
        origem_codigo=locacao.codigo,
        **campos,
    )


@pytest.fixture
def reembolsos(cenario, com_carteira) -> dict[str, Reembolso]:  # noqa: F811
    loc = com_carteira["LOC-2841"]
    return {
        "Juliana": _reembolso(
            cenario,
            loc,
            "Juliana",
            18300,
            motivo="Caução de R$ 600,00 menos diárias e acerto",
        ),
        "Lucas": _reembolso(
            cenario,
            loc,
            "Lucas",
            30000,
            origem_tipo="locacao",
            origem_id=loc.pk,
            forma="estorno_cartao",
            feito_em=_em(date(2026, 10, 7)),
        ),
        "Carlos": _reembolso(cenario, loc, "Carlos", 40000, feito_em=_em(date(2026, 10, 3))),
        "Diego": _reembolso(cenario, loc, "Diego", 40000, feito_em=_em(date(2026, 10, 1))),
        "Setembro": _reembolso(cenario, loc, "Lucas", 12000, feito_em=_em(date(2026, 9, 20))),
    }


def test_dev_02_lista_de_reembolsos_indicadores_e_filtros(cenario, com_carteira, reembolsos):  # noqa: F811
    api = cenario.moto.api("Lúcia")
    corpo = api.get(REEMBOLSOS).json()
    assert corpo["indicadores"] == {
        "a_fazer": {"valor_centavos": 18300, "quantidade": 1, "texto": "1 cliente com devolução"},
        "feitos": {"valor_centavos": 110000, "quantidade": 3, "texto": "3 reembolsos feitos"},
    }
    assert corpo["contagens"] == {"a_fazer": 1, "feito": 3, "todos": 4}
    assert (corpo["proximo"], corpo["anterior"]) == (None, None)
    [juliana] = corpo["resultados"]
    loc = com_carteira["LOC-2841"]
    assert juliana["cliente"]["nome"] == "Juliana Rocha"
    assert juliana["origem"] == {
        "tipo": "devolucao",
        "codigo": "LOC-2841",
        "id": loc.pk,  # "Ver acerto" abre a locação
        "veiculo": f"{placa_com_hifen(loc.veiculo.placa)} · {loc.veiculo.marca} "
        f"{loc.veiculo.modelo}",
    }
    assert juliana["origem_rotulo"] == "Devolução com caução"
    assert juliana["motivo"] == "Caução de R$ 600,00 menos diárias e acerto"
    assert (juliana["forma"], juliana["forma_rotulo"]) == ("pix", "Pix")
    assert (juliana["status"], juliana["status_rotulo"]) == ("a_fazer", "A fazer")
    assert (juliana["valor_centavos"], juliana["feito_em"], juliana["feito_por"]) == (
        18300,
        None,
        None,
    )
    assert juliana["comprovante"] is None
    assert juliana["acoes"] == {"marcar_feito": True}

    feitos = api.get(REEMBOLSOS, {"status": "feito"}).json()["resultados"]
    assert [r["valor_centavos"] for r in feitos] == [40000, 40000, 30000]  # sem o de setembro
    cancelamento = next(r for r in feitos if r["forma"] == "estorno_cartao")
    assert cancelamento["origem"]["tipo"] == "cancelamento"
    assert cancelamento["origem_rotulo"] == "Locação cancelada antes da retirada"
    assert cancelamento["forma_rotulo"] == "Estorno no cartão"
    assert cancelamento["acoes"] == {"marcar_feito": False}
    assert len(api.get(REEMBOLSOS, {"status": "todos"}).json()["resultados"]) == 4

    # O período vale para os feitos; os a fazer não dependem dele.
    hoje = api.get(REEMBOLSOS, {"periodo": "hoje"}).json()
    assert hoje["indicadores"]["a_fazer"]["quantidade"] == 1
    assert hoje["indicadores"]["feitos"] == {
        "valor_centavos": 30000,
        "quantidade": 1,
        "texto": "1 reembolso feito",
    }
    assert hoje["contagens"] == {"a_fazer": 1, "feito": 1, "todos": 2}

    # A busca muda as contagens das abas, não os indicadores.
    busca = api.get(REEMBOLSOS, {"busca": "juliana", "status": "todos"}).json()
    assert busca["contagens"] == {"a_fazer": 1, "feito": 0, "todos": 1}
    assert busca["indicadores"]["feitos"]["quantidade"] == 3
    assert api.get(REEMBOLSOS, {"busca": "LOC-2841"}).json()["contagens"]["todos"] == 4

    # Vendedor não vê a lista (administrador, gerente e financeiro).
    assert cenario.moto.api("Bruna").get(REEMBOLSOS).status_code == 403


def test_dev_02_marcar_feito_devolve_o_item_da_lista(cenario, reembolsos):  # noqa: F811
    juliana = reembolsos["Juliana"]
    resposta = cenario.moto.api("Lúcia").post(
        f"{REEMBOLSOS}{juliana.pk}/feito/", {"comprovante": _jpg("pix.jpg")}, format="multipart"
    )
    assert resposta.status_code == 200, resposta.json()
    item = resposta.json()
    assert (item["status"], item["status_rotulo"]) == ("feito", "Feito")
    assert item["feito_por"]["nome"] == cenario.pessoas["Lúcia"].nome
    assert item["comprovante"]["url"]
    assert item["acoes"] == {"marcar_feito": False}
    repetido = cenario.moto.api("Lúcia").post(f"{REEMBOLSOS}{juliana.pk}/feito/")
    assert (repetido.status_code, repetido.json()["codigo"]) == (409, "transicao_reembolso")


def test_plt_07_reembolso_suporte_sem_marcar_feito(cenario, relogio_jwt, reembolsos):  # noqa: F811
    """M-02 da T-384: o suporte lê a lista sem o comprovante (AUD-09) e sem marcar feito."""
    financeiro.marcar_reembolso_feito(
        reembolsos["Juliana"], usuario=cenario.pessoas["Lúcia"], comprovante=_jpg("pix.jpg")
    )
    suporte = _suporte(cenario)
    corpo = suporte.get(REEMBOLSOS, {"status": "todos"}).json()
    assert corpo["contagens"]["todos"] == 4
    juliana = next(r for r in corpo["resultados"] if r["id"] == reembolsos["Juliana"].pk)
    assert juliana["comprovante"] is None
    assert all(r["comprovante"] is None for r in corpo["resultados"])
    assert all(r["acoes"] == {"marcar_feito": False} for r in corpo["resultados"])

    a_fazer = _reembolso(cenario, Locacao.objects.get(codigo="LOC-2841"), "Diego", 5000)
    lista = suporte.get(REEMBOLSOS).json()["resultados"]
    assert [(r["id"], r["acoes"]["marcar_feito"]) for r in lista] == [(a_fazer.pk, False)]
    recusa = suporte.post(f"{REEMBOLSOS}{a_fazer.pk}/feito/", {}, format="multipart")
    assert (recusa.status_code, recusa.json()["codigo"]) == (403, "PLT-07")

    # Quem cadastra continua vendo o comprovante, com a URL de 15 minutos (AUD-05).
    lucia = cenario.moto.api("Lúcia").get(REEMBOLSOS, {"status": "feito"}).json()["resultados"]
    assert next(r for r in lucia if r["id"] == reembolsos["Juliana"].pk)["comprovante"]["url"]


# --- Pendências do pagamento (AUT-05) ---


def _carlos(com_carteira) -> ContaReceber:  # noqa: F811
    return ContaReceber.objects.get(
        origem_tipo="locacao", origem_id=com_carteira["LOC-2841"].pk, vencimento=date(2026, 9, 30)
    )


def _rafael(com_carteira) -> ContaReceber:  # noqa: F811
    return ContaReceber.objects.get(origem_tipo="locacao", origem_id=com_carteira["LOC-2790"].pk)


def _pendencia(
    conta: ContaReceber, externo_id: str, motivo: str, pago: int | None, status: str = "aguardando"
):
    cobranca = CobrancaExterna.objects.create(
        status=status,
        conta_receber=conta,
        tipo="pix",
        externo_id=externo_id,
        valor_centavos=30609,
        vence_em=date(2026, 10, 8),
        gerada_no_dia=date(2026, 10, 7),
    )
    return PendenciaPagamento.objects.create(
        cobranca=cobranca, motivo=motivo, valor_pago_centavos=pago
    )


@pytest.fixture
def pendencias(com_carteira) -> dict[str, PendenciaPagamento]:  # noqa: F811
    _contrato_com_juros(com_carteira["LOC-2841"])
    return {
        "carlos": _pendencia(_carlos(com_carteira), "pay_88192", "valor_diferente", 29940),
        "rafael": _pendencia(_rafael(com_carteira), "pay_88200", "estornada_no_parceiro", 134700),
    }


def test_aut_05_lista_de_pendencias_indicadores_e_filtros(cenario, com_carteira, pendencias):  # noqa: F811
    api = cenario.moto.api("Lúcia")
    ignorada = api.post(
        f"{PENDENCIAS}{pendencias['rafael'].pk}/resolver/",
        {"acao": "ignorar", "motivo": "Cliente pagou no caixa"},
        format="json",
    )
    assert ignorada.status_code == 200, ignorada.json()
    assert ignorada.json()["resolucao"]["texto"] == "Ignorada: Cliente pagou no caixa"
    assert ignorada.json()["acoes"] == {"resolver": False, "baixar": False}

    corpo = api.get(PENDENCIAS).json()
    assert corpo["indicadores"] == {
        "abertas": {"quantidade": 1, "valor_centavos": 29940, "texto": "R$ 299,40 em análise"},
        "resolvidas": {"quantidade": 1, "valor_centavos": 134700, "texto": "1 resolvida no mês"},
    }
    assert corpo["contagens"] == {"aberta": 1, "resolvida": 1, "todas": 2}
    [carlos] = corpo["resultados"]
    conta = _carlos(com_carteira)
    assert carlos["cobranca"] == {
        "id_no_parceiro": "pay_88192",
        "forma": "pix",
        "forma_rotulo": "Pix",
    }
    assert carlos["cliente"]["id"] == conta.cliente_id
    assert carlos["origem"] == {
        "codigo": "LOC-2841",
        "conta_id": conta.pk,
        "parcela": f"parcela {conta.numero_parcela} de {conta.total_parcelas}",
    }
    assert carlos["motivo"] == "valor_diferente"
    assert carlos["motivo_rotulo"] == "Valor pago diferente"
    assert carlos["detalhe"] == "Pagou R$ 299,40; a conta estava em R$ 306,09 (falta R$ 6,69)."
    assert (carlos["status"], carlos["status_rotulo"], carlos["resolucao"]) == (
        "aberta",
        "Aberta",
        None,
    )
    assert carlos["acoes"] == {"resolver": True, "baixar": True}

    resolvidas = api.get(PENDENCIAS, {"status": "resolvida"}).json()["resultados"]
    assert [p["motivo_rotulo"] for p in resolvidas] == ["Estornada no parceiro"]
    assert resolvidas[0]["detalhe"] == "O parceiro estornou o pagamento de R$ 1.347,00."
    assert resolvidas[0]["resolucao"]["em"].startswith("2026-10-07")
    assert len(api.get(PENDENCIAS, {"status": "todas"}).json()["resultados"]) == 2

    busca = api.get(PENDENCIAS, {"busca": "pay_88192", "status": "todas"}).json()
    assert busca["contagens"] == {"aberta": 1, "resolvida": 0, "todas": 1}
    assert busca["indicadores"]["resolvidas"]["quantidade"] == 1
    assert api.get(PENDENCIAS, {"busca": "LOC-2790"}).json()["contagens"]["resolvida"] == 1

    # Só administrador e financeiro; a empresa inteira, mesmo com uma filial no cabeçalho.
    assert cenario.moto.api("Rodrigo").get(PENDENCIAS).status_code == 403
    centro = cenario.moto.api("Lúcia", HTTP_X_FILIAL=str(cenario.frota.centro.pk))
    assert centro.get(PENDENCIAS, {"status": "todas"}).json()["contagens"]["todas"] == 2


def test_aut_05_acoes_da_pendencia_pela_conta(cenario, relogio_jwt, com_carteira, pendencias):  # noqa: F811
    rafael = _rafael(com_carteira)
    api = cenario.moto.api("Lúcia")
    abertas = {p["motivo"]: p for p in api.get(PENDENCIAS).json()["resultados"]}
    assert abertas["valor_diferente"]["acoes"] == {"resolver": True, "baixar": True}
    # Estornada no parceiro: só ignorar, mesmo com a conta do Rafael aberta.
    assert abertas["estornada_no_parceiro"]["acoes"] == {"resolver": True, "baixar": False}

    # A conta deixou de estar aberta: só ignorar.
    estados.transicionar(rafael, "cancelada", motivo="Teste", acao="conta_receber.cancelar")
    sem_conta = _pendencia(rafael, "pay_88300", "sem_conta", 134700, "divergente")
    item = next(p for p in api.get(PENDENCIAS).json()["resultados"] if p["id"] == sem_conta.pk)
    assert item["motivo_rotulo"] == "A conta já não estava aberta"
    assert item["detalhe"] == "Pagou R$ 1.347,00, mas a conta já estava cancelada."
    assert item["acoes"] == {"resolver": True, "baixar": False}
    baixar = api.post(
        f"{PENDENCIAS}{sem_conta.pk}/resolver/", {"acao": "baixar", "motivo": "x"}, format="json"
    )
    assert (baixar.status_code, baixar.json()["codigo"]) == (409, "transicao_conta")

    # Baixada pela conta aberta: o texto da resolução e a pendência fechada.
    carlos = pendencias["carlos"]
    baixada = api.post(
        f"{PENDENCIAS}{carlos.pk}/resolver/",
        {"acao": "baixar", "motivo": "Diferença de juros perdoada"},
        format="json",
    )
    assert baixada.status_code == 200, baixada.json()
    assert baixada.json()["resolucao"]["texto"] == "Baixada: Diferença de juros perdoada"
    repetida = api.post(
        f"{PENDENCIAS}{carlos.pk}/resolver/", {"acao": "ignorar", "motivo": "x"}, format="json"
    )
    assert (repetida.status_code, repetida.json()["codigo"]) == (409, "transicao_pendencia")

    # O suporte lê, mas as ações vêm desligadas (PLT-07).
    lista = _suporte(cenario).get(PENDENCIAS, {"status": "todas"}).json()["resultados"]
    assert lista and all(p["acoes"] == {"resolver": False, "baixar": False} for p in lista)


def test_plt_07_pendencia_suporte_resolver_403(cenario, relogio_jwt, com_carteira, pendencias):  # noqa: F811
    """Parecer da Segurança: o suporte em "ver e editar" não resolve pendência (T-324)."""
    carlos = _carlos(com_carteira)
    antes = (carlos.status, carlos.pago_em, carlos.forma)
    suporte = _suporte(cenario)
    for pendencia, corpo in (
        (pendencias["carlos"], {"acao": "baixar", "motivo": "Diferença de juros perdoada"}),
        (pendencias["rafael"], {"acao": "ignorar", "motivo": "Cliente pagou no caixa"}),
        (pendencias["carlos"], {}),  # o 403 vem antes de validar o corpo
    ):
        recusa = suporte.post(f"{PENDENCIAS}{pendencia.pk}/resolver/", corpo, format="json")
        assert (recusa.status_code, recusa.json()["codigo"]) == (403, "PLT-07")

    carlos.refresh_from_db()
    assert (carlos.status, carlos.pago_em, carlos.forma) == antes
    for pendencia in pendencias.values():
        pendencia.refresh_from_db()
        assert (pendencia.status, pendencia.resolucao) == ("aberta", "")


def test_plt_12_pendencias_essencial_403(cenario, planos, pendencias):  # noqa: F811
    Empresa._base_manager.filter(pk=cenario.moto.empresa.pk).update(plano=planos["Essencial"])
    api = cenario.moto.api("Lúcia")
    for resposta in (
        api.get(PENDENCIAS),
        api.post(
            f"{PENDENCIAS}{pendencias['carlos'].pk}/resolver/",
            {"acao": "ignorar", "motivo": "x"},
            format="json",
        ),
    ):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == "PLT-12"
    # Os reembolsos não dependem do recebimento pelo parceiro.
    assert api.get(REEMBOLSOS).status_code == 200


def test_dev_02_aut_05_isolamento_entre_empresas(cenario, reembolsos, pendencias, empresa_b):  # noqa: F811
    """Dado da Moto Rápida (empresa A) não aparece na empresa B."""
    assert connection.schema_name == "empresa_b"
    _, extras = selectors.lista_de_reembolsos(
        selectors.base_dos_reembolsos(), {"status": "todos"}, date(2026, 10, 7)
    )
    assert extras["contagens"]["todos"] == 0
    _, extras = selectors.lista_de_pendencias(
        selectors.base_das_pendencias(), {"status": "todas"}, date(2026, 10, 7)
    )
    assert extras["contagens"]["todas"] == 0
