"""T-127 · Seed parcial da Moto Rápida (`manage.py seed_moto_rapida`).

Roda o comando de verdade (pelos serviços, relógio do seed) e confere os números das regras:
uma empresa, as 5 pessoas, 86 veículos, 42 locações, a LOC-2836 pela LOC-01 e LOC-15, o bloqueio
do Rafael (CLI-05) e que uma segunda rodada não duplica nada.
"""

from decimal import Decimal
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.db import connection, transaction
from django_tenants.utils import tenant_context

from apps.auditoria.models import EventoAuditoria
from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.filiais.models import Filial
from apps.financeiro.models import ContaReceber
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa
from apps.veiculos.models import Categoria, PrecoCategoria, Veiculo
from seed import moto_rapida
from seed.carteira import PASTA

from .apoio import CONTAGENS_FROTA_SEED
from .conftest import cliente


def _semear() -> str:
    saida = StringIO()
    call_command("seed_moto_rapida", stdout=saida)
    connection.set_schema_to_public()
    return saida.getvalue()


def _contagens() -> dict[str, int]:
    empresa = Empresa.objects.get(subdominio="motorapida")
    with tenant_context(empresa):
        return {
            "filiais": Filial.objects.count(),
            "usuarios": Usuario.objects.count(),
            "categorias": Categoria.objects.count(),
            "precos": PrecoCategoria.objects.count(),
            "veiculos": Veiculo.objects.count(),
            "clientes": Cliente.objects.count(),
            "locacoes": Locacao.objects.count(),
            "contas": ContaReceber.objects.count(),
        }


@pytest.fixture(scope="module")
def _seed_do_modulo(django_db_setup, django_db_blocker):
    """Roda o seed uma vez por módulo, numa transação que fica aberta e volta no fim (T-149).

    Cada teste abre o savepoint dele por cima e volta ao estado do seed; quem semeia de novo
    (127_02, 138_08) só escreve dentro do próprio savepoint. Sem commit: nada sobra no banco.
    """
    with django_db_blocker.unblock():
        bloco = transaction.atomic()
        bloco.__enter__()
        try:
            saida = _semear()
        except BaseException:
            transaction.set_rollback(True)
            bloco.__exit__(None, None, None)
            raise
    yield saida
    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        transaction.set_rollback(True)
        bloco.__exit__(None, None, None)


@pytest.fixture
def semeado(db, relogio, planos, _seed_do_modulo):
    return _seed_do_modulo


def test_seed_127_01_cria_a_empresa_de_exemplo(semeado):
    assert "Criado: empresa" in semeado
    assert Empresa.objects.filter(subdominio="motorapida").count() == 1
    empresa = Empresa.objects.get(subdominio="motorapida")
    assert empresa.plano is not None
    assert (empresa.nome_exibicao, empresa.plano.nome) == ("Moto Rápida", "Profissional")
    assert str(empresa.teste_inicio) == "2026-10-07"
    contagens = _contagens()
    assert contagens["filiais"] == 1
    assert contagens["usuarios"] == 5
    assert contagens["categorias"] == 4
    assert contagens["precos"] == 5  # a Street tem o preço de antes de 01 out
    assert contagens["veiculos"] == CONTAGENS_FROTA_SEED["todos"] == 86
    assert contagens["locacoes"] == 42 + 9  # as 42 abertas e uma reserva por veículo reservado
    assert contagens["clientes"] == 42 + 9


def test_seed_127_02_roda_duas_vezes_sem_duplicar(semeado):
    antes = _contagens()
    segunda = _semear()
    assert "Criado: nada novo" in segunda
    assert _contagens() == antes


def test_seed_127_03_pessoas_entram_pela_api(semeado):
    for email in ("bruna@motorapida.com.br", "joao@motorapida.com.br", "rodrigo@motorapida.com.br"):
        resposta = cliente("motorapida.localhost").post(
            "/api/auth/entrar/",
            {"email": email, "senha": moto_rapida.SENHA_DEV},
            format="json",
        )
        assert resposta.status_code == 200, (email, resposta.json())
        assert "access" in resposta.json()


def test_seed_127_04_administradora_pede_o_codigo_de_2_etapas(semeado):
    mariana = "mariana@motorapida.com.br"
    codigo = moto_rapida.codigo_de_2fa(mariana)
    resposta = cliente("motorapida.localhost").post(
        "/api/auth/entrar/",
        {"email": mariana, "senha": moto_rapida.SENHA_DEV, "codigo": codigo},
        format="json",
    )
    assert resposta.status_code == 200, resposta.json()


