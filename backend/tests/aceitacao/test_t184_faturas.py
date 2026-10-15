"""T-184 · Faturas da assinatura e conta principal no parceiro (`docs/api/assinatura.md`).

1ª fatura na criação da empresa (PLT-01), código por empresa, pagador na conta principal,
endereço da nota copiado da matriz (PLT-15, T-213), webhook da conta principal baixando a fatura
uma vez só (PLT-14) e o cartão guardado da página do parceiro (PLT-13, ADR 0023). Relógio em
07 out 2026, como o seed Moto Rápida.
"""

import copy
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django_tenants.utils import tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.filiais import services as filiais
from apps.plataforma import selectors, services
from apps.plataforma.calendario import proximo_periodo
from apps.plataforma.models import (
    FaturaAssinatura,
    FormaAssinatura,
    FormaPagamentoAssinatura,
    StatusFormaPagamento,
    TipoFatura,
)
from comum.models import WebhookRecebido
from integracoes.pagamentos import CABECALHO_DO_TOKEN, conta_principal, hash_do_token, provedor
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.base import CartaoRecusado, Pagador, PedidoCobranca
from seed.moto_rapida import CENTRO

from .conftest import HOST_PLATAFORMA
from .conftest import cliente as cliente_http

WEBHOOK = "/api/webhooks/pagamentos/asaas/"
TOKEN_PRINCIPAL = "token-ficticio-da-conta-principal-t184"


@pytest.fixture
def moto(criar_empresa):
    pagamentos.limpar()
    yield criar_empresa()
    pagamentos.limpar()


@pytest.fixture
def conta_principal_ligada(settings):
    settings.GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH = hash_do_token(TOKEN_PRINCIPAL)


def _fat_0001(empresa: Any) -> FaturaAssinatura:
    return FaturaAssinatura.objects.get(empresa=empresa, codigo="FAT-0001")


def _emitir(fatura: FaturaAssinatura, tipo: str = "boleto") -> str:
    """Cobrança da fatura na conta principal do parceiro falso (a emissão é da T-186)."""
    cobranca = provedor().criar_cobranca(
        conta_principal(),
        PedidoCobranca(
            tipo, fatura.valor_centavos, fatura.vencimento, f"fatura-{fatura.pk}", Pagador("x")
        ),
    )
    fatura.cobranca_externa_id = cobranca.id
    fatura.save(update_fields=["cobranca_externa_id"])
    return cobranca.id


def _webhook(capturar: Any, corpo: dict[str, Any], token: str = TOKEN_PRINCIPAL) -> int:
    with capturar(execute=True):
        resposta = cliente_http(HOST_PLATAFORMA).post(
            WEBHOOK, corpo, format="json", headers={CABECALHO_DO_TOKEN: token}
        )
    connection.set_schema_to_public()
    return int(resposta.status_code)


def _criar_matriz(empresa: Any, dados: dict[str, Any] = CENTRO) -> Any:
    with tenant_context(empresa):
        mariana = Usuario.objects.get(email="mariana@motorapida.com.br")  # nasce com a empresa
        filial = filiais.criar_filial(copy.deepcopy(dados), mariana)
    connection.set_schema_to_public()
    return filial


# --- 1ª fatura (PLT-01) ---


def test_plt_01_primeira_fatura_dia_seguinte_ao_teste(moto):
    """CA-ASS-01: Moto Rápida, teste de 07 a 21 out → FAT-0001 de R$ 449,00 vencendo em 22 out."""
    fatura = _fat_0001(moto)
    assert (fatura.tipo, fatura.status, fatura.valor_centavos) == ("mensalidade", "aberta", 44900)
    assert fatura.vencimento == date(2026, 10, 22)
    assert (fatura.periodo_inicio, fatura.periodo_fim) == (date(2026, 10, 22), date(2026, 11, 21))
    assert fatura.competencia == date(2026, 10, 1)
    assert fatura.plano.nome == "Profissional"
    assert fatura.descricao == "Plano Profissional · 22 out a 21 nov"
    assert fatura.cobranca_externa_id is None  # emitida no parceiro 5 dias antes (T-186)
    moto.refresh_from_db()
    assert moto.dia_vencimento == 22
    assert moto.email_cobranca == "mariana@motorapida.com.br"
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto)
    assert (forma.forma, forma.status) == ("", StatusFormaPagamento.PENDENTE)
    assert EventoAuditoria.objects.filter(acao="fatura_assinatura.criar", regra="PLT-01").exists()


