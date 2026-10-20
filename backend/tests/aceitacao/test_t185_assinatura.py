"""T-185 (parte 1) · Rotas da assinatura: `GET /api/assinatura/` completo, planos, mudança de
plano e dados fiscais (`docs/api/assinatura.md`; PLT-01, PLT-04, PLT-05, PLT-11, PLT-13, PLT-15).

Também os requisitos que a segurança deixou para a T-185 na revisão da T-189
(`docs/seguranca/2026-10-15-t189-cartao-conta-principal.md`, "Para a T-185"): o suporte nunca
escreve na assinatura (1), a exceção da `suspensa` é uma lista explícita (2) e as rotas são só do
administrador (3). A lista completa da exceção e os requisitos 4 a 8 (forma de pagamento e
faturas) estão em `test_t185b_forma_faturas.py`.

Relógio em 07 out 2026, como o seed Moto Rápida: teste de 07 a 21 out, FAT-0001 de R$ 449,00 em
22 out, 86 veículos, 1 filial e 5 usuários no Profissional.
"""

import copy
from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from django.db import connection
from django_tenants.utils import schema_context, tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.filiais import services as filiais
from apps.filiais.models import Filial
from apps.plataforma import catalogo, services
from apps.plataforma.models import (
    DADOS_APAGADOS_DA_EMPRESA,
    Empresa,
    FaturaAssinatura,
    FormaPagamentoAssinatura,
    Plano,
    TipoFatura,
    UsoEmpresa,
)
from apps.plataforma.services import abrir_acesso_suporte
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from comum.classificacao import classificacao
from config import urls
from integracoes.pagamentos import falso as pagamentos
from seed.moto_rapida import CENTRO

from .conftest import CNPJ_MOTO_RAPIDA
from .conftest import cliente as cliente_http

HOST = "motorapida.localhost"
ASSINATURA = "/api/assinatura/"
PLANOS = "/api/assinatura/planos/"
SIMULAR = "/api/assinatura/mudanca-plano/simular/"
MUDANCA = "/api/assinatura/mudanca-plano/"
DADOS_FISCAIS = "/api/assinatura/dados-fiscais/"
DOM_LUIS = {
    "cep": "60115170",
    "logradouro": "Av. Dom Luís",
    "numero": "500",
    "complemento": "Sala 3",
    "bairro": "Meireles",
    "cidade": "Fortaleza",
    "uf": "CE",
}
BEZERRA = {
    "cep": "60325000",
    "logradouro": "Av. Bezerra de Menezes",
    "numero": "1200",
    "complemento": None,
    "bairro": "São Gerardo",
    "cidade": "Fortaleza",
    "uf": "CE",
}
PESSOAS = {
    "Rodrigo": ("rodrigo@motorapida.com.br", "gerente"),
    "Lúcia": ("lucia@motorapida.com.br", "financeiro"),
}
SUPORTE_NAO_MEXE = {"codigo": "PLT-07", "mensagem": "O suporte não mexe na assinatura da empresa"}
SO_ADMINISTRADOR = {"codigo": "permissao", "mensagem": "Só o administrador mexe na assinatura"}
# Desde a T-195, a `cancelada` não entra (AUD-08); a `pausada` só lê.
CODIGO_SEM_OPERACAO = {"pausada": "empresa_sem_operacao", "cancelada": "empresa_cancelada"}
PAGUE_ANTES = {
    "codigo": "transicao_empresa",
    "mensagem": "Pague a fatura em atraso antes de mudar de plano.",
}


class MotoRapida:
    """A empresa criada pelo serviço (1ª fatura, forma vazia), com o uso do seed e a equipe."""

    def __init__(self, empresa: Empresa) -> None:
        self.empresa = empresa
        UsoEmpresa.objects.filter(empresa=empresa).update(veiculos=86, filiais=1, usuarios=5)
        with tenant_context(empresa):
            Usuario._base_manager.filter(email="mariana@motorapida.com.br").update(status="ativo")
            self.pessoas = {"Mariana": Usuario.objects.get(email="mariana@motorapida.com.br")}
            for nome, (email, perfil) in PESSOAS.items():
                self.pessoas[nome] = Usuario.objects.create_user(
                    email, "senha-forte-123", nome=nome, perfil=perfil
                )
        connection.set_schema_to_public()

    def api(self, nome: str = "Mariana") -> Any:
        with tenant_context(self.empresa):
            token = str(emitir_tokens(self.pessoas[nome], AMR_SENHA_E_CODIGO).access_token)
        connection.set_schema_to_public()
        return cliente_http(HOST, token)

    def suporte(self, permissao: str) -> Any:
        with schema_context("public"):
            diego = Usuario.objects.filter(email="diego@girolocadoras.com.br").first()
            if diego is None:
                diego = Usuario.objects.create_user(
                    "diego@girolocadoras.com.br",
                    "senha-forte-123",
                    nome="Diego Santos",
                    funcao_plataforma="suporte",
                )
            _, token = abrir_acesso_suporte(
                Empresa.objects.get(pk=self.empresa.pk),
                diego,
                motivo="Chamado #1042",
                duracao_minutos=30,
                permissao=permissao,
            )
        connection.set_schema_to_public()
        return cliente_http(HOST, token)

    def recarregar(self) -> Empresa:
        return Empresa.objects.select_related("plano", "plano_proximo").get(pk=self.empresa.pk)

    def fatura(self, codigo: str) -> FaturaAssinatura:
        return FaturaAssinatura.objects.select_related("plano").get(
            empresa=self.empresa, codigo=codigo
        )

    def estado(self, **campos: Any) -> None:
        """Estados que as tarefas da T-186 e da T-195 ainda não fazem: montados direto."""
        Empresa._base_manager.filter(pk=self.empresa.pk).update(**campos)
        self.empresa.refresh_from_db()

    def pagar_fat_0001(self, em: str = "2026-10-22") -> None:
        FaturaAssinatura._base_manager.filter(empresa=self.empresa, codigo="FAT-0001").update(
            status="paga", pago_em=f"{em}T12:00:00-03:00", forma="boleto"
        )

    def no_completo(self) -> None:
        completo = Plano.objects.get(nome="Completo")
        self.estado(plano=completo, preco_contratado_centavos=89900)
        FaturaAssinatura.objects.filter(empresa=self.empresa).update(
            plano=completo, valor_centavos=89900
        )