def test_loc_15_seed_127_05_loc_2836_pela_tabela_de_01_out(semeado):
    empresa = Empresa.objects.get(subdominio="motorapida")
    with tenant_context(empresa):
        locacao = Locacao.objects.get(codigo="LOC-2836")
        assert locacao.status == "ativa"
        assert locacao.fim_previsto.isoformat() == "2026-10-14T21:00:00+00:00"  # 14 out 18:00 SP
        contas = ContaReceber.objects.filter(origem_codigo="LOC-2836").order_by(
            "tipo", "vencimento"
        )
        assert [(c.tipo, c.valor_centavos, c.status) for c in contas] == [
            ("caucao", 30000, "paga"),
            ("parcela", 32900, "paga"),
            ("parcela", 32900, "paga"),
        ]
        assert sum(c.valor_centavos for c in contas) == 95800  # R$ 958,00 (LOC-05)


def test_cli_05_seed_127_06_rafael_bloqueado_com_loc_2790_atrasada(semeado):
    empresa = Empresa.objects.get(subdominio="motorapida")
    with tenant_context(empresa):
        assert Cliente.objects.get(nome="Rafael Sousa").status == "bloqueado"
        assert Locacao.objects.get(codigo="LOC-2790").status == "devolucao_atrasada"
        assert Decimal(Veiculo.objects.filter(status="alugado").count()) == 42


def test_seed_127_07_copia_dos_csv_igual_a_docs():
    docs = Path(__file__).resolve().parents[3] / "docs" / "qa" / "carteira-outubro"
    if not docs.exists():
        pytest.skip("docs/ não está montada neste ambiente")
    for arquivo in ("locacoes.csv", "parcelas.csv"):
        assert (PASTA / arquivo).read_bytes() == (docs / arquivo).read_bytes(), arquivo


def _no_tenant():
    return tenant_context(Empresa.objects.get(subdominio="motorapida"))


def test_seed_138_01_reservado_tem_locacao_aguardando_retirada(semeado):
    """D-01: cada `reservado` tem uma locação `aguardando_retirada`; o Kwid é a LOC-2857."""
    with _no_tenant():
        reservados = Veiculo.objects.filter(status="reservado")
        assert reservados.count() == 9
        for veiculo in reservados:
            locacao = Locacao.objects.get(veiculo=veiculo, status="aguardando_retirada")
            assert locacao.inicio.date().isoformat() > "2026-10-07"
        assert Locacao.objects.get(veiculo__placa="RHT9F02").codigo == "LOC-2857"
        assert Locacao.objects.filter(status="aguardando_retirada").count() == 9


def test_loc_05_seed_138_02_planos_e_valores_da_tabela(semeado):
    """D-05: o período de cada locação é o da tabela (LOC-01); só a conta da LOC-2790 é dada."""
    with _no_tenant():
        rafael = Locacao.objects.get(codigo="LOC-2790")
        assert (rafael.periodicidade, rafael.valor_periodo_centavos) == ("semanal", 29940)
        assert rafael.diaria_centavos == 4490
        conta = ContaReceber.objects.get(origem_codigo="LOC-2790")
        assert (conta.valor_centavos, conta.status) == (134700, "aberta")


def test_cli_03_seed_138_03_so_o_rafael_com_cadastro_incompleto(semeado):
    """D-07: os demais clientes têm os 4 documentos e saem de `incompleto`."""
    with _no_tenant():
        assert Cliente.objects.filter(status="incompleto").count() == 0
        rafael = Cliente.objects.get(nome="Rafael Sousa")
        assert (rafael.status, rafael.documentos.count()) == ("bloqueado", 0)
        outros = Cliente.objects.exclude(pk=rafael.pk)
        assert all(c.documentos.filter(ativo=True).count() == 4 for c in outros)


def test_seed_138_04_nomes_e_placas_menos_genericos(semeado):
    """D-08, D-09: sem "Cliente NN" nem placa GEN; as placas das telas nas locações citadas."""
    with _no_tenant():
        assert not Cliente.objects.filter(nome__startswith="Cliente ").exists()
        assert not Veiculo.objects.filter(placa__startswith="GEN").exists()
        placas = {
            "LOC-2790": "PQD6E21",
            "LOC-2812": "SBC0J44",
            "LOC-2848": "RKP3D26",
            "LOC-2850": "RJD5B38",
            "LOC-2856": "SAK1D39",
        }
        for codigo, placa in placas.items():
            assert Locacao.objects.get(codigo=codigo).veiculo.placa == placa
        assert Veiculo.objects.filter(status="alugado").count() == 42


