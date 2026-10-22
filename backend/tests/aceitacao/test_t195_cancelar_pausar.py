"""T-195 · Cancelar, pausar e apagar a assinatura da empresa (`docs/api/cancelamento.md`; PLT-06,
AUD-08, ADR 0025; CA-ASS-30 a 39, 42 a 46, 54 a 58, 60 e 69).

Relógio de referência (ADR 0021): Moto Rápida em teste de 07 a 21 out, FAT-0001 de R$ 449,00
vencendo em 22 out (período de 22 out a 21 nov), e as seguintes todo dia 22. Dados de referência
"Cancelamento da Moto Rápida" (a) a (f), "Pausa da Moto Rápida" e "Desfazer o cancelamento da
Moto Rápida".
"""

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from django.db import connection
from django_tenants.utils import schema_context, schema_exists

from apps.auditoria.models import EventoAuditoria
from apps.plataforma import banco, selectors, services
from apps.plataforma.calendario import Periodo
from apps.plataforma.models import (
    Dominio,
    Empresa,
    FaturaAssinatura,
    FormaPagamentoAssinatura,
    Plano,
    TipoFatura,
    UsoEmpresa,
)
from comum import arquivos
from integracoes.pagamentos import falso as pagamentos

from .conftest import cliente as cliente_http
from .test_t185_assinatura import (
    BEZERRA,
    SO_ADMINISTRADOR,
    SUPORTE_NAO_MEXE,
    MotoRapida,
    _criar_matriz,
    _mudar,
    _rotas_que_escrevem_na_suspensa,
)
from .test_t186b_faturas_cobranca import _ativa_com_boleto, _ativa_com_cartao, _baixar

ASSINATURA = "/api/assinatura/"
CANCELAMENTO = "/api/assinatura/cancelamento/"
PAUSA = "/api/assinatura/pausa/"
DADOS_FISCAIS = "/api/assinatura/dados-fiscais/"
FORMA = "/api/assinatura/forma-pagamento/"
HOST = "motorapida.localhost"
MARIANA = "mariana@motorapida.com.br"
JA_CANCELADA_21_NOV = {
    "codigo": "transicao_empresa",
    "mensagem": "A assinatura já está cancelada. Você tem acesso até 21 nov.",
}
SEM_CANCELAMENTO = {"codigo": "transicao_empresa", "mensagem": "Não há cancelamento para desfazer."}
SEM_PAUSA = {"codigo": "transicao_empresa", "mensagem": "Não há pausa para encerrar."}
EMPRESA_CANCELADA = {
    "codigo": "empresa_cancelada",
    "mensagem": (
        "Esta assinatura foi cancelada. Para pedir seus dados ou voltar, fale com a equipe Giro."
    ),
}


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    yield MotoRapida(criar_empresa())
    pagamentos.limpar()


def _em(relogio, dia: str, hora: str = "10:00") -> None:
    relogio.em(f"{dia} {hora}")


def _virar(relogio, dia: str, capturar=None) -> services.Virada:
    relogio.em(f"{dia} 00:05")
    if capturar is None:
        return services.virar_estados()
    with capturar(execute=True):
        virada = services.virar_estados()
    connection.set_schema_to_public()
    return virada


def _gerar(relogio, dia: str, capturar) -> services.Geracao:
    relogio.em(f"{dia} 06:00")
    with capturar(execute=True):
        geracao = services.gerar_faturas()
    connection.set_schema_to_public()
    return geracao


def _cancelar(api: Any, nome: str = "Moto Rápida", motivo: str = "preco_alto") -> Any:
    resposta = api.post(CANCELAMENTO, {"motivo": motivo, "nome_confirmacao": nome}, format="json")
    connection.set_schema_to_public()
    return resposta


def _pausar(api: Any, meses: int = 2) -> Any:
    resposta = api.post(PAUSA, {"meses": meses}, format="json")
    connection.set_schema_to_public()
    return resposta


def _erro(resposta: Any) -> dict[str, Any]:
    corpo = resposta.json()
    return {"codigo": corpo["codigo"], "mensagem": corpo["mensagem"]}


def _eventos(acao: str, schema: str) -> list[EventoAuditoria]:
    with schema_context(schema):
        return list(EventoAuditoria.objects.filter(acao=acao).order_by("id"))


def _status(moto: MotoRapida) -> str:
    return str(moto.recarregar().status)


def _codigos(moto: MotoRapida) -> dict[str, str]:
    faturas = FaturaAssinatura.objects.filter(empresa=moto.empresa).order_by("numero")
    return {f.codigo: f.status for f in faturas}


