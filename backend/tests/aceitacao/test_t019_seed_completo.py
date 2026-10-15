"""T-019 · Seed Moto Rápida completo (docs/qa/criterios/T-019.md, CA-019-01 a 31).

Roda sobre o banco que o `seed_moto_rapida` deixa (uma vez por módulo, T-149), sem montar cenário:
cada teste pede à API ou ao serviço o número da regra e compara. O estado de referência é 07 out
2026 às 12:00 (relógio do teste, igual a `GIRO_DATA_REFERENCIA=2026-10-07` da ADR 0021); os casos
de outras datas movem o relógio dentro do próprio teste, que desfaz tudo no fim.

Casos que dependem de módulo que não existe (vendas, comissões, conciliação, DRE, manutenção)
ficam `xfail(strict)` com a tarefa que os destrava.
"""

import csv
from datetime import date, datetime
from importlib import import_module
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django_tenants.utils import get_public_schema_name, schema_context, tenant_context

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente
from apps.clientes.services import buscar_por_hash
from apps.contas.models import Usuario
from apps.contratos.marcadores import tem_clausula_juros
from apps.contratos.models import ModeloContrato
from apps.empresas.models import ConfiguracaoEmpresa
from apps.filiais.models import Filial
from apps.financeiro import leituras as financeiro_leituras
from apps.financeiro.models import Caixa, ContaReceber, Despesa, Reembolso
from apps.locacoes.models import Locacao, PlanoEspecial
from apps.plataforma.models import Empresa, UsoEmpresa
from apps.veiculos.models import Categoria, PrecoCategoria, Veiculo
from apps.vistorias.models import Devolucao, Vistoria
from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens
from seed.carteira import PASTA, pessoa

from .conftest import cliente as cliente_http
from .test_t016_vistorias import (
    LISTA,
    _abrir_devolucao,
    _aprovar_encerramento,
    _caucao_da_troca,
    _chegada,
    _conta_do_saldo,
    _encerrar,
    _forma,
    _ir_para,
    _item,
    _km_de_volta,
    _parcelas_do_acerto,
    _troca_pedida,
    _valor_do_item,
    _ver,
    _vistoriar,
)
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures

CONTAS = "/api/financeiro/contas-receber/"
CAIXAS = "/api/financeiro/caixas/"
HOST = "motorapida.localhost"
FUSO = ZoneInfo("America/Sao_Paulo")
EMAILS = {
    "Mariana": "mariana@motorapida.com.br",
    "Rodrigo": "rodrigo@motorapida.com.br",
    "Bruna": "bruna@motorapida.com.br",
    "João": "joao@motorapida.com.br",
    "Lúcia": "lucia@motorapida.com.br",
}


