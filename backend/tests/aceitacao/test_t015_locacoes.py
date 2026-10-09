"""T-015 · Locação: reserva, ciclo de status e lista (docs/qa/criterios/T-015.md).

Roda na `empresa_a` com as pessoas e a frota da Moto Rápida (Filial Centro) e o relógio em 07 out
2026, 10:00. A divisão combinada em 09 out: contratos (CA-015-11 a 13) são da T-090; renovação,
atraso, cancelamento e encerramento (CA-015-17, 19 a 24 e o estorno do 25), da T-091; troca de
veículo (CA-015-18), da T-092. Esses ficam `xfail` aqui, com os números do critério.

A vistoria de saída (T-016), a assinatura (T-090) e a baixa no caixa (T-017) entram pelas portas
que esses apps vão usar: `locacoes.services.registrar_vistoria_saida`, o evento
`contratos.contrato_assinado` e `financeiro.services.marcar_paga`.
"""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.clientes import services as clientes_services
from apps.contratos.models import ModeloContrato
from apps.financeiro import selectors as financeiro_selectors
from apps.financeiro import services as financeiro
from apps.financeiro.models import Comissao, ContaReceber
from apps.locacoes import leituras as locacoes_leituras
from apps.locacoes import services
from apps.locacoes.models import Locacao, PlanoEspecial
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from comum import eventos, relogio
from comum.codigos import ajustar_sequencia

from . import carteira
from .apoio import aguarda, pendente
from .frota import Frota, criar_veiculo, montar_frota
from .test_t012_filiais import MotoRapida
from .test_t013_veiculos import _caucaia
from .test_t014_clientes import ANA, CARLOS, DIEGO, JULIANA, PATRICIA, RAFAEL

LISTA = "/api/locacoes/"
SIMULAR = "/api/locacoes/simular/"
INICIO = "2026-10-07T15:30:00Z"  # 07 out, 12:30 em Fortaleza
LUCAS = carteira.pessoa("Lucas Ferreira", "12345678909", "85988771203", endereco=None)


class Cenario:
    """A Moto Rápida com frota, clientes, modelo de contrato publicado e LOC-2855 como último
    código (a próxima locação é a LOC-2856)."""

    def __init__(self, moto: MotoRapida, frota: Frota) -> None:
        self.moto = moto
        self.frota = frota
        self.pessoas = moto.pessoas
        self.clientes = {
            "Lucas": clientes_services.cadastrar(LUCAS),
            "Juliana": clientes_services.cadastrar(JULIANA),
            "Carlos": clientes_services.cadastrar(CARLOS),
            "Diego": clientes_services.cadastrar(
                {**DIEGO, "cnh": {**DIEGO["cnh"], "categoria": "AB"}}
            ),
        }
        self.modelo = ModeloContrato.objects.create(
            nome="Locação semanal",
            finalidade="locacao",
            texto="<p>{{cliente.nome}}</p>",
            publicado=True,
            publicado_em=relogio.agora(),
        )
        ajustar_sequencia("LOC", 2855)

    def cliente(self, nome: str) -> Any:
        return self.clientes[nome]

    def veiculo(
        self, categoria: str, status: str = "disponivel", exceto: tuple[str, ...] = ()
    ) -> Veiculo:
        veiculo = (
            Veiculo.objects.filter(categoria=self.frota.categorias[categoria], status=status)
            .exclude(placa__in=exceto)
            .order_by("placa")
            .first()
        )
        assert veiculo is not None
        return veiculo

    @property
    def sak(self) -> Veiculo:
        return self.frota.veiculos["SAK1D39"]

    def corpo(
        self, cliente: str = "Lucas", veiculo: Veiculo | None = None, **campos: Any
    ) -> dict[str, Any]:
        return {
            "cliente_id": self.cliente(cliente).pk,
            "veiculo_id": (veiculo or self.sak).pk,
            "periodicidade": "semanal",
            "plano_especial_id": None,
            "inicio": INICIO,
            "periodos": 1,
            "extras": [],
            "desconto_pct": "0.00",
            "forma_pagamento": "pix",
            **campos,
        }

    def simular(self, quem: str = "Bruna", **campos: Any) -> Any:
        return self.moto.api(quem).post(SIMULAR, self.corpo(**campos), format="json")

    def criar(self, quem: str = "Bruna", **campos: Any) -> dict[str, Any]:
        resposta = self.moto.api(quem).post(LISTA, self.corpo(**campos), format="json")
        assert resposta.status_code == 201, resposta.json()
        return dict(resposta.json())

    def confirmar(self, locacao_id: int, quem: str = "Bruna", **corpo: Any) -> Any:
        return self.moto.api(quem).post(f"{LISTA}{locacao_id}/confirmar/", corpo, format="json")

    def confirmada(self, quem: str = "Bruna", **campos: Any) -> dict[str, Any]:
        criada = self.criar(quem, **campos)
        resposta = self.confirmar(criada["id"], quem)
        assert resposta.status_code == 200, resposta.json()
        return dict(resposta.json())

    def detalhe(self, locacao_id: int, quem: str = "Bruna") -> dict[str, Any]:
        resposta = self.moto.api(quem).get(f"{LISTA}{locacao_id}/")
        assert resposta.status_code == 200, resposta.json()
        return dict(resposta.json())