def test_loc_05_seed_138_05_parcela_1_nao_nasce_atrasada(semeado):
    """D-21: a 1ª parcela das locações ativas está paga; só a conta dada da LOC-2790 não."""
    with _no_tenant():
        abertas = ContaReceber.objects.filter(
            tipo="parcela", numero_parcela=1, origem_tipo="locacao"
        ).exclude(status="paga")
        codigos = {c.origem_codigo for c in abertas}
        reservas = set(
            Locacao.objects.filter(status="aguardando_retirada").values_list("codigo", flat=True)
        )
        assert codigos - reservas == {"LOC-2790"}


def test_seed_138_06_locacoes_divididas_entre_vendedores(semeado):
    """D-24: a Bruna e o Rodrigo vendem; a Bruna fica com as locações das telas."""
    with _no_tenant():
        vendedores = set(Locacao.objects.values_list("vendedor__email", flat=True))
        assert vendedores == {"bruna@motorapida.com.br", "rodrigo@motorapida.com.br"}
        assert Locacao.objects.get(codigo="LOC-2836").vendedor.email == "bruna@motorapida.com.br"


def test_seed_138_07_historico_da_loc_2836_nas_datas_do_caso(semeado):
    """D-13: os eventos da locação levam o momento do relógio do seed, não a hora do seed rodar."""
    with _no_tenant():
        locacao = Locacao.objects.get(codigo="LOC-2836")
        eventos = EventoAuditoria.objects.filter(
            objeto_tipo__icontains="locacao", objeto_id=locacao.pk
        )
        dias = {
            e.ocorrido_em.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
            for e in eventos
        }
        assert dias and dias <= {"2026-10-01", "2026-10-07"}


def test_plt_08_seed_138_08_dono_da_plataforma_e_outras_empresas(semeado):
    """Dono no público com 2 etapas e 4 empresas; ativa e inadimplente pelas transições."""
    from apps.contas.models import Autenticador

    dono = Usuario.objects.get(email="dono@giro.example")
    assert (dono.funcao_plataforma, dono.status) == ("dono", "ativo")
    assert Autenticador.objects.filter(user=dono, confirmed=True).exists()
    estados = dict(
        Empresa.objects.exclude(subdominio="motorapida")
        .exclude(subdominio=None)
        .values_list("subdominio", "status")
    )
    assert estados["pedalada"] == "ativa"
    assert estados["rodavida"] == "inadimplente"
    assert set(estados) == {"pedalada", "rodavida", "ventosul", "estradafacil"}
    depois = _semear()
    assert "Criado: nada novo" in depois


def test_adr_0021_painel_do_seed_com_a_data_de_referencia(db, planos, _seed_do_modulo):
    """T-142: com o relógio real e GIRO_DATA_REFERENCIA em 07 out (sem a fixture `relogio`), o
    painel do financeiro mostra o mesmo que com o relógio congelado: em atraso R$ 1.646,40 em 2
    clientes, como nas regras. O "entra hoje" fica em R$ 299,40 (1 parcela), e não nos
    R$ 2.625,80 das regras, porque o seed paga as parcelas que venceriam até 07 out (T-138,
    D-21); com a data ligada, esse contorno pode sair do seed (qa)."""
    from datetime import date

    from django.test import override_settings

    from comum.autenticacao import AMR_SENHA_E_CODIGO, emitir_tokens

    empresa = Empresa.objects.get(subdominio="motorapida")
    with override_settings(GIRO_DATA_REFERENCIA=date(2026, 10, 7)):
        with tenant_context(empresa):
            lucia = Usuario.objects.get(email="lucia@motorapida.com.br")
            token = str(emitir_tokens(lucia, AMR_SENHA_E_CODIGO).access_token)
        resposta = cliente("motorapida.localhost", token).get("/api/painel/inicio/")
    assert resposta.status_code == 200, resposta.json()
    assert resposta["X-Giro-Data-Simulada"] == "2026-10-07"
    kpis = {kpi["chave"]: kpi for kpi in resposta.json()["kpis"]}
    assert kpis["em_atraso"]["valor"] == {"tipo": "centavos", "valor": 164640}
    assert kpis["em_atraso"]["contexto"] == "2 clientes"
    assert kpis["entra_hoje"]["valor"] == {"tipo": "centavos", "valor": 29940}