def _pausada_desde_22_nov(moto: MotoRapida, relogio) -> None:
    """`ativa` com a FAT-0001 paga, pausa de 2 meses pedida em 05 nov, `pausada` em 22 nov."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    assert _pausar(moto.api()).status_code == 200
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "pausada"


# --- Cancelar no teste (CA-ASS-30, caso (a)) ---


def test_plt_06_cancelar_no_teste(moto, relogio, django_capture_on_commit_callbacks):
    """Em 10 out: acesso até 21 out, FAT-0001 `cancelada`, `cancelada` em 22 out (não
    `suspensa`), apagamento em 20 jan 2027. O Pix automático é cancelado no parceiro na virada."""
    services.escolher_forma_pagamento(moto.recarregar(), "pix_automatico")
    autorizacao = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).autorizacao_externa_id
    _em(relogio, "2026-10-10")
    api = moto.api()
    tela = api.get(CANCELAMENTO)
    assert tela.status_code == 200, tela.json()
    tela = tela.json()
    assert tela["empresa"] == "Moto Rápida"
    assert tela["plano_resumo"] == "Plano Profissional · em teste até 21 out"
    assert [m["codigo"] for m in tela["motivos"]] == [
        "preco_alto",
        "faltou_funcao",
        "outro_sistema",
        "fechar_ou_pausar",
        "outro",
    ]
    assert tela["motivos"][0]["rotulo"] == "Preço alto para o meu tamanho"
    assert tela["alternativas"]["pausar"] is None  # CA-ASS-37: no teste, não oferece pausar
    assert tela["alternativas"]["mudar_para_essencial"] == {
        "plano": {
            "id": Plano.objects.get(nome="Essencial").pk,
            "nome": "Essencial",
            "preco_mensal_centavos": 19900,
        },
        "resumo": "Até 30 veículos, 1 filial e 3 usuários.",
        "cabe": False,
        "excede": {
            "veiculos": {"usado": 86, "limite": 30},
            "usuarios": {"usado": 5, "limite": 3},
        },
    }
    assert tela["o_que_acontece"] == [
        {"codigo": "acesso", "rotulo": "Acesso", "valor": "continua até 21 out"},
        {"codigo": "cobrancas", "rotulo": "Cobranças futuras", "valor": "nenhuma"},
        {"codigo": "dados", "rotulo": "Seus dados", "valor": "guardados por 90 dias"},
        {"codigo": "apagamento", "rotulo": "Depois de 90 dias", "valor": "apagados de vez"},
        {
            "codigo": "contratos",
            "rotulo": "Contratos dos seus clientes",
            "valor": "continuam válidos",
        },
    ]
    assert (tela["acesso_ate"], tela["cancelada_em"], tela["apagar_em"]) == (
        "2026-10-21",
        "2026-10-22",
        "2027-01-20",
    )
    assert tela["confirmacao"] == {"nome": "Moto Rápida"}
    assert tela["exportar"] == {
        "texto": (
            "Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro."
        )
    }

    resposta = _cancelar(api, motivo="outro_sistema")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["status"] == "em_teste"
    assert corpo["cancelamento"]["acesso_ate"] == "2026-10-21"
    assert corpo["cancelamento"]["motivo"] == "outro_sistema"
    assert corpo["cancelamento"]["rotulo"] == "Assinatura cancelada. Você tem acesso até 21 out."
    assert corpo["proxima_fatura"] is None
    assert corpo["acoes"]["cancelar"] is False
    assert corpo["acoes"]["desfazer_cancelamento"] is True
    assert corpo["acoes"]["mudar_plano"] is False
    fatura = moto.fatura("FAT-0001")
    assert (fatura.status, fatura.motivo_cancelamento) == ("cancelada", "cancelamento_assinatura")
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.cancelar", schema)[-1]
        assert evento.regra == "PLT-06"
        assert evento.depois["acesso_ate"] == "2026-10-21"
        assert evento.depois["apagar_em"] == "2027-01-20"
        assert evento.depois["faturas_canceladas"] == ["FAT-0001"]
    # Já cancelada: a tela de cancelar responde 409, e cancelar de novo também.
    assert _erro(api.get(CANCELAMENTO)) == {
        "codigo": "transicao_empresa",
        "mensagem": "A assinatura já está cancelada. Você tem acesso até 21 out.",
    }
    assert _cancelar(api).status_code == 409

    # A empresa opera normalmente até 21 out e vira `cancelada` em 22 out.
    _virar(relogio, "2026-10-21")
    assert _status(moto) == "em_teste"
    assert _virar(relogio, "2026-10-22", django_capture_on_commit_callbacks).estados == {
        "cancelada": 1
    }
    empresa = moto.recarregar()
    assert empresa.status == "cancelada"
    assert empresa.apagar_em == date(2027, 1, 20)
    assert empresa.cancelada_em is not None
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)
    assert (forma.forma, forma.autorizacao_externa_id) == ("", "")
    assert pagamentos.autorizacoes[autorizacao].status == "cancelada"
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.virar_cancelada", schema)[-1]
        assert (evento.ator_tipo, evento.regra) == ("sistema", "PLT-06")
    # Idempotente: a virada de novo no mesmo dia não muda nada.
    assert _virar(relogio, "2026-10-22").estados == {}


def test_plt_06_nome_nao_confere(moto, relogio):
    """CA-ASS-31: o nome confere sem espaços nas pontas ou repetidos e sem diferença de
    maiúsculas; os acentos contam. Diferente: 422, e nada muda. Sem motivo: 400."""
    _em(relogio, "2026-10-10")
    api = moto.api()
    resposta = _cancelar(api, nome="Moto Rapida")
    assert resposta.status_code == 422
    assert _erro(resposta) == {
        "codigo": "nome_nao_confere",
        "mensagem": "O nome digitado não confere com o nome da empresa.",
    }
    sem_motivo = api.post(CANCELAMENTO, {"nome_confirmacao": "Moto Rápida"}, format="json")
    assert sem_motivo.status_code == 400
    assert sem_motivo.json()["campos"] == {"motivo": ["Escolha o motivo."]}
    outro = _cancelar(api, motivo="caro")
    assert outro.json()["campos"] == {"motivo": ["Escolha o motivo."]}
    empresa = moto.recarregar()
    assert (empresa.acesso_ate, empresa.cancelamento_pedido_em) == (None, None)
    assert moto.fatura("FAT-0001").status == "aberta"
    assert _cancelar(api, nome="  moto   RÁPIDA ").status_code == 200


def test_plt_06_so_o_administrador_cancela(moto, relogio):
    """PLT-06: o Rodrigo e a Lúcia recebem 403; o suporte lê a tela e não cancela (PLT-07)."""
    _em(relogio, "2026-10-10")
    for nome in ("Rodrigo", "Lúcia"):
        resposta = _cancelar(moto.api(nome))
        assert resposta.status_code == 403
        assert _erro(resposta) == SO_ADMINISTRADOR
    suporte = moto.suporte("ver_editar")
    assert _erro(_cancelar(suporte)) == SUPORTE_NAO_MEXE
    assert suporte.get(CANCELAMENTO).status_code == 200
    acoes = suporte.get(ASSINATURA).json()["acoes"]
    connection.set_schema_to_public()
    assert not any(acoes.values())
    assert moto.recarregar().acesso_ate is None


# --- Em teste com a 1ª fatura paga (CA-ASS-54, caso (d)) ---


@pytest.mark.parametrize("desfaz", [False, True])
def test_plt_06_cancelar_no_teste_com_a_1a_paga(
    moto, relogio, desfaz, django_capture_on_commit_callbacks
):
    """FAT-0001 (22 out a 21 nov) paga em 12 out, cancela em 15 out: sem estorno, `em_teste` até
    21 out, `ativa` de 22 out a 21 nov, nenhuma fatura em 22 nov, `cancelada` em 22 nov,
    apagamento em 20 fev 2027. Desfazendo em 10 nov, nada nasce e a fatura de 22 nov é gerada em
    17 nov."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _em(relogio, "2026-10-12")
    moto.pagar_fat_0001(em="2026-10-12")
    _em(relogio, "2026-10-15")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["o_que_acontece"][0]["valor"] == "continua até 21 nov"
    assert (tela["acesso_ate"], tela["apagar_em"]) == ("2026-11-21", "2027-02-20")
    resposta = _cancelar(api)
    assert resposta.status_code == 200
    assert resposta.json()["cancelamento"]["acesso_ate"] == "2026-11-21"
    assert _codigos(moto) == {"FAT-0001": "paga"}  # sem estorno
    _virar(relogio, "2026-10-21")
    assert _status(moto) == "em_teste"
    _virar(relogio, "2026-10-22")
    assert _status(moto) == "ativa"
    if desfaz:
        _em(relogio, "2026-11-10")
        resposta = moto.api().delete(CANCELAMENTO)
        connection.set_schema_to_public()
        assert resposta.status_code == 200, resposta.json()
        assert resposta.json()["cancelamento"] is None
        assert _codigos(moto) == {"FAT-0001": "paga"}  # nada nasce
        assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 1
        _virar(relogio, "2026-11-22")
        assert _status(moto) == "ativa"
        return
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 0
    _virar(relogio, "2026-11-21")
    assert _status(moto) == "ativa"
    _virar(relogio, "2026-11-22")
    empresa = moto.recarregar()
    assert empresa.status == "cancelada"
    assert empresa.apagar_em == date(2027, 2, 20)
    assert _codigos(moto) == {"FAT-0001": "paga"}


# --- Ativa, mensal e anual (CA-ASS-32, CA-ASS-33, caso (b)) ---