@pytest.fixture
def cenario(empresa_a, planos, relogio) -> Cenario:
    # Os testes da T-014 trocam e removem fornecedores falsos no mesmo registro (ADR 0015).
    locacoes_leituras.registrar()
    moto = MotoRapida(empresa_a, planos["Profissional"])
    return Cenario(moto, montar_frota(moto))


def _contas(locacao_id: int) -> list[ContaReceber]:
    return list(financeiro_selectors.contas_da_origem("locacao", locacao_id))


def _parcelas(locacao_id: int) -> list[tuple[date, int]]:
    return [(c.vencimento, c.valor_centavos) for c in _contas(locacao_id) if c.tipo == "parcela"]


def _pagar(locacao_id: int, *, parcela: int | None = 1, caucao: bool = True) -> None:
    for conta in _contas(locacao_id):
        if (conta.tipo == "parcela" and conta.numero_parcela == parcela) or (
            caucao and conta.tipo == "caucao"
        ):
            financeiro.marcar_paga(conta, forma="pix")


def _assinar(locacao_id: int) -> None:
    eventos.publicar(
        "contratos.contrato_assinado",
        contrato_id=1,
        origem_tipo="locacao",
        origem_id=locacao_id,
        tipo="contrato",
        assinado_em=relogio.agora(),
    )


def _vistoriar(locacao_id: int) -> None:
    services.registrar_vistoria_saida(Locacao.objects.get(pk=locacao_id), km=3120)


def _sem_locacao(cenario: Cenario) -> None:
    assert not Locacao.objects.exclude(status="rascunho").exists()
    assert not ContaReceber.objects.exists()


# --- Simular e criar (LOC-01 a LOC-05, LOC-14, LOC-15) ---


def test_loc_01_ca_015_01_lucas_semanal_street(cenario):
    resposta = cenario.simular()
    assert resposta.status_code == 200, resposta.json()
    corpo = resposta.json()
    assert corpo["valor_periodo_centavos"] == 32900
    assert corpo["caucao_centavos"] == 30000
    assert corpo["hoje_na_retirada_centavos"] == 62900
    fim_previsto = datetime.fromisoformat(corpo["fim_previsto"])
    assert fim_previsto == datetime(2026, 10, 14, 15, 30, tzinfo=UTC)
    assert corpo["parcelas_previstas"] == [
        {"numero": 1, "vencimento": "2026-10-07", "valor_centavos": 32900}
    ]
    assert corpo["linhas"][0] == {"rotulo": "1 semana × R$ 329,00", "valor_centavos": 32900}
    assert corpo["texto_retirada"] == "Hoje: primeira semana mais caução."
    assert not Locacao.objects.exists()  # a simulação não grava nada


@pytest.mark.parametrize(
    ("categoria", "campos", "retirada", "proximas", "caucao"),
    [
        ("Street 150–160", {"periodicidade": "diaria", "periodos": 3}, 16470, [], 30000),
        (
            "Urbana 110–125",
            {"periodos": 3},
            29940,
            [("2026-10-14", 29940), ("2026-10-21", 29940)],
            30000,
        ),
        (
            "Urbana 110–125",
            {"periodicidade": "mensal", "periodos": 2, "parcelamento_mensal": "a_vista"},
            109000,
            [("2026-11-07", 109000)],
            30000,
        ),
        (
            "Urbana 110–125",
            {"periodicidade": "mensal", "periodos": 1, "parcelamento_mensal": "quatro_semanais"},
            27250,
            [("2026-10-14", 27250), ("2026-10-21", 27250), ("2026-10-28", 27250)],
            30000,
        ),
        ("Carro compacto", {"cliente": "Diego"}, 64900, [], 80000),
    ],
)
def test_loc_01_loc_05_loc_14_ca_015_02_diaria_semanal_e_mensal(
    cenario, categoria, campos, retirada, proximas, caucao
):
    veiculo = cenario.veiculo(categoria)
    corpo = cenario.simular(veiculo=veiculo, **campos).json()
    parcelas = corpo["parcelas_previstas"]
    assert parcelas[0] == {"numero": 1, "vencimento": "2026-10-07", "valor_centavos": retirada}
    assert [(p["vencimento"], p["valor_centavos"]) for p in parcelas[1:]] == proximas
    assert corpo["caucao_centavos"] == caucao
    assert corpo["hoje_na_retirada_centavos"] == retirada + caucao


def test_loc_14_ca_015_02_mensal_menor_que_um_mes(cenario):
    resposta = cenario.simular(
        periodicidade="mensal", periodos=None, fim_previsto="2026-10-30T15:30:00Z"
    )
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "validacao"
    assert "fim_previsto" in resposta.json()["campos"]