@pytest.fixture
def moto(criar_empresa, relogio_jwt) -> Iterator[MotoRapida]:
    pagamentos.limpar()
    yield MotoRapida(criar_empresa())
    pagamentos.limpar()


def _criar_matriz(moto: MotoRapida) -> Filial:
    with tenant_context(moto.empresa):
        filial = filiais.criar_filial(copy.deepcopy(CENTRO), moto.pessoas["Mariana"])
    connection.set_schema_to_public()
    return filial


def _eventos(acao: str, schema: str) -> list[EventoAuditoria]:
    with schema_context(schema):
        return list(EventoAuditoria.objects.filter(acao=acao).order_by("id"))


def _simular(api: Any, plano: str, ciclo: str = "mensal") -> Any:
    plano_id = Plano.objects.get(nome=plano).pk
    return api.post(SIMULAR, {"plano_id": plano_id, "ciclo": ciclo}, format="json")


def _mudar(api: Any, plano: str, valor: int = 0, ciclo: str = "mensal") -> Any:
    plano_id = Plano.objects.get(nome=plano).pk
    corpo = {"plano_id": plano_id, "ciclo": ciclo, "confirmar_valor_centavos": valor}
    return api.post(MUDANCA, corpo, format="json")


def _erro(resposta: Any) -> dict[str, Any]:
    corpo = resposta.json()
    return {"codigo": corpo["codigo"], "mensagem": corpo["mensagem"]}


# --- GET /api/assinatura/ (PLT-01, PLT-11, PLT-13, PLT-15) ---


def test_plt_01_ca_ass_01_assinatura_da_moto_rapida_em_07_out(moto):
    _criar_matriz(moto)
    resposta = moto.api().get(ASSINATURA)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["plano"] == {
        "id": Plano.objects.get(nome="Profissional").pk,
        "nome": "Profissional",
        "preco_contratado_centavos": 44900,
        "ciclo": "mensal",
    }
    assert corpo["status"] == "em_teste"
    assert corpo["teste"] == {"inicio": "2026-10-07", "fim": "2026-10-21", "dias_restantes": 14}
    # A 1ª fatura vence no dia seguinte ao fim do teste: 22 out, não 21 (PLT-01).
    assert corpo["proxima_fatura"] == {
        "vencimento": "2026-10-22",
        "valor_centavos": 44900,
        "descricao": "Plano Profissional · 22 out a 21 nov",
    }
    assert corpo["plano_proximo"] is None
    assert corpo["forma_pagamento"] == {
        "forma": None,
        "situacao": {
            "codigo": "sem_forma",
            "rotulo": "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso.",
            "tom": "alerta",
        },
        "cartao": None,
        "prazo": "2026-10-21",
    }
    assert corpo["dados_fiscais"] == {
        "razao_social": "Moto Rápida Locações Ltda",
        "cnpj": "12345678000195",
        "endereco": BEZERRA,
        "email_cobranca": "mariana@motorapida.com.br",
    }
    assert corpo["oferta"] == {
        "titulo": "Precisa de mais veículos ou filiais?",
        "plano": {
            "id": Plano.objects.get(nome="Completo").pk,
            "nome": "Completo",
            "preco_mensal_centavos": 89900,
        },
        "itens": [
            "Veículos, filiais e usuários sem limite",
            "Implantação acompanhada por chamada",
            "Suporte prioritário",
        ],
    }
    assert corpo["acoes"] == {
        "mudar_plano": True,
        "desfazer_mudanca_plano": False,
        "escolher_forma_pagamento": True,
        "editar_dados_fiscais": True,
        # Cancelar e pausar (T-195, cancelamento.md): no teste, cancela e não pausa.
        "cancelar": True,
        "desfazer_cancelamento": False,
        "pausar": False,
        "voltar_pausa": False,
        "desistir_pausa": False,
    }
    assert (corpo["cancelamento"], corpo["pausa"]) == (None, None)


@pytest.mark.parametrize("nome", ["Rodrigo", "Lúcia"])
def test_plt_13_blocos_do_administrador_ausentes_para_os_outros_perfis(moto, nome):
    corpo = moto.api(nome).get(ASSINATURA).json()
    assert {"forma_pagamento", "dados_fiscais", "oferta", "acoes"}.isdisjoint(corpo)
    assert corpo["proxima_fatura"]["vencimento"] == "2026-10-22"
    assert corpo["uso"]["veiculos"]["usado"] == 86


