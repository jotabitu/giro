"""T-262 · Troca do ramo em Configurações (`docs/api/empresas.md`, "Ramo da empresa";
`docs/api/configuracoes.md`, cartão `ramo`; PLT-12, ADR 0024, itens 9 e 10).

Roda na Moto Rápida da T-181 (Profissional, em teste, 07 out 2026). Os nomes de `modulos` são
os do enum `Recurso` de hoje; os três que a T-196 acrescenta (conciliação, Pix e boleto,
WhatsApp) entram com ela.
"""

from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.empresas import selectors
from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma.models import Empresa, Plano, UsoEmpresa
from comum import empresa as comum_empresa

from .test_t014_clientes import _suporte
from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t181_configuracoes import _get, _resumo, moto_rapida  # noqa: F401 - fixture

URL = "/api/ramo/"
PROFISSIONAL = [
    "Locação e vistoria",
    "Contas a receber",
    "Contrato digital",
    "Vendas e comissões",
    "Manutenção e despesas",
    "Relatórios",
]


def _put(moto, atividade: str, trabalha_com: str = "motos", quem: str = "Mariana") -> Any:
    corpo = {"atividade": atividade, "trabalha_com": trabalha_com}
    return moto.moto.api(quem).put(URL, corpo, format="json")


def test_plt_12_ramo_get_seed(moto_rapida):  # noqa: F811
    resposta = moto_rapida.moto.api("Mariana").get(URL)
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["atividade"] == "ambos" and corpo["trabalha_com"] == "motos"
    assert corpo["atividades"] == [
        {
            "valor": "aluga",
            "titulo": "Locação",
            "descricao": "Aluguel por dia, semana ou mês",
            "aviso": None,
        },
        {
            "valor": "vende",
            "titulo": "Venda de veículos",
            "descricao": "Novos, seminovos e consignados",
            "aviso": None,
        },
    ]
    assert corpo["atividades_aceitas"] == ["aluga", "vende", "ambos"]
    assert corpo["tipos"] == [
        {"valor": "motos", "titulo": "Motos"},
        {"valor": "carros", "titulo": "Carros"},
    ]
    assert corpo["modulos"] == {
        "aluga": [m for m in PROFISSIONAL if m != "Vendas e comissões"],
        "vende": [m for m in PROFISSIONAL if m != "Locação e vistoria"],
        "ambos": PROFISSIONAL,
    }


def test_plt_12_configuracoes_cartao_ramo(moto_rapida):  # noqa: F811
    """O cartão logo depois de `marca`, com o resumo da API, e sem cache depois da troca."""
    corpo = _get(moto_rapida)
    assert [c["chave"] for c in corpo["cartoes"]][:2] == ["marca", "ramo"]
    assert corpo["cartoes"][1] == {
        "chave": "ramo",
        "titulo": "O que a empresa faz",
        "resumo": "Locação e venda · motos",
    }
    assert _put(moto_rapida, "aluga", "ambos").status_code == 200
    assert _resumo(_get(moto_rapida), "ramo") == "Locação · motos e carros"


def test_plt_12_configuracoes_ramo_ausente_para_o_suporte(moto_rapida, relogio_jwt):  # noqa: F811
    resposta = _suporte(moto_rapida.moto, "ver_editar").get("/api/configuracoes/")
    assert resposta.status_code == 200, resposta.json()
    assert "ramo" not in [c["chave"] for c in resposta.json()["cartoes"]]


def test_plt_12_suporte_le_o_ramo_e_nao_troca(moto_rapida, relogio_jwt):  # noqa: F811
    suporte = _suporte(moto_rapida.moto, "ver_editar")
    assert suporte.get(URL).status_code == 200
    resposta = suporte.put(URL, {"atividade": "aluga", "trabalha_com": "motos"}, format="json")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "PLT-07"
    assert selectors.configuracao().atividade == "ambos"


@pytest.mark.parametrize("quem", ["Rodrigo", "Bruna", "João", "Lúcia"])
def test_plt_12_ramo_so_administrador(moto_rapida, quem):  # noqa: F811
    assert moto_rapida.moto.api(quem).get(URL).status_code == 403
    assert _put(moto_rapida, "aluga", quem=quem).status_code == 403