def _plano(cenario: Cenario, **dados: Any) -> dict[str, Any]:
    resposta = cenario.moto.api("Mariana").post("/api/planos-especiais/", dados, format="json")
    assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


def test_loc_01_ca_015_03_planos_especiais(cenario):
    entregador = _plano(
        cenario,
        nome="Entregador",
        periodicidade="semanal",
        regra="preco_fixo",
        preco_centavos=27900,
        condicoes="Semanal com km livre e troca de óleo inclusa",
    )
    fidelidade = _plano(
        cenario,
        nome="Mensal fidelidade",
        periodicidade="mensal",
        regra="desconto",
        desconto_pct="10.00",
        a_partir_do_periodo=3,
    )
    corpo = cenario.simular(plano_especial_id=entregador["id"]).json()
    assert corpo["valor_periodo_centavos"] == 27900

    urbana = cenario.veiculo("Urbana 110–125")
    corpo = cenario.simular(
        veiculo=urbana,
        periodicidade="mensal",
        periodos=4,
        plano_especial_id=fidelidade["id"],
        parcelamento_mensal="a_vista",
    ).json()
    assert [p["valor_centavos"] for p in corpo["parcelas_previstas"]] == [
        109000,
        109000,
        98100,
        98100,
    ]

    # Plano de outra periodicidade não vale.
    resposta = cenario.simular(veiculo=urbana, plano_especial_id=fidelidade["id"])
    assert resposta.status_code == 400
    # Só o administrador cuida dos planos.
    resposta = cenario.moto.api("Rodrigo").post(
        "/api/planos-especiais/",
        {"nome": "X", "periodicidade": "semanal", "regra": "preco_fixo", "preco_centavos": 1},
        format="json",
    )
    assert resposta.status_code == 403
    lista = cenario.moto.api("Bruna").get("/api/planos-especiais/").json()["resultados"]
    assert {p["nome"] for p in lista} == {"Entregador", "Mensal fidelidade"}


def test_loc_02_ca_015_04_extras_por_periodo(cenario):
    capacete = veiculos_services.criar_extra(
        {"nome": "Capacete extra", "valor_centavos": 1500, "cobranca": "por_periodo"}
    )
    corpo = cenario.simular(periodos=2, extras=[{"extra_id": capacete.pk, "quantidade": 1}]).json()
    assert {"rotulo": "Adicionais", "valor_centavos": 3000} in corpo["linhas"]
    assert [p["valor_centavos"] for p in corpo["parcelas_previstas"]] == [34400, 34400]

    criada = cenario.confirmada(periodos=2, extras=[{"extra_id": capacete.pk, "quantidade": 1}])
    assert criada["extras"] == [
        {
            "id": capacete.pk,
            "nome": "Capacete extra",
            "quantidade": 1,
            "valor_centavos": 1500,
            "cobranca": "por_periodo",
        }
    ]


def test_loc_15_ca_015_05_preco_congelado_na_confirmacao(cenario, relogio):
    relogio.em("2026-09-23 09:00")
    cenario.moto._tokens.clear()
    antiga = cenario.confirmada(cliente="Carlos", periodos=5, inicio="2026-09-23T12:00:00Z")
    assert {v for _, v in _parcelas(antiga["id"])} == {29940}
    assert antiga["precos"]["assinado_em_preco_de"] == "2026-09-23"

    relogio.em("2026-10-07 10:00")
    cenario.moto._tokens.clear()
    assert {v for _, v in _parcelas(antiga["id"])} == {29940}
    street = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    nova = cenario.confirmada(veiculo=street)
    assert _parcelas(nova["id"]) == [(date(2026, 10, 7), 32900)]


# --- Desconto (LOC-03, APR-01, APR-09) ---


def _decidir(cenario: Cenario, quem: str, pedido_id: int, acao: str, motivo: str = "") -> Any:
    return cenario.moto.api(quem).post(
        f"/api/aprovacoes/{pedido_id}/{acao}/", {"motivo": motivo}, format="json"
    )


def test_loc_03_ca_015_06_ate_5_por_cento_sem_aprovacao(cenario):
    corpo = cenario.simular(desconto_pct="5.00").json()
    assert corpo["valor_periodo_centavos"] == 31255
    assert corpo["precisa_aprovacao_desconto"] is False
    criada = cenario.confirmada(desconto_pct="5.00")
    assert criada["desconto"] is None
    assert _parcelas(criada["id"]) == [(date(2026, 10, 7), 31255)]
    assert not PedidoAprovacao.objects.exists()