def test_plt_06_cancelar_ativa(moto, relogio, django_capture_on_commit_callbacks):
    """Cancela em 05 nov: acesso até 21 nov, nenhuma fatura em 22 nov, `cancelada` em 22 nov,
    apagamento em 20 fev 2027. No painel da plataforma, "Cancela em 22 nov"."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["plano_resumo"] == "Plano Profissional · mensal"
    assert tela["o_que_acontece"][:2] == [
        {"codigo": "acesso", "rotulo": "Acesso", "valor": "continua até 21 nov"},
        {"codigo": "cobrancas", "rotulo": "Cobranças futuras", "valor": "nenhuma"},
    ]
    assert tela["alternativas"]["pausar"] == {
        "meses": [1, 2, 3],
        "inicio": "2026-11-22",
        "texto": "A pausa começa em 22 nov, no fim do período pago.",
    }
    resposta = _cancelar(api)
    assert resposta.status_code == 200
    assert resposta.json()["cancelamento"]["rotulo"] == (
        "Assinatura cancelada. Você tem acesso até 21 nov."
    )
    empresa = selectors.com_situacao().get(pk=moto.empresa.pk)
    assert selectors.situacao(empresa) == {
        "codigo": "cancelando",
        "rotulo": "Cancela em 22 nov",
        "tom": "alerta",
    }
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 0
    _virar(relogio, "2026-11-21")
    assert _status(moto) == "ativa"
    _virar(relogio, "2026-11-22")
    empresa = moto.recarregar()
    assert empresa.status == "cancelada"
    assert empresa.apagar_em == date(2027, 2, 20)
    assert _codigos(moto) == {"FAT-0001": "paga"}


def test_plt_06_cancelar_ativa_com_a_fatura_seguinte_emitida(
    moto, relogio, django_capture_on_commit_callbacks
):
    """CA-ASS-32: cancelando em 19 nov, depois de emitida a fatura de 22 nov (em 17 nov), essa
    fatura vira `cancelada` e a cobrança dela é cancelada no parceiro."""
    _ativa_com_boleto(moto)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    cobranca = moto.fatura("FAT-0002").cobranca_externa_id
    assert cobranca
    _em(relogio, "2026-11-19")
    assert _cancelar(moto.api()).status_code == 200
    fatura = moto.fatura("FAT-0002")
    assert (fatura.status, fatura.motivo_cancelamento) == ("cancelada", "cancelamento_assinatura")
    assert fatura.cobranca_externa_id is None
    assert pagamentos.cobrancas[cobranca].situacao.status == "cancelada"
    assert _eventos("empresa.cancelar", "public")[-1].depois["faturas_canceladas"] == ["FAT-0002"]


def test_plt_06_acesso_que_ja_acabou_termina_agora(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """CA-ASS-69, caso (e): `ativa`, FAT-0001 paga (período até 21 nov) e FAT-0002 de 22 nov
    emitida em boleto em 17 nov e não paga; cancela em 22 nov às 10:00: "termina agora"
    (`acesso_ate: null`), `cancelada` na hora, FAT-0002 `cancelada` e não devida, boleto cancelado
    no parceiro, nada a desfazer, aviso em 13 fev 2027 e apagamento em 20 fev 2027."""
    _ativa_com_boleto(moto)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    cobranca = moto.fatura("FAT-0002").cobranca_externa_id
    assert cobranca
    _em(relogio, "2026-11-22", "10:00")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["o_que_acontece"][:2] == [
        {"codigo": "acesso", "rotulo": "Acesso", "valor": "termina agora"},
        {"codigo": "cobrancas", "rotulo": "Cobranças futuras", "valor": "nenhuma"},
    ]
    assert (tela["acesso_ate"], tela["cancelada_em"], tela["apagar_em"]) == (
        None,
        "2026-11-22",
        "2027-02-20",
    )
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _cancelar(api)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["status"], corpo["cancelamento"]) == ("cancelada", None)
    assert corpo["acoes"]["desfazer_cancelamento"] is False
    empresa = moto.recarregar()
    assert (empresa.status, empresa.acesso_ate, empresa.apagar_em) == (
        "cancelada",
        None,
        date(2027, 2, 20),
    )
    fatura = moto.fatura("FAT-0002")
    assert (fatura.status, fatura.motivo_cancelamento) == ("cancelada", "cancelamento_assinatura")
    assert fatura.cobranca_externa_id is None
    assert pagamentos.cobrancas[cobranca].situacao.status == "cancelada"
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "cancelada"}
    assert _erro(api.delete(CANCELAMENTO)) == EMPRESA_CANCELADA
    connection.set_schema_to_public()
    with pytest.raises(services.Conflito) as erro:
        services.desfazer_cancelamento(moto.recarregar())
    assert erro.value.mensagem == "Não há cancelamento para desfazer."

    mailoutbox.clear()
    assert services.avisar_apagamentos(date(2027, 2, 12)) == 0
    assert services.avisar_apagamentos(date(2027, 2, 13)) == 1
    assert [m.to for m in mailoutbox] == [[MARIANA]]
    assert "20 fev 2027" in mailoutbox[0].body
    _em(relogio, "2027-02-19", "03:30")
    assert services.apagar_empresas() == 0
    _em(relogio, "2027-02-20", "03:30")
    assert services.apagar_empresas() == 1
    assert moto.recarregar().apagada_em is not None


def test_plt_06_ca_ass_69_fatura_do_dia_paga_no_cartao_mantem_acesso(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """CA-ASS-69, caso (f): `ativa` no cartão, FAT-0002 cobrada e paga em 22 nov às 08:00; cancela
    em 22 nov às 10:00: acesso continua até 21 dez, nenhuma fatura vence em 22 dez, `cancelada` em
    22 dez e dados apagados em 22 mar 2027."""
    _ativa_com_cartao(moto, relogio)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    _em(relogio, "2026-11-22", "08:00")
    with django_capture_on_commit_callbacks(execute=True):
        geracao = services.gerar_faturas()
    connection.set_schema_to_public()
    assert geracao.cartoes == {"cobrada": 1}
    fatura = moto.fatura("FAT-0002")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0002-cartao") == "baixada"
    assert moto.fatura("FAT-0002").status == "paga"

    _em(relogio, "2026-11-22", "10:00")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["o_que_acontece"][:2] == [
        {"codigo": "acesso", "rotulo": "Acesso", "valor": "continua até 21 dez"},
        {"codigo": "cobrancas", "rotulo": "Cobranças futuras", "valor": "nenhuma"},
    ]
    assert (tela["acesso_ate"], tela["cancelada_em"], tela["apagar_em"]) == (
        "2026-12-21",
        "2026-12-22",
        "2027-03-22",
    )
    resposta = _cancelar(api)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["status"] == "ativa"
    assert corpo["cancelamento"]["acesso_ate"] == "2026-12-21"
    assert corpo["cancelamento"]["rotulo"] == "Assinatura cancelada. Você tem acesso até 21 dez."
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "paga"}

    assert _gerar(relogio, "2026-12-17", django_capture_on_commit_callbacks).faturas == 0
    _virar(relogio, "2026-12-21")
    assert _status(moto) == "ativa"
    assert _virar(relogio, "2026-12-22", django_capture_on_commit_callbacks).estados == {
        "cancelada": 1
    }
    empresa = moto.recarregar()
    assert (empresa.status, empresa.apagar_em) == ("cancelada", date(2027, 3, 22))
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "paga"}

    mailoutbox.clear()
    assert services.avisar_apagamentos(date(2027, 3, 15)) == 1
    assert "22 mar 2027" in mailoutbox[0].body
    _em(relogio, "2027-03-22", "03:30")
    assert services.apagar_empresas() == 1
    assert moto.recarregar().apagada_em is not None


def test_plt_06_cancelar_anual_sem_devolucao(moto, relogio):
    """CA-ASS-33: anual de 22 out 2026 a 21 out 2027, cancela em 05 nov 2026: nada é devolvido e
    o acesso vai até 21 out 2027."""
    moto.estado(ciclo="anual", preco_contratado_centavos=449000, status="ativa")
    FaturaAssinatura.objects.filter(empresa=moto.empresa).update(
        ciclo="anual", valor_centavos=449000, periodo_fim=date(2027, 10, 21)
    )
    moto.pagar_fat_0001()
    _em(relogio, "2026-11-05")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["plano_resumo"] == "Plano Profissional · anual até 21 out 2027"
    assert tela["o_que_acontece"][:2] == [
        {
            "codigo": "acesso",
            "rotulo": "Acesso",
            "valor": "continua até 21 out 2027, sem devolução",
        },
        {
            "codigo": "cobrancas",
            "rotulo": "Cobranças futuras",
            "valor": "nenhuma. Os meses que faltam não são devolvidos.",
        },
    ]
    resposta = _cancelar(api)
    assert resposta.json()["cancelamento"]["rotulo"] == (
        "Assinatura cancelada. Você tem acesso até 21 out 2027."
    )
    empresa = moto.recarregar()
    assert (empresa.acesso_ate, empresa.apagar_em) == (date(2027, 10, 21), date(2028, 1, 20))
    assert _codigos(moto) == {"FAT-0001": "paga"}


def test_plt_06_cancelar_ativa_com_a_diferenca_do_upgrade_em_aberto(moto, relogio):
    """A diferença do upgrade continua devida: "nenhuma nova. A fatura FAT-0002, de R$ 304,84,
    continua devida." Ela não é cancelada."""
    _ativa_com_boleto(moto)
    services.criar_fatura(
        moto.recarregar(),
        tipo=TipoFatura.DIFERENCA_PLANO,
        vencimento=date(2026, 11, 8),
        periodo=Periodo(date(2026, 11, 1), date(2026, 11, 21)),
        plano=Plano.objects.get(nome="Completo"),
        ciclo="mensal",
        valor_centavos=30484,
    )
    _em(relogio, "2026-11-05")
    api = moto.api()
    cobrancas = api.get(CANCELAMENTO).json()["o_que_acontece"][1]["valor"]
    assert cobrancas == "nenhuma nova. A fatura FAT-0002, de R$ 304,84, continua devida."
    assert _cancelar(api).status_code == 200
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "aberta"}