def test_plt_13_forma_de_pagamento_pela_situacao(moto):
    formas = FormaPagamentoAssinatura._base_manager.filter(empresa=moto.empresa)
    formas.update(forma="cartao")
    situacao = moto.api().get(ASSINATURA).json()["forma_pagamento"]
    assert situacao["situacao"]["codigo"] == "cartao_na_primeira_fatura"
    assert situacao["prazo"] is None  # só com a forma nula
    formas.update(cartao_bandeira="visa", cartao_final="4242", status="ativa")
    corpo = moto.api().get(ASSINATURA).json()["forma_pagamento"]
    assert corpo["cartao"] == {"bandeira": "visa", "final": "4242"}
    assert corpo["situacao"] == {
        "codigo": "ativa",
        "rotulo": "Cartão Visa final 4242 · cobrança automática todo mês",
        "tom": "sucesso",
    }
    assert "token" not in str(corpo)
    FaturaAssinatura.objects.filter(empresa=moto.empresa).update(
        cartao_recusado_em="2026-10-22T09:00:00-03:00", tentativas_cartao=1
    )
    rotulo = moto.api().get(ASSINATURA).json()["forma_pagamento"]["situacao"]["rotulo"]
    assert rotulo == "O cartão foi recusado. Tentamos de novo amanhã."
    FaturaAssinatura.objects.filter(empresa=moto.empresa).update(tentativas_cartao=2)
    rotulo = moto.api().get(ASSINATURA).json()["forma_pagamento"]["situacao"]["rotulo"]
    assert rotulo == "O cartão foi recusado de novo. Pague a fatura por Pix ou boleto."
    formas.update(forma="pix_automatico", status="pendente")
    situacao = moto.api().get(ASSINATURA).json()["forma_pagamento"]["situacao"]
    assert situacao["codigo"] == "aguardando_autorizacao"


def test_plt_01_proxima_fatura_depois_da_primeira_paga(moto):
    """Com a FAT-0001 paga no teste, a próxima é a de 22 nov (CA-ASS-03, CA-ASS-07)."""
    moto.pagar_fat_0001(em="2026-10-18")
    corpo = moto.api().get(ASSINATURA).json()
    assert corpo["status"] == "em_teste"
    assert corpo["proxima_fatura"] == {
        "vencimento": "2026-11-22",
        "valor_centavos": 44900,
        "descricao": "Plano Profissional · 22 nov a 21 dez",
    }


def test_plt_06_proxima_fatura_nula_com_cancelamento_marcado_ou_pausada(moto):
    moto.estado(acesso_ate=date(2026, 10, 21))
    assert moto.api().get(ASSINATURA).json()["proxima_fatura"] is None
    moto.estado(acesso_ate=None, status="pausada")
    assert moto.api().get(ASSINATURA).json()["proxima_fatura"] is None


# --- Catálogo (PLT-11) e planos ---


def test_plt_11_catalogo_confere_a_tabela_da_regra():
    assert catalogo.textos("Essencial").inclui == (
        "Locação, vistoria e contas a receber",
        "Contrato digital, assinado pelo cliente no celular",
        "Sua marca e seu endereço de acesso",
    )
    assert catalogo.textos("Profissional").inclui[0] == "Tudo do Essencial"
    assert catalogo.textos("Completo").inclui[0] == "Tudo do Profissional"
    assert catalogo.textos("Profissional").a_mais == (
        "Vendas, manutenção e despesas",
        "Pix e boleto automáticos, cobrança pelo WhatsApp",
        "Comissão de vendedores e relatórios",
        "Até 150 veículos, 3 filiais e 10 usuários",
    )
    # CA-ASS-20: nada que ainda não existe, nem o contrato digital como extra do Completo.
    proibidos = ("nf-e", "nota fiscal", "domínio", "portal", "api", "integraç")
    for nome, textos in catalogo.CATALOGO.items():
        for texto in (*textos.inclui, *textos.a_mais):
            assert not any(p in texto.lower() for p in proibidos), (nome, texto)
    assert not any("contrato" in t.lower() for t in catalogo.textos("Completo").a_mais)


def test_plt_11_ca_ass_21_sem_oferta_no_completo(moto):
    moto.no_completo()
    assert moto.api().get(ASSINATURA).json()["oferta"] is None


def test_plt_04_planos_para_comparar(moto):
    resposta = moto.api().get(PLANOS)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["ciclo_atual"] == "mensal"
    essencial, profissional, completo = corpo["resultados"]
    assert (essencial["nome"], essencial["mudanca"], essencial["cabe"]) == (
        "Essencial",
        "downgrade",
        False,
    )
    # 86 de 30 veículos e 5 de 3 usuários; 1 filial cabe (CA-ASS-15).
    assert essencial["excede"] == {
        "veiculos": {"usado": 86, "limite": 30},
        "usuarios": {"usado": 5, "limite": 3},
    }
    assert (essencial["preco_mensal_centavos"], essencial["preco_anual_centavos"]) == (
        19900,
        199000,
    )
    assert essencial["itens"] == list(catalogo.textos("Essencial").inclui)
    assert "preco_contratado_centavos" not in essencial
    assert profissional["atual"] is True
    assert profissional["mudanca"] is None
    assert profissional["preco_contratado_centavos"] == 44900
    assert (completo["mudanca"], completo["cabe"], completo["excede"]) == ("upgrade", True, {})
    assert completo["limite_veiculos"] is None


