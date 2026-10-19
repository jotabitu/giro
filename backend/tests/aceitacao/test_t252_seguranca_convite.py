"""T-252 · Revisão de segurança do link do convite (USR-01, rota da T-250).

Relatório: `docs/seguranca/2026-10-16-t252-link-convite.md`. O que a T-250 já testa (só
administrador, suporte 403, `no-store`, limites por hora, evento sem token, link anterior que deixa
de valer) não se repete aqui. O achado B-01 (o e-mail de um convite já invalidado saía) foi
corrigido na T-282, e o teste dele deixou de ser `xfail`.
"""

from types import SimpleNamespace
from typing import Any

from django.core import mail
from django.core.cache import cache
from django.db import connection
from rest_framework.throttling import SimpleRateThrottle

from apps.contas.models import Convite, Usuario
from apps.contas.tasks import contas_enviar_convite
from comum.limites import LinkConvitePorAdministrador, LinkConvitePorConvidado
from integracoes.whatsapp.falso import caixa_de_saida

from .test_t011_contas import (
    adm,  # noqa: F401 - fixture
    moto,  # noqa: F401 - fixture
)
from .test_t250_decisoes import _carla, _copiar, _token


def _chave(limite: SimpleRateThrottle, pk: int) -> str:
    """A chave do limite como o Redis a guarda: `make_key` põe o schema da conexão atual."""
    requisicao: Any = SimpleNamespace(user=SimpleNamespace(pk=pk, is_authenticated=True))
    visao: Any = SimpleNamespace(kwargs={"pk": pk})
    chave = limite.get_cache_key(requisicao, visao)
    return str(cache.make_key(chave))


def test_usr_01_limite_do_link_conta_por_empresa(empresa_a, empresa_b):
    """O limite por convidado conta pelo `pk` da URL, que se repete entre empresas: a chave tem de
    levar o schema, senão o administrador de uma empresa esgota o limite da pessoa de mesmo `pk`
    em outra."""
    for limite in (LinkConvitePorConvidado(), LinkConvitePorAdministrador()):
        connection.set_tenant(empresa_a)
        da_a = _chave(limite, 7)
        connection.set_tenant(empresa_b)
        da_b = _chave(limite, 7)
        assert da_a != da_b
        assert "empresa_a" in da_a and "empresa_b" in da_b


def test_usr_01_email_de_convite_invalidado_nao_sai(
    adm,  # noqa: F811 - fixture
    relogio,
    django_capture_on_commit_callbacks,
):
    """E-mail do convite (ou do reenvio) ainda na fila, ou repetido pela fila, e o administrador
    copia o link antes: o convite do e-mail já não vale (P-06), e o e-mail e o WhatsApp dele não
    deveriam sair."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    do_email = Convite.objects.filter(usuario=carla).latest("criado_em")
    _token(_copiar(adm, api, carla))  # invalida o convite do e-mail
    Usuario.objects.filter(pk=carla.pk).update(celular="85999990000")
    connection.set_tenant(adm.empresa)
    enviados, whatsapps = len(mail.outbox), len(caixa_de_saida)
    hash_antes = Convite.objects.get(pk=do_email.pk).token_hash
    contas_enviar_convite(adm.empresa.schema_name, do_email.pk)
    assert len(mail.outbox) == enviados
    assert len(caixa_de_saida) == whatsapps
    # Nem gera token novo para o convite morto.
    assert Convite.objects.get(pk=do_email.pk).token_hash == hash_antes


def test_usr_01_convite_valendo_ainda_sai(
    adm,  # noqa: F811 - fixture
    relogio,
    django_capture_on_commit_callbacks,
):
    """T-282: a guarda só barra o convite vencido; o que vale segue saindo pela fila."""
    relogio.em("2026-10-07 10:00")
    api = adm.logar("Mariana")
    carla = _carla(adm, api, django_capture_on_commit_callbacks)
    valendo = Convite.objects.filter(usuario=carla).latest("criado_em")
    connection.set_tenant(adm.empresa)
    enviados = len(mail.outbox)
    contas_enviar_convite(adm.empresa.schema_name, valendo.pk)
    assert len(mail.outbox) == enviados + 1
    assert mail.outbox[-1].to == [carla.email]
