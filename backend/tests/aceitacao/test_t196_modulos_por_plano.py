"""T-196 · Módulos por plano e por ramo (PLT-12, ADR 0024; `docs/api/plataforma.md`, "Módulos por
plano"; CA-ASS-15, 22 a 24, 52 e 53).

A Moto Rápida criada pelo serviço (t185), no Profissional ou no Essencial. O que o plano não liga
some do menu, recebe 403 `PLT-12` nas rotas, não age nas tarefas e segura o downgrade enquanto
tiver algo aberto; os dados ficam guardados.
"""

import json
from datetime import date
from typing import Any

import pytest
from django.core import mail
from django.db import connection
from django_tenants.utils import tenant_context

from apps.empresas.models import ConfiguracaoEmpresa
from apps.empresas.services import criar_configuracao_padrao
from apps.financeiro import services as financeiro
from apps.financeiro.models import Comissao, Despesa
from apps.financeiro.services import Origem
from apps.plataforma.models import Empresa, Plano, UsoEmpresa
from apps.plataforma.selectors import recursos_da_empresa
from comum import leituras
from comum.empresa import tem_recurso
from integracoes.pagamentos import falso as pagamentos
from integracoes.whatsapp import falso as whatsapp

from .test_t185_assinatura import MotoRapida, _criar_matriz, _simular

DESPESAS = "/api/financeiro/despesas/"
LOCACOES = "/api/locacoes/"
EU = "/api/auth/eu/"
IMPLANTACAO = "/api/implantacao/"
SEM_MANUTENCAO = {
    "codigo": "PLT-12",
    "mensagem": "Seu plano não inclui Manutenção e despesas. Para usar, mude de plano.",
    "detalhes": {"recurso": "manutencao_despesas", "motivo": "plano"},
}
NAO_ALUGA = {
    "codigo": "PLT-12",
    "mensagem": "Sua empresa não está configurada para alugar. Mude em Configurações.",
    "detalhes": {"recurso": "locacoes_vistoria", "motivo": "ramo"},
}


@pytest.fixture
def criar_moto(criar_empresa, relogio_jwt):
    pagamentos.limpar()

    def criar(plano: str = "Profissional") -> MotoRapida:
        moto = MotoRapida(criar_empresa(plano=plano))
        UsoEmpresa.objects.filter(empresa=moto.empresa).update(filiais=0)  # a matriz vem agora
        _criar_matriz(moto)
        return moto

    yield criar
    pagamentos.limpar()


def _no_plano(moto: MotoRapida, nome: str) -> None:
    """A virada do período (CA-ASS-23): o plano muda direto, como na `aplicar_mudanca_agendada`."""
    moto.estado(plano=Plano.objects.get(nome=nome))


def _ramo(moto: MotoRapida, atividade: str) -> None:
    with tenant_context(moto.empresa):
        criar_configuracao_padrao()
        ConfiguracaoEmpresa.objects.update(atividade=atividade)
    connection.set_schema_to_public()


def _uso_que_cabe_no_essencial(moto: MotoRapida) -> None:
    UsoEmpresa.objects.filter(empresa=moto.empresa).update(veiculos=20, filiais=1, usuarios=3)


def _despesa(moto: MotoRapida, status: str, descricao: str = "Troca de pneus") -> int:
    with tenant_context(moto.empresa):
        criada = Despesa.objects.create(
            filial=_filial(),
            data=date(2026, 10, 7),
            descricao=descricao,
            categoria="manutencao",
            valor_centavos=68000,
            vencimento=date(2026, 10, 20),
            status=status,
            lancada_por=moto.pessoas["Mariana"],
        )
    connection.set_schema_to_public()
    return int(criada.pk)


def _get(api: Any, rota: str) -> Any:
    resposta = api.get(rota)
    connection.set_schema_to_public()
    return resposta