# --- Inadimplente, suspensa e pausada: na hora (CA-ASS-34, caso (c)) ---


def test_plt_06_cancelar_inadimplente_para_a_regua(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Inadimplente em 25 out com a FAT-0001 atrasada: `cancelada` na hora, a FAT-0001 continua
    `atrasada` e devida, e a régua para (nada em 29 out, D+7, nem em 06 nov)."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    _virar(relogio, "2026-10-23")
    assert _status(moto) == "inadimplente"
    _em(relogio, "2026-10-25")
    api = moto.api()
    tela = api.get(CANCELAMENTO).json()
    assert tela["o_que_acontece"][:2] == [
        {"codigo": "acesso", "rotulo": "Acesso", "valor": "termina agora"},
        {
            "codigo": "cobrancas",
            "rotulo": "Cobranças futuras",
            "valor": "nenhuma nova. A fatura em atraso continua devida.",
        },
    ]
    assert (tela["acesso_ate"], tela["cancelada_em"], tela["apagar_em"]) == (
        None,
        "2026-10-25",
        "2027-01-23",
    )
    assert tela["alternativas"] == {"pausar": None, "mudar_para_essencial": None}
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _cancelar(api)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "cancelada"
    empresa = moto.recarregar()
    assert (empresa.status, empresa.acesso_ate, empresa.apagar_em) == (
        "cancelada",
        None,
        date(2027, 1, 23),
    )
    assert moto.fatura("FAT-0001").status == "atrasada"
    assert FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).forma == ""
    # A próxima requisição já é recusada, inclusive tentativa de desfazer (CA-ASS-45).
    assert _erro(moto.api().get(ASSINATURA)) == EMPRESA_CANCELADA
    assert _erro(moto.api().delete(CANCELAMENTO)) == EMPRESA_CANCELADA
    connection.set_schema_to_public()
    with pytest.raises(services.Conflito) as erro:
        services.desfazer_cancelamento(moto.recarregar())
    assert erro.value.mensagem == "Não há cancelamento para desfazer."
    enviados = len(mailoutbox)
    for dia in ("2026-10-29", "2026-11-06"):
        assert services.regua_da_assinatura(date.fromisoformat(dia)) == {}
    assert len(mailoutbox) == enviados


@pytest.mark.parametrize("status", ["suspensa", "pausada"])
def test_plt_06_suspensa_e_pausada_cancelam_na_hora(moto, relogio, status):
    """A `suspensa` e a `pausada` cancelam (exceções do somente leitura): `cancelada` na hora, e a
    pausa acaba."""
    _ativa_com_boleto(moto)
    campos: dict[str, Any] = {"status": status}
    if status == "pausada":
        campos.update(pausa_inicio=date(2026, 11, 22), pausada_ate=date(2027, 1, 21))
    moto.estado(**campos)
    _em(relogio, "2026-12-10")
    resposta = _cancelar(moto.api())
    assert resposta.status_code == 200, resposta.json()
    empresa = moto.recarregar()
    assert empresa.status == "cancelada"
    assert (empresa.pausa_inicio, empresa.pausada_ate) == (None, None)
    assert empresa.apagar_em == date(2027, 3, 10)


# --- Desfazer o cancelamento (CA-ASS-43 a 45) ---


def test_plt_06_desfazer_cancelamento_no_teste(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-43: cancela em 10 out e desfaz em 15 out: a FAT-0001 continua `cancelada`, nasce a
    FAT-0002 `aberta`, R$ 449,00, vencendo em 22 out, emitida em 17 out; `em_teste` até 21 out e
    não vira `cancelada` em 22 out; nenhum apagamento marcado."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _em(relogio, "2026-10-10")
    assert _cancelar(moto.api()).status_code == 200
    _em(relogio, "2026-10-15")
    resposta = moto.api().delete(CANCELAMENTO)
    connection.set_schema_to_public()
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["cancelamento"] is None
    assert corpo["proxima_fatura"] == {
        "vencimento": "2026-10-22",
        "valor_centavos": 44900,
        "descricao": "Plano Profissional · 22 out a 21 nov",
    }
    assert corpo["acoes"]["cancelar"] is True
    antiga, nova = moto.fatura("FAT-0001"), moto.fatura("FAT-0002")
    assert antiga.status == "cancelada"
    assert antiga.substituida_por_id == nova.pk
    assert (nova.status, nova.tipo, nova.valor_centavos, nova.vencimento) == (
        "aberta",
        "mensalidade",
        44900,
        date(2026, 10, 22),
    )
    assert (nova.periodo_inicio, nova.periodo_fim) == (date(2026, 10, 22), date(2026, 11, 21))
    assert nova.descricao == "Plano Profissional · 22 out a 21 nov"
    assert nova.cobranca_externa_id is None  # mais de 5 dias: sai em 17 out
    empresa = moto.recarregar()
    assert (empresa.acesso_ate, empresa.apagar_em, empresa.motivo_cancelamento) == (None, None, "")
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.desfazer_cancelamento", schema)[-1]
        assert evento.depois["faturas_novas"] == ["FAT-0002"]
    assert _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks).emitidas == {
        "boleto": 1
    }
    _virar(relogio, "2026-10-22")
    assert _status(moto) == "em_teste"


