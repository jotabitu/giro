"""T-181 · Resumo da tela de Configurações (`docs/api/configuracoes.md`, "Casos para teste").

Roda na `empresa_a` com as pessoas, a Filial Centro, as 4 categorias e o modelo de locação
publicado da Moto Rápida (cenário da T-015), com o relógio em 07 out 2026.
"""

from datetime import date
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.contas import services as contas_services
from apps.contratos.models import ModeloContrato
from apps.filiais.models import Filial
from apps.plataforma.models import Empresa, UsoEmpresa
from apps.relatorios import configuracoes as textos

from .test_t014_clientes import _suporte
from .test_t015_locacoes import cenario  # noqa: F401 - fixture

URL = "/api/configuracoes/"
TODOS_OS_MODULOS = [
    "aprovacoes",
    "auditoria",
    "clientes",
    "configuracoes",
    "contas",
    "contratos",
    "empresas",
    "filiais",
    "financeiro",
    "locacoes",
    "plataforma",
    "veiculos",
    "vistorias",
]
SEED = [
    {
        "chave": "marca",
        "titulo": "Empresa e marca",
        "resumo": "Logo, cor, nome e endereço do sistema",
    },
    {"chave": "ramo", "titulo": "O que a empresa faz", "resumo": "Locação e venda · motos"},
    {"chave": "filiais", "titulo": "Filiais", "resumo": "1 filial · Filial Centro, Fortaleza"},
    {"chave": "usuarios", "titulo": "Usuários e perfis", "resumo": "5 de 10 usuários"},
    {"chave": "precos", "titulo": "Tabelas de preço", "resumo": "4 categorias"},
    {"chave": "modelos_contrato", "titulo": "Modelos de contrato", "resumo": "1 modelo"},
    {"chave": "assinatura", "titulo": "Assinatura", "resumo": "Profissional · teste até 21 out"},
    {"chave": "auditoria", "titulo": "Auditoria", "resumo": "Quem fez o quê no sistema"},
    {"chave": "exportar", "titulo": "Exportar dados", "resumo": "Baixe a auditoria em CSV"},
]


def _passos(*feitos: str) -> None:
    UsoEmpresa.objects.filter(empresa=connection.tenant).update(
        passos_implantacao={passo: "2026-09-20" for passo in feitos}
    )


@pytest.fixture
def moto_rapida(cenario, settings):  # noqa: F811
    """O seed em 07 out: em teste até 21 out, 5 usuários no uso, implantação concluída (IMP-01:
    a carteira tem locações)."""
    settings.GIRO_MODULOS_ATIVOS = TODOS_OS_MODULOS
    Empresa._base_manager.filter(pk=cenario.moto.empresa.pk).update(
        status="em_teste", teste_fim=date(2026, 10, 21)
    )
    UsoEmpresa.objects.filter(empresa=cenario.moto.empresa).update(usuarios=5)
    _passos("conta", "filial", "primeira_locacao")
    return cenario


def _get(cenario, quem: str = "Mariana") -> dict[str, Any]:  # noqa: F811
    resposta = cenario.moto.api(quem).get(URL)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _resumo(corpo: dict[str, Any], chave: str) -> str:
    return str(next(c["resumo"] for c in corpo["cartoes"] if c["chave"] == chave))


def _chaves(corpo: dict[str, Any]) -> list[str]:
    return [c["chave"] for c in corpo["cartoes"]]


def test_usr_05_configuracoes_seed_moto_rapida(moto_rapida):
    assert _get(moto_rapida) == {"cartoes": SEED, "implantacao": None}


