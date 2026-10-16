"""T-186 (parte 2) · Geração, emissão e cartão guardado (`docs/api/assinatura.md`, "Faturas,
cobrança e régua" e "Downgrade agendado: conferência e virada"; PLT-02, PLT-04, PLT-13).

Relógio de referência (ADR 0021): Moto Rápida em teste de 07 a 21 out, FAT-0001 de R$ 449,00
vencendo em 22 out, e as seguintes todo dia 22. A tarefa `gerar_faturas` roda às 06:00: gera a
fatura do período seguinte 5 dias antes do vencimento (17 nov para a de 22 nov), emite no
parceiro o que vence em até 5 dias e cobra o cartão guardado no vencimento.
"""

from collections.abc import Iterator
from datetime import date

import pytest
from django.db import connection, transaction
from django_tenants.utils import schema_context, tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.plataforma import selectors, services
from apps.plataforma.models import (
    Empresa,
    FaturaAssinatura,
    FormaPagamentoAssinatura,
    StatusFatura,
    StatusFormaPagamento,
    TipoFatura,
    UsoEmpresa,
)
from comum.erros import LimiteDoPlano
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos import hash_do_token
from integracoes.pagamentos.base import EventoWebhook

from .test_t184_faturas import TOKEN_PRINCIPAL, _webhook
from .test_t185_assinatura import MotoRapida, _mudar

COBRANCA = "financeiro@motorapida.com.br"
MARIANA = "mariana@motorapida.com.br"


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    moto = MotoRapida(criar_empresa())
    moto.estado(email_cobranca=COBRANCA)
    yield moto
    pagamentos.limpar()


@pytest.fixture
def conta_principal_ligada(settings) -> None:
    settings.GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH = hash_do_token(TOKEN_PRINCIPAL)


def _gerar(relogio, dia: str, capturar) -> services.Geracao:
    relogio.em(f"{dia} 06:00")
    with capturar(execute=True):
        geracao = services.gerar_faturas()
    connection.set_schema_to_public()
    return geracao


def _virar(relogio, dia: str) -> services.Virada:
    relogio.em(f"{dia} 00:05")
    return services.virar_estados()


def _eventos(acao: str, schema: str) -> list[EventoAuditoria]:
    with schema_context(schema):
        return list(EventoAuditoria.objects.filter(acao=acao).order_by("id"))


def _baixar(cobranca_id: str | None, evento: str) -> str:
    """O aviso da conta principal com a baixa (T-184): o parceiro já diz que está paga."""
    assert cobranca_id
    aviso = services.registrar_webhook_principal(
        EventoWebhook("asaas", evento, "PAYMENT_RECEIVED", cobranca_id, "", ""), {}
    )
    assert aviso is not None
    return services.processar_webhook_fatura(aviso.pk)


def _forma(moto: MotoRapida) -> FormaPagamentoAssinatura:
    return FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)


def _ativa_com_cartao(moto: MotoRapida, relogio) -> str:
    """Cartão escolhido no teste e digitado na página do parceiro ao pagar a FAT-0001 em 18 out
    (ADR 0023); ativa em 22 out. Devolve o token que o parceiro guardou."""
    relogio.em("2026-10-10 10:00")
    services.escolher_forma_pagamento(moto.recarregar(), "cartao")
    relogio.em("2026-10-18 10:00")
    fatura = services.pagar_fatura(moto.recarregar(), "FAT-0001")
    assert fatura.cobranca_tipo == "cartao_link"
    pagamentos.simular_pagamento(fatura.cobranca_externa_id or "")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0001") == "baixada"
    _virar(relogio, "2026-10-22")
    assert moto.recarregar().status == "ativa"
    return _forma(moto).cartao_token_cifrado_claro()


def _ativa_com_boleto(moto: MotoRapida) -> None:
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    moto.pagar_fat_0001()
    moto.estado(status="ativa")


# --- Emissão 5 dias antes (PLT-02, CA-ASS-10) ---


def test_plt_02_ca_ass_10_boleto_cinco_dias_antes(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Com boleto, o boleto com Pix da FAT-0001 nasce no parceiro em 17 out e vai por e-mail
    nesse dia para o e-mail de cobrança e para a Mariana. Rodar de novo não cria outro."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    assert _gerar(relogio, "2026-10-16", django_capture_on_commit_callbacks).emitidas == {}
    assert not moto.fatura("FAT-0001").cobranca_externa_id

    geracao = _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    assert geracao.emitidas == {"boleto": 1}
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "boleto"
    assert fatura.cobranca_boleto_url and fatura.cobranca_linha_digitavel
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [COBRANCA, MARIANA]
    assert "FAT-0001" in mailoutbox[0].subject
    assert "R$ 449,00" in mailoutbox[0].body and "22 out" in mailoutbox[0].body
    evento = _eventos("fatura_assinatura.emitir_cobranca", "public")[-1]
    assert evento.regra == "PLT-14"

    assert _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks).emitidas == {}
    assert moto.fatura("FAT-0001").cobranca_externa_id == fatura.cobranca_externa_id
    assert len(mailoutbox) == 1


