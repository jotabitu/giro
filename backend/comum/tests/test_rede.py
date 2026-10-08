"""ADR 0018, item 4 (C-03). Nos testes, GIRO_REDES_PROXY = 10.0.0.0/8 e 1 proxy confiável."""

from django.test import RequestFactory, override_settings

from comum.rede import ip_do_cliente

PROXY = "10.0.0.2"


def _ip(remoto: str, xff: str | None = None) -> str | None:
    request = RequestFactory().get("/", REMOTE_ADDR=remoto)
    if xff is not None:
        request.META["HTTP_X_FORWARDED_FOR"] = xff
    return ip_do_cliente(request)


def test_ip_do_cliente_ignora_xff_forjado_sem_proxy():
    assert _ip("203.0.113.50", "1.2.3.4") == "203.0.113.50"


def test_ip_do_cliente_com_proxy_confiavel_pega_a_entrada_da_direita():
    assert _ip(PROXY, "1.2.3.4, 203.0.113.9") == "203.0.113.9"


def test_ip_do_cliente_com_cabecalho_curto_vale_o_remote_addr():
    with override_settings(GIRO_PROXIES_CONFIAVEIS=2):
        assert _ip(PROXY, "203.0.113.9") == PROXY


def test_ip_do_cliente_com_dois_proxies():
    with override_settings(GIRO_PROXIES_CONFIAVEIS=2):
        assert _ip(PROXY, "1.2.3.4, 203.0.113.9, 10.0.0.7") == "203.0.113.9"


def test_ip_do_cliente_sem_cabecalho_vazio_ou_invalido_vale_o_remote_addr():
    assert _ip(PROXY) == PROXY
    assert _ip(PROXY, "") == PROXY
    assert _ip(PROXY, " , ") == PROXY
    assert _ip(PROXY, "1.2.3.4, nao-e-ip") == PROXY


def test_ip_do_cliente_sem_redes_configuradas_nunca_confia():
    with override_settings(GIRO_REDES_PROXY=[]):
        assert _ip(PROXY, "203.0.113.9") == PROXY


def test_ip_do_cliente_aceita_ipv6():
    with override_settings(GIRO_REDES_PROXY=["fd00::/8"]):
        assert _ip("fd00::1", "2001:db8::5") == "2001:db8::5"
    assert _ip("2001:db8::9", "203.0.113.9") == "2001:db8::9"


def test_aud_01_auditoria_grava_o_ip_do_cliente_atras_do_proxy():
    from comum.middleware import ator_da_requisicao

    request = RequestFactory().get(
        "/", REMOTE_ADDR=PROXY, HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.9"
    )
    assert ator_da_requisicao(request).ip == "203.0.113.9"