def _chaves_do_menu(api: Any) -> set[str]:
    corpo = _get(api, EU).json()
    return {i["chave"] for grupo in corpo["navegacao"]["menu_completo"] for i in grupo["itens"]}


def _filial() -> Any:
    """A matriz, no schema corrente."""
    from apps.filiais.models import Filial

    return Filial.objects.order_by("pk").first()


# --- Rotas, menu e implantação (CA-ASS-22) ---


def test_plt_12_essencial_sem_modulos_do_profissional(criar_moto):
    moto = criar_moto("Essencial")
    _despesa(moto, "paga")
    api = moto.api()
    for resposta in (
        _get(api, DESPESAS),
        api.post(DESPESAS, {}, format="json"),
        _get(moto.suporte("ver_editar"), DESPESAS),  # o suporte recebe a mesma recusa
    ):
        connection.set_schema_to_public()
        assert resposta.status_code == 403, resposta.json()
        assert resposta.json() == SEM_MANUTENCAO
    # O perfil não muda a recusa: quem nem lança despesas recebe o mesmo 403 (antes do perfil).
    assert _get(moto.api("Rodrigo"), DESPESAS).json() == SEM_MANUTENCAO
    # O núcleo e o Essencial seguem abertos.
    assert _get(api, LOCACOES).status_code == 200
    assert _get(api, "/api/financeiro/contas-receber/").status_code == 200
    menu = _chaves_do_menu(api)
    assert "locacoes" in menu and "receber" in menu
    assert not menu & {"vendas", "manutencoes", "despesas", "comissoes", "conciliacao"}
    assert "relatorios" not in menu
    # Sem `recebimento_parceiro`, o passo 10 (Recebimentos) não existe: 9 passos.
    assert "recebimentos" not in json.dumps(_get(api, IMPLANTACAO).json())
    with tenant_context(moto.empresa):
        assert recursos_da_empresa() == {"locacoes_vistoria", "contas_receber", "contrato_digital"}
        assert not tem_recurso("cobranca_whatsapp")
    connection.set_schema_to_public()


def test_plt_12_profissional_com_os_modulos(criar_moto):
    moto = criar_moto("Profissional")
    api = moto.api()
    assert _get(api, DESPESAS).status_code == 200
    assert "despesas" in _chaves_do_menu(api)
    assert "recebimentos" in json.dumps(_get(api, IMPLANTACAO).json())


def test_plt_12_dados_guardados_ao_descer(criar_moto):
    """CA-ASS-23: as despesas pagas ficam no banco no Essencial e voltam ao subir."""
    moto = criar_moto("Profissional")
    pk = _despesa(moto, "paga")
    _no_plano(moto, "Essencial")
    api = moto.api()
    assert _get(api, DESPESAS).status_code == 403
    assert "despesas" not in _chaves_do_menu(api)
    with tenant_context(moto.empresa):
        assert Despesa.objects.get(pk=pk).status == "paga"
    connection.set_schema_to_public()
    _no_plano(moto, "Profissional")
    lista = _get(moto.api(), DESPESAS)
    assert lista.status_code == 200
    assert [d["id"] for d in lista.json()["resultados"]] == [pk]


def test_plt_12_ramo_desliga_modulo(criar_moto):
    """O plano liga e o ramo não pede: `motivo: "ramo"`. Os blocos de locação não vêm e os
    contadores valem 0, sem rodar a query."""
    moto = criar_moto("Profissional")
    _ramo(moto, "vende")
    api = moto.api()
    resposta = _get(api, LOCACOES)
    assert resposta.status_code == 403
    assert resposta.json() == NAO_ALUGA
    assert _get(api, "/api/vistorias/agenda/").json() == NAO_ALUGA
    assert "locacoes" not in _chaves_do_menu(api)
    with tenant_context(moto.empresa):
        assert leituras.contar("filiais.Filial", _filial().pk, ["locacoes"]) == {"locacoes": 0}
    connection.set_schema_to_public()
    # De volta a "aluga e vende", tudo volta.
    _ramo(moto, "ambos")
    assert _get(moto.api(), LOCACOES).status_code == 200