def test_plt_05_plano_desativado_so_aparece_se_for_o_atual(moto):
    Plano.objects.filter(nome="Profissional").update(ativo=False)
    Plano.objects.filter(nome="Essencial").update(ativo=False)
    nomes = [p["nome"] for p in moto.api().get(PLANOS).json()["resultados"]]
    assert nomes == ["Profissional", "Completo"]
    assert _simular(moto.api(), "Essencial").status_code == 404


# --- Mudança de plano (PLT-04, PLT-05) ---


def test_plt_04_upgrade_em_teste(moto, relogio):
    """CA-ASS-13: Completo em 10 out, no teste: na hora, nada a cobrar, FAT-0001 a R$ 899,00."""
    relogio.em("2026-10-10 09:00")
    api = moto.api()
    simulacao = _simular(api, "Completo")
    assert simulacao.status_code == 200, simulacao.json()
    assert simulacao.json() == {
        "tipo": "upgrade",
        "vale_em": "2026-10-10",
        "preco_novo_centavos": 89900,
        "diferenca_centavos": 0,
        "fatura_diferenca": None,
        "proxima_fatura": {
            "vencimento": "2026-10-22",
            "valor_centavos": 89900,
            "descricao": "Plano Completo · 22 out a 21 nov",
        },
        "mensagem": "O plano Completo vale agora. A primeira fatura, em 22 out, fica em R$ 899,00.",
    }
    assert moto.recarregar().plano.nome == "Profissional"  # simular não grava

    resposta = _mudar(api, "Completo")
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["plano"]["nome"] == "Completo"
    assert corpo["plano"]["preco_contratado_centavos"] == 89900
    assert corpo["status"] == "em_teste"
    assert corpo["teste"]["fim"] == "2026-10-21"  # o teste não reinicia
    assert corpo["uso"]["veiculos"]["limite"] is None
    assert corpo["oferta"] is None
    fatura = moto.fatura("FAT-0001")
    assert (fatura.plano.nome, fatura.valor_centavos) == ("Completo", 89900)
    assert fatura.vencimento == date(2026, 10, 22)
    assert not FaturaAssinatura.objects.filter(
        empresa=moto.empresa, tipo=TipoFatura.DIFERENCA_PLANO
    ).exists()
    publico = _eventos("empresa.mudar_plano", "public")
    na_empresa = _eventos("empresa.mudar_plano", moto.empresa.schema_name)
    assert len(publico) == len(na_empresa) == 1
    assert publico[0].categoria == "financeiro"
    assert na_empresa[0].categoria == "configuracoes"
    assert na_empresa[0].antes["plano"] == "Profissional"
    assert na_empresa[0].depois["plano"] == "Completo"
    assert na_empresa[0].regra == "PLT-04"


def test_plt_04_downgrade_em_teste_que_cabe_vale_na_hora(moto, relogio):
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(veiculos=20, filiais=1, usuarios=3)
    relogio.em("2026-10-10 09:00")
    resposta = _mudar(moto.api(), "Essencial")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["plano"]["nome"] == "Essencial"
    assert resposta.json()["plano_proximo"] is None
    assert moto.fatura("FAT-0001").valor_centavos == 19900


def test_plt_04_upgrade_proporcional(moto, relogio):
    """CA-ASS-14: `ativa`, FAT-0001 paga, Completo em 01 nov → 45000 × 21 ÷ 31 = 30483,87 →
    R$ 304,84, vencendo em 04 nov; a fatura de 22 nov vem com R$ 899,00."""
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    api = moto.api()
    simulacao = _simular(api, "Completo").json()
    assert simulacao["diferenca_centavos"] == 30484
    assert simulacao["fatura_diferenca"] == {
        "valor_centavos": 30484,
        "vencimento": "2026-11-04",
        "descricao": "Mudança para o plano Completo · 01 a 21 nov",
    }
    assert simulacao["proxima_fatura"] == {
        "vencimento": "2026-11-22",
        "valor_centavos": 89900,
        "descricao": "Plano Completo · 22 nov a 21 dez",
    }
    assert (
        simulacao["mensagem"]
        == "O plano Completo vale agora. A diferença de R$ 304,84 vence em 04 nov."
    )

    # O valor mudou entre simular e confirmar: 409, nada gravado.
    recusa = _mudar(api, "Completo", valor=30000)
    assert recusa.status_code == 409
    assert recusa.json()["codigo"] == "valor_mudou"
    assert recusa.json()["mensagem"] == (
        "O valor da diferença mudou. Confira o novo valor antes de confirmar."
    )  # T-290
    assert recusa.json()["detalhes"] == {"diferenca_centavos": 30484}
    assert moto.recarregar().plano.nome == "Profissional"

    resposta = _mudar(api, "Completo", valor=30484)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["proxima_fatura"]["valor_centavos"] == 89900
    assert moto.recarregar().preco_contratado_centavos == 89900
    diferenca = moto.fatura("FAT-0002")
    assert (diferenca.tipo, diferenca.valor_centavos, diferenca.status) == (
        "diferenca_plano",
        30484,
        "aberta",
    )
    assert diferenca.vencimento == date(2026, 11, 4)
    assert diferenca.descricao == "Mudança para o plano Completo · 01 a 21 nov"
    evento = _eventos("empresa.mudar_plano", moto.empresa.schema_name)[0]
    assert evento.depois["diferenca_centavos"] == 30484