def test_plt_01_primeira_fatura_do_anual(criar_empresa):
    empresa = criar_empresa(ciclo="anual")
    fatura = _fat_0001(empresa)
    assert empresa.preco_contratado_centavos == fatura.valor_centavos == 449000  # 10 mensalidades
    assert (fatura.periodo_inicio, fatura.periodo_fim) == (date(2026, 10, 22), date(2027, 10, 21))
    assert fatura.descricao == "Plano Profissional anual · out 2026 a out 2027"


def test_plt_14_codigo_da_fatura_por_empresa(moto, criar_empresa):
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81")
    assert _fat_0001(outra).codigo == "FAT-0001"
    periodo = proximo_periodo(22, "mensal", date(2026, 11, 22))
    segunda = services.criar_fatura(
        moto,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=periodo.inicio,
        periodo=periodo,
        plano=moto.plano,
        ciclo="mensal",
        valor_centavos=44900,
    )
    assert segunda.codigo == "FAT-0002"
    assert segunda.descricao == "Plano Profissional · 22 nov a 21 dez"


def test_plt_01_uma_mensalidade_por_periodo(moto):
    periodo = proximo_periodo(22, "mensal", date(2026, 10, 22))
    with pytest.raises(IntegrityError), transaction.atomic():
        services.criar_fatura(
            moto,
            tipo=TipoFatura.MENSALIDADE,
            vencimento=periodo.inicio,
            periodo=periodo,
            plano=moto.plano,
            ciclo="mensal",
            valor_centavos=44900,
        )


def test_plt_14_faturas_recentes_so_da_empresa(moto, criar_empresa):
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81")
    recentes = selectors.faturas_recentes(moto)
    assert recentes == [
        {
            "codigo": "FAT-0001",
            "vencimento": date(2026, 10, 22),
            "valor_centavos": 44900,
            "status": "aberta",
            "observacao": "1ª cobrança após o teste",
        }
    ]
    assert len(selectors.faturas_recentes(outra)) == 1
    assert FaturaAssinatura.objects.filter(empresa=moto).count() == 1


# --- Endereço da nota (PLT-15, T-213) ---


def test_plt_15_endereco_nasce_da_matriz(moto):
    """CA-ASS-47: a Filial Centro nasce matriz e dá o endereço da nota."""
    moto.refresh_from_db()
    assert moto.endereco is None  # a compra não pede endereço
    _criar_matriz(moto)
    moto.refresh_from_db()
    assert moto.endereco == {
        "cep": "60325000",
        "logradouro": "Av. Bezerra de Menezes",
        "numero": "1200",
        "complemento": None,
        "bairro": "São Gerardo",
        "cidade": "Fortaleza",
        "uf": "CE",
    }
    evento = EventoAuditoria.objects.get(acao="empresa.dados_fiscais")
    assert (evento.regra, evento.ator_tipo) == ("PLT-15", "sistema")


def test_plt_15_endereco_da_nota_e_da_filial_separados(moto):
    """CA-ASS-48: editar a matriz não muda a nota; a cópia é uma vez só."""
    filial = _criar_matriz(moto)
    with tenant_context(moto):
        filiais.editar_filial(
            filial,
            {"endereco": {**CENTRO["endereco"], "logradouro": "Rua Nova", "numero": "10"}},
        )
    connection.set_schema_to_public()
    assert services.copiar_endereco_da_matriz({"cep": "60115170"}, empresa=moto) is False
    moto.refresh_from_db()
    assert (moto.endereco_logradouro, moto.endereco_numero) == ("Av. Bezerra de Menezes", "1200")


def test_plt_15_nota_pendente_so_com_a_nfse_ligada(
    moto, settings, django_capture_on_commit_callbacks
):
    settings.GIRO_NFSE_ASSINATURA_ATIVA = False
    with django_capture_on_commit_callbacks() as agendadas:
        _criar_matriz(moto)
    assert not [c for c in agendadas if "notas_pendentes" in repr(c)]


# --- Pagador na conta principal ---


def test_plt_15_pagador_leva_endereco_e_email_de_cobranca(moto):
    _criar_matriz(moto)
    moto.refresh_from_db()
    cliente_id = services.atualizar_pagador(moto)
    pagador = pagamentos.pagadores[cliente_id]
    assert (pagador.nome, pagador.documento, pagador.email) == (
        "Moto Rápida Locações Ltda",
        "12345678000195",
        "mariana@motorapida.com.br",
    )
    assert pagador.endereco is not None and pagador.endereco.cep == "60325000"
    # Na segunda vez, atualiza o mesmo cliente.
    assert services.atualizar_pagador(moto) == cliente_id
    assert FormaPagamentoAssinatura.objects.get(empresa=moto).cliente_externo_id == cliente_id