def test_apr_01_ca_015_06_acima_do_limite_gerente_aprova(cenario):
    assert cenario.simular(desconto_pct="5.01").json()["precisa_aprovacao_desconto"] is True
    criada = cenario.confirmada(desconto_pct="5.01", periodos=2)
    assert criada["status"] == "aguardando_retirada"
    assert criada["desconto"]["status"] == "pendente"
    pedido = PedidoAprovacao.objects.get(pk=criada["desconto"]["pedido_aprovacao_id"])
    assert (pedido.tipo, pedido.origem_codigo) == ("APR-01", "LOC-2856")
    assert [v for _, v in _parcelas(criada["id"])] == [32900, 32900]  # sem desconto

    _pagar(criada["id"], parcela=1, caucao=False)  # paga não muda
    resposta = _decidir(cenario, "Rodrigo", pedido.pk, "aprovar")
    assert resposta.status_code == 200, resposta.json()
    # 32900 − 5,01% (1648,29 → 1648) = 31252, só na parcela em aberto.
    assert [v for _, v in _parcelas(criada["id"])] == [32900, 31252]
    detalhe = cenario.detalhe(criada["id"])
    assert detalhe["desconto"]["status"] == "aprovado"
    assert detalhe["precos"]["desconto_pct"] == "5.01"


def test_apr_01_ca_015_06_recusado_volta_a_zero_e_avisa(cenario):
    criada = cenario.confirmada(desconto_pct="7.00")
    pedido_id = criada["desconto"]["pedido_aprovacao_id"]
    resposta = _decidir(cenario, "Rodrigo", pedido_id, "recusar", "Cliente novo, sem histórico")
    assert resposta.status_code == 200, resposta.json()
    detalhe = cenario.detalhe(criada["id"])
    assert detalhe["desconto"]["status"] == "recusado"
    assert detalhe["precos"]["desconto_pct"] == "0.00"
    assert _parcelas(criada["id"]) == [(date(2026, 10, 7), 32900)]
    aviso = Notificacao.objects.get(destinatario=cenario.pessoas["Bruna"])
    assert aviso.titulo == "Desconto da LOC-2856 recusado: Cliente novo, sem histórico"


def test_loc_03_ca_015_06_gerente_da_8_por_cento_direto(cenario):
    criada = cenario.confirmada("Rodrigo", desconto_pct="8.00")
    assert criada["desconto"] is None
    assert _parcelas(criada["id"]) == [(date(2026, 10, 7), 30268)]  # 32900 − 2632
    assert not PedidoAprovacao.objects.exists()


def test_apr_09_ca_015_06_vendedora_com_a_extra_nao_aprova_o_proprio(cenario):
    bruna = cenario.pessoas["Bruna"]
    bruna.permissoes_extras = ["aprovar_desconto"]
    bruna.save(update_fields=["permissoes_extras"])
    criada = cenario.confirmada(desconto_pct="6.00")
    resposta = _decidir(cenario, "Bruna", criada["desconto"]["pedido_aprovacao_id"], "aprovar")
    assert resposta.status_code in (403, 404)
    assert cenario.detalhe(criada["id"])["desconto"]["status"] == "pendente"


# --- Rascunho, confirmação e reserva ---