def test_plt_04_upgrade_no_teste_com_primeira_paga(moto, relogio):
    """FAT-0001 paga em 18 out, upgrade em 19 out: 45000 × 31 ÷ 31 = 45000, vence em 22 out; a
    empresa continua `em_teste` até 21 out."""
    moto.pagar_fat_0001(em="2026-10-18")
    relogio.em("2026-10-19 09:00")
    resposta = _mudar(moto.api(), "Completo", valor=45000)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "em_teste"
    diferenca = moto.fatura("FAT-0002")
    assert diferenca.valor_centavos == 45000
    assert diferenca.vencimento == date(2026, 10, 22)
    assert diferenca.descricao == "Mudança para o plano Completo · 22 out a 21 nov"


@pytest.mark.parametrize("status", ["em_teste", "ativa"])
def test_plt_04_downgrade_nao_cabe(moto, status):
    """CA-ASS-15: 86 de 30 veículos e 5 de 3 usuários; 1 filial cabe. Nada muda. Os `abertos`
    dos módulos que saem dependem da contagem da T-196 (`pendencias_dos_modulos`)."""
    if status == "ativa":
        moto.pagar_fat_0001()
        moto.estado(status="ativa")
    api = moto.api()
    for resposta in (_simular(api, "Essencial"), _mudar(api, "Essencial")):
        assert resposta.status_code == 422, resposta.json()
        assert resposta.json() == {
            "codigo": "PLT-04",
            "mensagem": (
                "Seu uso não cabe no plano Essencial. Desative veículos ou usuários antes de mudar."
            ),
            "detalhes": {
                "veiculos": {"usado": 86, "limite": 30},
                "usuarios": {"usado": 5, "limite": 3},
            },
        }
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.plano_proximo) == ("Profissional", None)
    assert not _eventos("empresa.mudar_plano", "public")


def test_plt_04_downgrade_agendado_e_desfeito(moto, relogio):
    """CA-ASS-16: Completo `ativa`, período de 22 out a 21 nov; Profissional em 01 nov vale em
    22 nov, nada cobrado nem devolvido; desfeito em 10 nov, a de 22 nov volta a R$ 899,00."""
    moto.no_completo()
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    api = moto.api()
    simulacao = _simular(api, "Profissional").json()
    assert simulacao["tipo"] == "downgrade"
    assert simulacao["vale_em"] == "2026-11-22"
    assert simulacao["diferenca_centavos"] == 0
    assert simulacao["mensagem"] == (
        "O plano Profissional vale a partir de 22 nov. Até lá, você continua no Completo."
    )
    corpo = _mudar(api, "Profissional").json()
    assert corpo["plano"]["nome"] == "Completo"
    assert corpo["plano_proximo"] == {
        "id": Plano.objects.get(nome="Profissional").pk,
        "nome": "Profissional",
        "ciclo": "mensal",
        "vale_em": "2026-11-22",
    }
    assert corpo["proxima_fatura"] == {
        "vencimento": "2026-11-22",
        "valor_centavos": 44900,
        "descricao": "Plano Profissional · 22 nov a 21 dez",
    }
    assert corpo["acoes"]["desfazer_mudanca_plano"] is True
    assert FaturaAssinatura.objects.filter(empresa=moto.empresa).count() == 1

    relogio.em("2026-11-10 09:00")
    api = moto.api()
    resposta = api.delete(MUDANCA)
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["plano_proximo"] is None
    assert resposta.json()["proxima_fatura"]["valor_centavos"] == 89900
    assert resposta.json()["acoes"]["desfazer_mudanca_plano"] is False
    assert len(_eventos("empresa.desfazer_mudanca_plano", "public")) == 1
    assert len(_eventos("empresa.desfazer_mudanca_plano", moto.empresa.schema_name)) == 1
    assert api.delete(MUDANCA).status_code == 404  # nada agendado


def test_plt_04_desfazer_depois_da_fatura_gerada_pelo_plano_menor(moto, relogio):
    """A fatura de 22 nov já gerada pelo Profissional (17 nov) volta ao Completo, R$ 899,00."""
    moto.no_completo()
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    api = moto.api()
    assert _mudar(api, "Profissional").status_code == 200
    relogio.em("2026-11-17 06:00")
    empresa = moto.recarregar()
    proxima = services.proxima_mensalidade(empresa)
    assert proxima is not None
    services.criar_fatura(  # o que a `gerar_faturas` (T-186) faz 5 dias antes
        empresa,
        tipo=TipoFatura.MENSALIDADE,
        vencimento=proxima.vencimento,
        periodo=proxima.periodo,
        plano=proxima.plano,
        ciclo=proxima.ciclo,
        valor_centavos=proxima.valor_centavos,
    )
    assert (moto.fatura("FAT-0002").plano.nome, moto.fatura("FAT-0002").valor_centavos) == (
        "Profissional",
        44900,
    )
    relogio.em("2026-11-18 09:00")
    api = moto.api()
    assert api.delete(MUDANCA).status_code == 200
    fatura = moto.fatura("FAT-0002")
    assert (fatura.plano.nome, fatura.valor_centavos, fatura.status) == (
        "Completo",
        89900,
        "aberta",
    )
    relogio.em("2026-11-22 09:00")
    api = moto.api()
    assert _mudar(api, "Profissional").status_code == 200
    relogio.em("2026-11-22 10:00")
    api = moto.api()
    recusa = api.delete(MUDANCA)  # no dia da virada já não se desfaz
    assert recusa.status_code == 409, recusa.json()


