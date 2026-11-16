"""T-476 · Demonstração da Moto Rápida numa empresa existente (`carregar_demo_moto_rapida`).

A empresa nasce como em produção (`criar_empresa`, só o administrador convidado). O comando carrega
os dados de negócio do seed sem criar conta, não duplica na segunda rodada, recusa empresa que não é
de demonstração e anda as datas até hoje sem mudar os valores de `dados-de-teste.md`.
"""

from datetime import date
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context, tenant_context

from apps.clientes.models import Cliente
from apps.contas.models import Usuario
from apps.filiais.models import Filial
from apps.financeiro.models import ContaReceber, Despesa
from apps.locacoes.models import Locacao
from apps.veiculos.models import Veiculo


def _carregar(confirmar: str = "motorapida") -> str:
    saida = StringIO()
    call_command("carregar_demo_moto_rapida", "--confirmar", confirmar, stdout=saida)
    connection.set_schema_to_public()
    return saida.getvalue()


def _contagens(empresa) -> dict[str, int]:
    with tenant_context(empresa):
        return {
            "usuarios": Usuario.objects.count(),
            "filiais": Filial.objects.count(),
            "veiculos": Veiculo.objects.count(),
            "clientes": Cliente.objects.count(),
            "locacoes": Locacao.objects.count(),
            "contas": ContaReceber.objects.count(),
            "despesas": Despesa.objects.count(),
        }


def _com_senha() -> int:
    return sum(1 for u in Usuario.objects.all() if u.has_usable_password())


@pytest.fixture
def empresa(criar_empresa):
    return criar_empresa()


def test_t476_demo_sem_contas_com_senha(empresa):
    with schema_context(get_public_schema_name()):
        publico_antes = (Usuario.objects.count(), _com_senha())
    with tenant_context(empresa):
        administrador = Usuario.objects.get()
        assert _com_senha() == 0

    assert "Criado:" in _carregar()
    primeira = _contagens(empresa)
    with tenant_context(empresa):
        assert list(Usuario.objects.values_list("pk", flat=True)) == [administrador.pk]
        assert _com_senha() == 0
        assert set(Locacao.objects.values_list("vendedor_id", flat=True)) == {administrador.pk}
    with schema_context(get_public_schema_name()):
        assert (Usuario.objects.count(), _com_senha()) == publico_antes

    assert "nada novo" in _carregar()
    assert _contagens(empresa) == primeira


def test_t476_totais_de_dados_de_teste(empresa):
    _carregar()
    contagens = _contagens(empresa)
    assert contagens["filiais"] == 1
    assert contagens["veiculos"] == 86
    assert contagens["locacoes"] == 42 + 9  # 42 abertas e uma reserva por veículo reservado
    assert contagens["clientes"] == 42 + 9
    with tenant_context(empresa):
        despesas = dict(Despesa.objects.values_list("descricao", "valor_centavos"))
        assert despesas["Rastreadores (86)"] == 172000
        assert despesas["Aluguel do ponto"] == 350000
        assert despesas["Pneus (2)"] == 120000
        assert Despesa.objects.get(descricao="Pneus (2)").data == date(2026, 10, 7)


def test_t476_datas_andam_ate_hoje(empresa, relogio):
    with tenant_context(empresa):
        criado_em = Usuario.objects.get().criado_em
    relogio.em("2026-11-14 10:00")  # 38 dias depois de 07 out
    assert "38 dias" in _carregar()
    with tenant_context(empresa):
        pneus = Despesa.objects.get(descricao="Pneus (2)")
        assert (pneus.data, pneus.valor_centavos) == (date(2026, 11, 14), 120000)
        assert Usuario.objects.get().criado_em == criado_em  # o que já existia não anda


def test_t476_recusa_sem_confirmacao_e_com_outro_usuario(empresa):
    with pytest.raises(CommandError, match="--confirmar motorapida"):
        _carregar("outra")
    with tenant_context(empresa):
        Usuario.objects.create(email="extra@motorapida.com.br", nome="Extra", perfil="vendedor")
    connection.set_schema_to_public()
    with pytest.raises(CommandError, match="único usuário"):
        _carregar()
    with tenant_context(empresa):
        assert not Veiculo.objects.exists()


def test_t476_recusa_empresa_com_dados_de_verdade(empresa):
    with tenant_context(empresa):
        Filial.objects.create(nome="Filial Própria", nome_curto="Própria")
    connection.set_schema_to_public()
    with pytest.raises(CommandError, match="já tem dados"):
        _carregar()
