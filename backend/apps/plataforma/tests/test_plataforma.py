"""Serviços e selectors da plataforma fora dos critérios de aceite (PLT-01, PLT-03, IMP-05)."""

from datetime import date, timedelta

import pytest

from apps.plataforma import selectors, services
from apps.plataforma.models import Empresa, Plano, UsoEmpresa
from comum.erros import TransicaoInvalida
from comum.estados import MudancaDeStatusForaDaMaquina, transicionar


@pytest.fixture
def profissional(publico):
    return Plano.objects.get(nome="Profissional")


def _com_plano(empresa, plano, **uso):
    empresa.plano = plano
    empresa.save(update_fields=["plano"])
    UsoEmpresa.objects.update_or_create(empresa=empresa, defaults=uso)


def test_plt_03_preco_anual_e_10_mensalidades(profissional):
    assert profissional.preco_anual_centavos == 449000


def test_plt_03_exigir_limite_fora_de_transacao_e_erro_de_programacao(empresa_a, monkeypatch):
    from django.db import connection

    monkeypatch.setattr(connection, "in_atomic_block", False)
    with pytest.raises(RuntimeError):
        services.exigir_limite("veiculos")


def test_plt_03_item_desconhecido(empresa_a):
    with pytest.raises(ValueError):
        services.atualizar_uso("motos", 1)


def test_plt_03_uso_nunca_fica_negativo(empresa_a, profissional):
    _com_plano(empresa_a, profissional, filiais=0)
    services.atualizar_uso("filiais", -1)
    assert UsoEmpresa.objects.get(empresa=empresa_a).filiais == 0


def test_plt_03_recalcular_uso_conta_com_o_contador_registrado(empresa_a, profissional):
    from apps.contas.models import Usuario

    _com_plano(empresa_a, profissional, usuarios=42, veiculos=86)
    Usuario.objects.create_user("a@a.com", "x", nome="A", perfil="gerente")
    pendente = Usuario(email="b@a.com", nome="B", perfil="vendedor", status="convite_pendente")
    pendente.set_unusable_password()
    pendente.save()
    desativado = Usuario.objects.create_user("c@a.com", "x", nome="C", perfil="vendedor")
    transicionar(desativado, "desativado")

    assert services.recalcular_uso(empresa_a) == {"usuarios": 2}
    uso = UsoEmpresa.objects.get(empresa=empresa_a)
    assert (uso.usuarios, uso.veiculos) == (2, 86)  # item sem contador fica como estava


def test_imp_05_passo_da_implantacao_move_o_funil(empresa_a, relogio):
    UsoEmpresa.objects.get_or_create(empresa=empresa_a)
    services.registrar_passo_implantacao("conta")
    empresa_a.refresh_from_db()
    assert empresa_a.etapa_implantacao == "marca"
    assert empresa_a.etapa_implantacao_desde == relogio.agora
    assert UsoEmpresa.objects.get(empresa=empresa_a).passos_implantacao == {"conta": "2026-10-07"}

    relogio.em("2026-10-09 10:00")
    services.registrar_passo_implantacao("ramo")  # não é etapa do funil: a etapa fica
    empresa_a.refresh_from_db()
    assert empresa_a.etapa_implantacao == "marca"
    assert empresa_a.etapa_implantacao_desde.date() == date(2026, 10, 7)


def test_registrar_acesso_escreve_no_maximo_a_cada_5_minutos(empresa_a, relogio):
    UsoEmpresa.objects.get_or_create(empresa=empresa_a)
    services.registrar_acesso()
    primeiro = relogio.agora
    relogio.em("2026-10-07 10:04")
    services.registrar_acesso()
    assert UsoEmpresa.objects.get(empresa=empresa_a).ultimo_acesso_em == primeiro
    relogio.em("2026-10-07 10:05")
    services.registrar_acesso()
    assert UsoEmpresa.objects.get(empresa=empresa_a).ultimo_acesso_em == relogio.agora


@pytest.mark.parametrize(
    ("campos", "codigo", "rotulo", "tom"),
    [
        (
            {"status": "cancelada", "acesso_ate": date(2026, 10, 30)},
            "cancelando",
            "Cancela em 30 out",
            "alerta",
        ),
        (
            {"status": "cancelada", "acesso_ate": date(2026, 10, 1)},
            "cancelada",
            "Cancelada",
            "neutro",
        ),
        ({"status": "suspensa"}, "suspensa", "Suspensa", "perigo"),
        ({"status": "inadimplente"}, "fatura_atrasada", "Fatura atrasada", "perigo"),
        (
            {"status": "pausada", "pausada_ate": date(2027, 1, 7)},
            "pausada",
            "Pausada até 07 jan",
            "neutro",
        ),
        ({"status": "ativa"}, "ativa", "Ativa", "sucesso"),
    ],
)
def test_situacao_de_cada_status(empresa_a, relogio, campos, codigo, rotulo, tom):
    Empresa._base_manager.filter(pk=empresa_a.pk).update(**campos)
    empresa = selectors.com_situacao().get(pk=empresa_a.pk)
    assert selectors.situacao(empresa) == {"codigo": codigo, "rotulo": rotulo, "tom": tom}


def test_imp_05_parada_mostra_o_primeiro_passo_aberto(empresa_a, relogio):
    UsoEmpresa.objects.update_or_create(
        empresa=empresa_a,
        defaults={
            "passos_implantacao": {
                "conta": "2026-10-01",
                "marca": "2026-10-01",
                "filial": "2026-10-01",
            }
        },
    )
    Empresa._base_manager.filter(pk=empresa_a.pk).update(
        status="em_teste",
        etapa_implantacao="precos",
        etapa_implantacao_desde=relogio.agora - timedelta(days=5),
    )
    empresa = selectors.com_situacao().get(pk=empresa_a.pk)
    assert selectors.situacao(empresa)["rotulo"] == "Parada no passo 4"


def test_contagens_e_filtro_por_aba(empresa_a, profissional):
    _com_plano(empresa_a, profissional, veiculos=140)
    contagens = selectors.contagens_das_empresas()
    assert contagens["com_problema"] >= 1
    assert empresa_a.pk in selectors.filtrar_empresas(situacao_aba="com_problema").values_list(
        "pk", flat=True
    )
    assert empresa_a.pk not in selectors.filtrar_empresas(situacao_aba="saindo").values_list(
        "pk", flat=True
    )


def test_status_da_empresa_so_muda_pela_maquina(empresa_a):
    with pytest.raises(MudancaDeStatusForaDaMaquina):
        Empresa.objects.filter(pk=empresa_a.pk).update(status="suspensa")
    with pytest.raises(TransicaoInvalida) as erro:
        transicionar(empresa_a, "em_teste")
    assert erro.value.codigo == "transicao_empresa"


def test_assinatura_com_faixa_de_aviso(empresa_a, profissional):
    _com_plano(empresa_a, profissional)
    Empresa._base_manager.filter(pk=empresa_a.pk).update(status="inadimplente")
    dados = selectors.assinatura(empresa_a)
    assert dados["faixa_aviso"]
    assert dados["somente_leitura"] is False
    assert dados["teste"] is None