def test_plt_12_troca_de_ramo_grava_audita_e_marca_o_passo(moto_rapida):  # noqa: F811
    resposta = _put(moto_rapida, "aluga", "ambos")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["atividade"] == "aluga"
    assert resposta.json()["trabalha_com"] == "ambos"
    assert comum_empresa.atividade() == "aluga"
    assert "vendas_comissoes" not in plataforma_selectors.recursos_da_empresa()
    evento = EventoAuditoria.objects.get(acao="empresa.mudar_ramo")
    assert evento.categoria == "configuracoes" and evento.regra == "PLT-12"
    assert evento.antes["atividade"] == "ambos" and evento.depois["atividade"] == "aluga"
    assert "vendas_comissoes" in evento.antes["recursos"]
    assert "vendas_comissoes" not in evento.depois["recursos"]
    passos = UsoEmpresa.objects.get(empresa=moto_rapida.moto.empresa).passos_implantacao
    assert "ramo" in passos
    # Mesmo ramo de novo: 200, sem outro evento.
    assert _put(moto_rapida, "aluga", "ambos").status_code == 200
    assert EventoAuditoria.objects.filter(acao="empresa.mudar_ramo").count() == 1


def test_plt_12_troca_de_ramo_com_algo_aberto(moto_rapida):  # noqa: F811
    """CA-ASS-50: deixar de alugar com uma locação aguardando retirada."""
    moto_rapida.confirmada()
    resposta = _put(moto_rapida, "vende")
    assert resposta.status_code == 422, resposta.json()
    assert resposta.json() == {
        "codigo": "PLT-12",
        "mensagem": "Para deixar de alugar, resolva o que está aberto: 1 locação aberta.",
        "detalhes": {
            "motivo": "abertos",
            "recurso": "locacoes_vistoria",
            "abertos": [{"grupo": "locacoes", "quantidade": 1, "texto": "1 locação aberta"}],
            "abertos_texto": "1 locação aberta",
        },
    }
    assert selectors.configuracao().atividade == "ambos"
    assert not EventoAuditoria.objects.filter(acao="empresa.mudar_ramo").exists()
    # Trocar só o tipo, sem tirar módulo, passa.
    assert _put(moto_rapida, "ambos", "carros").status_code == 200


def test_plt_12_essencial_sem_so_vende(moto_rapida):  # noqa: F811
    """CA-ASS-51: o `GET` e o `PUT` no Essencial."""
    Empresa._base_manager.filter(pk=moto_rapida.moto.empresa.pk).update(
        plano=Plano.objects.get(nome="Essencial")
    )
    corpo = moto_rapida.moto.api("Mariana").get(URL).json()
    assert corpo["atividades_aceitas"] == ["aluga", "ambos"]
    assert corpo["atividades"][1]["aviso"] == "Vendas faz parte do plano Profissional."
    assert set(corpo["modulos"]) == {"aluga", "ambos"}
    resposta = _put(moto_rapida, "vende")
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "PLT-12",
        "mensagem": "O plano Essencial não inclui vendas. Escolha locação, ou locação e venda.",
        "detalhes": {"motivo": "plano", "atividades_aceitas": ["aluga", "ambos"]},
    }


def test_plt_12_ramo_campo_fora_do_enum(moto_rapida):  # noqa: F811
    assert _put(moto_rapida, "troca").status_code == 400
    resposta = moto_rapida.moto.api("Mariana").put(URL, {"atividade": "aluga"}, format="json")
    assert resposta.status_code == 400


def test_plt_12_ramo_empresa_pausada_nao_troca(moto_rapida):  # noqa: F811
    Empresa._base_manager.filter(pk=moto_rapida.moto.empresa.pk).update(status="pausada")
    resposta = _put(moto_rapida, "aluga")
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "empresa_sem_operacao"


def test_plt_12_recursos_para_e_atividades_aceitas():
    essencial = Plano(nome="Essencial", recursos=["locacoes_vistoria", "contas_receber"])
    assert plataforma_selectors.atividades_aceitas(essencial) == ("aluga", "ambos")
    assert plataforma_selectors.recursos_para(essencial, "vende") == frozenset({"contas_receber"})
    profissional = Plano(nome="Profissional", recursos=["locacoes_vistoria", "vendas_comissoes"])
    assert plataforma_selectors.atividades_aceitas(profissional) == ("aluga", "vende", "ambos")
    assert plataforma_selectors.recursos_para(profissional, "aluga") == frozenset(
        {"locacoes_vistoria"}
    )
