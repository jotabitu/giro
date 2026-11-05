"""T-435 · Compra pública (`docs/api/compra.md`; PLT-01, PLT-11, PLT-13, PLT-16, USR-01).

Moto Rápida dos dados de referência: compra em 07 out 2026, teste até 21 out, FAT-0001 de
R$ 449,00 vencendo em 22 out (R$ 4.490,00 no anual).
"""

import re
from datetime import date, timedelta
from typing import Any

import pytest
from django.core import mail
from django.db import connection
from django_tenants.utils import tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Convite, Usuario
from apps.plataforma import compra
from apps.plataforma.models import (
    Empresa,
    FaturaAssinatura,
    PedidoCompra,
    StatusFatura,
    StatusPedidoCompra,
)
from apps.plataforma.services import PlanoForaDaVenda, mudar_plano, plano_para_mudar
from comum.estados import transicionar
from integracoes import cnpj as integracao_cnpj
from integracoes.cnpj import DadosDoCnpj

from .conftest import CNPJ_MOTO_RAPIDA, HOST_PLATAFORMA, cliente

BASE = "/api/publico/compra/"


def _cnpj(base: str) -> str:
    """CNPJ válido a partir de 12 dígitos (os dígitos verificadores pela regra da Receita)."""
    from comum.documentos import _digito_cnpj

    primeiro = _digito_cnpj(base)
    return base + primeiro + _digito_cnpj(base + primeiro)


def _api() -> Any:
    return cliente(HOST_PLATAFORMA)


def _corpo(**mudar: Any) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "plano": "profissional",
        "ciclo": "mensal",
        "forma_pagamento": None,
        "administrador": {
            "nome": "Mariana Costa",
            "email": "mariana@motorapida.com.br",
            "celular": "85998124410",
            "aceita_whatsapp": True,
        },
        "empresa": {
            "cnpj": CNPJ_MOTO_RAPIDA,
            "razao_social": "Moto Rápida Locações Ltda",
            "nome_exibicao": "Moto Rápida",
            "cidade": "Fortaleza",
            "uf": "CE",
            "subdominio": "motorapida",
        },
        "aceite_termos": True,
    }
    corpo.update(mudar)
    return corpo


def _codigo_do_email() -> str:
    achado = re.search(r"Seu código é (\d{6})", mail.outbox[-1].body)
    assert achado, mail.outbox[-1].body
    return achado.group(1)


def _pedir(api: Any, capturar: Any, **mudar: Any) -> tuple[str, str]:
    with capturar(execute=True):
        resposta = api.post(f"{BASE}pedidos/", _corpo(**mudar), format="json")
    assert resposta.status_code == 202, resposta.json()
    return resposta.json()["chave"], _codigo_do_email()


def _confirmar(api: Any, capturar: Any, chave: str, codigo: str) -> Any:
    with capturar(execute=True):
        resposta = api.post(f"{BASE}pedidos/{chave}/confirmar/", {"codigo": codigo}, format="json")
    connection.set_schema_to_public()
    return resposta


def _apagar(empresa: Empresa) -> None:
    """A empresa como depois do apagamento (AUD-08): só a linha, com o CNPJ."""
    Empresa.objects.filter(pk=empresa.pk).update(apagada_em=empresa.criado_em)


# --- Catálogo (PLT-11, T-378) ---


def test_plt_11_catalogo_publico_sem_completo(publico, relogio, planos):
    resposta = _api().get(f"{BASE}planos/")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [p["codigo"] for p in corpo["planos"]] == ["essencial", "profissional"]
    profissional = corpo["planos"][1]
    assert profissional["mensal_centavos"] == 44900
    assert profissional["anual_centavos"] == 449000
    assert profissional["limites"] == {"veiculos": 150, "filiais": 3, "usuarios": 10}
    assert profissional["inclui"] == [
        "Tudo do Essencial, mais despesas",
        "Pix e boleto automáticos e cobrança pelo WhatsApp",
    ]
    assert profissional["destaque"] is True and corpo["planos"][0]["destaque"] is False
    assert corpo["teste"] == {
        "dias": 14,
        "inicio": "2026-10-07",
        "fim": "2026-10-21",
        "lembrete": "2026-10-19",
        "primeira_fatura": "2026-10-22",
    }


