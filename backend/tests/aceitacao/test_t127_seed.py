"""T-127 · Seed parcial da Moto Rápida (`manage.py seed_moto_rapida`).

Roda o comando de verdade (pelos serviços, relógio do seed) e confere os números das regras:
uma empresa, as 5 pessoas, 86 veículos, 42 locações, a LOC-2836 pela LOC-01 e LOC-15, o bloqueio
do Rafael (CLI-05) e que uma segunda rodada não duplica nada.
"""

from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import tenant_context

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


@pytest.fixture
def semeado(db, relogio, planos):
    return _semear()


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
    assert contagens["locacoes"] == 42
    assert contagens["clientes"] == 42


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