def test_plt_04_segunda_mudanca_agendada(moto, relogio):
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(veiculos=20, filiais=1, usuarios=3)
    moto.no_completo()
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    api = moto.api()
    assert _mudar(api, "Profissional").status_code == 200
    recusa = _mudar(api, "Essencial")
    assert recusa.status_code == 409
    assert _erro(recusa) == {
        "codigo": "transicao_empresa",
        "mensagem": "Já existe uma mudança agendada para 22 nov. Desfaça antes de escolher outra.",
    }


def test_plt_04_upgrade_desfaz_o_downgrade_agendado(moto, relogio):
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(veiculos=20, filiais=1, usuarios=3)
    relogio.em("2026-11-01 09:00")
    api = moto.api()
    assert _mudar(api, "Essencial").status_code == 200
    assert moto.recarregar().plano_proximo.nome == "Essencial"
    resposta = _mudar(api, "Completo", valor=30484)
    assert resposta.status_code == 200, resposta.json()
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.plano_proximo) == ("Completo", None)


@pytest.mark.parametrize("status", ["inadimplente", "suspensa"])
def test_plt_04_ca_ass_17_pague_antes_de_mudar(moto, status):
    moto.estado(status=status)
    api = moto.api()
    for resposta in (_simular(api, "Completo"), _mudar(api, "Completo"), api.delete(MUDANCA)):
        assert resposta.status_code == 409, resposta.json()
        assert _erro(resposta) == PAGUE_ANTES
    acoes = api.get(ASSINATURA).json()["acoes"]
    assert (acoes["mudar_plano"], acoes["desfazer_mudanca_plano"]) == (False, False)
    assert acoes["escolher_forma_pagamento"] is True  # a suspensa paga (PLT-13)


@pytest.mark.parametrize("status", ["pausada", "cancelada"])
def test_plt_04_ca_ass_17_pausada_e_cancelada_sem_operacao(moto, status):
    moto.estado(status=status)
    api = moto.api()
    for resposta in (_simular(api, "Completo"), _mudar(api, "Completo"), api.delete(MUDANCA)):
        assert resposta.status_code == 403
        assert resposta.json()["codigo"] == CODIGO_SEM_OPERACAO[status]
    if status == "pausada":
        # Na pausada, só voltar da pausa ou cancelar na hora (PLT-06, T-195).
        acoes = api.get(ASSINATURA).json()["acoes"]
        assert [nome for nome, pode in acoes.items() if pode] == ["cancelar", "voltar_pausa"]


def test_plt_06_mudar_de_plano_com_cancelamento_marcado(moto):
    """CA-ASS-56: com o cancelamento marcado, primeiro desfaz."""
    moto.estado(acesso_ate=date(2026, 10, 21))
    api = moto.api()
    for resposta in (_simular(api, "Completo"), _mudar(api, "Completo"), api.delete(MUDANCA)):
        assert resposta.status_code == 409
        assert resposta.json()["mensagem"] == "Desfaça o cancelamento antes de mudar de plano."
    assert api.get(ASSINATURA).json()["acoes"]["mudar_plano"] is False


def test_plt_04_ca_ass_18_ciclo_mesmo_plano_e_plano_inexistente(moto):
    api = moto.api()
    anual = _simular(api, "Completo", ciclo="anual")
    assert anual.status_code == 422
    assert _erro(anual) == {
        "codigo": "mudanca_ciclo",
        "mensagem": "Para mudar entre mensal e anual, fale com o suporte.",
    }
    mesmo = _mudar(api, "Profissional")
    assert mesmo.status_code == 422
    assert _erro(mesmo) == {"codigo": "mesmo_plano", "mensagem": "Este já é o seu plano."}
    corpo = {"plano_id": 999999, "ciclo": "mensal"}
    assert api.post(SIMULAR, corpo, format="json").status_code == 404


def test_plt_04_mudanca_de_ciclo_pela_equipe(moto, relogio):
    """Mensal → anual pela equipe (PLT-04): vale na próxima fatura, com o preço de tabela do
    anual; a empresa não desfaz."""
    moto.pagar_fat_0001()
    moto.estado(status="ativa")
    relogio.em("2026-11-01 09:00")
    profissional = Plano.objects.get(nome="Profissional")
    services.mudar_plano(
        moto.recarregar(), profissional, "anual", services.POR_EQUIPE, "Pedido no chamado #1051"
    )
    corpo = moto.api().get(ASSINATURA).json()
    assert corpo["plano"]["ciclo"] == "mensal"
    assert corpo["plano_proximo"] == {
        "id": profissional.pk,
        "nome": "Profissional",
        "ciclo": "anual",
        "vale_em": "2026-11-22",
    }
    assert corpo["proxima_fatura"] == {
        "vencimento": "2026-11-22",
        "valor_centavos": 449000,
        "descricao": "Plano Profissional anual · nov 2026 a nov 2027",
    }
    assert corpo["acoes"]["desfazer_mudanca_plano"] is False
    assert moto.api().delete(MUDANCA).status_code == 404
    evento = _eventos("empresa.mudar_ciclo", moto.empresa.schema_name)[0]
    assert evento.motivo == "Pedido no chamado #1051"