def test_plt_11_pedido_com_completo_recusado(publico, relogio, planos):
    resposta = _api().post(f"{BASE}pedidos/", _corpo(plano="completo"), format="json")
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "plano_fora_da_venda"
    assert resposta.json()["mensagem"] == "O plano Completo ainda não está à venda."
    assert not PedidoCompra.objects.exists()


def test_plt_11_completo_fora_da_mudanca_de_plano(criar_empresa, planos):
    empresa = criar_empresa()
    with pytest.raises(
        PlanoForaDaVenda, match=re.escape("O plano Completo ainda não está à venda.")
    ):
        plano_para_mudar(planos["Completo"].pk, empresa)
    assert plano_para_mudar(planos["Essencial"].pk, empresa) == planos["Essencial"]
    assert mudar_plano  # a mudança passa sempre por `plano_para_mudar` na API


# --- CNPJ (PLT-16) e consulta pública (ADR 0039) ---


def test_plt_16_checagem_cnpj_quatro_situacoes(criar_empresa, relogio):
    api = _api()
    nova = api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json").json()
    assert nova["pode_comprar"] is True and nova["teste_gratis"] is True
    assert nova["aviso"] is None
    assert nova["dados"] == {
        "razao_social": "Moto Rápida Locações Ltda",
        "nome_fantasia": "Moto Rápida",
        "cidade": "Fortaleza",
        "uf": "CE",
        "ativo": True,
    }

    empresa = criar_empresa()
    em_uso = api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json").json()
    assert em_uso == {
        "pode_comprar": False,
        "codigo": "cnpj_em_uso",
        "mensagem": "Este CNPJ já tem uma assinatura no Giro. Para voltar, fale com a equipe Giro.",
    }

    _apagar(empresa)
    ja_foi = api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json").json()
    assert ja_foi["pode_comprar"] is True and ja_foi["teste_gratis"] is False
    assert ja_foi["aviso"] == "Este CNPJ já usou o teste grátis. A 1ª fatura vence hoje."
    assert ja_foi["primeira_fatura"] == "2026-10-07"

    fatura = FaturaAssinatura.objects.get(empresa=empresa)
    transicionar(fatura, StatusFatura.ATRASADA)
    atraso = api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json").json()
    assert atraso["pode_comprar"] is False
    assert atraso["codigo"] == "fatura_anterior_em_atraso"

    invalido = api.post(f"{BASE}cnpj/", {"cnpj": "12.345.678/0001-90"}, format="json")
    assert invalido.status_code == 400
    assert invalido.json()["campos"] == {"cnpj": ["Confira o CNPJ. Os números não batem."]}


def test_compra_cnpj_sem_consulta_quando_o_provedor_cai(publico, relogio, monkeypatch):
    def fora(_: str) -> None:
        raise integracao_cnpj.CnpjIndisponivel

    monkeypatch.setattr("integracoes.cnpj.falso.CnpjFalso.consultar", lambda self, c: fora(c))
    corpo = _api().post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json").json()
    assert corpo["pode_comprar"] is True and corpo["dados"] is None


def test_compra_brasilapi_le_os_campos(monkeypatch):
    from integracoes.cnpj import brasilapi

    class Resposta:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"razao_social": "MOTO RAPIDA LOCACOES LTDA", "nome_fantasia": "MOTO RAPIDA",'
                b' "municipio": "FORTALEZA", "uf": "CE", "descricao_situacao_cadastral": "ATIVA"}'
            )

    monkeypatch.setattr(brasilapi, "urlopen", lambda *a, **k: Resposta())
    dados = brasilapi.BrasilApi().consultar("12345678000195")
    assert dados == DadosDoCnpj(
        "MOTO RAPIDA LOCACOES LTDA", "MOTO RAPIDA", "Fortaleza", "CE", ativo=True
    )


# --- Endereço de acesso ---