class _Moto:
    """O que os apoios da T-016 pedem de `cenario.moto`: `api(nome)` e `_tokens`. O token sai a
    cada chamada, com o relógio do momento (não vence ao mudar de dia)."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def api(self, nome: str = "Mariana", **cabecalhos: str) -> Any:
        usuario = Usuario.objects.get(email=EMAILS[nome])
        token = str(emitir_tokens(usuario, AMR_SENHA_E_CODIGO).access_token)
        api = cliente_http(HOST, token)
        if cabecalhos:
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}", **cabecalhos)
        return api


class _Cenario:
    def __init__(self) -> None:
        self.moto = _Moto()

    def detalhe(self, locacao_id: int, quem: str = "Bruna") -> dict[str, Any]:
        resposta = self.moto.api(quem).get(f"{LISTA}{locacao_id}/")
        assert resposta.status_code == 200, resposta.json()
        return dict(resposta.json())


@pytest.fixture
def seed(semeado, relogio):  # noqa: F811
    """O seed pronto, o relógio em 07 out 12:00 e o schema da Moto Rápida."""
    relogio.em("2026-10-07 12:00")
    with tenant_context(Empresa.objects.get(subdominio="motorapida")):
        yield _Cenario()


def _api(seed: Any, nome: str = "Mariana", **cabecalhos: str) -> Any:
    return seed.moto.api(nome, **cabecalhos)


def _loc(codigo: str) -> Locacao:
    return Locacao.objects.select_related("cliente", "veiculo").get(codigo=codigo)


def _contas(codigo: str, tipo: str = "parcela") -> list[ContaReceber]:
    return list(
        ContaReceber.objects.filter(origem_codigo=codigo, tipo=tipo).order_by("vencimento", "pk")
    )


def _sp(momento: datetime | None) -> str:
    if momento is None:
        raise AssertionError("momento ausente")
    return momento.astimezone(FUSO).strftime("%Y-%m-%d %H:%M")


# --- Empresa, pessoas e plataforma ---


def test_plt_01_seed_019_03_empresa(seed):
    empresa = Empresa.objects.get(subdominio="motorapida")
    assert (empresa.razao_social, empresa.cnpj, empresa.status) == (
        "Moto Rápida Locações Ltda",
        "12345678000195",
        "em_teste",
    )
    assert empresa.plano is not None and empresa.plano.nome == "Profissional"
    assert (str(empresa.teste_inicio), str(empresa.teste_fim)) == ("2026-10-07", "2026-10-21")
    centro = Filial.objects.get()
    assert (centro.nome, centro.matriz, centro.cidade, centro.uf) == (
        "Filial Centro",
        True,
        "Fortaleza",
        "CE",
    )
    resumo = _api(seed).get(f"/api/filiais/{centro.pk}/").json()["horario_resumo"]
    assert resumo == "seg a sex 8h–18h · sáb 8h–12h"


def test_usr_01_seed_019_04_as_5_pessoas_ativas(seed):
    pessoas = Usuario.objects.all()
    assert {(u.nome, u.perfil, u.status) for u in pessoas} == {
        ("Mariana Costa", "administrador", "ativo"),
        ("Rodrigo Pinheiro", "gerente", "ativo"),
        ("Bruna Alves", "vendedor", "ativo"),
        ("João Silva", "vistoriador", "ativo"),
        ("Lúcia Freitas", "financeiro", "ativo"),
    }
    assert not pessoas.filter(status="convite_pendente").exists()


def test_plt_03_seed_019_05_uso_do_plano(seed):
    uso = UsoEmpresa.objects.get(empresa__subdominio="motorapida")
    assert (uso.veiculos, uso.filiais, uso.usuarios) == (86, 1, 5)
    plano = _api(seed).get("/api/filiais/").json()["plano"]
    assert (plano["usado"], plano["limite"], plano["aviso"]) == (1, 3, False)


def test_imp_01_seed_019_06_implantacao_concluida(seed):
    uso = UsoEmpresa.objects.get(empresa__subdominio="motorapida")
    assert set(uso.passos_implantacao) == {
        "conta",
        "marca",
        "filial",
        "ramo",
        "precos",
        "contrato",
        "recebimentos",
        "importar",
        "equipe",
        "primeira_locacao",
    }
    assert _api(seed, "Mariana").get("/api/painel/inicio/").json()["variante"] == "geral"
    modelo = ModeloContrato.objects.get(publicado=True, finalidade="locacao")
    assert tem_clausula_juros(modelo.texto)


def test_plt_01_seed_019_07_plataforma(seed):
    with schema_context(get_public_schema_name()):
        equipe = {
            u.email: (u.nome, u.funcao_plataforma, u.status)
            for u in Usuario.objects.filter(funcao_plataforma__isnull=False)
        }
    assert set(equipe.values()) == {
        ("Dono Giro", "dono", "ativo"),
        ("Diego Santos", "suporte", "ativo"),
        ("Paula Andrade", "financeiro", "ativo"),
        ("Caio Ribeiro", "sucesso", "ativo"),
        ("Larissa Melo", "suporte", "convite_pendente"),
    }
    estados = dict(
        Empresa.objects.exclude(subdominio="motorapida")
        .exclude(subdominio=None)
        .values_list("subdominio", "status")
    )
    assert estados["pedalada"] == "ativa" and estados["rodavida"] == "inadimplente"


# --- Preços e configuração, frota ---


def test_loc_01_seed_019_08_tabela_e_configuracao(seed):
    esperado = {
        "Urbana 110–125": (4490, 29940, 109000, 30000),
        "Street 150–160": (5490, 32900, 119000, 30000),
        "Scooter premium": (7990, 44900, 159000, 50000),
        "Carro compacto": (10900, 64900, 229000, 80000),
    }
    for categoria in Categoria.objects.all():
        preco = categoria.precos.order_by("-vigente_desde").first()
        assert preco is not None
        assert (
            preco.diaria_centavos,
            preco.semanal_centavos,
            preco.mensal_centavos,
            preco.caucao_centavos,
        ) == esperado[categoria.nome]
    street = Categoria.objects.get(nome="Street 150–160")
    assert sorted(
        (str(p.vigente_desde), p.semanal_centavos)
        for p in PrecoCategoria.objects.filter(categoria=street)
    ) == [("2026-09-01", 29940), ("2026-10-01", 32900)]
    entregador = PlanoEspecial.objects.get(nome="Entregador")
    assert (entregador.periodicidade, entregador.preco_centavos) == ("semanal", 27900)
    fidelidade = PlanoEspecial.objects.get(nome="Mensal fidelidade")
    assert (str(fidelidade.desconto_pct), fidelidade.a_partir_do_periodo) == ("10.00", 3)
    config = ConfiguracaoEmpresa.objects.get()
    assert config.tolerancia_atraso_minutos == 60
    assert (str(config.multa_atraso_pct), str(config.juros_mes_pct)) == ("2.00", "1.00")
    assert str(config.desconto_sem_aprovacao_pct) == "5.00"
    assert Filial.objects.get().preco_litro_centavos == 550


def test_vei_01_seed_019_09_frota_de_86(seed):
    total: dict[str, dict[str, int]] = {}
    for veiculo in Veiculo.objects.select_related("categoria"):
        por_status = total.setdefault(veiculo.categoria.nome, {})
        por_status[veiculo.status] = por_status.get(veiculo.status, 0) + 1
    assert total == {
        "Urbana 110–125": {
            "disponivel": 8,
            "reservado": 4,
            "alugado": 20,
            "em_manutencao": 4,
            "a_venda": 6,
        },
        "Street 150–160": {
            "disponivel": 6,
            "reservado": 3,
            "alugado": 16,
            "em_manutencao": 2,
            "a_venda": 5,
        },
        "Scooter premium": {"disponivel": 1, "reservado": 1, "alugado": 3, "a_venda": 1},
        "Carro compacto": {"disponivel": 1, "reservado": 1, "alugado": 3, "em_manutencao": 1},
    }
    assert Veiculo.objects.values("placa").distinct().count() == 86
    assert Veiculo.objects.values("chassi").distinct().count() == 86
    placas = {
        "LOC-2841": "QXA4B21",
        "LOC-2836": "PNB7C04",
        "LOC-2856": "SAK1D39",
        "LOC-2790": "PQD6E21",
        "LOC-2850": "RJD5B38",
        "LOC-2848": "RKP3D26",
        "LOC-2812": "SBC0J44",
        "LOC-2857": "RHT9F02",
    }
    for codigo, placa in placas.items():
        assert _loc(codigo).veiculo.placa == placa


def test_vei_02_seed_019_10_qxa_4b21(seed):
    veiculo = Veiculo.objects.get(placa="QXA4B21")
    assert (veiculo.marca, veiculo.modelo, veiculo.ano_modelo, veiculo.cor) == (
        "Honda",
        "CG 160 Fan",
        2023,
        "vermelha",
    )
    assert (veiculo.chassi, veiculo.status, veiculo.km_atual) == (
        "9C2KC2210PR004401",
        "alugado",
        18950,
    )
    assert veiculo.km_atualizado_em is not None
    assert _sp(veiculo.km_atualizado_em).startswith("2026-09-23")


@pytest.mark.xfail(
    strict=True, raises=ImportError, reason="sem módulo de manutenção: troca de óleo (MAN-03)"
)
def test_man_03_seed_019_10_proxima_troca_de_oleo_aos_19900():
    """Última troca aos 18.900 km, próxima aos 19.900 (faltam 950)."""
    import_module("apps.manutencao.models")


def test_dev_08_seed_019_11_factor_e_nmax(seed):
    factor = Veiculo.objects.get(placa="PNB7C04")
    assert (factor.modelo, str(factor.capacidade_tanque_litros), factor.status) == (
        "Factor 150",
        "16.0",
        "alugado",
    )
    saida = Vistoria.objects.get(locacao__codigo="LOC-2836", tipo="saida")
    assert (saida.km, saida.combustivel, saida.status) == (21870, "cheio", "concluida")
    nmax = Veiculo.objects.filter(modelo="NMax 160")
    assert {str(v.capacidade_tanque_litros) for v in nmax} == {"8.0"}


# --- Clientes ---


def test_cli_03_seed_019_12_os_clientes_das_telas(seed):
    assert Cliente.objects.count() == 51
    nomes = {
        "Juliana Rocha",
        "Carlos Menezes",
        "Rafael Sousa",
        "Lucas Ferreira",
        "Diego Martins",
        "Patrícia Gomes",
        "Marcos Viana",
    }
    assert nomes <= set(Cliente.objects.values_list("nome", flat=True))
    assert not Cliente.objects.filter(nome__startswith="Cliente ").exists()
    juliana = Cliente.objects.get(nome="Juliana Rocha")
    lucas = Cliente.objects.get(nome="Lucas Ferreira")
    assert juliana.documento_hash == buscar_por_hash("05221833018")
    assert lucas.documento_hash == buscar_por_hash("12345678909")
    todos = Cliente.objects.all()
    assert all(c.documentos.filter(ativo=True).count() == 4 for c in todos)
    assert all(c.consentimento_em is not None for c in todos)
    assert set(todos.exclude(nome="Rafael Sousa").values_list("status", flat=True)) == {"ativo"}


def test_cli_05_seed_019_13_bloqueio_do_rafael(seed):
    rafael = Cliente.objects.get(nome="Rafael Sousa")
    assert rafael.status == "bloqueado"
    assert _loc("LOC-2790").status == "devolucao_atrasada"
    evento = EventoAuditoria.objects.filter(
        objeto_tipo__icontains="cliente", objeto_id=rafael.pk, acao__icontains="bloque"
    ).get()
    assert _sp(evento.ocorrido_em).startswith("2026-10-07")
    assert evento.ator_tipo == "sistema"  # o bloqueio automático é a exceção (CA-019-25)


def test_cli_04_seed_019_14_historico_da_analise_em_07_out(seed):
    """Juliana e Lucas `ok`, Carlos e Rafael `problema`, cliente novo `ok`."""

    def situacao(nome: str) -> str:
        historico = financeiro_leituras.montar_historico(Cliente.objects.get(nome=nome))
        assert historico is not None
        return f"{historico['situacao']}: {historico['rotulo']}"

    assert situacao("Juliana Rocha") == "ok: Sem atraso na empresa"
    assert situacao("Lucas Ferreira") == "ok: Sem atraso na empresa"
    assert situacao("Carlos Menezes") == "problema: Conta em atraso na empresa"
    assert situacao("Rafael Sousa") == "problema: Conta em atraso na empresa"
    # O cliente cadastrado hoje, sem conta, é o do caso (nenhum do seed está nessa situação).
    novo = clientes_services.cadastrar(pessoa("Cliente de hoje", "52998224725", "85999990000"))
    assert financeiro_leituras.montar_historico(novo) == {
        "situacao": "ok",
        "rotulo": "Cliente novo na empresa",
    }


def test_fin_01_seed_019_15_em_aberto_dos_clientes(seed):
    corpo = _api(seed, "Rodrigo").get("/api/clientes/").json()
    assert corpo["indicadores"]["em_aberto_total_centavos"] == 164640
    assert corpo["contagens"]["em_aberto"] == 2
    em_aberto = {
        c.nome: financeiro_leituras.em_aberto_centavos(c.pk)
        for c in Cliente.objects.filter(nome__in=("Carlos Menezes", "Rafael Sousa"))
    }
    assert em_aberto == {"Carlos Menezes": 29940, "Rafael Sousa": 134700}


# --- Locações ---


def test_loc_01_seed_019_16_quantas_locacoes(seed):
    assert Locacao.objects.count() == 51
    por_status: dict[str, int] = {}
    for status in Locacao.objects.values_list("status", flat=True):
        por_status[status] = por_status.get(status, 0) + 1
    assert por_status == {"ativa": 41, "devolucao_atrasada": 1, "aguardando_retirada": 9}
    contadores = _api(seed, "Mariana").get("/api/painel/contadores/").json()["contadores"]
    assert contadores["locacoes"] == 51


def test_loc_05_seed_019_17_as_locacoes_das_telas(seed):
    # LOC-2790: conta de R$ 1.347,00 vencida em 12 set.
    assert _loc("LOC-2790").status == "devolucao_atrasada"
    conta = _contas("LOC-2790")[0]
    assert (conta.valor_centavos, conta.vencimento, conta.status) == (
        134700,
        date(2026, 9, 12),
        "aberta",
    )
    # LOC-2812: pedido de encerramento antecipado da Bruna, APR-02 pendente para o Rodrigo.
    patricia = _loc("LOC-2812")
    assert (patricia.status, patricia.valor_periodo_centavos) == ("ativa", 159000)
    pedido = PedidoAprovacao.objects.get(tipo="APR-02", origem_id=patricia.pk)
    assert (pedido.status, pedido.solicitante.nome) == ("pendente", "Bruna Alves")
    assert "multa R$ 84,80" in pedido.detalhe
    assert _api(seed).get(f"{LISTA}{patricia.pk}/").json()["sinais"]["cancelamento_pendente"]
    # LOC-2836: confirmada e retirada em 01 out, parcelas pagas, total R$ 958,00.
    juliana = _loc("LOC-2836")
    assert (juliana.status, _sp(juliana.inicio), _sp(juliana.fim_previsto)) == (
        "ativa",
        "2026-09-30 18:00",
        "2026-10-14 18:00",
    )
    p1, p2 = _contas("LOC-2836")
    assert (p1.vencimento, p1.multa_centavos, p1.status) == (date(2026, 9, 30), 0, "paga")
    assert p1.pago_em is not None and _sp(p1.pago_em).startswith("2026-10-01")
    assert p2.pago_em is not None and _sp(p2.pago_em) == "2026-10-07 08:02"
    assert sum(c.valor_centavos for c in ContaReceber.objects.filter(origem_codigo="LOC-2836")) == (
        95800
    )
    # LOC-2841: parcela 1 paga, 2 atrasada, 3 vence hoje, 4 e 5 a vencer; assinada em 23 set.
    carlos = _loc("LOC-2841")
    assert (carlos.valor_periodo_centavos, _sp(carlos.inicio), _sp(carlos.fim_previsto)) == (
        29940,
        "2026-09-23 09:00",
        "2026-10-28 09:00",
    )
    assert [(c.vencimento.isoformat()[5:], c.status) for c in _contas("LOC-2841")] == [
        ("09-23", "paga"),
        ("09-30", "aberta"),
        ("10-07", "aberta"),
        ("10-14", "aberta"),
        ("10-21", "aberta"),
    ]
    assert _api(seed).get(f"{LISTA}{carlos.pk}/").json()["sinais"]["pagamento_atrasado"]
    # LOC-2848: 3 diárias pagas em 06 out e a renovação paga no cartão às 08:40.
    diego = _contas("LOC-2848")
    assert [(c.valor_centavos, c.status) for c in diego] == [(32700, "paga"), (10900, "paga")]
    assert diego[1].forma == "cartao_credito"
    assert diego[1].pago_em is not None and _sp(diego[1].pago_em) == "2026-10-07 08:40"
    assert _sp(_loc("LOC-2848").fim_previsto) == "2026-10-10 09:00"
    # LOC-2850 mensal pago; LOC-2856 retirada em 07 out; LOC-2826 diária por Pix às 11:05.
    assert [(c.valor_centavos, c.status) for c in _contas("LOC-2850")] == [(109000, "paga")]
    lucas = _contas("LOC-2856")
    assert [(c.valor_centavos, c.status) for c in lucas] == [(32900, "paga"), (32900, "aberta")]
    assert lucas[0].forma == "dinheiro" and _sp(lucas[0].pago_em) == "2026-10-07 09:15"
    diaria = _contas("LOC-2826")[0]
    assert (diaria.valor_centavos, diaria.forma, _sp(diaria.pago_em)) == (
        4490,
        "pix",
        "2026-10-07 11:05",
    )
    assert _loc("LOC-2857").veiculo.placa == "RHT9F02"
    assert _loc("LOC-2857").status == "aguardando_retirada"


def test_loc_05_seed_019_18_parcelas_de_outubro_iguais_ao_csv(seed):
    """As 35 geradas (e as demais) têm exatamente as parcelas do CSV, com a mesma situação; as
    que começam em 07 out ou depois começaram um período antes, com essa parcela paga."""
    with open(PASTA / "parcelas.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    reservas = Locacao.objects.filter(status="aguardando_retirada").values_list("codigo", flat=True)
    banco = {
        (c.origem_codigo, c.vencimento.isoformat(), c.valor_centavos, c.status == "paga")
        for c in ContaReceber.objects.filter(tipo="parcela", origem_tipo="locacao").exclude(
            origem_codigo__in=list(reservas)
        )
    }
    csv_ = {
        (
            linha["codigo"],
            linha["vencimento"],
            int(linha["valor_centavos"]),
            linha["situacao"] == "paga",
        )
        for linha in linhas
    }
    assert csv_ <= banco
    # O que sobra no banco é a parcela do período anterior das 10 geradas que começam em 07 out
    # ou depois: paga na retirada, vencida antes de 07 out (LOC-05).
    extras = sorted(banco - csv_)
    assert len(extras) == 10, extras
    assert all(pago and vencimento < "2026-10-07" for _, vencimento, _, pago in extras)
    # Nenhuma locação começa depois de 07 out.
    assert (
        not Locacao.objects.exclude(status="aguardando_retirada")
        .filter(inicio__date__gt=date(2026, 10, 7))
        .exists()
    )
    # Das parcelas de 07 out em diante, só as 4 do caixa estão pagas.
    pagas = ContaReceber.objects.filter(
        tipo="parcela", status="paga", vencimento__gte=date(2026, 10, 7)
    ).exclude(
        origem_codigo__in=Locacao.objects.filter(status="aguardando_retirada").values_list(
            "codigo", flat=True
        )
    )
    assert sorted(c.origem_codigo for c in pagas) == [
        "LOC-2826",
        "LOC-2836",
        "LOC-2848",
        "LOC-2856",
    ]
    # LOC-2815: 1º vencimento de outubro em 07 out; começou 30 set com a parcela anterior paga.
    primeira, segunda = _contas("LOC-2815")[:2]
    assert (primeira.vencimento, primeira.status) == (date(2026, 9, 30), "paga")
    assert (segunda.vencimento, segunda.status) == (date(2026, 10, 7), "aberta")
    assert _sp(_loc("LOC-2815").inicio) == "2026-09-30 09:00"


def test_loc_15_seed_019_19_reservas_em_novembro(seed):
    reservas = list(Locacao.objects.filter(status="aguardando_retirada"))
    assert len(reservas) == 9
    assert sorted(_sp(r.inicio)[:10] for r in reservas) == [
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
        "2026-11-09",
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-13",
    ]
    assert {_sp(r.inicio)[11:] for r in reservas} == {"09:00"}
    contas = ContaReceber.objects.filter(origem_codigo__in=[r.codigo for r in reservas])
    assert contas and min(c.vencimento for c in contas) >= date(2026, 11, 3)
    assert _loc("LOC-2857").veiculo.placa == "RHT9F02"


# --- Financeiro ---


def test_fin_15_seed_019_20_contas_a_receber_de_outubro(seed):
    corpo = _api(seed, "Lúcia").get(CONTAS, {"periodo": "mes"}).json()
    i = corpo["indicadores"]
    assert (i["previsto_mes_centavos"], i["previsto_mes_parcelas"]) == (5200210, 128)
    assert (i["recebido_mes_centavos"], i["recebido_pct"]) == (1340170, "25.77")
    assert (i["vence_hoje_centavos"], i["vence_hoje_parcelas"]) == (262580, 6)
    assert (i["em_atraso_centavos"], i["em_atraso_clientes"], i["em_atraso_parcelas"]) == (
        164640,
        2,
        2,
    )
    assert i["faixas"] == {"1_7": 29940, "8_30": 134700, "mais_30": 0}
    assert corpo["contagens"] == {
        "todas": 130,
        "atrasadas": 2,
        "vencem_hoje": 6,
        "a_vencer": 92,
        "pagas": 30,
    }
    a_vencer = _api(seed, "Lúcia").get(
        CONTAS, {"periodo": "mes", "situacao": "a_vencer", "tamanho": 100}
    )
    assert sum(c["valor_centavos"] for c in a_vencer.json()["resultados"]) == 3597460


def test_fin_15_seed_019_21_semana(seed):
    api = _api(seed, "Lúcia")
    corpo = api.get(CONTAS, {"periodo": "semana"}).json()
    assert corpo["contagens"] == {
        "todas": 36,
        "atrasadas": 2,
        "vencem_hoje": 6,
        "a_vencer": 13,
        "pagas": 15,
    }
    a_vencer = api.get(CONTAS, {"periodo": "semana", "situacao": "a_vencer", "tamanho": 100}).json()
    pagas = api.get(CONTAS, {"periodo": "semana", "situacao": "pagas", "tamanho": 100}).json()
    assert sum(c["valor_centavos"] for c in a_vencer["resultados"]) == 573920
    assert sum(c["valor_centavos"] for c in pagas["resultados"]) == 588250
    # A caução do Lucas só aparece com ?cliente= (ou a origem).
    lucas = Cliente.objects.get(nome="Lucas Ferreira")
    geral = api.get(CONTAS, {"periodo": "semana", "tamanho": 100}).json()["resultados"]
    assert not [
        c
        for c in geral
        if c["valor_centavos"] == 30000 and c["cliente"]["nome"] == "Lucas Ferreira"
    ]
    do_lucas = api.get(CONTAS, {"cliente": lucas.pk}).json()["resultados"]
    assert 30000 in [c["valor_centavos"] for c in do_lucas]


def test_fin_07_seed_019_22_caixa_de_07_out(seed):
    corpo = _api(seed, "Bruna").get(f"{CAIXAS}hoje/").json()
    resumo = corpo["resumo"]
    assert (corpo["status"], corpo["aberto_por"]["nome"]) == ("aberto", "Bruna Alves")
    assert (resumo["entrou_hoje_centavos"], resumo["recebimentos"]) == (111190, 5)
    assert resumo["por_forma"]["pix"] == {"centavos": 37390, "quantidade": 2}
    assert resumo["por_forma"]["cartao"]["centavos"] == 10900
    assert resumo["por_forma"]["dinheiro"] == {"centavos": 62900, "quantidade": 2}
    assert resumo["gaveta"] == {
        "troco_centavos": 20000,
        "entradas_dinheiro_centavos": 62900,
        "saidas_dinheiro_centavos": 54800,
        "esperado_centavos": 28100,
    }
    caixa = Caixa.objects.get()
    horas = [
        _sp(e.ocorrido_em)[11:]
        for e in EventoAuditoria.objects.filter(acao__startswith="movimento_caixa").order_by("id")
    ]
    assert horas == ["08:02", "08:40", "09:15", "09:15", "10:30", "11:05", "11:20"]
    abertura = EventoAuditoria.objects.get(acao="caixa.abrir", objeto_id=caixa.pk)
    assert (_sp(abertura.ocorrido_em), abertura.ator_nome) == ("2026-10-07 07:55", "Bruna Alves")
    pagas = ContaReceber.objects.filter(movimento_caixa__isnull=False).order_by("pago_em")
    assert [(c.origem_codigo, c.tipo, c.valor_centavos) for c in pagas] == [
        ("LOC-2836", "parcela", 32900),
        ("LOC-2848", "parcela", 10900),
        ("LOC-2856", "parcela", 32900),
        ("LOC-2856", "caucao", 30000),
        ("LOC-2826", "parcela", 4490),
    ]
    assert _loc("LOC-2856").cliente.nome == "Lucas Ferreira"
    assert _loc("LOC-2848").cliente.nome == "Diego Martins"


def test_fin_05_seed_019_23_despesas_de_outubro(seed):
    linhas = {
        d.descricao: (d.data.isoformat()[5:], d.valor_centavos, d.lancada_por.nome, d.status)
        for d in Despesa.objects.select_related("lancada_por")
    }
    assert linhas == {
        "Pneus (2)": ("10-07", 120000, "João Silva", "aguardando_aprovacao"),
        "Óleo 1 litro": ("10-07", 4800, "Bruna Alves", "paga"),
        "Conta de luz": ("10-06", 41230, "Lúcia Freitas", "a_pagar"),
        "Aluguel do ponto": ("10-05", 350000, "Lúcia Freitas", "paga"),
        "IPVA ROE2A88": ("10-03", 18640, "Lúcia Freitas", "a_pagar"),
        "Rastreadores (86)": ("10-02", 172000, "Lúcia Freitas", "paga"),
    }
    aluguel = Despesa.objects.get(descricao="Aluguel do ponto")
    assert aluguel.forma == "boleto" and _sp(aluguel.pago_em)[:10] == "2026-10-05"
    rastreadores = Despesa.objects.get(descricao="Rastreadores (86)")
    assert rastreadores.forma == "cartao" and _sp(rastreadores.pago_em)[:10] == "2026-10-02"
    oleo = Despesa.objects.get(descricao="Óleo 1 litro")
    assert (
        _sp(oleo.pago_em) == "2026-10-07 11:20"
        and oleo.veiculo_id == Veiculo.objects.get(placa="QXA4B21").pk
    )
    pneus = PedidoAprovacao.objects.get(tipo="APR-03", status="pendente")
    assert (pneus.status, pneus.solicitante.nome) == ("pendente", "João Silva")
    for pedido in PedidoAprovacao.objects.filter(tipo="APR-03", aprovador__isnull=False):
        assert pedido.aprovador_id != pedido.solicitante_id  # APR-09
    corpo = _api(seed, "Lúcia").get("/api/financeiro/despesas/", {"mes": "2026-10"}).json()
    i = corpo["indicadores"]
    assert i["gasto_mes_centavos"] == 706670
    assert (i["aguardando_aprovacao_centavos"], i["aguardando_aprovacao_quantidade"]) == (120000, 1)
    assert i["por_categoria"] == {
        "fixas": 391230,
        "rastreamento": 172000,
        "manutencao": 124800,
        "impostos": 18640,
    }
    ipva = next(d for d in corpo["resultados"] if d["descricao"].startswith("IPVA"))
    assert ipva["status"] == "a_pagar"


def test_fin_16_despesa_por_veiculo_no_seed(seed):
    # CA-DES-01: 706670 ÷ 86 veículos = 8217,09 → 8217. As 6 despesas têm nota (FIN-06).
    corpo = _api(seed, "Lúcia").get("/api/financeiro/despesas/", {"mes": "2026-10"}).json()
    assert corpo["indicadores"]["despesa_por_veiculo_centavos"] == 8217
    assert all(d["nota"] and d["nota"]["url"] for d in corpo["resultados"])
    assert len(corpo["resultados"]) == 6


def test_fin_15_seed_019_24_inicio_e_contadores_em_07_out(seed):
    mariana = _api(seed, "Mariana").get("/api/painel/contadores/").json()["contadores"]
    assert (mariana["receber"], mariana["despesas"], mariana["veiculos"], mariana["locacoes"]) == (
        2,
        1,
        86,
        51,
    )
    pendentes = PedidoAprovacao.objects.filter(status="pendente")
    assert sorted(p.tipo for p in pendentes) == ["APR-02", "APR-03"]
    rodrigo = _api(seed, "Rodrigo").get("/api/painel/contadores/").json()["contadores"]
    assert rodrigo["aprovacoes"] == 2
    lucia = _api(seed, "Lúcia").get("/api/painel/inicio/").json()
    kpis = {k["chave"]: k for k in lucia["kpis"]}
    assert kpis["entra_hoje"]["valor"] == {"tipo": "centavos", "valor": 262580}
    assert kpis["sai_hoje"]["valor"] == {"tipo": "centavos", "valor": 0}
    assert lucia["caixas_do_dia"][0]["esperado_gaveta_centavos"] == 28100
    assert lucia["para_hoje"] == []
    agenda = _api(seed, "João").get("/api/vistorias/agenda/").json()["resultados"]
    # Nada marcado para 07 out; só a devolução atrasada do Rafael (12 set), que a agenda mantém.
    assert [a["horario"][:10] for a in agenda] == ["2026-09-12"]


# --- Auditoria ---


def test_aud_01_seed_019_25_eventos_nas_horas_do_seed(seed):
    confirmacao = EventoAuditoria.objects.filter(
        acao="locacao.confirmar", objeto_codigo="LOC-2836"
    ).get()
    assert _sp(confirmacao.ocorrido_em).startswith("2026-10-01")
    assert confirmacao.ator_nome in {"Bruna Alves", "Rodrigo Pinheiro"}
    sangria = EventoAuditoria.objects.get(acao="movimento_caixa.sangria")
    assert (_sp(sangria.ocorrido_em), sangria.ator_nome) == ("2026-10-07 10:30", "Bruna Alves")
    de_pessoas = EventoAuditoria.objects.filter(
        acao__in=[
            "locacao.confirmar",
            "caixa.abrir",
            "movimento_caixa.sangria",
            "despesa.lancar",
            "despesa.pagar",
            "pedido_aprovacao.aprovar",
        ]
    )
    assert de_pessoas.exists()
    assert set(de_pessoas.values_list("ator_tipo", flat=True)) == {"usuario"}
    quem = dict(
        EventoAuditoria.objects.filter(acao="despesa.lancar").values_list(
            "objeto_codigo", "ator_nome"
        )
    )
    assert quem  # o ator de cada despesa é quem lançou (Bruna, Lúcia, João)
    assert {"Bruna Alves", "Lúcia Freitas", "João Silva"} <= set(
        EventoAuditoria.objects.filter(acao="despesa.lancar").values_list("ator_nome", flat=True)
    )


def test_fin_07_sangria_audita_com_filial_do_caixa(seed):
    """T-150 (CA-019-25): a sangria da Bruna aparece no filtro da Filial Centro."""
    centro = Filial.objects.get()
    corpo = _api(seed, "Mariana").get("/api/auditoria/eventos/", {"filial": centro.pk}).json()
    sangrias = [e for e in corpo["resultados"] if e["acao"] == "movimento_caixa.sangria"]
    assert len(sangrias) == 1
    sangria = sangrias[0]
    assert (sangria["resumo"], sangria["detalhe"]) == (
        "Fez sangria de R$ 500,00",
        "Caixa da Filial Centro",
    )
    assert sangria["ator"]["nome"] == "Bruna Alves"
    assert sangria["objeto"]["filial"] == "Filial Centro"


# --- Casos que rodam sobre o seed ---


def test_dev_02_seed_019_26_devolucao_da_loc_2836_devolve_183(seed, relogio):
    _ir_para(seed, relogio, "2026-10-14 10:00")
    juliana = _loc("LOC-2836")
    detalhe = seed.detalhe(juliana.pk)
    assert detalhe["sinais"]["devolve_hoje"] is True
    agenda = _api(seed, "João").get("/api/vistorias/agenda/").json()["resultados"]
    assert "LOC-2836" in [a["locacao"]["codigo"] for a in agenda]
    _ir_para(seed, relogio, "2026-10-14 18:00")
    devolucao = _abrir_devolucao(seed, juliana.pk)
    corpo = _chegada(
        seed, devolucao, 22500, "tres_quartos", avarias=(("Retrovisor esquerdo riscado", {}),)
    )
    retrovisor = _item(corpo, "avaria")
    assert _valor_do_item(seed, devolucao["id"], retrovisor["id"], 8500).status_code == 200
    assert _forma(seed, devolucao["id"]).status_code == 200
    acerto = _ver(seed, devolucao["id"])["acerto"]
    assert {i["tipo"]: i["valor_centavos"] for i in acerto["itens"]} == {
        "combustivel": 3200,
        "avaria": 8500,
        "atraso": 0,
        "km_excedente": 0,
    }
    assert acerto["resultado"]["botao"] == "Encerrar e devolver R$ 183,00"
    assert _encerrar(seed, devolucao["id"]).status_code == 200
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=devolucao["id"])
    assert (reembolso.valor_centavos, reembolso.forma, reembolso.status) == (
        18300,
        "pix",
        "a_fazer",
    )


def test_loc_09_seed_019_27_troca_de_veiculo_da_loc_2836(seed, relogio):
    juliana = _loc("LOC-2836")
    renovou = _api(seed, "Bruna").post(
        f"{LISTA}{juliana.pk}/renovar/", {"periodos": 1}, format="json"
    )
    assert renovou.status_code == 200, renovou.json()
    _ir_para(seed, relogio, "2026-10-07 18:00")
    nmax = Veiculo.objects.filter(modelo="NMax 160", status="disponivel").order_by("placa").first()
    assert nmax is not None
    troca = _troca_pedida(seed, juliana.pk, nmax)
    devolucao = _abrir_devolucao(seed, juliana.pk)
    resposta = _vistoriar(
        seed, troca["devolucao_vistoria_id"], 22000, "tres_quartos", avarias=("Retrovisor",)
    )
    assert resposta.status_code == 200, resposta.json()
    retrovisor = _item(_ver(seed, devolucao["id"]), "avaria")
    assert _valor_do_item(seed, devolucao["id"], retrovisor["id"], 8500).status_code == 200
    from apps.financeiro import services as financeiro_services

    caucao = _caucao_da_troca(juliana)
    assert caucao.valor_centavos == 20000
    financeiro_services.marcar_paga(caucao, forma="pix")
    assert _vistoriar(seed, troca["saida_vistoria_id"], nmax.km_atual).status_code == 200
    parcela_3 = ContaReceber.objects.get(origem_codigo="LOC-2836", numero_parcela=3)
    assert parcela_3.valor_centavos == 44900
    _ir_para(seed, relogio, "2026-10-14 10:00")
    financeiro_services.marcar_paga(parcela_3, forma="pix")
    _ir_para(seed, relogio, "2026-10-21 18:00")
    corpo = _chegada(seed, _abrir_devolucao(seed, juliana.pk), nmax.km_atual + 400)
    assert corpo["acerto"]["total_cobrancas_centavos"] == 23700
    assert corpo["acerto"]["resultado"]["valor_centavos"] == 26300
    assert _forma(seed, corpo["id"]).status_code == 200
    assert _encerrar(seed, corpo["id"]).status_code == 200
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=corpo["id"])
    assert (reembolso.valor_centavos, reembolso.forma) == (26300, "pix")
    assert Devolucao.objects.filter(locacao=juliana).count() == 1


def test_loc_12_seed_019_28_encerramento_antecipado_da_loc_2812(seed):
    patricia = _loc("LOC-2812")
    pedido = PedidoAprovacao.objects.get(tipo="APR-02", origem_id=patricia.pk)
    resposta = _api(seed, "Rodrigo").post(
        f"/api/aprovacoes/{pedido.pk}/aprovar/", {}, format="json"
    )
    assert resposta.status_code == 200, resposta.json()
    devolucao = _abrir_devolucao(seed, patricia.pk)
    corpo = _chegada(seed, devolucao, _km_de_volta(patricia))
    acerto = corpo["acerto"]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 8480
    assert acerto["saldo_centavos"] == 78620
    assert acerto["resultado"]["texto"] == "Devolve a caução de R$ 500,00 e mais R$ 286,20"
    assert _encerrar(seed, devolucao["id"]).status_code == 200
    reembolso = Reembolso.objects.get(origem_tipo="devolucao", origem_id=devolucao["id"])
    assert reembolso.valor_centavos == 78620


def _carlos_devolvido_em(seed: Any, relogio: Any, quando: str) -> tuple[Locacao, dict[str, Any]]:
    carlos = _loc("LOC-2841")
    _aprovar_encerramento(seed, carlos)  # Rodrigo cancela direto, em 07 out
    _ir_para(seed, relogio, quando)
    corpo = _chegada(seed, _abrir_devolucao(seed, carlos.pk), _km_de_volta(carlos))
    return carlos, corpo


def test_dev_07_seed_019_29_loc_2841_devolvida_em_07_out(seed, relogio):
    _, corpo = _carlos_devolvido_em(seed, relogio, "2026-10-07 12:00")
    p2, p3 = (ContaReceber.objects.get(origem_codigo="LOC-2841", numero_parcela=n) for n in (2, 3))
    assert _parcelas_do_acerto(corpo) == [(30609, p2.pk), (29940, p3.pk)]
    assert _item(corpo, "multa_encerramento")["valor_centavos"] == 5988
    assert corpo["acerto"]["resultado"]["botao"] == "Encerrar e cobrar R$ 365,37"
    assert _encerrar(seed, corpo["id"]).status_code == 200
    assert _conta_do_saldo(corpo["id"]).valor_centavos == 36537


def test_dev_07_seed_019_29_loc_2841_devolvida_em_16_out(seed, relogio):
    _, corpo = _carlos_devolvido_em(seed, relogio, "2026-10-16 10:00")
    assert [v for v, _ in _parcelas_do_acerto(corpo)] == [30699, 30629, 30559]
    assert corpo["acerto"]["resultado"]["botao"] == "Encerrar e cobrar R$ 673,77"


def test_dev_07_seed_019_29_loc_2841_devolvida_no_fim_previsto(seed, relogio):
    _, corpo = _carlos_devolvido_em(seed, relogio, "2026-10-28 09:00")
    assert [v for v, _ in _parcelas_do_acerto(corpo)] == [30818, 30749, 30679, 30609]
    assert corpo["acerto"]["resultado"]["botao"] == "Encerrar e cobrar R$ 928,55"
    resposta = _encerrar(seed, corpo["id"])
    assert resposta.json()["locacao"]["status"] == "encerrada"


def test_dev_07_seed_019_29_loc_2841_devolvida_depois_do_fim_previsto(seed, relogio):
    _, corpo = _carlos_devolvido_em(seed, relogio, "2026-10-30 09:00")
    assert [v for v, _ in _parcelas_do_acerto(corpo)] == [30838, 30769, 30699, 30629]
    assert _item(corpo, "atraso")["valor_centavos"] == 10980
    assert corpo["acerto"]["saldo_centavos"] == -103915


def test_fin_03_seed_019_30_multa_e_juros_no_caixa(seed):
    api = _api(seed, "Bruna")
    carlos = ContaReceber.objects.get(origem_codigo="LOC-2841", vencimento=date(2026, 9, 30))
    rafael = ContaReceber.objects.get(origem_codigo="LOC-2790")
    pago = api.post(
        f"{CONTAS}{carlos.pk}/receber/",
        {"forma": "cartao_debito", "valor_centavos": 30609},
        format="json",
    )
    assert pago.status_code == 200, pago.json()
    carlos.refresh_from_db()
    assert (carlos.multa_centavos, carlos.juros_centavos) == (599, 70)
    pago = api.post(
        f"{CONTAS}{rafael.pk}/receber/",
        {"forma": "dinheiro", "valor_centavos": 138517},
        format="json",
    )
    assert pago.status_code == 200, pago.json()
    rafael.refresh_from_db()
    assert (rafael.multa_centavos, rafael.juros_centavos) == (2694, 1123)
    # CLI-05: desbloqueia sozinho; com os 4 documentos volta `ativo` (CA-019-30).
    assert Cliente.objects.get(nome="Rafael Sousa").status == "ativo"


# --- Fase 2: sem módulo no backend (CA-019-31) ---

SEM_VENDAS = "módulo de vendas ainda não existe (apps/vendas é só README; VEN-02, VEN-04)"


@pytest.mark.xfail(strict=True, raises=ImportError, reason=SEM_VENDAS)
def test_ven_02_seed_019_31_venda_ven_0177():
    """Tabela 22.900,00, desconto 8%, entrada 5.000,00, 12 parcelas: final 21.068,00,
    12 × 1.339,00 e vai para aprovação."""
    from apps.vendas import services  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason=SEM_VENDAS)
def test_fin_09_seed_019_31_comissao_da_venda_ven_0177():
    """3% de 21.068,00 = R$ 632,04 pendente; outubro R$ 968,00; setembro R$ 1.890,00."""
    from apps.vendas import services  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason="sem módulo de conciliação (FIN-12)")
def test_fin_12_seed_019_31_conciliacao_diferenca_de_137_10():
    from apps.financeiro import conciliacao  # noqa: F401


@pytest.mark.xfail(strict=True, raises=ImportError, reason="sem selector da DRE (FIN-13)")
def test_fin_13_seed_019_31_dre_de_setembro_34231_30():
    from apps.relatorios.selectors import dre  # noqa: F401