def test_plt_02_ca_ass_11_cartao_sem_cartao_guardado_emite_a_pagina(
    moto, relogio, django_capture_on_commit_callbacks
):
    """Com cartão escolhido e nenhum guardado, sai a cobrança com a página do parceiro em 17 out
    (o link vai no D-3 e no "Pagar"); nada é cobrado sozinho."""
    services.escolher_forma_pagamento(moto.recarregar(), "cartao")
    geracao = _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks)
    assert geracao.emitidas == {"cartao_link": 1}
    assert geracao.cartoes == {}
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "cartao_link"
    assert fatura.cobranca_url_pagina
    assert _gerar(relogio, "2026-10-22", django_capture_on_commit_callbacks).cartoes == {}


def test_plt_02_sem_forma_nada_e_emitido(moto, relogio, django_capture_on_commit_callbacks):
    assert _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks).emitidas == {
        "sem_forma": 1
    }
    assert not moto.fatura("FAT-0001").cobranca_externa_id


# --- Pix automático autorizado (PLT-13) ---


def test_plt_13_pix_automatico_autorizado_e_cobrado_pela_autorizacao(
    moto, relogio, conta_principal_ligada, django_capture_on_commit_callbacks
):
    """Antes de autorizar no banco, a forma fica `aguardando_autorizacao`. O aviso da autorização
    (conferido no parceiro) tira a forma da espera, e a cobrança da FAT-0001, emitida depois,
    sai pela autorização, sem boleto. Sem a autorização na emissão, ver a T-297."""
    relogio.em("2026-10-10 10:00")
    services.escolher_forma_pagamento(moto.recarregar(), "pix_automatico")
    forma = _forma(moto)
    assert forma.status == StatusFormaPagamento.PENDENTE

    relogio.em("2026-10-16 10:00")
    corpo = pagamentos.autorizar_pix(forma.autorizacao_externa_id)
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200  # o mesmo aviso de novo
    assert _forma(moto).status == StatusFormaPagamento.ATIVA
    situacao = selectors.forma_de_pagamento(moto.recarregar())["situacao"]
    assert situacao["rotulo"] == "Pix automático autorizado"
    assert [e.regra for e in _eventos("assinatura.forma_ativa", "public")] == ["PLT-13"]

    assert _gerar(relogio, "2026-10-17", django_capture_on_commit_callbacks).emitidas == {
        "pix_automatico": 1
    }
    fatura = moto.fatura("FAT-0001")
    assert fatura.cobranca_tipo == "pix_auto"
    assert not fatura.cobranca_boleto_url
    cobranca = selectors.cobranca_da_fatura(fatura)
    assert cobranca is not None
    assert cobranca["forma"] == "pix"


def test_plt_13_aviso_de_autorizacao_confere_no_parceiro(
    moto, relogio, conta_principal_ligada, django_capture_on_commit_callbacks
):
    """O corpo diz "ativada", mas o parceiro diz que a autorização ainda espera: a forma não muda
    (S-14). Aviso de autorização que o Giro não conhece: só fica no resultado."""
    services.escolher_forma_pagamento(moto.recarregar(), "pix_automatico")
    forma = _forma(moto)
    corpo = {
        "id": "evt-falso-1",
        "event": "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED",
        "pixAutomaticAuthorization": {"id": forma.autorizacao_externa_id},
    }
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    assert _forma(moto).status == StatusFormaPagamento.PENDENTE
    outro = {**corpo, "id": "evt-falso-2", "pixAutomaticAuthorization": {"id": "aut_de_fora"}}
    assert _webhook(django_capture_on_commit_callbacks, outro) == 200
    from comum.models import WebhookRecebido

    resultados = list(WebhookRecebido.objects.order_by("id").values_list("resultado", flat=True))
    assert resultados == ["autorizacao_pendente", "autorizacao_desconhecida"]


# --- Geração da fatura do período seguinte (PLT-01, PLT-02) ---


