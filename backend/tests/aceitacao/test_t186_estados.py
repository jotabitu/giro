"""T-186 (parte 1) · Estados da empresa e virada do dia (`docs/api/assinatura.md`, "Transições da
empresa" e "Downgrade agendado: conferência e virada"; PLT-01, PLT-02, PLT-04).

Relógio de referência (ADR 0021): Moto Rápida em teste de 07 a 21 out, FAT-0001 de R$ 449,00
vencendo em 22 out. Com forma e sem pagar: `inadimplente` em 23 out e `suspensa` em 06 nov; sem
forma: `suspensa` em 22 out; paga: `ativa` em 22 out, ou na hora se paga depois do fim do teste.
A geração das faturas seguintes (5 dias antes) é da parte 2: aqui a fatura do período seguinte
nasce pelo serviço `criar_fatura`, como a `gerar_faturas` fará.
"""

from collections.abc import Iterator
from datetime import date

import pytest
from django_tenants.utils import schema_context

from apps.auditoria.models import EventoAuditoria
from apps.plataforma import services
from apps.plataforma.calendario import proximo_periodo
from apps.plataforma.models import Empresa, FaturaAssinatura, Plano, StatusFatura, TipoFatura
from integracoes.pagamentos import falso as pagamentos
from integracoes.pagamentos.base import EventoWebhook

from .test_t185_assinatura import MotoRapida, _mudar


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    yield MotoRapida(criar_empresa())
    pagamentos.limpar()


def _virar(relogio, dia: str) -> services.Virada:
    relogio.em(f"{dia} 00:05")
    return services.virar_estados()


def _status(moto: MotoRapida) -> str:
    return moto.recarregar().status


def _pagar_pelo_parceiro(moto: MotoRapida, codigo: str, evento: str) -> str:
    """O "Pagar" pelo boleto e o aviso da conta principal com a baixa (T-184, T-185)."""
    fatura = services.pagar_fatura(moto.recarregar(), codigo, meio="boleto")
    assert fatura.cobranca_externa_id
    pagamentos.simular_pagamento(fatura.cobranca_externa_id)
    cobranca = fatura.cobranca_externa_id
    aviso = services.registrar_webhook_principal(
        EventoWebhook("asaas", evento, "PAYMENT_RECEIVED", cobranca, "", ""), {}
    )
    assert aviso is not None
    return services.processar_webhook_fatura(aviso.pk)


def _eventos(acao: str, schema: str) -> list[EventoAuditoria]:
    with schema_context(schema):
        return list(EventoAuditoria.objects.filter(acao=acao).order_by("id"))


def _com_boleto(moto: MotoRapida) -> None:
    services.escolher_forma_pagamento(moto.recarregar(), "boleto")


# --- Fatura atrasada em D+1 (PLT-02) ---


def test_plt_02_fatura_atrasada_no_dia_seguinte_ao_vencimento(moto, relogio):
    _com_boleto(moto)
    assert _virar(relogio, "2026-10-22").atrasadas == 0
    assert moto.fatura("FAT-0001").status == StatusFatura.ABERTA
    assert _virar(relogio, "2026-10-23").atrasadas == 1
    assert moto.fatura("FAT-0001").status == StatusFatura.ATRASADA
    evento = _eventos("fatura_assinatura.atrasar", "public")[-1]
    assert evento.regra == "PLT-02"
    assert evento.ator_tipo == "sistema"


# --- Fim do teste (PLT-01, tabela de estados) ---


def test_plt_01_paga_no_teste_continua_em_teste_e_vira_ativa_no_dia_seguinte(moto, relogio):
    """Moto Rápida: `em_teste` até 21 out mesmo pagando antes; paga até 22 out → `ativa` em 22."""
    _com_boleto(moto)
    relogio.em("2026-10-15 10:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0001", "evt-1") == "baixada"
    assert _status(moto) == "em_teste"
    _virar(relogio, "2026-10-21")
    assert _status(moto) == "em_teste"
    assert _virar(relogio, "2026-10-22").estados == {"ativa": 1}
    assert _status(moto) == "ativa"
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.ativa", schema)[-1]
        assert (evento.antes["status"], evento.depois["status"]) == ("em_teste", "ativa")
        assert evento.ator_tipo == "sistema"