def test_plt_06_desfazer_cancelamento_na_ativa(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-44, caso (b): cancela em 05 nov e desfaz em 10 nov: nada nasce; a fatura de 22 nov
    é gerada em 17 nov, como sempre."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    assert _cancelar(moto.api()).status_code == 200
    _em(relogio, "2026-11-10")
    assert moto.api().delete(CANCELAMENTO).status_code == 200
    connection.set_schema_to_public()
    assert _codigos(moto) == {"FAT-0001": "paga"}
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 1
    assert moto.fatura("FAT-0002").vencimento == date(2026, 11, 22)
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "ativa"


def test_plt_06_desfazer_cancelamento_na_ativa_com_a_fatura_emitida(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """CA-ASS-44, caso (c): cancela em 19 nov (FAT-0002 de 22 nov `cancelada`) e desfaz em 20 nov:
    nasce a FAT-0003 `aberta`, R$ 449,00, vencendo em 22 nov, "Plano Profissional · 22 nov a 21
    dez", com o boleto por e-mail em 20 nov."""
    _ativa_com_boleto(moto)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    _em(relogio, "2026-11-19")
    assert _cancelar(moto.api()).status_code == 200
    _em(relogio, "2026-11-20")
    mailoutbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        resposta = moto.api().delete(CANCELAMENTO)
    connection.set_schema_to_public()
    assert resposta.status_code == 200, resposta.json()
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "cancelada", "FAT-0003": "aberta"}
    nova = moto.fatura("FAT-0003")
    assert (nova.valor_centavos, nova.vencimento) == (44900, date(2026, 11, 22))
    assert nova.descricao == "Plano Profissional · 22 nov a 21 dez"
    assert nova.cobranca_tipo == "boleto"
    assert moto.fatura("FAT-0002").substituida_por_id == nova.pk
    assert [m.subject for m in mailoutbox] == ["Giro: boleto da fatura FAT-0003, vence em 22 nov"]


def test_plt_06_quem_nao_desfaz(moto, relogio):
    """CA-ASS-45: depois do último dia de acesso a empresa já é `cancelada` e nem entra; na
    `inadimplente` cancelada na hora (CA-ASS-34) não há o que desfazer; o Rodrigo, a Lúcia e o
    suporte não desfazem; sem cancelamento marcado, não há o que desfazer."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    assert _erro(moto.api().delete(CANCELAMENTO)) == SEM_CANCELAMENTO
    assert _cancelar(moto.api()).status_code == 200
    for nome in ("Rodrigo", "Lúcia"):
        assert _erro(moto.api(nome).delete(CANCELAMENTO)) == SO_ADMINISTRADOR
    assert _erro(moto.suporte("ver_editar").delete(CANCELAMENTO)) == SUPORTE_NAO_MEXE
    connection.set_schema_to_public()
    assert moto.recarregar().acesso_ate == date(2026, 11, 21)
    _virar(relogio, "2026-11-22")
    _em(relogio, "2026-11-22")
    resposta = moto.api().delete(CANCELAMENTO)
    assert resposta.status_code == 403
    assert _erro(resposta) == EMPRESA_CANCELADA
    connection.set_schema_to_public()
    with pytest.raises(services.Conflito) as erro:
        services.desfazer_cancelamento(moto.recarregar())
    assert erro.value.mensagem == "Não há cancelamento para desfazer."


@pytest.mark.xfail(
    strict=True,
    reason="reativar_empresa (assinatura.md, CA-ASS-46) ainda não implementada no backend",
)
def test_plt_06_reativar_so_com_atrasada_paga(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-46: `inadimplente` com a FAT-0001 `atrasada`, cancelada em 25 out; em 01 dez a equipe
    tenta reativar e recebe 409 `fatura_em_atraso` ("Receba a fatura em atraso antes de reativar.");
    paga a FAT-0001 pela 2ª via e reativada em 01 dez, vira `ativa`, com a FAT-0002 de R$ 449,00
    vencendo em 01 dez ("Plano Profissional · 01 dez a 31 dez") e as seguintes todo dia 1."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    _virar(relogio, "2026-10-23")
    _em(relogio, "2026-10-25")
    assert _cancelar(moto.api()).json()["status"] == "cancelada"
    _em(relogio, "2026-12-01")
    reativar = services.reativar_empresa
    with pytest.raises(services.Conflito) as recusa:
        reativar(moto.recarregar(), por=services.POR_EQUIPE, motivo="Pedido no chamado #1090")
    assert (recusa.value.codigo, recusa.value.mensagem) == (
        "fatura_em_atraso",
        "Receba a fatura em atraso antes de reativar.",
    )
    fatura = moto.fatura("FAT-0001")
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0001-2via") == "baixada"
    reativar(moto.recarregar(), por=services.POR_EQUIPE, motivo="Pedido no chamado #1090")
    empresa = moto.recarregar()
    assert (empresa.status, empresa.dia_vencimento) == ("ativa", 1)
    nova = moto.fatura("FAT-0002")
    assert (nova.status, nova.valor_centavos, nova.vencimento) == (
        "aberta",
        44900,
        date(2026, 12, 1),
    )
    assert nova.descricao == "Plano Profissional · 01 dez a 31 dez"


# --- Pausar (CA-ASS-35 a 37, 42) ---


def test_plt_06_pausar_por_ate_3_meses(moto, relogio):
    """CA-ASS-35: pausando por 2 meses em 05 nov, continua `ativa` até 21 nov e fica `pausada` de
    22 nov a 21 jan 2027, sem fatura. Pausar por 4 meses é recusado."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    api = moto.api()
    recusa = _pausar(api, meses=4)
    assert recusa.status_code == 400
    assert recusa.json()["campos"] == {"meses": ["Escolha de 1 a 3 meses."]}
    resposta = _pausar(api)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["status"] == "ativa"
    assert corpo["pausa"] == {
        "situacao": "agendada",
        "meses": 2,
        "inicio": "2026-11-22",
        "ate": "2027-01-21",
        "volta_em": "2027-01-22",
        "rotulo": "Pausa marcada de 22 nov a 21 jan. Até lá, tudo continua.",
    }
    assert corpo["proxima_fatura"] is None
    assert (corpo["acoes"]["pausar"], corpo["acoes"]["desistir_pausa"]) == (False, True)
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.pausar", schema)[-1]
        assert (evento.depois["meses"], evento.depois["pausa_inicio"]) == (2, "2026-11-22")
        assert evento.depois["pausada_ate"] == "2027-01-21"
    _virar(relogio, "2026-11-21")
    assert _status(moto) == "ativa"
    assert _virar(relogio, "2026-11-22").estados == {"pausada": 1}
    corpo = moto.api().get(ASSINATURA).json()
    connection.set_schema_to_public()
    assert corpo["pausa"]["situacao"] == "em_andamento"
    assert corpo["pausa"]["rotulo"] == "Assinatura pausada até 21 jan. Volta sozinha em 22 jan."
    assert corpo["faixa_aviso"] == "Assinatura pausada até 21 jan. Você só consulta os dados."
    assert corpo["somente_leitura"] is True
    assert (corpo["acoes"]["voltar_pausa"], corpo["acoes"]["desistir_pausa"]) == (True, False)
    # Somente leitura: o resto não escreve.
    resposta = moto.api().patch(DADOS_FISCAIS, {"razao_social": "Outra"}, format="json")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_sem_operacao"
    connection.set_schema_to_public()
    assert _codigos(moto) == {"FAT-0001": "paga"}


def test_plt_06_pausa_e_volta_automatica(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-35: volta sozinha a `ativa` em 22 jan 2027, com uma fatura de R$ 449,00 vencendo
    nesse dia."""
    _pausada_desde_22_nov(moto, relogio)
    assert _gerar(relogio, "2026-12-17", django_capture_on_commit_callbacks).faturas == 0
    _virar(relogio, "2027-01-21")
    assert _status(moto) == "pausada"
    virada = _virar(relogio, "2027-01-22", django_capture_on_commit_callbacks)
    assert virada.estados == {"ativa": 1}
    empresa = moto.recarregar()
    assert (empresa.status, empresa.pausa_inicio, empresa.pausada_ate) == ("ativa", None, None)
    assert empresa.dia_vencimento == 22
    fatura = moto.fatura("FAT-0002")
    assert (fatura.tipo, fatura.status, fatura.valor_centavos) == ("mensalidade", "aberta", 44900)
    assert (fatura.vencimento, fatura.periodo_fim) == (date(2027, 1, 22), date(2027, 2, 21))
    assert fatura.cobranca_tipo == "boleto"  # a cobrança sai na hora
    evento = _eventos("empresa.voltar_pausa", "public")[-1]
    assert (evento.ator_tipo, evento.depois["por"]) == ("sistema", "sistema")
    assert _virar(relogio, "2027-01-22").estados == {}


def test_plt_06_volta_manual_da_pausa(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-36: voltando em 10 dez, `ativa` na hora, com a fatura de R$ 449,00 vencendo em 10
    dez ("Plano Profissional · 10 dez a 09 jan"), e as seguintes todo dia 10."""
    _pausada_desde_22_nov(moto, relogio)
    _em(relogio, "2026-12-10")
    with django_capture_on_commit_callbacks(execute=True):
        resposta = moto.api().delete(PAUSA)
    connection.set_schema_to_public()
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["status"], corpo["pausa"], corpo["faixa_aviso"]) == ("ativa", None, None)
    fatura = moto.fatura("FAT-0002")
    assert (fatura.vencimento, fatura.valor_centavos) == (date(2026, 12, 10), 44900)
    assert fatura.descricao == "Plano Profissional · 10 dez a 09 jan"
    assert fatura.cobranca_tipo == "boleto"
    assert moto.recarregar().dia_vencimento == 10
    assert _gerar(relogio, "2027-01-05", django_capture_on_commit_callbacks).faturas == 1
    assert moto.fatura("FAT-0003").vencimento == date(2027, 1, 10)


def test_plt_06_pausa_comeca_no_fim_do_periodo_pago(
    moto, relogio, django_capture_on_commit_callbacks
):
    """CA-ASS-42: pausando em 19 nov, depois de emitida a FAT-0002 de 22 nov, ela vira `cancelada`
    (nada é cobrado em 22 nov); `ativa` até 21 nov e `pausada` de 22 nov a 21 jan 2027."""
    _ativa_com_boleto(moto)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    cobranca = moto.fatura("FAT-0002").cobranca_externa_id
    _em(relogio, "2026-11-19")
    corpo = _pausar(moto.api()).json()
    assert (corpo["pausa"]["inicio"], corpo["pausa"]["ate"]) == ("2026-11-22", "2027-01-21")
    fatura = moto.fatura("FAT-0002")
    assert (fatura.status, fatura.motivo_cancelamento) == ("cancelada", "pausa")
    assert pagamentos.cobrancas[cobranca].situacao.status == "cancelada"
    _virar(relogio, "2026-11-21")
    assert _status(moto) == "ativa"
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "pausada"
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "cancelada"}
    _virar(relogio, "2027-01-21")
    assert _status(moto) == "pausada"