def test_usr_05_configuracoes_so_cartoes_de_apps_ativos(moto_rapida, settings):
    # Sem `auditoria`: sem Auditoria e sem Exportar.
    settings.GIRO_MODULOS_ATIVOS = [m for m in TODOS_OS_MODULOS if m != "auditoria"]
    assert _chaves(_get(moto_rapida)) == [
        "marca",
        "ramo",
        "filiais",
        "usuarios",
        "precos",
        "modelos_contrato",
        "assinatura",
    ]
    # Sem `empresas` (a tela Empresa e marca é da T-154): o cartão `marca` não vem, e o item
    # `config` do menu continua, pela chave própria `configuracoes`.
    settings.GIRO_MODULOS_ATIVOS = [m for m in TODOS_OS_MODULOS if m != "empresas"]
    assert not {"marca", "ramo"} & set(_chaves(_get(moto_rapida)))
    eu = moto_rapida.moto.api("Mariana").get("/api/auth/eu/").json()
    administracao = next(
        [i["chave"] for i in g["itens"]]
        for g in eu["navegacao"]["menu_completo"]
        if g["grupo"] == "Administração"
    )
    assert "config" in administracao and "marca" not in administracao
    # O padrão do backend: Configurações liga, Empresa e marca não, Auditoria não.
    settings.GIRO_MODULOS_ATIVOS = [
        "aprovacoes",
        "clientes",
        "configuracoes",
        "contas",
        "contratos",
        "filiais",
        "financeiro",
        "locacoes",
        "plataforma",
        "veiculos",
        "vistorias",
    ]
    assert _chaves(_get(moto_rapida)) == [
        "filiais",
        "usuarios",
        "precos",
        "modelos_contrato",
        "assinatura",
    ]
    # Sem `locacoes`, o plano especial sai do texto (o cartão é de `veiculos`).
    settings.GIRO_MODULOS_ATIVOS = [m for m in TODOS_OS_MODULOS if m != "locacoes"]
    assert _resumo(_get(moto_rapida), "precos") == "4 categorias"


def test_plt_03_configuracoes_usuarios_conta_convites(moto_rapida):
    mariana = moto_rapida.pessoas["Mariana"]
    centro = moto_rapida.frota.centro.pk
    for email in ("ana@motorapida.com.br", "caio@motorapida.com.br"):
        contas_services.convidar(email=email, perfil="vendedor", filiais=[centro], por=mariana)
    assert _resumo(_get(moto_rapida), "usuarios") == "7 de 10 usuários · 2 convites"


def test_loc_01_configuracoes_planos_especiais(moto_rapida):
    api = moto_rapida.moto.api("Mariana")
    for dados in (
        {
            "nome": "Entregador",
            "periodicidade": "semanal",
            "regra": "preco_fixo",
            "preco_centavos": 27900,
        },
        {
            "nome": "Mensal fidelidade",
            "periodicidade": "mensal",
            "regra": "desconto",
            "desconto_pct": "10.00",
            "a_partir_do_periodo": 3,
        },
    ):
        assert api.post("/api/planos-especiais/", dados, format="json").status_code == 201
    assert _resumo(_get(moto_rapida), "precos") == "4 categorias · 2 planos especiais"


def test_imp_04_configuracoes_rascunho_e_sem_modelo_publicado(moto_rapida):
    ModeloContrato.objects.create(nome="Venda", finalidade="venda", texto="<p>x</p>")
    assert _resumo(_get(moto_rapida), "modelos_contrato") == "2 modelos · 1 rascunho"


def test_imp_04_configuracoes_sem_modelo_publicado(moto_rapida):
    ModeloContrato.objects.filter(pk=moto_rapida.modelo.pk).update(arquivado=True)
    assert _resumo(_get(moto_rapida), "modelos_contrato") == "Nenhum modelo publicado"


def test_plt_07_configuracoes_suporte_sem_auditoria(moto_rapida, relogio_jwt):
    resposta = _suporte(moto_rapida.moto, "ver").get(URL)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    # Nem `ramo` (T-259): a tela só serve para trocar, e o suporte não troca.
    fora = ("ramo", "auditoria", "exportar")
    assert _chaves(corpo) == [c["chave"] for c in SEED if c["chave"] not in fora]
    assert corpo["cartoes"] == [c for c in SEED if c["chave"] not in fora]


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna", "João", "Lúcia"])
def test_usr_05_configuracoes_so_administrador(moto_rapida, quem):
    resposta = moto_rapida.moto.api(quem).get(URL)
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "permissao"
    assert resposta.json()["mensagem"] == "Seu perfil não tem acesso a esta página"


