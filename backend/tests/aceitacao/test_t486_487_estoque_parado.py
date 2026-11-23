"""T-486 e T-487 · Dias em estoque, veículo parado, capital imobilizado e ticket médio.

Sobre o seed da Moto Rápida (T-499, `docs/regras/dados-de-teste.md`, casos "Dias em estoque em
07 out", "Alerta de veículo parado" e "Estoque à venda em 07 out"): PVE-1A07, PVF-2B18 e PVG-3C29
à venda desde 15 ago, 06 set e 07 set, e os outros 9 `a_venda` desde 07 out às 07:00, todos na
Filial Centro, com o limite da empresa de 30 dias.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.core import mail
from django.core.cache import cache

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from apps.empresas import selectors as empresas_selectors
from apps.empresas import services as empresas_services
from apps.notificacoes.models import Notificacao
from apps.relatorios import selectors as relatorios_selectors
from apps.veiculos import selectors as veiculos_selectors
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from apps.veiculos.tasks import aut_18_veiculos_parados

from .test_t019_seed_completo import EMAILS, _api, seed  # noqa: F401 - fixture
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures

FROTA = "/api/veiculos/"
INICIO = "/api/painel/inicio/"
ESTOQUE = "/api/configuracoes/estoque/"
PARADOS = ["PVE1A07", "PVF2B18", "PVG3C29"]
CAMPOS_DO_ESTOQUE = {"a_venda_desde", "dias_em_estoque", "parado"}


def _veiculo(placa: str) -> Veiculo:
    return Veiculo.objects.get(placa=placa)


def _a_venda(cenario: Any, quem: str = "Mariana", **parametros: str) -> list[dict[str, Any]]:
    resposta = _api(cenario, quem).get(FROTA, {"status": "a_venda", "tamanho": 50, **parametros})
    assert resposta.status_code == 200, resposta.json()
    return list(resposta.json()["resultados"])


def _ficha(cenario: Any, placa: str, quem: str = "Mariana") -> dict[str, Any]:
    resposta = _api(cenario, quem).get(f"{FROTA}{_veiculo(placa).pk}/")
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _inicio(cenario: Any, quem: str) -> dict[str, Any]:
    cache.clear()
    resposta = _api(cenario, quem).get(INICIO)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json())


def _avisos(nome: str) -> list[str]:
    usuario = Usuario.objects.get(email=EMAILS[nome])
    return list(
        Notificacao.objects.filter(destinatario=usuario, tipo="veiculo_parado")
        .order_by("id")
        .values_list("titulo", flat=True)
    )


def _sem_os_outros_avisos(nomes: list[str]) -> None:
    for nome in nomes:
        assert _avisos(nome) == []


# --- VEI-18: dias em estoque na lista e na ficha ---


def test_vei_18_lista_a_venda_na_ordem_do_mais_parado(seed):  # noqa: F811
    linhas = _a_venda(seed)
    placas = [linha["placa"] for linha in linhas]
    outros = sorted(p for p in placas if p not in PARADOS)
    assert placas == [*PARADOS, *outros]  # os 9 de hoje pela placa
    assert len(outros) == 9
    por_placa = {linha["placa"]: linha for linha in linhas}
    assert [
        (por_placa[p]["a_venda_desde"], por_placa[p]["dias_em_estoque"], por_placa[p]["parado"])
        for p in PARADOS
    ] == [
        ("2026-08-15", 53, True),
        ("2026-09-06", 31, True),
        ("2026-09-07", 30, False),  # no limite, ainda não está parado
    ]
    assert {(por_placa[p]["dias_em_estoque"], por_placa[p]["parado"]) for p in outros} == {
        (0, False)
    }  # "Hoje"


def test_vei_18_ordem_em_estoque_pagina_e_poe_os_sem_entrada_no_fim(seed):  # noqa: F811
    api = _api(seed, "Mariana")
    placas: list[str] = []
    url: str | None = FROTA
    parametros: dict[str, Any] | None = {"ordem": "em_estoque", "tamanho": 5}
    while url and len(placas) < 20:
        resposta = api.get(url, parametros)
        assert resposta.status_code == 200, resposta.json()
        corpo = resposta.json()
        placas += [linha["placa"] for linha in corpo["resultados"]]
        url, parametros = corpo["proximo"], None
    assert placas[:3] == PARADOS
    assert len(set(placas)) == len(placas)  # o cursor não repete nem pula
    # Depois dos 12 à venda vêm os fora do estoque (sem o número), pela placa.
    seguintes = placas[12:20]
    assert seguintes == sorted(seguintes)
    assert all(_veiculo(p).status != "a_venda" for p in seguintes)


def test_vei_18_ficha_com_a_entrada_os_dias_e_o_limite(seed):  # noqa: F811
    ficha = _ficha(seed, "PVE1A07")
    assert (ficha["a_venda_desde"], ficha["dias_em_estoque"], ficha["parado"]) == (
        "2026-08-15",
        53,
        True,
    )
    assert ficha["limite_dias_parado"] == 30
    alugado = Veiculo.objects.filter(status="alugado").first()
    assert alugado is not None
    ficha = _ficha(seed, alugado.placa)
    assert (ficha["a_venda_desde"], ficha["dias_em_estoque"], ficha["parado"]) == (
        None,
        None,
        False,
    )


def test_vei_18_quem_ve_os_dias(seed):  # noqa: F811
    for quem in ("Rodrigo", "Bruna", "Lúcia"):
        linhas = _a_venda(seed, quem)
        assert linhas[0]["placa"] == "PVE1A07"
        assert linhas[0]["dias_em_estoque"] == 53
        assert _ficha(seed, "PVE1A07", quem)["dias_em_estoque"] == 53
    # O vistoriador vê do veículo só km e avarias: os campos não vêm (ausentes, não nulos).
    linhas = _a_venda(seed, "João")
    assert all(not (CAMPOS_DO_ESTOQUE & linha.keys()) for linha in linhas)
    ficha = _ficha(seed, "PVE1A07", "João")
    assert not ((CAMPOS_DO_ESTOQUE | {"limite_dias_parado"}) & ficha.keys())


def test_vei_18_venda_cancelada_nao_recomeca_a_contagem(seed):  # noqa: F811
    veiculo = _veiculo("PVE1A07")
    origem = veiculo_services_origem()
    veiculos_services.transicionar(veiculo, "vendido", origem=origem)
    veiculos_services.transicionar(_veiculo("PVE1A07"), "a_venda", origem=origem)  # VEN-07
    ficha = _ficha(seed, "PVE1A07")
    assert (ficha["a_venda_desde"], ficha["dias_em_estoque"]) == ("2026-08-15", 53)


def test_vei_18_voltou_para_a_frota_recomeca_do_zero(seed):  # noqa: F811
    veiculos_services.voltar_para_frota(_veiculo("PVE1A07"))
    ficha = _ficha(seed, "PVE1A07")
    assert (ficha["a_venda_desde"], ficha["dias_em_estoque"]) == (None, None)
    veiculos_services.transicionar(_veiculo("PVE1A07"), "a_venda", origem=veiculo_services_origem())
    ficha = _ficha(seed, "PVE1A07")
    assert (ficha["a_venda_desde"], ficha["dias_em_estoque"], ficha["parado"]) == (
        "2026-10-07",
        0,
        False,
    )


def test_vei_18_sem_entrada_no_historico_vai_para_o_fim(seed):  # noqa: F811
    veiculo = _veiculo("PVE1A07")
    veiculo.historico.filter(para="a_venda").delete()
    linhas = _a_venda(seed)
    assert linhas[-1]["placa"] == "PVE1A07"
    assert (linhas[-1]["a_venda_desde"], linhas[-1]["dias_em_estoque"]) == (None, None)
    assert linhas[-1]["parado"] is False


def veiculo_services_origem() -> Any:
    return veiculos_services.MANUAL


# --- VEI-18, VEI-19: "Parados à venda" no início do gerente ---


def test_vei_18_parados_a_venda_no_inicio_do_rodrigo(seed):  # noqa: F811
    bloco = _inicio(seed, "Rodrigo")["parados_a_venda"]
    outros = sorted(
        v.placa for v in Veiculo.objects.filter(status="a_venda") if v.placa not in PARADOS
    )
    assert [item["placa"] for item in bloco["itens"]] == [*PARADOS, *outros[:2]]
    assert [item["dias_em_estoque"] for item in bloco["itens"]] == [53, 31, 30, 0, 0]
    assert [item["parado"] for item in bloco["itens"]] == [True, True, False, False, False]
    assert bloco["itens"][0]["veiculo"] == "Honda Biz 125"
    assert (bloco["acima_do_limite"], bloco["limite_dias_parado"]) == (2, 30)
    assert bloco["subtitulo"] == "2 acima de 30 dias"


def test_vei_18_parados_so_no_inicio_do_gerente(seed):  # noqa: F811
    assert "parados_a_venda" not in _inicio(seed, "Mariana")
    for quem in ("Bruna", "Lúcia", "João"):
        assert "parados_a_venda" not in _inicio(seed, quem)


def test_vei_18_parados_sem_veiculo_a_venda(seed):  # noqa: F811
    bloco = veiculos_selectors.parados_a_venda([], 30, date(2026, 10, 7))
    assert (bloco["acima_do_limite"], bloco["itens"]) == (0, [])


# --- VEI-19: o limite da empresa ---


def test_vei_19_limite_padrao_e_quem_edita(seed):  # noqa: F811
    resposta = _api(seed, "Mariana").get(ESTOQUE)
    assert resposta.json() == {"limite_dias_parado": 30, "pode_editar": True}
    for quem in ("Rodrigo", "Bruna", "Lúcia", "João"):
        assert _api(seed, quem).get(ESTOQUE).json() == {
            "limite_dias_parado": 30,
            "pode_editar": False,
        }
        mudar = _api(seed, quem).patch(ESTOQUE, {"limite_dias_parado": 45}, format="json")
        assert mudar.status_code == 403, quem
    assert empresas_selectors.limite_dias_parado() == 30


def test_vei_19_mariana_muda_para_45_com_auditoria(seed, relogio):  # noqa: F811
    relogio.em("2026-10-08 09:00")
    resposta = _api(seed, "Mariana").patch(ESTOQUE, {"limite_dias_parado": 45}, format="json")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["limite_dias_parado"] == 45
    evento = EventoAuditoria.objects.filter(acao="empresa.alterar_limite_estoque").get()
    assert (evento.antes, evento.depois) == (
        {"limite_dias_parado": 30},
        {"limite_dias_parado": 45},
    )
    # Só o PVE-1A07 (54 dias) fica parado; o destaque segue o limite novo na hora.
    linhas = {linha["placa"]: linha for linha in _a_venda(seed)}
    assert [(p, linhas[p]["dias_em_estoque"], linhas[p]["parado"]) for p in PARADOS] == [
        ("PVE1A07", 54, True),
        ("PVF2B18", 32, False),
        ("PVG3C29", 31, False),
    ]
    assert _inicio(seed, "Rodrigo")["parados_a_venda"]["subtitulo"] == "1 acima de 45 dias"


@pytest.mark.parametrize("valor", [0, 366, "", None, "abc", 1.5, True, -3])
def test_vei_19_limite_fora_da_faixa_recusado(seed, valor):  # noqa: F811
    resposta = _api(seed, "Mariana").patch(ESTOQUE, {"limite_dias_parado": valor}, format="json")
    assert resposta.status_code == 422, resposta.json()
    assert resposta.json()["codigo"] == "VEI-19"
    assert resposta.json()["mensagem"] == "Informe um número inteiro de 1 a 365."
    assert empresas_selectors.limite_dias_parado() == 30
    assert not EventoAuditoria.objects.filter(acao="empresa.alterar_limite_estoque").exists()


def test_vei_19_limites_da_faixa_aceitos(seed):  # noqa: F811
    for valor in (1, 365, "30"):
        empresas_services.definir_limite_dias_parado(valor)
        assert empresas_selectors.limite_dias_parado() == int(valor)


# --- AUT-18: aviso de veículo parado ---


def test_aut_18_avisos_de_07_e_08_out(seed, relogio, django_capture_on_commit_callbacks):  # noqa: F811
    relogio.em("2026-10-07 07:00")
    with django_capture_on_commit_callbacks(execute=True):
        assert aut_18_veiculos_parados("motorapida") == {"veiculos": 2, "avisos": 2}
    assert _avisos("Rodrigo") == [
        "O veículo PVE-1A07 (Honda Biz 125) está à venda há 53 dias. "
        "O limite da empresa é 30 dias.",
        "O veículo PVF-2B18 (Honda CG 160 Fan) está à venda há 31 dias. "
        "O limite da empresa é 30 dias.",
    ]
    primeira = Notificacao.objects.filter(tipo="veiculo_parado").order_by("id").first()
    assert primeira is not None
    assert primeira.link == f"/veiculos/{_veiculo('PVE1A07').pk}"  # o aviso abre a ficha
    assert [m.subject for m in mail.outbox if "está à venda há" in m.subject] == _avisos("Rodrigo")
    # De novo no mesmo dia: nada se repete.
    assert aut_18_veiculos_parados("motorapida") == {"veiculos": 0, "avisos": 0}

    relogio.em("2026-10-08 07:00")
    assert aut_18_veiculos_parados("motorapida") == {"veiculos": 1, "avisos": 1}
    assert _avisos("Rodrigo")[2:] == [
        "O veículo PVG-3C29 (Yamaha Factor 150) está à venda há 31 dias. "
        "O limite da empresa é 30 dias."
    ]
    # Administradores, vendedora, financeiro e vistoriador não recebem.
    _sem_os_outros_avisos(["Mariana", "Bruna", "Lúcia", "João"])


def test_aut_18_limite_20_antes_das_07_avisa_os_tres(seed, relogio):  # noqa: F811
    relogio.em("2026-10-07 06:59")
    empresas_services.definir_limite_dias_parado(20)
    relogio.em("2026-10-07 07:00")
    assert aut_18_veiculos_parados("motorapida")["avisos"] == 3
    assert [t.split(" (")[0] for t in _avisos("Rodrigo")] == [
        "O veículo PVE-1A07",
        "O veículo PVF-2B18",
        "O veículo PVG-3C29",
    ]
    assert _avisos("Rodrigo")[2].endswith("há 30 dias. O limite da empresa é 20 dias.")


def test_aut_18_subir_o_limite_nao_desfaz_e_venda_cancelada_nao_repete(seed, relogio):  # noqa: F811
    relogio.em("2026-10-07 07:00")
    aut_18_veiculos_parados("motorapida")
    relogio.em("2026-10-08 09:00")
    empresas_services.definir_limite_dias_parado(45)
    assert len(_avisos("Rodrigo")) == 2  # nenhum aviso é desfeito
    origem = veiculo_services_origem()
    veiculos_services.transicionar(_veiculo("PVE1A07"), "vendido", origem=origem)
    veiculos_services.transicionar(_veiculo("PVE1A07"), "a_venda", origem=origem)
    relogio.em("2026-10-09 07:00")
    assert aut_18_veiculos_parados("motorapida")["avisos"] == 0


def test_aut_18_saiu_e_voltou_pode_ser_avisado_de_novo(seed, relogio):  # noqa: F811
    relogio.em("2026-10-07 07:00")
    aut_18_veiculos_parados("motorapida")
    relogio.em("2026-10-07 10:00")
    veiculos_services.voltar_para_frota(_veiculo("PVF2B18"))
    veiculos_services.transicionar(_veiculo("PVF2B18"), "a_venda", origem=veiculo_services_origem())
    relogio.em("2026-11-08 07:00")  # 32 dias depois da nova entrada
    aut_18_veiculos_parados("motorapida")
    novos = [t for t in _avisos("Rodrigo") if "PVF-2B18" in t]
    assert novos[-1] == (
        "O veículo PVF-2B18 (Honda CG 160 Fan) está à venda há 32 dias. "
        "O limite da empresa é 30 dias."
    )
    assert len(novos) == 2


def test_aut_18_execucao_perdida_sai_na_proxima(seed, relogio):  # noqa: F811
    relogio.em("2026-10-09 07:00")  # 07 e 08 out sem rodar
    assert aut_18_veiculos_parados("motorapida")["avisos"] == 3
    assert "há 32 dias" in next(t for t in _avisos("Rodrigo") if "PVG-3C29" in t)


def test_aut_18_filial_sem_gerente_ativo_fica_sem_aviso(seed, relogio):  # noqa: F811
    ligacoes = Usuario.objects.get(email=EMAILS["Rodrigo"]).filiais_ligadas
    ligacoes.update(ativo=False)  # a Filial Centro fica sem gerente ativo (FIL-02)
    relogio.em("2026-10-07 07:00")
    assert aut_18_veiculos_parados("motorapida") == {"veiculos": 2, "avisos": 0}
    ligacoes.update(ativo=True)
    assert aut_18_veiculos_parados("motorapida") == {"veiculos": 0, "avisos": 0}


def test_aut_18_tarefa_no_beat_as_07(settings):
    agenda = settings.CELERY_BEAT_SCHEDULE["aut_18_veiculos_parados"]
    assert agenda["task"] == "aut_18_veiculos_parados_de_todas"
    assert (agenda["schedule"].hour, agenda["schedule"].minute) == ({7}, {0})


# --- VEI-20: capital imobilizado, custo médio e margem potencial ---


def test_vei_20_bloco_do_estoque_de_mariana_e_rodrigo(seed):  # noqa: F811
    for quem in ("Mariana", "Rodrigo"):
        bloco = _inicio(seed, quem)["estoque_a_venda"]
        assert bloco["quantidade"] == 12
        assert bloco["capital_imobilizado_centavos"] == 3950000  # R$ 39.500,00
        assert bloco["veiculos_na_conta"] == 3
        assert bloco["custo_medio_centavos"] == 1316667  # R$ 13.166,67
        assert bloco["margem_centavos"] == 210000  # R$ 2.100,00
        assert bloco["margem_pct"] == "5.05"
        assert bloco["margem_negativa"] is False
        assert (bloco["sem_valor_compra"], bloco["sem_valor_venda"]) == (9, 0)
        assert bloco["legenda_capital"] == "compra e despesas de 3 veículos"
        assert bloco["legenda_custo_medio"] == "3 veículos na conta"
        assert bloco["margem_texto"] == "R$ 2.100,00"
        assert bloco["legenda_margem"] == "5,05% sobre o valor de venda"
        assert bloco["avisos"] == ["9 veículos sem valor de compra não entram na conta."]
    assert _inicio(seed, "Rodrigo")["estoque_a_venda"]["subtitulo"] == (
        "12 veículos à venda · Filial Centro"
    )


def test_vei_20_quem_nao_ve_o_bloco(seed):  # noqa: F811
    for quem in ("Bruna", "Lúcia", "João"):
        inicio = _inicio(seed, quem)
        assert "estoque_a_venda" not in inicio, quem
        assert "ticket_medio" not in inicio, quem


def test_vei_20_so_o_pvg_com_compra_e_margem_negativa(seed):  # noqa: F811
    Veiculo.objects.filter(placa__in=["PVE1A07", "PVF2B18"]).update(valor_compra_centavos=None)
    bloco = relatorios_selectors._estoque_a_venda(_escopo_da_filial())
    assert bloco["capital_imobilizado_centavos"] == 1395000
    assert bloco["custo_medio_centavos"] == 1395000
    assert (bloco["margem_centavos"], bloco["margem_pct"]) == (-75000, Decimal("-5.68"))
    assert bloco["margem_negativa"] is True
    assert bloco["margem_texto"] == "−R$ 750,00"
    assert bloco["legenda_margem"] == "−5,68% sobre o valor de venda"
    assert bloco["legenda_capital"] == "compra e despesas de 1 veículo"
    assert bloco["legenda_custo_medio"] == "1 veículo na conta"
    assert bloco["avisos"] == ["11 veículos sem valor de compra não entram na conta."]


def test_vei_20_com_compra_e_sem_valor_de_venda(seed):  # noqa: F811
    Veiculo.objects.filter(placa="PVF2B18").update(valor_venda_centavos=None)
    bloco = relatorios_selectors._estoque_a_venda(_escopo_da_filial())
    assert bloco["capital_imobilizado_centavos"] == 3950000  # entra no capital
    assert bloco["custo_medio_centavos"] == 1316667
    assert bloco["margem_centavos"] == 125000 - 75000  # fora da margem
    assert bloco["margem_pct"] == Decimal("1.92")  # 50.000 ÷ 2.610.000
    assert bloco["avisos"] == [
        "9 veículos sem valor de compra não entram na conta.",
        "1 veículo sem valor de venda.",
    ]


def test_vei_20_nenhum_com_valor_de_compra(seed):  # noqa: F811
    Veiculo.objects.filter(status="a_venda").update(valor_compra_centavos=None)
    bloco = relatorios_selectors._estoque_a_venda(_escopo_da_filial())
    assert bloco["capital_imobilizado_centavos"] == 0
    assert (bloco["custo_medio_centavos"], bloco["margem_centavos"], bloco["margem_pct"]) == (
        None,
        None,
        None,
    )
    assert bloco["legenda_capital"] == "Nenhum veículo à venda com valor de compra."
    assert bloco["legenda_custo_medio"] is None
    vazio = veiculos_selectors.estoque_a_venda([])
    assert (vazio["quantidade"], vazio["capital_imobilizado_centavos"]) == (0, 0)


def test_vei_20_compra_zero_e_valor_informado(seed):  # noqa: F811
    Veiculo.objects.filter(placa="PVF2B18").update(valor_compra_centavos=0)
    bloco = veiculos_selectors.estoque_a_venda(_escopo_da_filial().filiais)
    assert bloco["veiculos_na_conta"] == 3
    assert bloco["capital_imobilizado_centavos"] == 1165000 + 0 + 1395000


def _escopo_da_filial() -> Any:
    filial = _veiculo("PVE1A07").filial_id
    return relatorios_selectors.Escopo(filiais=frozenset({filial}), todas=False)


# --- VEN-12: ticket médio do mês ---


def test_ven_12_sem_vendas_ate_o_fluxo_de_venda(seed):  # noqa: F811
    """A venda da quitação (VEN-11) não conta; sem venda concluída do fluxo, "Sem vendas"."""
    for quem in ("Mariana", "Rodrigo"):
        bloco = _inicio(seed, quem)["ticket_medio"]
        assert bloco["vazio"] == "Sem vendas em outubro."
        assert (bloco["vendas"], bloco["ticket_centavos"], bloco["variacao_pct"]) == (0, None, None)
        assert bloco["comparacao"] is None
        assert bloco["subtitulo"] == "Vendas de outubro · Filial Centro"


def test_ven_12_ticket_e_variacao_com_o_mes_anterior(seed, monkeypatch):  # noqa: F811
    """Os números da tela de referência: 4 vendas, R$ 31.200,00, ticket R$ 7.800,00; setembro
    com ticket R$ 13.750,00: −43,27%."""
    vendas = {10: (4, 3120000), 9: (2, 2750000)}

    def vendidas_entre(filiais: Any, inicio: Any, fim: Any) -> tuple[int, int]:
        return vendas.get(inicio.month, (0, 0))

    monkeypatch.setattr(relatorios_selectors.vendas_selectors, "vendidas_entre", vendidas_entre)
    bloco = relatorios_selectors._ticket_medio(_escopo_da_filial())
    assert (bloco["vendas"], bloco["soma_centavos"], bloco["ticket_centavos"]) == (
        4,
        3120000,
        780000,
    )
    assert bloco["resumo"] == "4 vendas · R$ 31.200,00"
    assert bloco["rotulo"] == "Ticket médio de outubro"
    assert bloco["mes_anterior"]["ticket_centavos"] == 1375000
    assert bloco["variacao_pct"] == Decimal("-43.27")
    assert bloco["comparacao"] == "−43,27% em relação a setembro (R$ 13.750,00)"
    assert bloco["vazio"] is None

    vendas.pop(9)
    bloco = relatorios_selectors._ticket_medio(_escopo_da_filial())
    assert bloco["variacao_pct"] is None
    assert bloco["comparacao"] == "Sem vendas em setembro para comparar."

    vendas[10] = (1, 780000)
    assert relatorios_selectors._ticket_medio(_escopo_da_filial())["resumo"] == (
        "1 venda · R$ 7.800,00"
    )