# --- Webhook da conta principal (PLT-14) ---


def test_plt_14_webhook_da_fatura_baixa_uma_vez(
    moto, conta_principal_ligada, django_capture_on_commit_callbacks
):
    fatura = _fat_0001(moto)
    cobranca_id = _emitir(fatura)
    corpo = pagamentos.simular_pagamento(cobranca_id, evento_id="evt_t184_1")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200  # o mesmo aviso de novo
    confirmado = pagamentos.corpo_do_webhook(cobranca_id, "PAYMENT_CONFIRMED", "evt_t184_2")
    assert _webhook(django_capture_on_commit_callbacks, confirmado) == 200
    fatura.refresh_from_db()
    assert (fatura.status, fatura.forma) == ("paga", "boleto")
    assert fatura.pago_em is not None
    assert WebhookRecebido.objects.filter(evento_id="evt_t184_1").count() == 1
    resultados = dict(WebhookRecebido.objects.values_list("evento_id", "resultado"))
    assert resultados == {"evt_t184_1": "baixada", "evt_t184_2": "ja_baixada"}
    pagar = EventoAuditoria.objects.filter(acao="fatura_assinatura.pagar")
    assert pagar.count() == 1
    assert (pagar.get().regra, pagar.get().ator_tipo) == ("PLT-14", "sistema")


def test_plt_14_webhook_nao_confia_no_corpo(
    moto, conta_principal_ligada, django_capture_on_commit_callbacks
):
    """Pago com outro valor no parceiro: não baixa (a equipe confere)."""
    fatura = _fat_0001(moto)
    cobranca_id = _emitir(fatura)
    corpo = pagamentos.simular_pagamento(cobranca_id, 40000, evento_id="evt_t184_3")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    fatura.refresh_from_db()
    assert fatura.status == "aberta"
    assert WebhookRecebido.objects.get(evento_id="evt_t184_3").resultado == "valor_diferente"


def test_plt_14_webhook_com_token_errado(
    moto, conta_principal_ligada, django_capture_on_commit_callbacks
):
    cobranca_id = _emitir(_fat_0001(moto))
    corpo = pagamentos.simular_pagamento(cobranca_id, evento_id="evt_t184_4")
    assert _webhook(django_capture_on_commit_callbacks, corpo, token="outro") == 401
    assert not WebhookRecebido.objects.filter(evento_id="evt_t184_4").exists()


def test_plt_14_sem_hash_configurado_nada_e_da_conta_principal(
    moto, settings, django_capture_on_commit_callbacks
):
    settings.GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH = ""
    cobranca_id = _emitir(_fat_0001(moto))
    corpo = pagamentos.simular_pagamento(cobranca_id, evento_id="evt_t184_5")
    assert _webhook(django_capture_on_commit_callbacks, corpo, token="") == 401
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 401


def test_plt_14_tarefa_tenta_de_novo_com_o_parceiro_fora():
    from apps.plataforma.tasks import plataforma_processar_webhook_fatura
    from integracoes.pagamentos.base import ParceiroIndisponivel

    assert ParceiroIndisponivel in plataforma_processar_webhook_fatura.autoretry_for


# --- Cartão da página do parceiro (PLT-13, ADR 0023) ---


def _escolher_cartao(empresa: Any) -> None:
    # A rota `PUT forma-pagamento/` é da T-185; aqui só a forma gravada.
    forma = FormaPagamentoAssinatura.objects.get(empresa=empresa)
    forma.forma = FormaAssinatura.CARTAO
    forma.save(update_fields=["forma"])


def test_plt_13_cartao_pago_na_pagina_fica_guardado(
    moto, conta_principal_ligada, django_capture_on_commit_callbacks
):
    _escolher_cartao(moto)
    fatura = _fat_0001(moto)
    cobranca_id = _emitir(fatura, "cartao_link")
    corpo = pagamentos.simular_pagamento(cobranca_id, evento_id="evt_t184_6")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    fatura.refresh_from_db()
    assert (fatura.status, fatura.forma) == ("paga", "cartao")
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto)
    assert (forma.status, forma.cartao_bandeira, forma.cartao_final) == ("ativa", "visa", "4242")
    token = f"tok_falso_{cobranca_id}"
    assert forma.cartao_token_cifrado_claro() == token
    assert token not in forma.cartao_token_cifrado  # cifrado no banco
    eventos = EventoAuditoria.objects.filter(acao__startswith="assinatura.")
    assert eventos.exists()
    assert all(token not in str(e.antes) + str(e.depois) for e in eventos)