def test_plt_06_quem_nao_pausa(moto, relogio):
    """CA-ASS-37: no teste, a tela não oferece pausar, e pausar é recusado; a `inadimplente` e a
    `suspensa` pagam antes; com uma pausa marcada, outra é recusada; a `pausada` não pausa; o
    Rodrigo e o suporte não pausam."""
    _em(relogio, "2026-10-10")
    assert _erro(_pausar(moto.api())) == {
        "codigo": "transicao_empresa",
        "mensagem": (
            "A pausa só vale para a assinatura ativa. No teste, você pode cancelar ou mudar de "
            "plano."
        ),
    }
    pague = {"codigo": "transicao_empresa", "mensagem": "Pague a fatura em atraso antes de pausar."}
    for status in ("inadimplente", "suspensa"):
        moto.estado(status=status)
        resposta = _pausar(moto.api())
        assert resposta.status_code == 409
        assert _erro(resposta) == pague
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    assert _erro(_pausar(moto.api("Rodrigo"))) == SO_ADMINISTRADOR
    assert _erro(_pausar(moto.suporte("ver_editar"))) == SUPORTE_NAO_MEXE
    assert _pausar(moto.api()).status_code == 200
    assert _erro(_pausar(moto.api())) == {
        "codigo": "transicao_empresa",
        "mensagem": "Já existe uma pausa marcada até 21 jan.",
    }
    _virar(relogio, "2026-11-22")
    resposta = _pausar(moto.api())
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_sem_operacao"


