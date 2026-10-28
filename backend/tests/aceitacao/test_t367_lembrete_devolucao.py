"""T-367 · Lembrete de devolução (AUT-01; modelo 11 de `docs/qa/criterios/whatsapp.md`).

Carteira de outubro da Moto Rápida: a LOC-2836 (Juliana, Filial Centro) tem o fim previsto em
14 out 18:00 (LOC-06). Às 08:00 desse dia, a tarefa lembra a Juliana uma vez.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.cache import cache

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.empresas.models import ConfiguracaoEmpresa
from apps.locacoes import services
from apps.locacoes.models import Locacao
from apps.locacoes.tasks import aut_01_lembrete_de_devolucao
from comum import estados
from integracoes.whatsapp import falso as whatsapp

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t017_financeiro import com_carteira  # noqa: F401 - fixture

LEMBRETE_DA_JULIANA = (
    "Olá, Juliana. Moto Rápida informa: hoje é o dia da devolução da LOC-2836, às 18:00, no "
    "endereço Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza. Para mudar o horário, ligue "
    "para a loja."
)


@pytest.fixture(autouse=True)
def moto_rapida(cenario):  # noqa: F811
    """A marca dos textos: o nome de exibição da empresa é "Moto Rápida"."""
    configuracao = ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()
    configuracao.nome_exibicao = "Moto Rápida"
    configuracao.save()
    cache.clear()
    whatsapp.caixa_de_saida.clear()
    mail.outbox.clear()
    yield
    whatsapp.caixa_de_saida.clear()


def _mensagens(celular: str) -> list[str]:
    return [m.texto for m in whatsapp.caixa_de_saida if m.celular == celular]


def _eventos(locacao: Locacao) -> list[EventoAuditoria]:
    return list(
        EventoAuditoria.objects.filter(
            objeto_tipo="locacao", objeto_id=locacao.pk, acao=services.LEMBRETE_DE_DEVOLUCAO
        )
    )


def test_aut_01_lembrete_de_devolucao(cenario, com_carteira, relogio):  # noqa: F811
    """Em 14 out às 08:00, a Juliana recebe pelo WhatsApp o horário e o endereço da Filial
    Centro. Rodar de novo no dia, ou depois, não manda outro (uma vez por locação)."""
    juliana = cenario.clientes["Juliana"]
    locacao = com_carteira["LOC-2836"]
    relogio.em("2026-10-14 08:00")
    aut_01_lembrete_de_devolucao("empresa_a")
    assert _mensagens(juliana.celular) == [LEMBRETE_DA_JULIANA]
    assert mail.outbox == []
    (evento,) = _eventos(locacao)
    assert (evento.regra, evento.depois, evento.ator_tipo) == (
        "AUT-01",
        {"canal": "whatsapp"},
        "sistema",
    )

    aut_01_lembrete_de_devolucao("empresa_a")
    relogio.em("2026-10-14 12:00")
    aut_01_lembrete_de_devolucao("empresa_a")
    assert _mensagens(juliana.celular) == [LEMBRETE_DA_JULIANA]
    assert len(_eventos(locacao)) == 1


def test_aut_01_so_no_dia_da_devolucao(cenario, com_carteira, relogio):  # noqa: F811
    """Antes do dia, nada sai: em 07 out nenhuma locação da carteira devolve hoje (caso "Fim
    previsto da LOC-2836"), e em 13 out a LOC-2836 ainda não é lembrada."""
    juliana = cenario.clientes["Juliana"]
    for dia in ("2026-10-07 08:00", "2026-10-13 08:00"):
        relogio.em(dia)
        assert services.lembrar_devolucoes() == 0
    assert _mensagens(juliana.celular) == []


def test_aut_01_renovada_nao_lembra_de_novo(cenario, com_carteira, relogio):  # noqa: F811
    """Uma vez por locação: lembrada em 14 out e renovada para 21 out, não recebe outro."""
    juliana = cenario.clientes["Juliana"]
    locacao = com_carteira["LOC-2836"]
    relogio.em("2026-10-14 08:00")
    assert services.lembrar_devolucoes() == 1
    Locacao.objects.filter(pk=locacao.pk).update(
        fim_previsto=locacao.fim_previsto + timedelta(days=7)
    )
    relogio.em("2026-10-21 08:00")
    services.lembrar_devolucoes()  # a LOC-2856 da carteira devolve em 21 out
    assert len(_mensagens(juliana.celular)) == 1
    assert len(_eventos(locacao)) == 1


def test_aut_01_sem_celular_vai_pelo_email(cenario, com_carteira, relogio):  # noqa: F811
    """Sem celular, o mesmo texto sai pelo e-mail com a marca da locadora. Sem os dois, nada sai,
    e o evento guarda o canal vazio."""
    juliana = cenario.clientes["Juliana"]
    locacao = com_carteira["LOC-2836"]
    Cliente.objects.filter(pk=juliana.pk).update(celular="")
    relogio.em("2026-10-14 08:00")
    assert services.lembrar_devolucoes() == 1
    assert whatsapp.caixa_de_saida == []
    (email,) = mail.outbox
    assert (email.to, email.subject, email.body) == (
        ["juliana@email.com"],
        "Moto Rápida: lembrete de devolução",
        LEMBRETE_DA_JULIANA,
    )
    assert email.from_email.startswith("Moto Rápida <")
    assert _eventos(locacao)[0].depois == {"canal": "email"}


def test_aut_01_sem_celular_e_sem_email_nada_sai(cenario, com_carteira, relogio):  # noqa: F811
    juliana = cenario.clientes["Juliana"]
    locacao = com_carteira["LOC-2836"]
    Cliente.objects.filter(pk=juliana.pk).update(celular="", email="")
    relogio.em("2026-10-14 08:00")
    assert services.lembrar_devolucoes() == 1
    assert (whatsapp.caixa_de_saida, mail.outbox) == ([], [])
    assert _eventos(locacao)[0].depois == {"canal": ""}


def test_aut_01_so_a_locacao_ativa(cenario, com_carteira, relogio):  # noqa: F811
    """A locação que já não está `ativa` no dia (encerrada antes da hora) não é lembrada."""
    locacao = com_carteira["LOC-2836"]
    relogio.em("2026-10-14 08:00")
    estados.transicionar(
        locacao, "encerrada", motivo="Devolvida antes", acao="locacao.encerrar", regra="DEV-01"
    )
    assert services.lembrar_devolucoes() == 0
    assert _mensagens(cenario.clientes["Juliana"].celular) == []