def test_plt_04_mudanca_de_plano_isolada_por_empresa(moto, criar_empresa, relogio):
    outra = criar_empresa(subdominio="outra", cnpj="11.222.333/0001-81", nome_exibicao="Outra")
    relogio.em("2026-10-10 09:00")
    assert _mudar(moto.api(), "Completo").status_code == 200
    fatura_da_outra = FaturaAssinatura.objects.get(empresa=outra, codigo="FAT-0001")
    assert (fatura_da_outra.plano.nome, fatura_da_outra.valor_centavos) == ("Profissional", 44900)
    assert Empresa.objects.get(pk=outra.pk).plano == Plano.objects.get(nome="Profissional")
    with schema_context(outra.schema_name):
        assert not EventoAuditoria.objects.filter(acao="empresa.mudar_plano").exists()


# --- Dados fiscais (PLT-15) ---


def test_plt_15_dados_fiscais(moto):
    """CA-ASS-29 e CA-ASS-48: razão social, endereço da nota e e-mail de cobrança; a filial não
    muda."""
    centro = _criar_matriz(moto)
    resposta = moto.api().patch(
        DADOS_FISCAIS,
        {
            "razao_social": "Moto Rápida Locações e Vendas Ltda",
            "endereco": DOM_LUIS,
            "email_cobranca": "Financeiro@MotoRapida.com.br",
        },
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {
        "dados_fiscais": {
            "razao_social": "Moto Rápida Locações e Vendas Ltda",
            "cnpj": "12345678000195",
            "endereco": DOM_LUIS,
            "email_cobranca": "financeiro@motorapida.com.br",
        }
    }
    with tenant_context(moto.empresa):
        assert Filial.objects.get(pk=centro.pk).logradouro == "Av. Bezerra de Menezes"
    connection.set_schema_to_public()
    parcial = moto.api().patch(DADOS_FISCAIS, {"email_cobranca": "mariana@motorapida.com.br"})
    assert parcial.status_code == 200
    assert parcial.json()["dados_fiscais"]["endereco"] == DOM_LUIS


def test_plt_15_cnpj_e_endereco_nulo_recusados(moto):
    api = moto.api()
    cnpj = api.patch(DADOS_FISCAIS, {"cnpj": "11222333000181"}, format="json")
    assert cnpj.status_code == 400
    assert cnpj.json()["campos"] == {"cnpj": ["O CNPJ não muda por aqui. Fale com o suporte."]}
    nulo = api.patch(DADOS_FISCAIS, {"endereco": None}, format="json")
    assert nulo.status_code == 400
    assert "endereco" in nulo.json()["campos"]
    incompleto = api.patch(
        DADOS_FISCAIS, {"endereco": {**DOM_LUIS, "cep": "123", "numero": ""}}, format="json"
    )
    assert incompleto.status_code == 400
    assert set(incompleto.json()["campos"]) == {"endereco.cep", "endereco.numero"}
    assert moto.recarregar().cnpj == "12345678000195"
    assert moto.recarregar().endereco is None


def test_aud_08_dados_fiscais_sem_valor_na_auditoria_do_public(moto):
    """CA-ASS-58: no public, `{"alterado": true}`; no schema da empresa, os valores."""
    _criar_matriz(moto)
    resposta = moto.api().patch(
        DADOS_FISCAIS,
        {"endereco": DOM_LUIS, "email_cobranca": "financeiro@motorapida.com.br"},
        format="json",
    )
    assert resposta.status_code == 200
    publico = _eventos("empresa.dados_fiscais", "public")
    na_empresa = _eventos("empresa.dados_fiscais", moto.empresa.schema_name)
    # A cópia da matriz e a edição, nos dois lugares (T-236).
    assert len(publico) == len(na_empresa) == 2
    assert publico[-1].depois["endereco_logradouro"] == {"alterado": True}
    assert publico[-1].depois["email_cobranca"] == {"alterado": True}
    assert na_empresa[-1].depois["endereco_logradouro"] == "Av. Dom Luís"
    assert na_empresa[-1].antes["endereco_logradouro"] == "Av. Bezerra de Menezes"
    assert na_empresa[0].depois["endereco_logradouro"] == "Av. Bezerra de Menezes"
    with schema_context("public"):
        textos = [str(e.antes) + str(e.depois) for e in EventoAuditoria.objects.all()]
    assert not any("Bezerra" in t or "Dom Luís" in t or "financeiro@" in t for t in textos)


def test_aud_08_dados_da_empresa_omitidos_no_public():
    """Um campo novo de dados da empresa não escapa da lista (`auditoria.md`)."""
    regras = classificacao(Empresa)
    assert regras.omitir_no_public == frozenset(DADOS_APAGADOS_DA_EMPRESA)
    assert {"cnpj", "subdominio", "cidade", "uf"}.isdisjoint(regras.omitir_no_public)


def test_plt_15_dados_fiscais_atualizam_o_pagador(moto, django_capture_on_commit_callbacks):
    forma = FormaPagamentoAssinatura.objects.get(empresa=moto.empresa)
    forma.cliente_externo_id = "cus_falso_moto"
    forma.save(update_fields=["cliente_externo_id"])
    with django_capture_on_commit_callbacks(execute=True):
        resposta = moto.api().patch(
            DADOS_FISCAIS, {"razao_social": "Moto Rápida Ltda", "endereco": DOM_LUIS}, format="json"
        )
    assert resposta.status_code == 200, resposta.json()
    pagador = pagamentos.pagadores["cus_falso_moto"]
    assert pagador.nome == "Moto Rápida Ltda"
    assert pagador.endereco is not None
    assert pagador.endereco.logradouro == "Av. Dom Luís"


# --- Requisitos da segurança para a T-185 (T-189) ---


@pytest.mark.parametrize("permissao", ["ver", "ver_editar"])
def test_plt_07_ca_ass_19_suporte_nao_escreve_na_assinatura(moto, permissao):
    """Requisito 1: nenhuma escrita aceita o token de suporte, nem com "ver e editar"."""
    suporte = moto.suporte(permissao)
    completo = Plano.objects.get(nome="Completo").pk
    escritas = [
        suporte.post(SIMULAR, {"plano_id": completo, "ciclo": "mensal"}, format="json"),
        suporte.post(
            MUDANCA,
            {"plano_id": completo, "ciclo": "mensal", "confirmar_valor_centavos": 0},
            format="json",
        ),
        suporte.delete(MUDANCA),
        suporte.patch(DADOS_FISCAIS, {"razao_social": "Outra Razão"}, format="json"),
    ]
    for resposta in escritas:
        assert resposta.status_code == 403
        assert _erro(resposta) == SUPORTE_NAO_MEXE
    empresa = moto.recarregar()
    assert (empresa.plano.nome, empresa.razao_social) == (
        "Profissional",
        "Moto Rápida Locações Ltda",
    )
    assert moto.fatura("FAT-0001").valor_centavos == 44900
    assert not pagamentos.cobrancas and not pagamentos.pagadores
    # Lê, com as ações desligadas.
    leitura = suporte.get(ASSINATURA)
    assert leitura.status_code == 200
    assert leitura.json()["dados_fiscais"]["cnpj"] == "12345678000195"
    assert not any(leitura.json()["acoes"].values())
    assert suporte.get(PLANOS).status_code == 200


@pytest.mark.parametrize("nome", ["Rodrigo", "Lúcia"])
def test_plt_04_ca_ass_19_so_o_administrador(moto, nome):
    """Requisito 3: todas as rotas novas só do administrador."""
    api = moto.api(nome)
    respostas = [
        api.get(PLANOS),
        _simular(api, "Completo"),
        _mudar(api, "Completo"),
        api.delete(MUDANCA),
        api.patch(DADOS_FISCAIS, {"razao_social": "Outra"}, format="json"),
    ]
    for resposta in respostas:
        assert resposta.status_code == 403
        assert _erro(resposta) == SO_ADMINISTRADOR
    assert moto.recarregar().plano.nome == "Profissional"


def _rotas_que_escrevem_na_suspensa(atributo: str = "escreve_na_suspensa") -> set[tuple[str, str]]:
    from django.urls import URLPattern, URLResolver

    achadas: set[tuple[str, str]] = set()

    def visitar(padroes: list[Any], prefixo: str) -> None:
        for padrao in padroes:
            if isinstance(padrao, URLResolver):
                visitar(padrao.url_patterns, prefixo + str(padrao.pattern))
            elif isinstance(padrao, URLPattern):
                classe = getattr(padrao.callback, "view_class", None)
                valor = getattr(classe, atributo, False)
                metodos = ("POST", "PUT", "PATCH", "DELETE") if valor is True else valor or ()
                for metodo in metodos:
                    if hasattr(classe, metodo.lower()):
                        achadas.add((prefixo + str(padrao.pattern), metodo))

    visitar(urls.urlpatterns, "")
    return achadas


def test_plt_13_ca_ass_27_suspensa_edita_os_dados_fiscais(moto):
    moto.estado(status="suspensa")
    api = moto.api()
    resposta = api.patch(DADOS_FISCAIS, {"email_cobranca": "financeiro@motorapida.com.br"})
    assert resposta.status_code == 200, resposta.json()
    # O resto continua só leitura.
    outra = api.post("/api/filiais/", copy.deepcopy(CENTRO), format="json")
    assert outra.status_code == 403
    assert outra.json()["codigo"] == "empresa_sem_operacao"


@pytest.mark.parametrize("status", ["pausada", "cancelada"])
def test_plt_13_pausada_e_cancelada_nao_entram_na_excecao(moto, status):
    moto.estado(status=status)
    resposta = moto.api().patch(DADOS_FISCAIS, {"email_cobranca": "x@motorapida.com.br"})
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == CODIGO_SEM_OPERACAO[status]
    assert moto.recarregar().email_cobranca == "mariana@motorapida.com.br"


def test_plt_01_cnpj_da_fixture():
    assert CNPJ_MOTO_RAPIDA.replace(".", "").replace("/", "").replace("-", "") == "12345678000195"