def test_plt_12_tarefa_pulada_sem_o_modulo(criar_moto, monkeypatch):
    from apps.locacoes import services as locacoes_services
    from apps.locacoes.tasks import aut_02_marcar_devolucao_atrasada

    chamadas: list[str] = []

    def marcar() -> int:
        chamadas.append("x")
        return 0

    monkeypatch.setattr(locacoes_services, "marcar_devolucoes_atrasadas", marcar)
    moto = criar_moto("Profissional")
    assert aut_02_marcar_devolucao_atrasada(moto.empresa.schema_name) == 0
    assert chamadas == ["x"]
    _ramo(moto, "vende")
    assert aut_02_marcar_devolucao_atrasada(moto.empresa.schema_name) is None
    assert chamadas == ["x"]


# --- Downgrade (CA-ASS-15, 24 e 52) ---


def test_plt_12_downgrade_recusado_com_modulo_aberto(criar_moto):
    """CA-ASS-24: dentro dos limites do Essencial, 1 despesa a pagar segura a mudança. As OS
    abertas entram com o app `manutencao` (o grupo vale 0 até lá)."""
    moto = criar_moto("Profissional")
    _uso_que_cabe_no_essencial(moto)
    _despesa(moto, "a_pagar")
    _despesa(moto, "paga", "Óleo")
    resposta = _simular(moto.api(), "Essencial")
    connection.set_schema_to_public()
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "PLT-04",
        "mensagem": (
            "Seu uso não cabe no plano Essencial. Resolva o que está aberto antes de mudar: "
            "1 despesa a pagar."
        ),
        "detalhes": {
            "abertos": [
                {"grupo": "despesas_a_pagar", "quantidade": 1, "texto": "1 despesa a pagar"}
            ],
            "abertos_texto": "1 despesa a pagar",
        },
    }
    assert moto.recarregar().plano.nome == "Profissional"


def test_plt_04_downgrade_nao_cabe_com_os_abertos_do_seed(criar_moto):
    """CA-ASS-15: 86 de 30 veículos, 5 de 3 usuários, os pneus aguardando aprovação e o IPVA e a
    conta de luz a pagar."""
    moto = criar_moto("Profissional")
    _despesa(moto, "aguardando_aprovacao", "Pneus")
    _despesa(moto, "a_pagar", "IPVA ROE2A88")
    _despesa(moto, "a_pagar", "Conta de luz")
    _despesa(moto, "paga", "Óleo")
    resposta = _simular(moto.api(), "Essencial")
    connection.set_schema_to_public()
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "PLT-04",
        "mensagem": (
            "Seu uso não cabe no plano Essencial. Desative veículos ou usuários e resolva o que "
            "está aberto antes de mudar: 1 despesa aguardando aprovação e 2 despesas a pagar."
        ),
        "detalhes": {
            "veiculos": {"usado": 86, "limite": 30},
            "usuarios": {"usado": 5, "limite": 3},
            "abertos": [
                {
                    "grupo": "despesas_aguardando_aprovacao",
                    "quantidade": 1,
                    "texto": "1 despesa aguardando aprovação",
                },
                {"grupo": "despesas_a_pagar", "quantidade": 2, "texto": "2 despesas a pagar"},
            ],
            "abertos_texto": "1 despesa aguardando aprovação e 2 despesas a pagar",
        },
    }
    # O mesmo `excede` na linha do Essencial de `planos/`.
    planos = _get(moto.api(), "/api/assinatura/planos/").json()["resultados"]
    essencial = next(p for p in planos if p["nome"] == "Essencial")
    assert essencial["excede"]["abertos_texto"] == (
        "1 despesa aguardando aprovação e 2 despesas a pagar"
    )