def test_compra_subdominio_sugestao_e_em_uso(criar_empresa):
    api = _api()
    sugestao = api.post(f"{BASE}subdominio/", {"nome": "Moto Rápida"}, format="json").json()
    assert sugestao["subdominio"] == "motorapida" and sugestao["disponivel"] is True
    criar_empresa()
    em_uso = api.post(f"{BASE}subdominio/", {"subdominio": "motorapida"}, format="json").json()
    assert em_uso["disponivel"] is False
    assert em_uso["sugestao"] == "motorapida2"
    assert em_uso["mensagem"] == "Este endereço já está em uso. Escolha outro."
    reservado = api.post(f"{BASE}subdominio/", {"subdominio": "admin"}, format="json")
    assert reservado.status_code == 400
    assert reservado.json()["campos"]["subdominio"] == [
        "Este endereço não pode ser usado. Escolha outro."
    ]


# --- Pedido e código (D-430-01) ---


def test_compra_nao_cria_empresa_sem_codigo(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    chave, _ = _pedir(_api(), django_capture_on_commit_callbacks)
    pedido = PedidoCompra.objects.get(chave=chave)
    assert pedido.status == StatusPedidoCompra.AGUARDANDO_CONFIRMACAO
    assert not Empresa.objects.filter(subdominio="motorapida").exists()
    assert mail.outbox[-1].subject == "Seu código para criar o sistema no Giro"
    assert len(_codigo_do_email()) == 6
    assert pedido.codigo_hash and _codigo_do_email() not in pedido.codigo_hash  # só o hash
    andamento = _api().get(f"{BASE}pedidos/{chave}/").json()
    assert andamento == {"status": "aguardando_confirmacao"}  # sem dados antes do código
    evento = EventoAuditoria.objects.get(acao="compra.pedido")
    assert "mariana" not in str(evento.depois or "") + str(evento.antes or "")


def test_compra_codigo_cinco_tentativas(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    errado = "000000" if codigo != "000000" else "111111"
    primeira = _confirmar(api, django_capture_on_commit_callbacks, chave, errado)
    assert primeira.status_code == 400
    assert primeira.json() == {
        "codigo": "codigo_invalido",
        "mensagem": "Código incorreto. Você tem mais 4 tentativas.",
        "tentativas_restantes": 4,
    }
    for _ in range(3):
        _confirmar(api, django_capture_on_commit_callbacks, chave, errado)
    quinta = _confirmar(api, django_capture_on_commit_callbacks, chave, errado)
    assert quinta.json()["codigo"] == "codigo_bloqueado"
    certo_tarde = _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert certo_tarde.json()["codigo"] == "codigo_bloqueado"
    assert not Empresa.objects.filter(subdominio="motorapida").exists()


def test_compra_codigo_expira(publico, relogio, planos, django_capture_on_commit_callbacks):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    relogio.em("2026-10-07 10:16")
    vencido = _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert vencido.json()["codigo"] == "codigo_expirado"

    with django_capture_on_commit_callbacks(execute=True):
        novo = api.post(f"{BASE}pedidos/{chave}/reenviar-codigo/")
    assert novo.status_code == 202
    assert _codigo_do_email() != "" and novo.json()["mensagem"] == "Enviamos um código novo."
    logo = api.post(f"{BASE}pedidos/{chave}/reenviar-codigo/")
    assert logo.status_code == 429 and logo.json()["codigo"] == "limite_reenvio"


def test_plt_13_compra_sem_cartao(publico, relogio, planos):
    corpo = _corpo(forma_pagamento="cartao")
    corpo["cartao"] = {"numero_cartao": "4111111111111111", "cvv": "123"}
    resposta = _api().post(f"{BASE}pedidos/", corpo, format="json")
    assert resposta.status_code == 400 and resposta.json()["codigo"] == "cartao_nao_aceito"
    assert not PedidoCompra.objects.exists()


def test_compra_validacao_junta_os_campos(publico, relogio, planos):
    corpo = _corpo(aceite_termos=False)
    corpo["administrador"] = {"nome": "", "email": "sem-arroba", "celular": "123"}
    resposta = _api().post(f"{BASE}pedidos/", corpo, format="json")
    assert resposta.status_code == 400
    campos = resposta.json()["campos"]
    assert campos["aceite_termos"] == [
        "Para continuar, aceite os Termos de uso e o Acordo de tratamento de dados."
    ]
    assert campos["administrador.nome"] == ["Informe seu nome completo."]
    assert campos["administrador.email"] == ["Confira o e-mail."]
    assert campos["administrador.celular"] == ["Confira o celular com DDD."]


# --- Limites e teto (D-430-08) ---


def test_compra_limites_por_ip_email_cnpj(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    api = _api()
    for numero in range(3):  # 3 por dia por e-mail (CNPJs diferentes para não substituir)
        empresa = dict(_corpo()["empresa"], subdominio=f"loja{numero}x")
        empresa["cnpj"] = _cnpj(f"1122233300{numero}1")
        _pedir(api, django_capture_on_commit_callbacks, empresa=empresa)
    quarto = api.post(
        f"{BASE}pedidos/",
        _corpo(empresa=dict(_corpo()["empresa"], cnpj=_cnpj("114447770001"))),
        format="json",
    )
    assert quarto.status_code == 429
    assert quarto.json() == {
        "codigo": "limite",
        "mensagem": "Muitas tentativas. Tente de novo mais tarde.",
    }
    assert quarto.has_header("Retry-After")

    for _ in range(20):  # 20 por hora por IP na checagem do CNPJ
        api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json")
    estourou = api.post(f"{BASE}cnpj/", {"cnpj": CNPJ_MOTO_RAPIDA}, format="json")
    assert estourou.status_code == 429 and estourou.json()["codigo"] == "limite"


def test_compra_teto_diario(publico, relogio, planos, settings, django_capture_on_commit_callbacks):
    settings.GIRO_COMPRA_TETO_DIARIO = 0
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    resposta = _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert resposta.json()["status"] == "confirmado"
    assert resposta.json()["mensagem"] == (
        "Recebemos o seu pedido. A equipe Giro libera o seu sistema e avisa você por e-mail."
    )
    assert not Empresa.objects.filter(subdominio="motorapida").exists()
    assert mail.outbox[-1].to == [settings.GIRO_EMAIL_EQUIPE]


# --- Criação (PLT-01, PLT-16, USR-01) ---


def test_plt_01_compra_publica_teste_e_primeira_fatura(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    resposta = _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert resposta.status_code == 202

    empresa = Empresa.objects.get(subdominio="motorapida")
    assert empresa.origem == "compra" and empresa.status == "em_teste"
    assert (empresa.teste_inicio, empresa.teste_fim) == (date(2026, 10, 7), date(2026, 10, 21))
    assert empresa.aceite_termos_versao == "rascunho"
    fatura = FaturaAssinatura.objects.get(empresa=empresa)
    assert (fatura.codigo, fatura.vencimento, fatura.valor_centavos) == (
        "FAT-0001",
        date(2026, 10, 22),
        44900,
    )

    andamento = api.get(f"{BASE}pedidos/{chave}/").json()
    assert andamento["status"] == "pronto"
    assert andamento["administrador"] == {"nome": "Mariana", "email": "mariana@motorapida.com.br"}
    assert [p["passo"] for p in andamento["passos"]] == [
        "administrador",
        "banco",
        "endereco",
        "assinatura",
    ]
    assert all(p["feito_em"] for p in andamento["passos"])
    assert andamento["passos"][3]["texto"] == "Teste de 14 dias ativo, até 21 out"


def test_usr_01_convite_do_administrador_da_compra(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    empresa = Empresa.objects.get(subdominio="motorapida")
    with tenant_context(empresa):
        mariana = Usuario.objects.get(email="mariana@motorapida.com.br")
        assert (mariana.perfil, mariana.status) == ("administrador", "convite_pendente")
        convite = Convite.objects.get(usuario=mariana)
        assert convite.expira_em - relogio.agora == timedelta(days=7)


def test_compra_link_do_convite_sai_uma_vez(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    primeira = api.get(f"{BASE}pedidos/{chave}/").json()
    connection.set_schema_to_public()
    assert primeira["acessar"]["uma_vez"] is True
    assert "/convite#" in primeira["acessar"]["url"]
    segunda = api.get(f"{BASE}pedidos/{chave}/").json()
    connection.set_schema_to_public()
    assert segunda["acessar"] is None
    empresa = Empresa.objects.get(subdominio="motorapida")
    with tenant_context(empresa):  # o link do e-mail continua valendo
        assert Convite.objects.filter(expira_em__gt=relogio.agora).count() == 2

    relogio.em("2026-10-08 10:01")  # mais de 24 h depois do pronto
    assert api.get(f"{BASE}pedidos/{chave}/").status_code == 404


def test_compra_confirmar_idempotente(publico, relogio, planos, django_capture_on_commit_callbacks):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    de_novo = _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert de_novo.status_code == 200 and de_novo.json()["status"] == "pronto"
    assert Empresa.objects.filter(cnpj="12345678000195").count() == 1


def test_plt_16_compra_publica_sem_teste(
    criar_empresa, relogio, django_capture_on_commit_callbacks
):
    antiga = criar_empresa(subdominio="motorapidaantiga")
    _apagar(antiga)
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    nova = Empresa.objects.get(subdominio="motorapida")
    assert nova.status == "ativa" and nova.teste_inicio is None and nova.teste_fim is None
    assert nova.dia_vencimento == 7 and nova.empresa_anterior_id == antiga.pk
    fatura = FaturaAssinatura.objects.get(empresa=nova)
    assert fatura.vencimento == date(2026, 10, 7)
    passos = api.get(f"{BASE}pedidos/{chave}/").json()["passos"]
    assert passos[3]["texto"] == "1ª fatura de R$ 449,00 vence hoje"


def test_plt_16_situacao_muda_ate_a_confirmacao(
    criar_empresa, relogio, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)
    criar_empresa(subdominio="outra")  # o CNPJ vira cliente entre o pedido e o código
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    andamento = api.get(f"{BASE}pedidos/{chave}/").json()
    assert andamento == {
        "status": "falhou",
        "mensagem": "Este CNPJ já tem uma assinatura no Giro. Para voltar, fale com a equipe Giro.",
    }


def test_compra_falha_desfaz_schema(
    publico, relogio, planos, monkeypatch, django_capture_on_commit_callbacks
):
    api = _api()
    chave, codigo = _pedir(api, django_capture_on_commit_callbacks)

    def quebra(_: Any) -> None:
        raise RuntimeError("falha no meio")

    monkeypatch.setattr("apps.plataforma.services.criar_primeira_fatura", quebra)
    _confirmar(api, django_capture_on_commit_callbacks, chave, codigo)
    assert not Empresa.objects.filter(subdominio="motorapida").exists()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'motorapida'")
        assert cursor.fetchone() is None
    corpo = api.get(f"{BASE}pedidos/{chave}/").json()
    assert corpo["status"] == "falhou"
    assert corpo["mensagem"].startswith("Não conseguimos criar o seu sistema agora.")


# --- Onde as rotas moram e o que expira ---


def test_compra_rotas_so_no_dominio_principal(criar_empresa, settings):
    criar_empresa()
    resposta = cliente(f"motorapida.{settings.DOMINIO_BASE}").get(f"{BASE}planos/")
    assert resposta.status_code == 404


def test_compra_pedido_expirado_apaga_dados_pessoais(
    publico, relogio, planos, django_capture_on_commit_callbacks
):
    chave, codigo = _pedir(_api(), django_capture_on_commit_callbacks)
    relogio.em("2026-10-08 10:01")
    assert compra.expirar_pedidos_compra() == {"expirados": 1, "dados_apagados": 0}
    resposta = _confirmar(_api(), django_capture_on_commit_callbacks, chave, codigo)
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "pedido_nao_encontrado"
    relogio.em("2026-10-15 10:01")
    assert compra.expirar_pedidos_compra() == {"expirados": 0, "dados_apagados": 1}
    pedido = PedidoCompra.objects.get(chave=chave)
    assert (pedido.administrador_email, pedido.cnpj, pedido.razao_social) == ("", "", "")
    assert pedido.plano.nome == "Profissional"