def test_plt_01_ca_ass_06_sem_forma_suspensa_no_dia_seguinte_ao_teste(moto, relogio):
    """Sem forma no fim do teste: `suspensa` em 22 out; paga depois → `ativa` na hora, e a
    próxima continua no dia 22."""
    _virar(relogio, "2026-10-21")
    assert _status(moto) == "em_teste"
    assert _virar(relogio, "2026-10-22").estados == {"suspensa": 1}
    assert _status(moto) == "suspensa"
    relogio.em("2026-10-25 15:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0001", "evt-1") == "baixada"
    empresa = moto.recarregar()
    assert empresa.status == "ativa"
    assert empresa.dia_vencimento == 22
    proxima = services.proxima_mensalidade(empresa)
    assert proxima is not None
    assert proxima.vencimento == date(2026, 11, 22)


def test_plt_02_ca_ass_05_com_forma_inadimplente_em_d1_e_suspensa_em_d15(moto, relogio):
    """Com forma e sem pagar: `em_teste` no vencimento, `inadimplente` em 23 out, `suspensa` em
    06 nov (D+15 do vencimento de 22 out)."""
    _com_boleto(moto)
    _virar(relogio, "2026-10-22")
    assert _status(moto) == "em_teste"
    assert _virar(relogio, "2026-10-23").estados == {"inadimplente": 1}
    assert _status(moto) == "inadimplente"
    _virar(relogio, "2026-11-05")
    assert _status(moto) == "inadimplente"
    assert _virar(relogio, "2026-11-06").estados == {"suspensa": 1}
    assert _status(moto) == "suspensa"
    assert [e.depois["status"] for e in _eventos("empresa.suspensa", moto.empresa.schema_name)] == [
        "suspensa"
    ]


def test_plt_02_primeira_paga_depois_do_fim_do_teste_ativa_na_hora(moto, relogio):
    """Com forma, a 1ª paga no dia do vencimento (o teste já acabou): `ativa` na hora."""
    _com_boleto(moto)
    _virar(relogio, "2026-10-22")
    relogio.em("2026-10-22 14:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0001", "evt-1") == "baixada"
    assert _status(moto) == "ativa"


# --- Volta a ativa ao pagar (tabela de estados) ---


def test_plt_02_inadimplente_que_paga_volta_a_ativa_na_hora(moto, relogio):
    _com_boleto(moto)
    _virar(relogio, "2026-10-23")
    relogio.em("2026-10-24 11:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0001", "evt-1") == "baixada"
    assert _status(moto) == "ativa"
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.ativa", schema)[-1]
        assert (evento.antes["status"], evento.depois["status"]) == ("inadimplente", "ativa")
        assert evento.regra == "PLT-02"
    # Já ativa, a virada seguinte não muda nada.
    assert _virar(relogio, "2026-10-25").estados == {}


def test_plt_02_paga_uma_mas_outra_atrasada_continua_inadimplente(moto, relogio):
    """Paga a FAT-0001 com a diferença do upgrade ainda atrasada: segue `inadimplente`, e o
    D+15 segue o vencimento da que ficou."""
    _com_boleto(moto)
    services.criar_fatura(
        moto.recarregar(),
        tipo=TipoFatura.DIFERENCA_PLANO,
        vencimento=date(2026, 10, 25),
        periodo=proximo_periodo(22, "mensal", date(2026, 10, 22)),
        plano=Plano.objects.get(nome="Completo"),
        ciclo="mensal",
        valor_centavos=45000,
    )
    _virar(relogio, "2026-10-26")
    assert _status(moto) == "inadimplente"
    relogio.em("2026-10-27 10:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0001", "evt-1") == "baixada"
    assert _status(moto) == "inadimplente"
    _virar(relogio, "2026-11-06")
    assert _status(moto) == "inadimplente"  # o D+15 é o da FAT-0002, 09 nov
    assert _virar(relogio, "2026-11-09").estados == {"suspensa": 1}
    relogio.em("2026-11-10 10:00")
    assert _pagar_pelo_parceiro(moto, "FAT-0002", "evt-2") == "baixada"
    assert _status(moto) == "ativa"