def test_plt_12_downgrade_so_vende(criar_moto):
    """CA-ASS-52: quem só vende não vai para o Essencial, mesmo cabendo. Nada muda."""
    moto = criar_moto("Profissional")
    _uso_que_cabe_no_essencial(moto)
    _ramo(moto, "vende")
    resposta = _simular(moto.api(), "Essencial")
    connection.set_schema_to_public()
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "PLT-04",
        "mensagem": "O plano Essencial não inclui vendas. Para mudar, sua empresa precisa alugar.",
        "detalhes": {"atividade": {"atual": "vende", "aceitas": ["aluga", "ambos"]}},
    }
    assert moto.recarregar().plano.nome == "Profissional"
    # Com "aluga e vende", cabe.
    _ramo(moto, "ambos")
    assert _simular(moto.api(), "Essencial").status_code == 200
    connection.set_schema_to_public()


# --- Régua e comissão (CA-ASS-22, CA-ASS-53) ---


def _conta_do_carlos(moto: MotoRapida) -> Any:
    from apps.clientes.models import Cliente
    from apps.financeiro.models import ContaReceber

    with tenant_context(moto.empresa):
        cliente = Cliente.objects.create(
            tipo="pf",
            nome="Carlos Lima",
            documento="52998224725",
            celular="85985554433",
            email="carlos@exemplo.com",
            cliente_desde=date(2026, 3, 10),
        )
        conta = ContaReceber.objects.create(
            filial=_filial(),
            cliente=cliente,
            tipo="outro",
            valor_centavos=29940,
            vencimento=date(2026, 10, 7),
            origem_tipo="locacao",
            origem_id=1,
            origem_codigo="LOC-2841",
        )
    connection.set_schema_to_public()
    return conta


def test_aut_03_essencial_so_email(criar_moto, relogio):
    """AUT-03 no Essencial: a cobrança sai só por e-mail, sem o Pix do parceiro, mesmo com a
    subconta aprovada."""
    from apps.plataforma.models import ContaPagamento

    relogio.em("2026-10-07 09:00")
    moto = criar_moto("Essencial")
    ContaPagamento.objects.create(
        empresa=moto.empresa, conta_externa_id="acc_moto_rapida", status="aprovada"
    )
    conta = _conta_do_carlos(moto)
    whatsapp.caixa_de_saida.clear()
    mail.outbox.clear()
    with tenant_context(moto.empresa):
        assert financeiro.cobrar(conta)
        from apps.financeiro.models import CobrancaExterna

        assert not CobrancaExterna.objects.exists()
    connection.set_schema_to_public()
    assert whatsapp.caixa_de_saida == []
    assert [m.to for m in mail.outbox] == [["carlos@exemplo.com"]]
    assert mail.outbox[0].body.endswith("Pague na loja ou fale com a gente por aqui.")


def test_plt_12_comissao_so_depois_do_upgrade(criar_moto):
    """CA-ASS-53: a comissão de locação só nasce com `vendas_comissoes` ligado no momento da
    confirmação; a confirmada no Essencial não ganha comissão depois do upgrade."""
    moto = criar_moto("Essencial")
    bruna = moto.pessoas["Rodrigo"]
    with tenant_context(moto.empresa):
        no_essencial = financeiro.lancar_comissao(
            Origem("locacao", 1, "LOC-2856"), usuario_id=bruna.pk, valor_centavos=1600
        )
        assert no_essencial is None
    connection.set_schema_to_public()
    _no_plano(moto, "Profissional")
    with tenant_context(Empresa.objects.get(pk=moto.empresa.pk)):
        assert financeiro.confirmar_comissao(Origem("locacao", 1, "LOC-2856")) == 0
        depois = financeiro.lancar_comissao(
            Origem("locacao", 2, "LOC-2857"), usuario_id=bruna.pk, valor_centavos=1600
        )
        assert depois is not None
        assert list(Comissao.objects.values_list("origem_codigo", flat=True)) == ["LOC-2857"]
    connection.set_schema_to_public()