def test_imp_05_configuracoes_faixa_da_implantacao(moto_rapida):
    _passos("conta", "marca", "filial", "ramo", "precos", "equipe")
    assert _get(moto_rapida)["implantacao"] == {
        "concluidos": 6,
        "total": 10,
        "titulo": "Implantação concluída em 6 de 10 passos",
        "faltam": "Faltam contrato, recebimentos, importar dados e a 1ª locação.",
        "acao": None,
    }
    _passos(*[p for p in textos.NOMES_DOS_PASSOS if p != "primeira_locacao"])
    assert _get(moto_rapida)["implantacao"] == {
        "concluidos": 9,
        "total": 10,
        "titulo": "Implantação concluída em 9 de 10 passos",
        "faltam": "Falta a 1ª locação.",
        "acao": {"rotulo": "Fazer uma locação de teste", "destino": "nova_locacao"},
    }


def test_plt_01_configuracoes_empresa_suspensa_responde(moto_rapida):
    # Suspender é ação da fase 2: o estado é montado direto, como na T-010.
    Empresa._base_manager.filter(pk=moto_rapida.moto.empresa.pk).update(status="suspensa")
    assert _resumo(_get(moto_rapida), "assinatura") == "Profissional · suspensa"


def _consultas(usuario: Any) -> int:
    """Consultas de dados de `configuracoes(...)`; o `SET search_path` que o django-tenants
    repete a cada cursor não conta."""
    from apps.relatorios import selectors

    with CaptureQueriesContext(connection) as feitas:
        selectors.configuracoes(usuario, suporte=False)
    return sum(1 for q in feitas.captured_queries if not q["sql"].startswith("SET search_path"))


def test_usr_05_configuracoes_no_maximo_11_queries(moto_rapida):
    mariana = moto_rapida.pessoas["Mariana"]
    antes = _consultas(mariana)
    # 10 da T-181 mais a linha de `ConfiguracaoEmpresa` do cartão `ramo` (T-259, T-262).
    assert antes <= 11
    # Sem N+1 por filial nem por modelo.
    for nome, cidade in (("Filial Caucaia", "Caucaia"), ("Filial Maracanaú", "Maracanaú")):
        Filial.objects.create(**{**_campos_da_filial(moto_rapida), "nome": nome, "cidade": cidade})
    for nome in ("Venda", "Aditivo"):
        ModeloContrato.objects.create(nome=nome, finalidade="venda", texto="<p>x</p>")
    assert _consultas(mariana) <= antes
    corpo = _get(moto_rapida)
    assert _resumo(corpo, "filiais") == "3 filiais · Fortaleza, Caucaia e Maracanaú"
    assert _resumo(corpo, "modelos_contrato") == "3 modelos · 2 rascunhos"


def _campos_da_filial(cenario) -> dict[str, Any]:  # noqa: F811
    centro = cenario.frota.centro
    return {
        f.attname: getattr(centro, f.attname)
        for f in Filial._meta.concrete_fields
        if not f.primary_key and f.attname not in ("matriz", "cnpj", "criado_em", "atualizado_em")
    }


# --- Textos (função pura, tabela "Cartões") ---


def test_usr_05_configuracoes_textos_dos_cartoes():
    assert textos.resumo_filiais(2, ["Fortaleza", "Caucaia"], None) == (
        "2 filiais · Fortaleza e Caucaia"
    )
    assert textos.resumo_filiais(3, ["A", "B", "C"], None) == "3 filiais · A, B e C"
    assert textos.resumo_filiais(5, ["A", "B", "C", "D"], None) == "5 filiais em 4 cidades"
    assert textos.resumo_usuarios(3, None, 1) == "3 usuários · 1 convite"
    assert textos.resumo_precos(1, 1) == "1 categoria · 1 plano especial"
    assert textos.resumo_precos(0, 2) == "Nenhuma categoria cadastrada"
    assert textos.resumo_modelos(1, 0, True) == "1 modelo"

    def assinatura(status: str, pausada_ate: date | None = None) -> str:
        return textos.resumo_assinatura("Essencial", status, "anual", None, pausada_ate)

    assert assinatura("ativa") == "Essencial · anual"
    assert assinatura("inadimplente") == "Essencial · fatura em atraso"
    assert assinatura("pausada") == "Essencial · pausada"
    assert assinatura("pausada", date(2026, 11, 30)) == "Essencial · pausada até 30 nov"
    assert assinatura("cancelada") == "Essencial · cancelada"