def test_plt_06_desistir_da_pausa_agendada(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """CA-ASS-55: pausa pedida em 19 nov (FAT-0002 de 22 nov `cancelada`) e desistida em 20 nov:
    nasce a FAT-0003 `aberta`, R$ 449,00, vencendo em 22 nov, com o boleto por e-mail em 20 nov;
    a empresa segue `ativa`. O Rodrigo e o suporte não desistem."""
    _ativa_com_boleto(moto)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    _em(relogio, "2026-11-19")
    assert _pausar(moto.api()).status_code == 200
    _em(relogio, "2026-11-20")
    assert _erro(moto.api("Rodrigo").delete(PAUSA)) == SO_ADMINISTRADOR
    assert _erro(moto.suporte("ver_editar").delete(PAUSA)) == SUPORTE_NAO_MEXE
    connection.set_schema_to_public()
    mailoutbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        resposta = moto.api().delete(PAUSA)
    connection.set_schema_to_public()
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert (corpo["status"], corpo["pausa"]) == ("ativa", None)
    assert _codigos(moto) == {"FAT-0001": "paga", "FAT-0002": "cancelada", "FAT-0003": "aberta"}
    nova = moto.fatura("FAT-0003")
    assert (nova.vencimento, nova.valor_centavos) == (date(2026, 11, 22), 44900)
    assert nova.descricao == "Plano Profissional · 22 nov a 21 dez"
    assert [m.subject for m in mailoutbox] == ["Giro: boleto da fatura FAT-0003, vence em 22 nov"]
    for schema in ("public", moto.empresa.schema_name):
        assert _eventos("empresa.desistir_pausa", schema)[-1].depois["faturas_novas"] == [
            "FAT-0003"
        ]
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "ativa"
    assert _erro(moto.api().delete(PAUSA)) == SEM_PAUSA


# --- Mudanças com cancelamento ou pausa (CA-ASS-56, CA-ASS-57) ---


def test_plt_06_mudar_de_plano_com_cancelamento_marcado(
    moto, relogio, django_capture_on_commit_callbacks
):
    """CA-ASS-56: com o cancelamento marcado, mudar de plano e pausar são recusados; trocar a
    forma continua. O downgrade agendado antes continua e vale em 22 nov se o cancelamento for
    desfeito."""
    moto.no_completo()
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-01")
    assert _mudar(moto.api(), "Profissional").status_code == 200
    connection.set_schema_to_public()
    assert moto.recarregar().plano_proximo.nome == "Profissional"
    _em(relogio, "2026-11-05")
    assert _cancelar(moto.api()).status_code == 200
    desfaca = {
        "codigo": "transicao_empresa",
        "mensagem": "Desfaça o cancelamento antes de mudar de plano.",
    }
    for plano in ("Completo", "Essencial"):
        resposta = _mudar(moto.api(), plano)
        connection.set_schema_to_public()
        assert _erro(resposta) == desfaca
    assert _erro(_pausar(moto.api())) == {
        "codigo": "transicao_empresa",
        "mensagem": "Desfaça o cancelamento antes de pausar.",
    }
    assert moto.api().put(FORMA, {"forma": "boleto"}, format="json").status_code == 200
    connection.set_schema_to_public()
    assert moto.recarregar().plano_proximo.nome == "Profissional"  # o agendamento continua
    _em(relogio, "2026-11-10")
    assert moto.api().delete(CANCELAMENTO).status_code == 200
    connection.set_schema_to_public()
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    fatura = moto.fatura("FAT-0002")
    assert (fatura.plano.nome, fatura.valor_centavos) == ("Profissional", 44900)


def test_plt_06_diferenca_em_aberto_na_pausa(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-57: pausa a partir de 22 nov e diferença vencendo em 23 nov: régua em 23 nov (D0) e
    26 nov (D+3), `pausada` (não `inadimplente`) em 24 nov; volta em 01 dez sem pagar →
    `inadimplente`, e `suspensa` em 08 dez."""
    _ativa_com_boleto(moto)
    _em(relogio, "2026-11-05")
    assert _pausar(moto.api()).status_code == 200
    services.criar_fatura(
        moto.recarregar(),
        tipo=TipoFatura.DIFERENCA_PLANO,
        vencimento=date(2026, 11, 23),
        periodo=Periodo(date(2026, 11, 20), date(2026, 11, 21)),
        plano=Plano.objects.get(nome="Completo"),
        ciclo="mensal",
        valor_centavos=2903,
    )
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "pausada"
    assert services.regua_da_assinatura(date(2026, 11, 23)) == {"D0": 1}
    _virar(relogio, "2026-11-24")
    assert moto.fatura("FAT-0002").status == "atrasada"
    assert _status(moto) == "pausada"
    assert services.regua_da_assinatura(date(2026, 11, 26)) == {"D+3": 1}
    _em(relogio, "2026-12-01")
    with django_capture_on_commit_callbacks(execute=True):
        resposta = moto.api().delete(PAUSA)
    connection.set_schema_to_public()
    assert resposta.status_code == 200, resposta.json()
    assert _status(moto) == "inadimplente"
    assert moto.fatura("FAT-0003").vencimento == date(2026, 12, 1)  # a fatura da volta nasce
    _virar(relogio, "2026-12-07")
    assert _status(moto) == "inadimplente"
    assert _virar(relogio, "2026-12-08").estados == {"suspensa": 1}


def test_plt_06_cancelada_no_dia_seguinte_ao_acesso(
    moto, relogio, django_capture_on_commit_callbacks
):
    """A virada leva a `cancelada` no dia seguinte a `acesso_ate`; o cartão guardado é esquecido e
    a forma fica nula (ADR 0023)."""
    _ativa_com_cartao(moto, relogio)
    assert FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).cartao_final
    _em(relogio, "2026-11-05")
    assert _cancelar(moto.api()).status_code == 200
    assert _virar(relogio, "2026-11-21").estados == {}
    virada = _virar(relogio, "2026-11-22", django_capture_on_commit_callbacks)
    assert virada.estados == {"cancelada": 1}
    empresa = moto.recarregar()
    assert empresa.status == "cancelada"
    assert empresa.apagar_em == date(2027, 2, 20)
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)
    assert (forma.forma, forma.cartao_final, forma.cartao_bandeira) == ("", "", "")
    assert not forma.cartao_token_cifrado
    for schema in ("public", moto.empresa.schema_name):
        assert _eventos("empresa.cancelada", schema)[-1].regra == "PLT-06"


def test_plt_06_excecoes_do_somente_leitura():
    """A lista explícita de exceções (`cancelamento.md`): a `suspensa` e a `pausada` cancelam; a
    `pausada` volta da pausa."""
    assert ("api/assinatura/cancelamento/", "POST") in _rotas_que_escrevem_na_suspensa()
    assert _rotas_que_escrevem_na_suspensa("escreve_na_pausada") == {
        ("api/assinatura/cancelamento/", "POST"),
        ("api/assinatura/pausa/", "DELETE"),
    }


# --- Empresa cancelada, aviso e apagamento (AUD-08, ADR 0025) ---


def test_aud_08_cancelada_nao_entra(moto, relogio):
    """Todo pedido da `cancelada` recebe 403 `empresa_cancelada`, inclusive entrar e renovar; o
    token ainda válido para na hora."""
    _em(relogio, "2026-10-10")
    api = moto.api()
    assert api.get(ASSINATURA).status_code == 200
    connection.set_schema_to_public()
    moto.estado(status="inadimplente")
    assert _cancelar(moto.api()).json()["status"] == "cancelada"
    for resposta in (
        api.get(ASSINATURA),
        api.get("/api/eu/"),
        cliente_http(HOST).post(
            "/api/auth/entrar/", {"email": MARIANA, "senha": "x"}, format="json"
        ),
        cliente_http(HOST).post("/api/auth/renovar/", {"refresh": "x"}, format="json"),
    ):
        assert resposta.status_code == 403
        assert resposta.json() == EMPRESA_CANCELADA
    connection.set_schema_to_public()


def _cancelada_em_22_out(moto: MotoRapida, relogio) -> None:
    """Caso (a): cancela em 10 out, no teste; `cancelada` em 22 out, apagamento em 20 jan 2027."""
    _em(relogio, "2026-10-10")
    assert _cancelar(moto.api()).status_code == 200
    _virar(relogio, "2026-10-22")
    assert _status(moto) == "cancelada"


def test_aud_08_aviso_7_dias_antes(moto, relogio, mailoutbox):
    """O aviso sai em 13 jan 2027 aos administradores ativos, uma vez só."""
    _cancelada_em_22_out(moto, relogio)
    mailoutbox.clear()
    assert services.avisar_apagamentos(date(2027, 1, 12)) == 0
    assert services.avisar_apagamentos(date(2027, 1, 13)) == 1
    assert [m.to for m in mailoutbox] == [[MARIANA]]
    assert mailoutbox[0].body == (
        "Os dados da Moto Rápida serão apagados em 20 jan 2027. Para pedir uma cópia ou reativar "
        "a assinatura, fale com a equipe Giro."
    )
    assert moto.recarregar().aviso_apagamento_enviado_em is not None
    assert services.avisar_apagamentos(date(2027, 1, 14)) == 0
    assert len(mailoutbox) == 1
    evento = _eventos("empresa.avisar_apagamento", "public")[-1]
    assert (evento.regra, evento.ator_tipo) == ("AUD-08", "sistema")


def test_aud_08_apaga_no_90_dia(moto, relogio):
    """Em 20 jan 2027 saem os arquivos e o schema da Moto Rápida; o evento fica no public."""
    _cancelada_em_22_out(moto, relogio)
    schema = moto.empresa.schema_name
    caminho = f"{schema}/veiculos/veiculo/1/crlv.pdf"
    arquivos.provedor().salvar(caminho, b"%PDF-1.4", "application/pdf")
    _em(relogio, "2027-01-19", "03:30")
    assert services.apagar_empresas() == 0
    _em(relogio, "2027-01-20", "03:30")
    assert services.apagar_empresas() == 1
    assert not schema_exists(schema)
    assert not arquivos.provedor().existe(caminho)
    empresa = moto.recarregar()
    assert empresa.apagada_em is not None
    assert not Dominio.objects.filter(tenant_id=empresa.pk).exists()
    evento = _eventos("empresa.apagar", "public")[-1]
    assert (evento.regra, evento.categoria, evento.ator_tipo) == ("AUD-08", "seguranca", "sistema")
    assert evento.depois == {"schema": schema, "arquivos": 1, "data": "2027-01-20"}
    assert services.apagar_empresas() == 0  # já apagada


def test_aud_08_nao_apaga_outra_empresa(moto, criar_empresa, relogio):
    """O apagamento de uma empresa não toca o schema, os arquivos nem a linha de outra."""
    outra = criar_empresa(
        subdominio="motoveloz",
        cnpj="11.222.333/0001-81",
        nome_exibicao="Moto Veloz",
        administrador=services.Administrador(nome="Ana", email="ana@motoveloz.com.br"),
    )
    caminho = f"{outra.schema_name}/veiculos/veiculo/1/crlv.pdf"
    arquivos.provedor().salvar(caminho, b"%PDF-1.4", "application/pdf")
    try:
        _cancelada_em_22_out(moto, relogio)
        with pytest.raises(banco.ApagamentoRecusado):
            banco.apagar_schema(outra.pk)
        _em(relogio, "2027-01-20", "03:30")
        assert services.apagar_empresas() == 1
        assert schema_exists(outra.schema_name)
        assert arquivos.provedor().existe(caminho)
        restante = Empresa.objects.get(pk=outra.pk)
        assert (restante.nome_exibicao, restante.apagada_em) == ("Moto Veloz", None)
        assert Dominio.objects.filter(tenant_id=outra.pk).exists()
    finally:
        arquivos.provedor().apagar(caminho)
    for nome in ("public", "pg_catalog", "information_schema", "Moto-Rapida", "a;drop", "ab"):
        assert not banco.schema_apagavel(nome)
    assert banco.schema_apagavel("motorapida")


def test_aud_08_nao_apaga_reativada(moto, relogio):
    """A empresa reativada pela equipe dentro dos 90 dias não é apagada."""
    _cancelada_em_22_out(moto, relogio)
    moto.estado(status="ativa")  # a reativação pela equipe (assinatura.md) não é desta tarefa
    _em(relogio, "2027-01-20", "03:30")
    assert services.apagar_empresas() == 0
    with pytest.raises(banco.ApagamentoRecusado):
        banco.apagar_schema(moto.empresa.pk)
    assert schema_exists(moto.empresa.schema_name)
    assert moto.recarregar().apagada_em is None


def test_aud_08_linha_apagada_so_com_cnpj(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-58: a linha da `Empresa` fica só com o CNPJ, o plano, as datas, a cidade e a UF; a
    FAT-0001 continua, com o tomador como foi na baixa; o pagador no parceiro fica sem e-mail e
    telefone. No painel, "Dados apagados"."""
    _criar_matriz(moto)
    moto.estado(responsavel_telefone="85999990000")
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _em(relogio, "2026-10-18")
    fatura = services.pagar_fatura(moto.recarregar(), "FAT-0001")
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0001") == "baixada"
    cliente = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa).cliente_externo_id
    assert pagamentos.pagadores[cliente].email == MARIANA
    _virar(relogio, "2026-10-22")
    _em(relogio, "2026-11-05")
    assert _cancelar(moto.api()).status_code == 200
    _virar(relogio, "2026-11-22", django_capture_on_commit_callbacks)
    _em(relogio, "2027-02-20", "03:30")
    assert services.apagar_empresas() == 1

    empresa = moto.recarregar()
    assert empresa.cnpj == "12345678000195"
    assert (empresa.cidade, empresa.uf, empresa.plano.nome) == ("Fortaleza", "CE", "Profissional")
    assert (empresa.status, empresa.apagar_em) == ("cancelada", date(2027, 2, 20))
    assert empresa.teste_inicio == date(2026, 10, 7)
    for campo in (
        "razao_social",
        "nome_exibicao",
        "email_cobranca",
        "responsavel_nome",
        "responsavel_email",
        "responsavel_telefone",
        "endereco_cep",
        "endereco_logradouro",
        "endereco_cidade",
    ):
        assert getattr(empresa, campo) == "", campo
    assert (empresa.subdominio, empresa.schema_name) == ("motorapida", "motorapida")
    assert not UsoEmpresa.objects.filter(empresa=empresa).exists()
    assert not FormaPagamentoAssinatura.objects.filter(empresa=empresa).exists()
    fat = moto.fatura("FAT-0001")
    assert (fat.status, fat.tomador_razao_social, fat.tomador_cnpj) == (
        "paga",
        "Moto Rápida Locações Ltda",
        "12345678000195",
    )
    assert fat.tomador_endereco == {**BEZERRA, "complemento": None}
    assert (pagamentos.pagadores[cliente].email, pagamentos.pagadores[cliente].celular) == ("", "")
    assert pagamentos.anonimizados == [cliente]
    situacao = selectors.situacao(selectors.com_situacao().get(pk=empresa.pk))
    assert situacao == {"codigo": "cancelada", "rotulo": "Dados apagados", "tom": "neutro"}
    # O evento do apagamento não leva dado pessoal.
    evento = _eventos("empresa.apagar", "public")[-1]
    assert "Moto Rápida" not in str(evento.depois)
    assert MARIANA not in str(evento.depois)


def test_aud_08_fatura_atrasada_guarda_email(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-60: `inadimplente`, cancelada em 25 out, apagada em 23 jan 2027 com a FAT-0001
    atrasada: a fatura fica com o tomador e o e-mail de cobrança; paga depois pelo webhook, o
    e-mail sai da fatura, o tomador fica, e a empresa continua apagada."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    _virar(relogio, "2026-10-23")
    _em(relogio, "2026-10-25")
    assert _cancelar(moto.api()).json()["status"] == "cancelada"
    _em(relogio, "2027-01-23", "03:30")
    assert services.apagar_empresas() == 1
    fatura = moto.fatura("FAT-0001")
    assert (fatura.status, fatura.email_cobranca) == ("atrasada", MARIANA)
    assert fatura.tomador_cnpj == "12345678000195"
    assert services.regua_da_assinatura(date(2027, 1, 23)) == {}
    _em(relogio, "2027-02-01")
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-depois") == "baixada"
    fatura = moto.fatura("FAT-0001")
    assert (fatura.status, fatura.email_cobranca) == ("paga", "")
    assert fatura.tomador_cnpj == "12345678000195"
    assert _status(moto) == "cancelada"
    assert moto.recarregar().apagada_em is not None