def test_plt_02_ativa_vira_inadimplente_em_d1(moto, relogio):
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    empresa = moto.recarregar()
    services.criar_fatura(
        empresa,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=date(2026, 11, 22),
        periodo=proximo_periodo(22, "mensal", date(2026, 11, 22)),
        plano=empresa.plano,
        ciclo="mensal",
        valor_centavos=44900,
    )
    _virar(relogio, "2026-11-22")
    assert _status(moto) == "ativa"
    assert _virar(relogio, "2026-11-23").estados == {"inadimplente": 1}


def test_plt_02_virada_idempotente_no_mesmo_dia(moto, relogio):
    _com_boleto(moto)
    primeira = _virar(relogio, "2026-10-23")
    assert (primeira.atrasadas, primeira.estados) == (1, {"inadimplente": 1})
    segunda = _virar(relogio, "2026-10-23")
    assert (segunda.atrasadas, segunda.mudancas_de_plano, segunda.estados) == (0, 0, {})
    assert len(_eventos("empresa.inadimplente", "public")) == 1


def test_plt_02_estados_isolados_por_empresa(moto, relogio, criar_empresa):
    """Cada empresa vira pelas próprias faturas e pela própria forma: a Moto Rápida, sem forma,
    fica `suspensa`; a outra, com boleto, `inadimplente`. Nenhum evento cruza os schemas."""
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81", nome_exibicao="Outra")
    services.escolher_forma_pagamento(outra, "boleto")
    _virar(relogio, "2026-10-23")
    assert _status(moto) == "suspensa"
    assert Empresa.objects.get(pk=outra.pk).status == "inadimplente"
    assert not _eventos("empresa.inadimplente", moto.empresa.schema_name)
    assert not _eventos("empresa.suspensa", outra.schema_name)


# --- Downgrade agendado: a virada no dia do vencimento (PLT-04, CA-ASS-41) ---


def test_plt_04_downgrade_agendado_vira_no_dia_do_vencimento(moto, relogio):
    """Completo `ativa` (22 out a 21 nov), Profissional agendado em 01 nov; a fatura de 22 nov
    saiu pelo Profissional (R$ 449,00). Em 21 nov nada muda; em 22 nov o plano vira, com o
    preço de tabela, sem conferir o uso de novo, e com o ator do sistema nos dois lugares."""
    moto.no_completo()
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    assert _mudar(moto.api(), "Profissional").status_code == 200
    profissional = Plano.objects.get(nome="Profissional")
    services.criar_fatura(
        moto.recarregar(),
        tipo=TipoFatura.MENSALIDADE,
        vencimento=date(2026, 11, 22),
        periodo=proximo_periodo(22, "mensal", date(2026, 11, 22)),
        plano=profissional,
        ciclo="mensal",
        valor_centavos=44900,
    )
    assert _virar(relogio, "2026-11-21").mudancas_de_plano == 0
    assert moto.recarregar().plano.nome == "Completo"
    assert _virar(relogio, "2026-11-22").mudancas_de_plano == 1
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.ciclo, empresa.preco_contratado_centavos) == (
        "Profissional",
        "mensal",
        44900,
    )
    assert (empresa.plano_proximo, empresa.ciclo_proximo) == (None, "")
    for schema in ("public", moto.empresa.schema_name):
        evento = _eventos("empresa.mudar_plano", schema)[-1]
        assert evento.ator_tipo == "sistema"
        assert evento.depois["plano"] == "Profissional"
        assert evento.depois["vale_em"] == "2026-11-22"
    assert _virar(relogio, "2026-11-22").mudancas_de_plano == 0


def test_plt_04_downgrade_sem_a_fatura_do_periodo_nao_vira(moto, relogio):
    """Sem a fatura do período gerada pelo plano agendado, o plano não muda."""
    moto.no_completo()
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    assert _mudar(moto.api(), "Profissional").status_code == 200
    assert _virar(relogio, "2026-11-22").mudancas_de_plano == 0
    assert moto.recarregar().plano.nome == "Completo"
    assert FaturaAssinatura.objects.filter(empresa=moto.empresa).count() == 1