def test_plt_02_gera_a_fatura_do_periodo_seguinte_cinco_dias_antes(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """FAT-0001 paga e ativa: a FAT-0002 (22 nov a 21 dez, R$ 449,00) nasce em 17 nov, com o
    boleto; em 16 nov ainda não. Uma por período: rodar de novo não gera outra."""
    _ativa_com_boleto(moto)
    assert _gerar(relogio, "2026-11-16", django_capture_on_commit_callbacks).faturas == 0
    geracao = _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    assert (geracao.faturas, geracao.emitidas) == (1, {"boleto": 1})
    fatura = moto.fatura("FAT-0002")
    assert (fatura.tipo, fatura.status, fatura.valor_centavos) == ("mensalidade", "aberta", 44900)
    assert (fatura.vencimento, fatura.periodo_inicio, fatura.periodo_fim) == (
        date(2026, 11, 22),
        date(2026, 11, 22),
        date(2026, 12, 21),
    )
    assert fatura.competencia == date(2026, 11, 1)
    assert fatura.plano.nome == "Profissional"
    assert _eventos("fatura_assinatura.criar", "public")[-1].regra == "PLT-02"
    assert len(mailoutbox) == 1

    de_novo = _gerar(relogio, "2026-11-18", django_capture_on_commit_callbacks)
    assert (de_novo.faturas, de_novo.emitidas) == (0, {})
    assert FaturaAssinatura.objects.filter(empresa=moto.empresa).count() == 2


def test_plt_02_gera_mesmo_com_a_anterior_atrasada(
    moto, relogio, django_capture_on_commit_callbacks
):
    """A `inadimplente` continua recebendo as faturas dos períodos seguintes (a dívida soma)."""
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")
    _virar(relogio, "2026-10-23")
    assert moto.recarregar().status == "inadimplente"
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 1
    assert moto.fatura("FAT-0002").vencimento == date(2026, 11, 22)


def test_plt_02_nao_gera_para_cancelada_pausada_nem_depois_do_acesso(
    moto, relogio, criar_empresa, django_capture_on_commit_callbacks
):
    """Nada nasce para a `pausada` e a `cancelada`, nem o período que começa depois do fim do
    acesso (cancelamento marcado, PLT-06)."""
    _ativa_com_boleto(moto)
    moto.estado(acesso_ate=date(2026, 11, 21))
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 0
    moto.estado(acesso_ate=None, status="pausada")
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 0
    moto.estado(status="cancelada")
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 0
    assert FaturaAssinatura.objects.filter(empresa=moto.empresa).count() == 1


def test_plt_02_geracao_isolada_por_empresa(
    moto, relogio, criar_empresa, django_capture_on_commit_callbacks
):
    """Cada empresa recebe a própria fatura, com o próprio código, e a auditoria de cada uma fica
    no próprio schema."""
    _ativa_com_boleto(moto)
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81", nome_exibicao="Outra")
    FaturaAssinatura._base_manager.filter(empresa=outra).update(status="paga")
    Empresa._base_manager.filter(pk=outra.pk).update(status="ativa")
    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 2
    assert list(
        FaturaAssinatura.objects.filter(vencimento=date(2026, 11, 22))
        .order_by("empresa_id")
        .values_list("empresa_id", "codigo")
    ) == [(moto.empresa.pk, "FAT-0002"), (outra.pk, "FAT-0002")]


# --- Downgrade agendado: conferência na geração (PLT-04, CA-ASS-40 e 41) ---


def _completo_com_profissional_agendado(moto: MotoRapida, relogio) -> None:
    """Completo `ativa`, período de 22 out a 21 nov, Profissional agendado em 01 nov."""
    moto.no_completo()
    _ativa_com_boleto(moto)
    relogio.em("2026-11-01 09:00")
    assert _mudar(moto.api(), "Profissional").status_code == 200
    agendado = moto.recarregar().plano_proximo
    assert agendado is not None
    assert agendado.nome == "Profissional"


def test_plt_04_downgrade_agendado_deixa_de_caber(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """CA-ASS-40: com 11 usuários em 12 nov, a geração de 17 nov não desce: a FAT-0002 sai pelo
    Completo (R$ 899,00), o agendamento cai, o administrador e o e-mail de cobrança recebem o
    motivo, e a auditoria do sistema fica nos dois lugares. Em 22 nov o plano não muda."""
    _completo_com_profissional_agendado(moto, relogio)
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(usuarios=11)

    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 1
    fatura = moto.fatura("FAT-0002")
    assert (fatura.plano.nome, fatura.valor_centavos) == ("Completo", 89900)
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.plano_proximo) == ("Completo", None)
    assinatura = moto.api().get("/api/assinatura/").json()
    assert assinatura["plano_proximo"] is None
    assert assinatura["acoes"]["desfazer_mudanca_plano"] is False

    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.mudar_plano_recusado", schema)[-1]
        assert (evento.ator_tipo, evento.regra) == ("sistema", "PLT-04")
        assert evento.antes == {"plano_proximo": "Profissional"}
        assert evento.depois["detalhes"]["usuarios"] == {"usado": 11, "limite": 10}

    assert len(mailoutbox) == 2  # o motivo e o boleto
    aviso = next(m for m in mailoutbox if "não aconteceu" in m.subject)
    assert aviso.to == [COBRANCA, MARIANA]
    assert "11 de 10 usuários" in aviso.body
    assert "plano Completo" in aviso.body

    _virar(relogio, "2026-11-22")
    assert moto.recarregar().plano.nome == "Completo"


def test_plt_04_downgrade_cabia_na_geracao(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-41: sem convidar ninguém até 17 nov, a FAT-0002 sai pelo Profissional (R$ 449,00,
    "Plano Profissional · 22 nov a 21 dez") e o agendamento fica. Os convites de 19 nov entram
    (o limite ainda é o do Completo), e em 22 nov o plano vira com 11 de 10: ninguém sai, e um
    novo convite é recusado pelo limite (PLT-03)."""
    _completo_com_profissional_agendado(moto, relogio)

    assert _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks).faturas == 1
    fatura = moto.fatura("FAT-0002")
    assert (fatura.plano.nome, fatura.valor_centavos) == ("Profissional", 44900)
    proxima = services.proxima_mensalidade(moto.recarregar())
    assert proxima is not None
    assert proxima.descricao == ("Plano Profissional · 22 nov a 21 dez")
    assert moto.recarregar().plano_proximo.nome == "Profissional"
    assert not _eventos("empresa.mudar_plano_recusado", "public")

    relogio.em("2026-11-19 10:00")
    # O uso do seed (5) é montado; aqui as pessoas são de verdade, porque a virada recalcula.
    assert services.recalcular_uso(moto.recarregar())["usuarios"] == 3
    with tenant_context(moto.empresa):
        for numero in range(8):
            with transaction.atomic():
                services.exigir_limite("usuarios")  # o limite ainda é o do Completo
                Usuario.objects.create_user(
                    f"pessoa{numero}@motorapida.com.br",
                    "senha-forte-123",
                    nome=f"Pessoa {numero}",
                    perfil="gerente",
                )
                services.atualizar_uso("usuarios", 1)
    connection.set_schema_to_public()
    assert UsoEmpresa.objects.get(empresa=moto.empresa).usuarios == 11

    assert _virar(relogio, "2026-11-22").mudancas_de_plano == 1
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.preco_contratado_centavos) == ("Profissional", 44900)
    assert UsoEmpresa.objects.get(empresa=moto.empresa).usuarios == 11  # ninguém sai
    with pytest.raises(LimiteDoPlano), transaction.atomic():
        services.exigir_limite("usuarios", empresa)


# --- Cartão guardado no vencimento, uma tentativa a mais (PLT-02, CA-ASS-12) ---


def test_plt_02_cartao_guardado_cobrado_no_dia_do_vencimento(
    moto, relogio, django_capture_on_commit_callbacks
):
    """A FAT-0002 nasce em 17 nov sem cobrança (o cartão guardado espera o vencimento); em 22 nov,
    às 06:00, é cobrada pelo token, e a baixa vem pelo aviso do parceiro."""
    _ativa_com_cartao(moto, relogio)
    geracao = _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)
    assert (geracao.faturas, geracao.emitidas) == (1, {"cartao_guardado": 1})
    assert _gerar(relogio, "2026-11-21", django_capture_on_commit_callbacks).cartoes == {}

    assert _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks).cartoes == {
        "cobrada": 1
    }
    fatura = moto.fatura("FAT-0002")
    assert fatura.cobranca_tipo == "cartao"
    assert _eventos("fatura_assinatura.cobrar_cartao", "public")[-1].ator_tipo == "sistema"
    # Mesmo dia de novo: não cobra duas vezes.
    assert _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks).cartoes == {
        "ja_cobrada": 1
    }

    relogio.em("2026-11-22 06:01")
    assert _baixar(fatura.cobranca_externa_id, "evt-fat-0002") == "baixada"
    assert moto.fatura("FAT-0002").status == StatusFatura.PAGA
    assert moto.recarregar().status == "ativa"


def test_plt_02_cartao_uma_tentativa_a_mais(moto, relogio, django_capture_on_commit_callbacks):
    """CA-ASS-12: recusado em 22 nov, "Tentamos de novo amanhã"; o mesmo dia não tenta de novo;
    `inadimplente` em 23 nov e a 2ª tentativa nesse dia; recusado de novo, não há terceira, e a
    Mariana paga por Pix pelo "Pagar"."""
    token = _ativa_com_cartao(moto, relogio)
    pagamentos.recusar_cartao(token)
    _gerar(relogio, "2026-11-17", django_capture_on_commit_callbacks)

    assert _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks).cartoes == {
        "recusado": 1
    }
    fatura = moto.fatura("FAT-0002")
    assert fatura.tentativas_cartao == 1
    assert not fatura.cobranca_externa_id
    situacao = selectors.forma_de_pagamento(moto.recarregar())["situacao"]
    assert situacao["rotulo"] == "O cartão foi recusado. Tentamos de novo amanhã."
    recusa = _eventos("fatura_assinatura.cartao_recusado", "public")[-1]
    assert (recusa.ator_tipo, recusa.regra) == ("sistema", "PLT-02")
    assert _gerar(relogio, "2026-11-22", django_capture_on_commit_callbacks).cartoes == {
        "tenta_amanha": 1
    }

    assert _virar(relogio, "2026-11-23").estados == {"inadimplente": 1}
    assert _gerar(relogio, "2026-11-23", django_capture_on_commit_callbacks).cartoes == {
        "recusado": 1
    }
    assert moto.fatura("FAT-0002").tentativas_cartao == 2
    situacao = selectors.forma_de_pagamento(moto.recarregar())["situacao"]
    assert situacao["rotulo"] == "O cartão foi recusado de novo. Pague a fatura por Pix ou boleto."
    assert _gerar(relogio, "2026-11-24", django_capture_on_commit_callbacks).cartoes == {}
    assert len(_eventos("fatura_assinatura.cartao_recusado", "public")) == 2

    relogio.em("2026-11-25 10:00")
    paga = services.pagar_fatura(moto.recarregar(), "FAT-0002", meio="pix")
    assert paga.cobranca_tipo == "pix"
    pagamentos.simular_pagamento(paga.cobranca_externa_id or "")
    assert _baixar(paga.cobranca_externa_id, "evt-fat-0002") == "baixada"
    assert moto.recarregar().status == "ativa"
    assert _forma(moto).forma == "cartao"  # pagar por outro meio não troca a forma


# --- Diferença do upgrade (PLT-04) ---


def test_plt_04_diferenca_do_upgrade_no_cartao_guardado_na_hora(
    moto, relogio, django_capture_on_commit_callbacks
):
    """CA-ASS-14 com cartão guardado: Profissional para Completo em 01 nov, a diferença de
    R$ 304,84 é cobrada no cartão na hora, sem esperar a geração."""
    _ativa_com_cartao(moto, relogio)
    relogio.em("2026-11-01 09:00")
    with django_capture_on_commit_callbacks(execute=True):
        resposta = _mudar(moto.api(), "Completo", 30484)
    connection.set_schema_to_public()
    assert resposta.status_code == 200
    diferenca = moto.fatura("FAT-0002")
    assert (diferenca.tipo, diferenca.valor_centavos) == (TipoFatura.DIFERENCA_PLANO, 30484)
    assert diferenca.cobranca_tipo == "cartao"
    assert diferenca.vencimento == date(2026, 11, 4)

    relogio.em("2026-11-01 09:01")
    assert _baixar(diferenca.cobranca_externa_id, "evt-dif") == "baixada"
    assert moto.fatura("FAT-0002").status == StatusFatura.PAGA


def test_plt_04_diferenca_do_upgrade_no_boleto_sai_na_geracao(
    moto, relogio, mailoutbox, django_capture_on_commit_callbacks
):
    """Com boleto, a diferença (vence em 04 nov) é emitida na geração das 06:00 seguinte."""
    _ativa_com_boleto(moto)
    relogio.em("2026-11-01 09:00")
    assert _mudar(moto.api(), "Completo", 30484).status_code == 200
    assert not moto.fatura("FAT-0002").cobranca_externa_id
    assert _gerar(relogio, "2026-11-02", django_capture_on_commit_callbacks).emitidas == {
        "boleto": 1
    }
    assert moto.fatura("FAT-0002").cobranca_tipo == "boleto"
    assert len(mailoutbox) == 1