def test_plt_13_cartao_com_outra_forma_nao_guarda_token(
    moto, conta_principal_ligada, django_capture_on_commit_callbacks
):
    """Pagar no cartão sem a forma cartão (o `meio` do "Pagar") não troca a forma."""
    fatura = _fat_0001(moto)
    cobranca_id = _emitir(fatura, "cartao_link")
    corpo = pagamentos.simular_pagamento(cobranca_id, evento_id="evt_t184_7")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto)
    assert (forma.forma, forma.cartao_token_cifrado, forma.cartao_final) == ("", "", "")


def test_plt_02_cartao_salvo_recusado_no_parceiro_falso(moto):
    pagamentos.recusar_cartao("tok_recusado")
    fatura = _fat_0001(moto)
    pedido = PedidoCobranca(
        "cartao", fatura.valor_centavos, fatura.vencimento, f"fatura-{fatura.pk}", Pagador("x")
    )
    with pytest.raises(CartaoRecusado):
        provedor().cobrar_cartao_salvo(conta_principal(), "tok_recusado", pedido)
    cobranca = provedor().cobrar_cartao_salvo(conta_principal(), "tok_bom", pedido)
    assert provedor().consultar_cobranca(conta_principal(), cobranca.id).status == "paga"


# --- Tomador da fatura (PLT-14, T-236, CA-ASS-59) ---

DOM_LUIS = {
    "cep": "60115170",
    "logradouro": "Av. Dom Luís",
    "numero": "500",
    "complemento": "Sala 3",
    "bairro": "Meireles",
    "cidade": "Fortaleza",
    "uf": "CE",
}


def _mudar_endereco_da_nota(empresa: Any, endereco: dict[str, str]) -> None:
    # A rota `PATCH dados-fiscais/` é da T-185; aqui só a mudança na `Empresa`.
    empresa.refresh_from_db()
    for campo, valor in endereco.items():
        setattr(empresa, f"endereco_{campo}", valor)
    empresa.save(update_fields=[f"endereco_{campo}" for campo in endereco])


def test_plt_14_fatura_guarda_tomador(
    moto, conta_principal_ligada, relogio, django_capture_on_commit_callbacks
):
    """CA-ASS-59, com a emissão da nota desligada (MVP): o tomador nasce na baixa."""
    _criar_matriz(moto)
    fat_1 = _fat_0001(moto)
    assert fat_1.tomador_gravado_em is None  # aberta, sem tomador
    relogio.em("2026-10-22 09:00")
    corpo = pagamentos.simular_pagamento(_emitir(fat_1), evento_id="evt_t184_8")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    fat_1.refresh_from_db()
    assert (fat_1.tomador_razao_social, fat_1.tomador_cnpj) == (
        "Moto Rápida Locações Ltda",
        "12345678000195",
    )
    assert fat_1.tomador_endereco["logradouro"] == "Av. Bezerra de Menezes"
    assert fat_1.tomador_gravado_em is not None

    relogio.em("2026-11-05 10:00")
    _mudar_endereco_da_nota(moto, DOM_LUIS)
    assert services.gravar_tomador(fat_1) is False  # gravado uma vez, não muda
    fat_1.refresh_from_db()
    assert fat_1.tomador_endereco["logradouro"] == "Av. Bezerra de Menezes"

    periodo = proximo_periodo(22, "mensal", date(2026, 11, 22))
    fat_2 = services.criar_fatura(
        moto,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=periodo.inicio,
        periodo=periodo,
        plano=moto.plano,
        ciclo="mensal",
        valor_centavos=44900,
    )
    relogio.em("2026-11-22 09:00")
    corpo = pagamentos.simular_pagamento(_emitir(fat_2), evento_id="evt_t184_9")
    assert _webhook(django_capture_on_commit_callbacks, corpo) == 200
    fat_2.refresh_from_db()
    assert fat_2.codigo == "FAT-0002"
    assert fat_2.tomador_endereco == DOM_LUIS
    # Os eventos da fatura no public não levam o tomador.
    assert not EventoAuditoria.objects.filter(depois__icontains="Bezerra").exists()


@pytest.mark.xfail(
    reason="Pedido da nota (gravar o tomador ao pedir a NFS-e) é da T-197, CA-ASS-29"
)
def test_plt_14_fatura_guarda_tomador_ao_pedir_a_nota(moto, settings):
    settings.GIRO_NFSE_ASSINATURA_ATIVA = True
    from apps.plataforma.tasks import plataforma_emitir_nota_fatura  # noqa: F401