def test_loc_05_ca_015_07_rascunho_e_confirmacao(cenario, relogio):
    criada = cenario.criar()
    assert (criada["status"], criada["codigo"]) == ("rascunho", "LOC-2856")
    assert criada["acoes"]["confirmar"] is True

    editada = cenario.moto.api("Bruna").patch(
        f"{LISTA}{criada['id']}/", {"periodos": 2}, format="json"
    )
    assert editada.status_code == 200, editada.json()
    assert editada.json()["periodos"] == 2

    resposta = cenario.confirmar(criada["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "aguardando_retirada"
    contas = _contas(criada["id"])
    assert [(c.tipo, c.numero_parcela, c.valor_centavos) for c in contas] == [
        ("caucao", None, 30000),
        ("parcela", 1, 32900),
        ("parcela", 2, 32900),
    ]
    assert all(c.origem_codigo == "LOC-2856" for c in contas)

    de_novo = cenario.moto.api("Bruna").patch(
        f"{LISTA}{criada['id']}/", {"periodos": 3}, format="json"
    )
    assert de_novo.status_code == 409
    assert de_novo.json()["codigo"] == "transicao_locacao"
    assert cenario.confirmar(criada["id"]).status_code == 409


def test_loc_ca_015_07_rascunho_sem_uso_por_24_horas_e_cancelado(cenario, relogio):
    criada = cenario.criar()
    relogio.em("2026-10-08 09:59")
    assert services.cancelar_rascunhos_sem_uso() == 0
    relogio.em("2026-10-08 10:01")
    assert services.cancelar_rascunhos_sem_uso() == 1
    locacao = Locacao.objects.get(pk=criada["id"])
    assert locacao.status == "cancelada"
    assert EventoAuditoria.objects.filter(
        objeto_tipo="locacao", objeto_id=locacao.pk, acao="locacao.cancelar_rascunho"
    ).exists()
    assert services.cancelar_rascunhos_sem_uso() == 0


def test_loc_03_ca_015_08_reserva_com_retirada_futura(cenario):
    futura = cenario.confirmada(inicio="2026-10-09T12:00:00Z")
    sak = Veiculo.objects.get(pk=cenario.sak.pk)
    assert sak.status == "reservado"
    ultima = sak.historico.last()
    assert ultima is not None and ultima.origem_codigo == futura["codigo"]

    street = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    cenario.confirmada(cliente="Juliana", veiculo=street)
    assert Veiculo.objects.get(pk=street.pk).status == "disponivel"


# --- Impedimentos ---


def _recusada(cenario: Cenario, codigo: str, status: int = 422, **campos: Any) -> dict[str, Any]:
    criada = cenario.criar(**campos)
    resposta = cenario.confirmar(criada["id"])
    assert resposta.status_code == status, resposta.json()
    assert resposta.json()["codigo"] == codigo
    assert Locacao.objects.get(pk=criada["id"]).status == "rascunho"
    assert not ContaReceber.objects.exists()
    return dict(resposta.json())


def test_cli_05_ca_015_09_cliente_bloqueado(cenario):
    cenario.clientes["Rafael"] = clientes_services.cadastrar(RAFAEL)
    clientes_services.bloquear(cenario.cliente("Rafael"), "25 dias de atraso")
    impedimentos = cenario.simular(cliente="Rafael").json()["impedimentos"]
    assert [i["codigo"] for i in impedimentos] == ["CLI-05"]
    _recusada(cenario, "CLI-05", cliente="Rafael")


def test_cli_09_ca_015_09_cliente_inativo(cenario):
    cenario.clientes["Patrícia"] = clientes_services.cadastrar(PATRICIA)
    clientes_services.inativar(cenario.cliente("Patrícia"), "Mudou de cidade")
    _recusada(cenario, "cliente_inativo", cliente="Patrícia")


def test_cli_02_ca_015_09_cnh_so_b_alugando_moto(cenario):
    cenario.clientes["Ana"] = clientes_services.cadastrar(
        {**ANA, "cnh": {**ANA["cnh"], "categoria": "B"}}
    )
    corpo = _recusada(cenario, "CLI-02", cliente="Ana")
    assert corpo["mensagem"] == "A CNH do cliente não tem a categoria A."


def test_imp_04_ca_015_09_sem_modelo_de_contrato_publicado(cenario):
    ModeloContrato.objects.filter(pk=cenario.modelo.pk).update(arquivado=True)
    avisos = cenario.simular().json()["avisos"]
    assert {
        "codigo": "IMP-04",
        "mensagem": "Publique um modelo de contrato antes de concluir a locação",
        "link": "/admin/contratos",
    } in avisos
    corpo = _recusada(cenario, "IMP-04")
    assert corpo["detalhes"] == {"link": "/admin/contratos"}


def test_fil_05_ca_015_09_veiculo_de_outra_filial(cenario):
    caucaia = _caucaia(cenario.moto)
    de_caucaia = criar_veiculo(900, cenario.frota.categorias["Street 150–160"], caucaia)
    corpo = _recusada(cenario, "FIL-05", veiculo=de_caucaia)
    assert corpo["mensagem"] == "O veículo é de outra filial. Transfira antes de alugar."


@pytest.mark.parametrize("status", ["alugado", "em_manutencao"])
def test_loc_03_ca_015_09_veiculo_indisponivel(cenario, status):
    veiculo = cenario.veiculo("Street 150–160", status=status)
    corpo = _recusada(cenario, "LOC-03", status=409, veiculo=veiculo)
    assert corpo["mensagem"] == "Veículo indisponível no período"


def test_loc_03_ca_015_09_veiculo_com_outra_locacao_aberta(cenario):
    cenario.confirmada()
    _recusada_depois = cenario.criar(cliente="Juliana")
    resposta = cenario.confirmar(_recusada_depois["id"])
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "LOC-03"


def test_loc_03_ca_015_09_duas_confirmacoes_ao_mesmo_tempo_so_uma_passa(cenario, monkeypatch):
    """A corrida passa pela conferência das duas e para na restrição do banco
    (`uma_locacao_aberta_por_veiculo`): a segunda recebe 409 `LOC-03`."""
    primeira = cenario.criar()
    segunda = cenario.criar(cliente="Juliana")
    monkeypatch.setattr(services, "_outra_locacao_aberta", lambda *a, **k: False)
    assert cenario.confirmar(primeira["id"]).status_code == 200
    resposta = cenario.confirmar(segunda["id"])
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "LOC-03"
    assert Locacao.objects.get(pk=segunda["id"]).status == "rascunho"
    assert Locacao.objects.filter(status="aguardando_retirada").count() == 1


def test_cli_03_ca_015_10_o_que_so_avisa(cenario):
    avisos = cenario.simular().json()["avisos"]
    assert [a["codigo"] for a in avisos] == ["CLI-03"]  # Lucas sem endereço
    assert cenario.confirmada()["status"] == "aguardando_retirada"

    cenario.clientes["Ana"] = clientes_services.cadastrar(
        {**ANA, "cnh": {**ANA["cnh"], "validade": "2026-08-01"}}
    )
    street = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    corpo = cenario.simular(cliente="Ana", veiculo=street).json()
    assert corpo["impedimentos"] == []
    assert "CLI-02" in [a["codigo"] for a in corpo["avisos"]]
    assert cenario.confirmada(cliente="Ana", veiculo=street)["status"] == "aguardando_retirada"


# --- Ativação ---


ORDENS = [
    ("vistoria", "assinatura", "pagamento"),
    ("pagamento", "vistoria", "assinatura"),
    ("assinatura", "pagamento", "vistoria"),
]


@pytest.mark.parametrize("ordem", ORDENS)
def test_loc_ca_015_14_tres_condicoes_em_qualquer_ordem(cenario, ordem):
    criada = cenario.confirmada()
    passos = {
        "vistoria": lambda: _vistoriar(criada["id"]),
        "assinatura": lambda: _assinar(criada["id"]),
        "pagamento": lambda: _pagar(criada["id"]),
    }
    for passo in ordem[:-1]:
        passos[passo]()
        assert Locacao.objects.get(pk=criada["id"]).status == "aguardando_retirada"
        assert Veiculo.objects.get(pk=cenario.sak.pk).status == "disponivel"
    passos[ordem[-1]]()
    assert Locacao.objects.get(pk=criada["id"]).status == "ativa"
    assert Veiculo.objects.get(pk=cenario.sak.pk).status == "alugado"
    assert cenario.detalhe(criada["id"])["km_saida"] == 3120


def test_loc_ca_015_14_so_a_parcela_paga_nao_ativa(cenario):
    criada = cenario.confirmada()
    assert cenario.detalhe(criada["id"])["situacao"]["rotulo"] == "Aguardando assinatura"
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"], caucao=False)
    detalhe = cenario.detalhe(criada["id"])
    assert detalhe["status"] == "aguardando_retirada"
    assert detalhe["situacao"]["codigo"] == "aguardando_pagamento"
    assert detalhe["pagamento"]["rotulo"] == "R$ 329,00 pago"
    _pagar(criada["id"], parcela=None)
    assert cenario.detalhe(criada["id"])["status"] == "ativa"


def test_loc_06_ca_015_15_total_pago_loc_2836(cenario, com_carteira):
    detalhe = cenario.detalhe(com_carteira["LOC-2836"].pk)
    assert detalhe["total_pago_centavos"] == 95800  # 32900 + 32900 + 30000
    pagas = [p for p in detalhe["parcelas"] if p["tipo"] == "parcela"]
    assert [(p["numero"], p["status"]) for p in pagas] == [(1, "paga"), (2, "paga")]
    caucao = next(p for p in detalhe["parcelas"] if p["tipo"] == "caucao")
    assert caucao["observacao"] == "Devolver na entrega"


def test_loc_06_total_pago_pelo_fluxo(cenario):
    """O mesmo total pelo fluxo da API: 2 semanas e a caução pagas."""
    criada = cenario.confirmada(cliente="Juliana", periodos=2)
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    _pagar(criada["id"], parcela=2, caucao=False)
    assert cenario.detalhe(criada["id"])["total_pago_centavos"] == 95800


# --- Lista e sinais (seed: carteira de outubro) ---


@pytest.fixture
def com_carteira(cenario) -> dict[str, Locacao]:
    return carteira.carregar(cenario.frota, cenario.pessoas["Bruna"])


def _linha(corpo: dict[str, Any], codigo: str) -> dict[str, Any]:
    return next(item for item in corpo["resultados"] if item["codigo"] == codigo)


def test_loc_07_loc_10_ca_015_16_sinais_e_lista(cenario, com_carteira):
    corpo = cenario.moto.api("Rodrigo").get(LISTA, {"tamanho": 100}).json()
    indicadores = corpo["indicadores"]
    assert indicadores["ativas"] == 42
    assert indicadores["devolucao_atrasada"] == 1
    assert indicadores["devolucao_atrasada_destaque"] == "Rafael · 25 dias"
    assert indicadores["pagamentos_atrasados"] == 2
    assert indicadores["pagamentos_atrasados_centavos"] == 164640
    assert corpo["contagens"]["abertas"] == 42

    juliana = _linha(corpo, "LOC-2836")
    assert juliana["sinais"]["devolve_hoje"] is True
    assert juliana["acao_principal"] == {
        "codigo": "receber_devolucao",
        "rotulo": "Receber devolução",
    }
    assert juliana["pagamento"]["rotulo"] == "Pago"

    carlos = _linha(corpo, "LOC-2841")
    assert carlos["sinais"]["pagamento_atrasado"] is True
    assert carlos["situacao"]["rotulo"] == "Parcela 2 atrasada"
    assert carlos["acao_principal"]["codigo"] == "cobrar"
    assert carlos["pagamento"] == {
        "rotulo": "R$ 299,40 em aberto",
        "tom": "perigo",
        "em_aberto_centavos": 29940,
    }

    rafael = _linha(corpo, "LOC-2790")
    assert rafael["situacao"] == {
        "codigo": "devolucao_atrasada",
        "rotulo": "Devolução atrasada 25 dias",
        "tom": "perigo",
    }

    acao = cenario.moto.api("Rodrigo").get(LISTA, {"aba": "precisam_acao"}).json()
    assert {x["codigo"] for x in acao["resultados"]} == {"LOC-2790", "LOC-2841"}
    hoje = cenario.moto.api("Rodrigo").get(LISTA, {"aba": "devolvem_hoje"}).json()
    assert [x["codigo"] for x in hoje["resultados"]] == ["LOC-2836"]
    busca = cenario.moto.api("Rodrigo").get(LISTA, {"busca": "qxa4b21"}).json()
    assert [x["codigo"] for x in busca["resultados"]] == ["LOC-2841"]


@aguarda("T-091")
def test_apr_02_ca_015_16_loc_2812_cancelamento_pendente(cenario):
    pendente(locacao="LOC-2812", sinal="cancelamento_pendente", pagamento="Multa R$ 84,80")


def test_loc_ca_015_16_vistoriador_sem_lista_e_sem_valores(cenario, com_carteira):
    assert cenario.moto.api("João").get(LISTA).status_code == 403
    detalhe = cenario.detalhe(com_carteira["LOC-2841"].pk, "João")

    def chaves(dados: Any) -> set[str]:
        if isinstance(dados, dict):
            return set(dados) | {c for v in dados.values() for c in chaves(v)}
        if isinstance(dados, list):
            return {c for item in dados for c in chaves(item)}
        return set()

    assert not [c for c in chaves(detalhe) if c.endswith("_centavos")]
    assert "parcelas" not in detalhe and "pagamento" not in detalhe


def test_usr_07_locacao_fora_da_filial_responde_404(cenario):
    criada = cenario.confirmada()
    caucaia = _caucaia(cenario.moto, "Bruna")
    resposta = cenario.moto.api("Bruna", HTTP_X_FILIAL=str(caucaia.pk)).get(
        f"{LISTA}{criada['id']}/"
    )
    assert resposta.status_code == 404


# --- O que a locação fornece aos outros apps (ADR 0015) ---


def test_loc_leituras_veiculo_cliente_e_filial(cenario, com_carteira):
    qxa = cenario.frota.veiculos["QXA4B21"]
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{qxa.pk}/").json()
    assert ficha["locacao_atual"]["codigo"] == "LOC-2841"
    assert ficha["locacao_atual"]["cliente_nome"] == "Carlos Menezes"

    pnb = (
        cenario.moto.api("Rodrigo")
        .get(f"/api/veiculos/{com_carteira['LOC-2790'].veiculo_id}/")
        .json()
    )
    assert pnb["situacao"]["rotulo"] == "Atrasado"

    clientes = cenario.moto.api("Rodrigo").get("/api/clientes/").json()
    assert clientes["contagens"]["com_locacao"] == 42
    juliana = (
        cenario.moto.api("Rodrigo")
        .get(f"/api/clientes/{com_carteira['LOC-2836'].cliente_id}/")
        .json()
    )
    assert juliana["locacao_atual"]["codigo"] == "LOC-2836"
    assert juliana["locacao_atual"]["detalhe"] == "devolve hoje"

    filiais = cenario.moto.api("Mariana").get("/api/filiais/").json()["resultados"]
    assert filiais[0]["indicadores"]["locacoes_ativas"] == 42


def test_loc_leituras_lista_de_veiculos_sem_n_mais_1(cenario):
    api = cenario.moto.api("Rodrigo")
    with CaptureQueriesContext(connection) as antes:
        api.get("/api/veiculos/")
    cenario.confirmada()
    street = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    cenario.confirmada(cliente="Juliana", veiculo=street)
    with CaptureQueriesContext(connection) as depois:
        api.get("/api/veiculos/")
    assert len(depois) == len(antes)


# --- Comissão (FIN-09) ---


def test_fin_09_ca_015_25_comissao_da_locacao_nova(cenario):
    criada = cenario.confirmada()
    comissao = Comissao.objects.get(origem_tipo="locacao", origem_id=criada["id"])
    assert (comissao.valor_centavos, comissao.status) == (1600, "pendente")
    assert comissao.usuario == cenario.pessoas["Bruna"]
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    comissao.refresh_from_db()
    assert comissao.status == "confirmada"
    assert comissao.mes_pagamento == date(2026, 11, 1)

    street = cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    segunda = cenario.confirmada(cliente="Juliana", veiculo=street)
    _vistoriar(segunda["id"])
    _assinar(segunda["id"])
    _pagar(segunda["id"])
    bruna = cenario.pessoas["Bruna"].pk
    assert financeiro_selectors.comissoes_confirmadas_centavos(bruna, date(2026, 10, 1)) == 3200


@aguarda("T-091")
def test_fin_09_ca_015_25_estorno_e_renovacao_sem_comissao(cenario):
    pendente(
        cancelada_antes_da_retirada="estornada", encerramento_antecipado="confirmada", renovar=0
    )


# --- Auditoria e isolamento ---


def test_loc_ca_015_24_mudancas_de_status_gravam_auditoria(cenario):
    criada = cenario.confirmada()
    _vistoriar(criada["id"])
    _assinar(criada["id"])
    _pagar(criada["id"])
    acoes = set(
        EventoAuditoria.objects.filter(objeto_tipo="locacao", objeto_id=criada["id"]).values_list(
            "acao", flat=True
        )
    )
    assert {"locacao.criar", "locacao.confirmar", "locacao.ativar"} <= acoes
    historico = cenario.moto.api("Bruna").get(f"{LISTA}{criada['id']}/historico/").json()
    rotulos = [item["rotulo"] for item in historico["resultados"]]
    assert "Locação ativa" in rotulos and "Caução paga · R$ 300,00" in rotulos
    do_joao = cenario.moto.api("João").get(f"{LISTA}{criada['id']}/historico/").json()
    assert not [i for i in do_joao["resultados"] if i["tipo"] == "pagamento"]


def test_loc_locacao_da_empresa_a_nao_aparece_na_b(cenario):
    criada = cenario.confirmada()
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Locacao.objects.exists()
        assert not ContaReceber.objects.exists()
        assert not Comissao.objects.exists()
    finally:
        connection.set_tenant(cenario.moto.empresa)
    assert Locacao.objects.filter(pk=criada["id"]).exists()


def test_loc_01_plano_especial_campo_da_regra(cenario):
    resposta = cenario.moto.api("Mariana").post(
        "/api/planos-especiais/",
        {"nome": "Sem preço", "periodicidade": "semanal", "regra": "preco_fixo"},
        format="json",
    )
    assert resposta.status_code == 400
    plano = PlanoEspecial.objects.create(
        nome="Entregador", periodicidade="semanal", regra="preco_fixo", preco_centavos=27900
    )
    resposta = cenario.moto.api("Mariana").post(f"/api/planos-especiais/{plano.pk}/desativar/")
    assert resposta.status_code == 200 and resposta.json()["ativo"] is False
    assert cenario.simular(plano_especial_id=plano.pk).status_code == 400


# --- Das tarefas seguintes (divisão de 09 out) ---


@aguarda("T-090")
def test_fin_03_ca_015_11_gerar_e_enviar_contrato(cenario):
    pendente(locacao="LOC-2856", resposta=202, status="enviado", segundo_post="contrato_existente")


@aguarda("T-090")
def test_s_15_ca_015_12_link_de_assinatura(cenario):
    pendente(valido_ate="2026-10-14", expirado_em="2026-10-15", nome="lucas ferreira")


@aguarda("T-090")
def test_s_09_ca_015_13_modelo_de_contrato(cenario):
    pendente(marcador_invalido="{{cliente.salario}}", arquivar_ultimo="IMP-04")


@aguarda("T-091")
def test_loc_08_ca_015_17_renovacao(cenario):
    pendente(locacao="LOC-2841", parcelas_novas=[32900, 32900], antigas=29940, mais_dias=14)


@aguarda("T-092")
def test_loc_09_ca_015_18_troca_de_veiculo(cenario):
    pendente(locacao="LOC-2836", diferenca_caucao=20000, parcelas_abertas=44900)


@aguarda("T-091")
def test_loc_10_ca_015_19_tolerancia_e_diarias(cenario):
    pendente(as_19h00=0, as_19h01=5490, dia_8_17h59=5490, dia_8_18h01=10980)


@aguarda("T-091")
def test_loc_11_ca_015_20_filial_fechada_e_feriado(cenario):
    pendente(sabado_11h30=0, sabado_10h00=10980, com_feriado=10980)


@aguarda("T-091")
def test_loc_12_loc_13_ca_015_21_patricia_loc_2812(cenario):
    pendente(restante=42400, multa=8480, credito=37100, devolver=28620)


@aguarda("T-091")
def test_loc_12_ca_015_22_antes_da_retirada_sem_multa(cenario):
    pendente(reembolso=62900, veiculo="disponivel", comissao="estornada")


@aguarda("T-091")
def test_loc_12_ca_015_23_multa_minima(cenario):
    pendente(street_1_dia=5490, nmax_6_dias_cobrar=6360)


@aguarda("T-091")
def test_loc_12_ca_015_24_estados_finais(cenario):
    pendente(cancelar_encerrada="transicao_locacao")


def test_dinheiro_formatar_reais():
    from comum.dinheiro import formatar_reais

    assert formatar_reais(32900) == "R$ 329,00"
    assert formatar_reais(164640) == "R$ 1.646,40"
    assert formatar_reais(5) == "R$ 0,05"
