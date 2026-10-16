"""Endurecimento de produção (T-035): S-16, S-17, S-18, C-04. Cada caso sobe um processo limpo."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
AMBIENTE_PROD = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "segredo-django-de-teste",
    "JWT_SIGNING_KEY": "segredo-dos-tokens-de-teste",
    "DATABASE_URL": "postgres://u:p@db:5432/giro",
    "GIRO_REDES_PROXY": "10.0.0.0/8",
    "GIRO_CHAVE_DADOS_PESSOAIS": "1:" + "A" * 43 + "=",
    "GIRO_CHAVE_SEGREDOS": "1:" + "B" * 43 + "=",
    "GIRO_PEPPER_HMAC": "p" * 40,
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "smtp.example.com",
    "GIRO_ARMAZENAMENTO": "s3",
    "GIRO_PROVEDOR_PAGAMENTOS": "asaas",
    "GIRO_ASAAS_CHAVE_API": "chave-do-asaas-de-teste",
    "REDIS_URL": "redis://:senha-do-redis@redis:6379/0",
    "CELERY_BROKER_URL": "redis://:senha-do-redis@redis:6379/1",
    "CELERY_RESULT_BACKEND": "redis://:senha-do-redis@redis:6379/2",
}


def rodar(codigo: str, **variaveis: str | None) -> subprocess.CompletedProcess[str]:
    ambiente = {k: v for k, v in os.environ.items() if k not in AMBIENTE_PROD}
    ambiente.update({k: v for k, v in {**AMBIENTE_PROD, **variaveis}.items() if v is not None})
    return subprocess.run(  # noqa: S603 (argumentos fixos, sem entrada externa)
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )


def configuracao_de_prod(**variaveis: str | None) -> dict[str, Any]:
    resultado = rodar(
        "import json; from django.conf import settings as s;"
        "print(json.dumps({k: getattr(s, k) for k in ("
        "'SHOW_PUBLIC_IF_NO_TENANT_FOUND','SECURE_HSTS_SECONDS','SECURE_HSTS_PRELOAD',"
        "'SECURE_HSTS_INCLUDE_SUBDOMAINS','SECURE_REFERRER_POLICY','X_FRAME_OPTIONS',"
        "'EXPOR_DOCUMENTACAO_DA_API','USE_X_FORWARDED_HOST')}))",
        **variaveis,
    )
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def test_s16_prod_nao_serve_o_public_em_host_desconhecido():
    assert configuracao_de_prod()["SHOW_PUBLIC_IF_NO_TENANT_FOUND"] is False


def test_s17_prod_fecha_schema_e_docs_por_padrao():
    assert configuracao_de_prod()["EXPOR_DOCUMENTACAO_DA_API"] is False
    assert configuracao_de_prod(GIRO_EXPOR_DOCUMENTACAO_DA_API="1")["EXPOR_DOCUMENTACAO_DA_API"]


def test_t158_x_forwarded_host_so_em_dev_e_prod():
    assert configuracao_de_prod()["USE_X_FORWARDED_HOST"] is True
    for modulo, esperado in (("test", False), ("dev", True), ("base", False)):
        resultado = rodar(
            "from django.conf import settings as s; print(s.USE_X_FORWARDED_HOST)",
            DJANGO_SETTINGS_MODULE=f"config.settings.{modulo}",
        )
        assert resultado.returncode == 0, resultado.stderr
        assert resultado.stdout.strip() == str(esperado)


def test_s18_prod_hsts_com_preload_e_cabecalhos():
    cfg = configuracao_de_prod()
    assert cfg["SECURE_HSTS_SECONDS"] >= 31536000
    assert cfg["SECURE_HSTS_PRELOAD"] is True
    assert cfg["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert cfg["SECURE_REFERRER_POLICY"] == "same-origin"
    assert cfg["X_FRAME_OPTIONS"] == "DENY"


def test_t277_prod_sessao_do_admin_de_4_horas_que_fecha_com_o_navegador():
    resultado = rodar(
        "import json; from django.conf import settings as s;"
        "print(json.dumps({k: getattr(s, k) for k in ("
        "'SESSION_COOKIE_AGE','SESSION_EXPIRE_AT_BROWSER_CLOSE','SESSION_COOKIE_SECURE',"
        "'SESSION_COOKIE_DOMAIN','CSRF_COOKIE_SECURE')}))"
    )
    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout) == {
        "SESSION_COOKIE_AGE": 4 * 60 * 60,
        "SESSION_EXPIRE_AT_BROWSER_CLOSE": True,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_DOMAIN": None,
        "CSRF_COOKIE_SECURE": True,
    }


def test_s18_prod_recusa_chave_dos_tokens_igual_a_chave_do_django():
    resultado = rodar("import django.conf as c; c.settings.DEBUG", JWT_SIGNING_KEY=None)
    assert resultado.returncode != 0
    assert "JWT_SIGNING_KEY" in resultado.stderr


def test_prod_recusa_subir_sem_rede_de_proxy():
    resultado = rodar("import django.conf as c; c.settings.DEBUG", GIRO_REDES_PROXY=None)
    assert resultado.returncode != 0
    assert "GIRO_REDES_PROXY" in resultado.stderr


def recusa(mensagem: str, **variaveis: str | None) -> None:
    resultado = rodar("import django.conf as c; c.settings.DEBUG", **variaveis)
    assert resultado.returncode != 0
    assert mensagem in resultado.stderr, resultado.stderr


def test_r03_prod_recusa_as_chaves_e_o_pepper_do_env_example():
    exemplo_dados = "1:O6Era8PkgBlfbOR6Nt6IGvnBlEL9vRRNA3iXRdxDtkg="
    exemplo_segredos = "1:b/jBUdVpQ6mwUQJnFhzjnMkTVZvziqLLZfoEWrBDhs0="
    pepper = "07128db7f37327bc0128ca29852fae5bf3b0f67c758ad430d12af360c0332089"
    recusa("do .env.example", GIRO_CHAVE_DADOS_PESSOAIS=exemplo_dados)
    recusa("do .env.example", GIRO_CHAVE_SEGREDOS=exemplo_segredos)
    # Trocar só o id não esconde a chave de exemplo.
    recusa("do .env.example", GIRO_CHAVE_DADOS_PESSOAIS="7:" + exemplo_dados.split(":")[1])
    recusa("do .env.example", GIRO_PEPPER_HMAC=pepper)


def test_r03_prod_recusa_chaves_iguais_entre_dados_e_segredos():
    recusa("repetem uma chave", GIRO_CHAVE_SEGREDOS="2:" + "A" * 43 + "=")


def test_r03_prod_recusa_chave_que_nao_tem_32_bytes():
    recusa("32 bytes", GIRO_CHAVE_DADOS_PESSOAIS="1:AAAA")


def test_r03_prod_recusa_pepper_curto_ou_igual_a_outro_segredo():
    recusa("pelo menos 32 bytes", GIRO_PEPPER_HMAC="curto")
    repetido = "segredo-dos-tokens-de-teste" + "x" * 10
    recusa("repetir outro segredo", GIRO_PEPPER_HMAC=repetido, JWT_SIGNING_KEY=repetido)


CHAVES_OBRIGATORIAS = [
    "JWT_SIGNING_KEY",
    "GIRO_CHAVE_DADOS_PESSOAIS",
    "GIRO_CHAVE_SEGREDOS",
    "GIRO_PEPPER_HMAC",
]


@pytest.mark.parametrize("nome", CHAVES_OBRIGATORIAS)
@pytest.mark.parametrize("valor", ["", "   ", None])
def test_t133_prod_recusa_chave_vazia_ou_ausente(nome, valor):
    recusa(f"Defina {nome}", **{nome: valor})


def test_t133_dev_com_variaveis_vazias_cai_nos_padroes():
    # O compose entrega `NOME=` do .env como string vazia; o login não pode assinar com chave vazia.
    resultado = rodar(
        "import json; from django.conf import settings as s;"
        "print(json.dumps([s.SIMPLE_JWT['SIGNING_KEY'], s.SECRET_KEY, s.GIRO_PEPPER_HMAC,"
        "s.GIRO_CHAVE_DADOS_PESSOAIS, s.GIRO_CHAVE_SEGREDOS]))",
        DJANGO_SETTINGS_MODULE="config.settings.dev",
        **dict.fromkeys(CHAVES_OBRIGATORIAS, ""),
    )
    assert resultado.returncode == 0, resultado.stderr
    assinatura, segredo, pepper, dados, segredos = json.loads(resultado.stdout)
    assert assinatura == segredo == "segredo-django-de-teste"
    assert len(pepper) >= 32
    assert dados and segredos and dados != segredos


def test_t133_dev_com_chave_dos_tokens_preenchida_usa_a_chave():
    resultado = rodar(
        "from django.conf import settings as s; print(s.SIMPLE_JWT['SIGNING_KEY'])",
        DJANGO_SETTINGS_MODULE="config.settings.dev",
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "segredo-dos-tokens-de-teste"


@pytest.mark.parametrize("rede", ["0.0.0.0/0", "::/0", "nao-e-rede"])
def test_prod_recusa_rede_de_proxy_aberta_ou_invalida(rede):
    recusa("GIRO_REDES_PROXY", GIRO_REDES_PROXY=rede)


@pytest.mark.parametrize("modulo", ["config.wsgi", "config.asgi", "config.celery"])
def test_c04_sem_padrao_dev_quando_a_variavel_falta(modulo):
    resultado = rodar(f"import {modulo}", DJANGO_SETTINGS_MODULE=None)
    assert resultado.returncode != 0
    assert "DJANGO_SETTINGS_MODULE" in resultado.stderr


@pytest.mark.parametrize("tipo", ["console", "locmem", "filebased", "dummy"])
def test_t157_prod_recusa_email_de_desenvolvimento(tipo):
    recusa(
        "só vale no desenvolvimento", EMAIL_BACKEND=f"django.core.mail.backends.{tipo}.EmailBackend"
    )


def test_t157_prod_recusa_email_sem_backend_definido():
    # Sem a variável, base.py cai no console, que mandaria o token dos e-mails para o log.
    recusa("só vale no desenvolvimento", EMAIL_BACKEND=None)


@pytest.mark.parametrize("valor", ["", "  ", None])
def test_t157_prod_recusa_smtp_sem_servidor(valor):
    recusa("Defina EMAIL_HOST", EMAIL_HOST=valor)


@pytest.mark.parametrize("valor", ["falso", "", None])
def test_t157_prod_recusa_armazenamento_que_nao_e_s3(valor):
    recusa("GIRO_ARMAZENAMENTO=s3", GIRO_ARMAZENAMENTO=valor)


@pytest.mark.parametrize("valor", ["falso", "", None])
def test_t157_prod_recusa_pagamentos_falso(valor):
    recusa("GIRO_PROVEDOR_PAGAMENTOS=asaas", GIRO_PROVEDOR_PAGAMENTOS=valor)


@pytest.mark.parametrize("valor", ["", "   ", None])
def test_t157_prod_recusa_asaas_sem_chave(valor):
    recusa("Defina GIRO_ASAAS_CHAVE_API", GIRO_ASAAS_CHAVE_API=valor)


def test_t157_prod_sobe_com_as_integracoes_reais():
    resultado = rodar(
        "import json; from django.conf import settings as s;"
        "print(json.dumps([s.EMAIL_BACKEND, s.GIRO_ARMAZENAMENTO, s.GIRO_PROVEDOR_PAGAMENTOS]))"
    )
    assert resultado.returncode == 0, resultado.stderr
    assert json.loads(resultado.stdout) == [
        "django.core.mail.backends.smtp.EmailBackend",
        "s3",
        "asaas",
    ]


@pytest.mark.parametrize("url", ["postgres://giro@db:5432/giro", "postgres://db:5432/giro"])
def test_t274_prod_recusa_banco_sem_senha(url):
    recusa("DATABASE_URL sem senha", DATABASE_URL=url)


@pytest.mark.parametrize("nome", ["REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"])
@pytest.mark.parametrize("url", ["redis://redis:6379/0", "redis://usuario@redis:6379/0", None])
def test_t274_prod_recusa_redis_sem_senha(nome, url):
    # Ausente cai no padrão de base.py (`redis://redis:6379/N`), sem senha: também recusado.
    recusa(f"{nome} sem senha", **{nome: url})


def test_t274_prod_aceita_redis_com_senha_e_tls():
    resultado = rodar(
        "from django.conf import settings as s; print(s.REDIS_URL)",
        REDIS_URL="rediss://usuario:senha@redis.interno:6380/0",
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip() == "rediss://usuario:senha@redis.interno:6380/0"
