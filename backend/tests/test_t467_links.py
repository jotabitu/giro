"""T-467 · Links que o sistema manda ou copia: esquema e porta vêm da configuração.

No compose, o link abre como está (http e a porta do Next); em homologação e produção, https
e sem porta, como antes. O webhook de pagamentos continua sempre em https.
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from apps.contas.services import link_do_convite
from apps.contratos.services import link_de_assinatura
from apps.vistorias.services import link_do_recibo
from comum import enderecos

from .test_producao import rodar

HOST = "motorapida.localhost"
PRODUCAO = "motorapida.girolocadoras.com.br"
LINK = f"from comum.enderecos import link; print(link({PRODUCAO!r}, '/recibo#t'))"


@override_settings(GIRO_LINKS_ESQUEMA="http", GIRO_LINKS_PORTA="3000")
def test_t467_links_do_desenvolvimento_abrem_no_compose():
    assert link_do_recibo(HOST, "tok") == "http://motorapida.localhost:3000/recibo#tok"
    assert link_do_convite(HOST, "tok") == "http://motorapida.localhost:3000/convite#tok"
    assert link_de_assinatura(HOST, "tok") == "http://motorapida.localhost:3000/assinar#tok"


@override_settings(GIRO_LINKS_ESQUEMA="https", GIRO_LINKS_PORTA="")
def test_t467_links_de_producao_sem_porta():
    host = "motorapida.girolocadoras.com.br"
    assert link_do_recibo(host, "tok") == "https://motorapida.girolocadoras.com.br/recibo#tok"
    assert link_de_assinatura(host, "tok") == "https://motorapida.girolocadoras.com.br/assinar#tok"


@override_settings(GIRO_LINKS_ESQUEMA="ftp", GIRO_LINKS_PORTA="")
def test_t467_esquema_desconhecido_nao_monta_link():
    with pytest.raises(ImproperlyConfigured):
        enderecos.origem(HOST)


@override_settings(GIRO_LINKS_ESQUEMA="https", GIRO_LINKS_PORTA="30a0")
def test_t467_porta_que_nao_e_numero_nao_monta_link():
    with pytest.raises(ImproperlyConfigured):
        enderecos.origem(HOST)


def test_t467_settings_de_desenvolvimento_usam_http_e_3000():
    resultado = rodar(f"import django; {LINK}", DJANGO_SETTINGS_MODULE="config.settings.dev")
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "http://motorapida.girolocadoras.com.br:3000/recibo#t"


def test_t467_producao_continua_https_sem_porta_e_recusa_http():
    padrao = rodar(LINK)
    assert padrao.returncode == 0, padrao.stderr
    assert padrao.stdout.strip() == "https://motorapida.girolocadoras.com.br/recibo#t"

    recusa = rodar(LINK, GIRO_LINKS_ESQUEMA="http")
    assert recusa.returncode != 0
    assert "GIRO_LINKS_ESQUEMA só pode ser http no desenvolvimento" in recusa.stderr
