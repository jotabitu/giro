"""T-502 · Fluxo de venda, fase 1a: estados, proposta e aprovação (ADR 0042, item 1a;
`docs/api/vendas.md`).

Cenário da T-015: Moto Rápida, Filial Centro, 07 out 2026, 10:00. A CB 300F é um veículo
`a_venda` da frota com o valor de venda de R$ 22.900,00 (VEN-0177, `dados-de-teste.md`). A Bruna
(vendedora) vende; o Rodrigo (gerente) decide os descontos.
"""

from decimal import Decimal
from typing import Any

import pytest
from django.db import connection

from apps.aprovacoes import services as aprovacoes_services
from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria
from apps.empresas.models import ConfiguracaoEmpresa
from apps.financeiro.models import Comissao
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import Veiculo
from apps.vendas import services
from apps.vendas.models import Venda
from comum.erros import Conflito, SemPermissao

from .test_t015_locacoes import Cenario, cenario  # noqa: F401

VENDAS = "/api/vendas/"
SIMULAR = "/api/vendas/simular/"
VEN_0177: dict[str, Any] = {
    "forma": "entrada_parcelas",
    "desconto_pct": "8.00",
    "entrada_centavos": 500000,
    "num_parcelas": 12,
}


def _cb(cenario: Cenario, indice: int = 0) -> Veiculo:  # noqa: F811
    """Um veículo `a_venda` do Centro, como a CB 300F de R$ 22.900,00."""
    veiculo = Veiculo.objects.filter(filial=cenario.frota.centro, status="a_venda").order_by(
        "placa"
    )[indice]
    veiculo.marca, veiculo.modelo, veiculo.valor_venda_centavos = "Honda", "CB 300F", 2290000
    veiculo.save(update_fields=["marca", "modelo", "valor_venda_centavos"])
    return veiculo


def _corpo(cenario: Cenario, acao: str, veiculo: Veiculo | None = None, **campos: Any):  # noqa: F811
    return {
        "veiculo_id": (veiculo or _cb(cenario)).pk,
        "cliente_id": cenario.cliente("Diego").pk,
        "acao": acao,
        **campos,
    }


def _criar(cenario: Cenario, acao: str, quem: str = "Bruna", **campos: Any) -> Any:  # noqa: F811
    return cenario.moto.api(quem).post(VENDAS, _corpo(cenario, acao, **campos), format="json")


def _criada(cenario: Cenario, acao: str, quem: str = "Bruna", **campos: Any) -> dict[str, Any]:  # noqa: F811
    resposta = _criar(cenario, acao, quem, **campos)
    assert resposta.status_code == 201, resposta.json()
    return dict(resposta.json())


def _post(cenario: Cenario, venda_id: int, rota: str, quem: str = "Bruna", **corpo: Any):  # noqa: F811
    return _api(cenario, quem).post(f"{VENDAS}{venda_id}/{rota}/", corpo, format="json")


def _api(cenario: Cenario, quem: str = "Bruna") -> Any:  # noqa: F811
    """Token novo a cada chamada: os testes andam o relógio (o token vence com ele)."""
    cenario.moto._tokens.pop(quem, None)
    return cenario.moto.api(quem)


def _pedido(venda_id: int) -> PedidoAprovacao:
    return PedidoAprovacao.objects.get(origem_tipo="venda", origem_id=venda_id)


def _comissao(venda_id: int) -> Comissao:
    return Comissao.objects.get(origem_tipo="venda", origem_id=venda_id)


# --- Criação e proposta (VEN-01, VEN-14) ---


def test_ven_01_proposta_copia_o_preco_de_tabela_e_o_vendedor(cenario, relogio):  # noqa: F811
    criada = _criada(cenario, "enviar", forma="a_vista", desconto_pct="2.00")
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.origem, venda.vendedor) == (
        "proposta",
        "balcao",
        cenario.pessoas["Bruna"],
    )
    assert venda.preco_tabela_centavos == 2290000
    assert (venda.desconto_centavos, venda.preco_final_centavos) == (45800, 2244200)
    assert venda.entrada_centavos == 2244200 and venda.num_parcelas is None
    assert venda.proposta_enviada_em == venda.entrou_proposta_em == relogio.agora
    assert venda.ultimo_contato_em == relogio.agora
    assert criada["forma_texto"] == "Pix à vista"
    assert criada["proposta_vence_em"] == "2026-10-14"
    assert criada["situacao_texto"] == "Proposta enviada"
    assert criada["calculo"]["preco_final_centavos"] == 2244200
    # O preço do veículo muda depois; o da venda, não.
    Veiculo.objects.filter(pk=venda.veiculo_id).update(valor_venda_centavos=2500000)
    detalhe = cenario.moto.api("Bruna").get(f"{VENDAS}{venda.pk}/").json()
    assert detalhe["calculo"]["preco_tabela_centavos"] == 2290000
    evento = EventoAuditoria.objects.get(acao="venda.criar", objeto_id=venda.pk)
    assert (evento.regra, evento.depois["status"]) == ("VEN-13", "proposta")


def test_ven_01_veiculo_fora_de_a_venda(cenario):  # noqa: F811
    disponivel = cenario.veiculo("Urbana 110–125")
    resposta = _criar(cenario, "enviar", veiculo=disponivel, forma="a_vista")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEN-01"


def test_ven_14_interessado_so_com_nome_e_celular(cenario):  # noqa: F811
    corpo = _corpo(cenario, "interessado")
    corpo.pop("cliente_id")
    corpo["interessado"] = {"nome": "Carla Mendes", "celular": "(85) 98877-1100"}
    resposta = cenario.moto.api("Bruna").post(VENDAS, corpo, format="json")
    assert resposta.status_code == 201, resposta.json()
    dados = resposta.json()
    assert dados["status"] == "interessado" and dados["cliente"] is None
    assert dados["interessado"] == {"nome": "Carla Mendes", "celular": "85988771100"}
    assert dados["comprador_nome"] == "Carla Mendes"
    # A proposta pede o cliente cadastrado com CPF.
    enviar = _post(cenario, dados["id"], "enviar")
    assert enviar.status_code == 400
    assert "cliente_id" in enviar.json()["campos"]
    # O dado pessoal sem cadastro vai mascarado na auditoria.
    evento = EventoAuditoria.objects.get(acao="venda.criar", objeto_id=dados["id"])
    assert evento.depois["interessado_nome"] != "Carla Mendes"
    assert "98877" not in str(evento.depois["interessado_celular"])


def test_ven_14_interessado_vira_proposta_com_o_cliente(cenario):  # noqa: F811
    corpo = _corpo(cenario, "interessado")
    corpo.pop("cliente_id")
    corpo["interessado"] = {"nome": "Diego", "celular": "85999990000"}
    criada = cenario.moto.api("Bruna").post(VENDAS, corpo, format="json").json()
    editada = cenario.moto.api("Bruna").patch(
        f"{VENDAS}{criada['id']}/",
        {"cliente_id": cenario.cliente("Diego").pk, "forma": "a_vista"},
        format="json",
    )
    assert editada.status_code == 200, editada.json()
    assert editada.json()["interessado"] is None
    enviada = _post(cenario, criada["id"], "enviar")
    assert enviada.status_code == 200, enviada.json()
    # VEN-15 (fase 1c): o Diego tem e-mail no cadastro, e a proposta vai por e-mail com o PDF.
    assert enviada.json()["email_enviado"] is True
    assert enviada.json()["venda"]["status"] == "proposta"


# --- Desconto e aprovação (VEN-02, VEN-13, APR-01, FIN-09) ---


def test_ven_02_desconto_acima_de_5_pede_aprovacao(cenario):  # noqa: F811
    resposta = _criar(cenario, "enviar", **VEN_0177)
    assert resposta.status_code == 400
    assert resposta.json()["campos"]["desconto_pct"] == [
        "Acima de 5% precisa do gerente. Use Pedir aprovação."
    ]
    assert not Venda.objects.exists()


def test_ven_02_simular_ven_0177(cenario):  # noqa: F811
    corpo = {"veiculo_id": _cb(cenario).pk, **VEN_0177}
    resposta = cenario.moto.api("Bruna").post(SIMULAR, corpo, format="json")
    assert resposta.status_code == 200, resposta.json()
    dados = resposta.json()
    assert dados["preco_final_centavos"] == 2106800
    assert dados["desconto_centavos"] == 183200
    assert dados["parcela_centavos"] == 133900
    assert dados["comissao_centavos"] == 63204
    assert dados["precisa_aprovacao"] is True
    assert dados["limite_desconto_pct"] == "5.00"
    assert not Venda.objects.exists()


def test_ven_18_simular_financiamento_recusado(cenario):  # noqa: F811
    corpo = {"veiculo_id": _cb(cenario).pk, "forma": "financiamento"}
    dados = cenario.moto.api("Bruna").post(SIMULAR, corpo, format="json").json()
    assert dados["erros"] == {"forma": ["O financiamento ainda não está disponível."]}


def test_ven_02_fin_09_ven_0177_pedido_de_aprovacao(cenario):  # noqa: F811
    """Nova venda que já nasce pedindo aprovação: `aguardando_aprovacao`, o pedido APR-01 e a
    comissão pendente de R$ 632,04 (FIN-10)."""
    criada = _criada(cenario, "pedir_aprovacao", motivo="Cliente fiel", **VEN_0177)
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.status_antes_aprovacao, venda.aprovacao) == (
        "aguardando_aprovacao",
        "interessado",
        "pendente",
    )
    assert (venda.preco_final_centavos, venda.parcela_centavos) == (2106800, 133900)
    assert venda.entrou_negociacao_em is not None and venda.entrou_proposta_em is None
    pedido = _pedido(venda.pk)
    assert (pedido.tipo, pedido.status, pedido.valor_centavos, pedido.pct) == (
        "APR-01",
        "pendente",
        183200,
        Decimal("8.00"),
    )
    assert venda.pedido_aprovacao_id == pedido.pk
    celulas = {c["rotulo"]: c["valor"] for c in pedido.resumo["celulas"]}
    assert celulas["Com desconto"] == "R$ 21.068,00"
    comissao = _comissao(venda.pk)
    assert (comissao.status, comissao.valor_centavos, comissao.base_centavos, comissao.pct) == (
        "pendente",
        63204,
        2106800,
        Decimal("3.00"),
    )
    assert comissao.usuario == cenario.pessoas["Bruna"]
    assert criada["situacao_texto"] == "Aguardando gerente"
    assert criada["aprovacao"]["texto"] == (
        "Pedido de 8% enviado para Rodrigo. Você não edita a proposta até ele decidir."
    )
    assert criada["comissao_centavos"] == 63204


def test_apr_01_aprovado_volta_e_envia_a_que_veio_de_interessado(cenario, relogio):  # noqa: F811
    criada = _criada(cenario, "pedir_aprovacao", **VEN_0177)
    relogio.em("2026-10-07 11:00")
    aprovacoes_services.aprovar(_pedido(criada["id"]), cenario.pessoas["Rodrigo"])
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.aprovacao, venda.desconto_aprovado_pct) == (
        "proposta",
        "aprovado",
        Decimal("8.00"),
    )
    assert venda.preco_final_centavos == 2106800
    assert venda.proposta_enviada_em == venda.entrou_proposta_em == relogio.agora
    assert _comissao(venda.pk).status == "pendente"
    assert EventoAuditoria.objects.filter(acao="venda.aprovar_desconto", regra="APR-01").exists()
    # Até o desconto aprovado, a edição não pede de novo.
    editada = cenario.moto.api("Bruna").patch(
        f"{VENDAS}{venda.pk}/", {"desconto_pct": "7.50"}, format="json"
    )
    assert editada.status_code == 200, editada.json()
    assert _comissao(venda.pk).valor_centavos == 63548  # 3% de 21.182,50 → 635,475 → 635,48


def test_apr_01_recusado_zera_o_desconto_e_avisa_o_vendedor(cenario):  # noqa: F811
    criada = _criada(
        cenario, "enviar", forma="entrada_parcelas", entrada_centavos=500000, num_parcelas=12
    )
    pedido = _post(cenario, criada["id"], "pedir-aprovacao", desconto_pct="8.00", motivo="Fiel")
    assert pedido.status_code == 200, pedido.json()
    assert pedido.json()["status"] == "aguardando_aprovacao"
    assert _comissao(criada["id"]).valor_centavos == 63204
    aprovacoes_services.recusar(_pedido(criada["id"]), cenario.pessoas["Rodrigo"], "Margem baixa")
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.aprovacao, venda.desconto_pct) == ("proposta", "recusado", 0)
    assert (venda.preco_final_centavos, venda.parcela_centavos) == (2290000, 149166)
    assert venda.motivo_recusa == "Margem baixa"
    assert _comissao(venda.pk).valor_centavos == 68700  # recalculada sobre 22.900,00
    aviso = Notificacao.objects.get(destinatario=cenario.pessoas["Bruna"], tipo="desconto_recusado")
    assert aviso.titulo == f"Desconto da {venda.codigo} recusado: Margem baixa"
    detalhe = cenario.moto.api("Bruna").get(f"{VENDAS}{venda.pk}/").json()
    assert detalhe["situacao_texto"] == "Proposta enviada"
    assert detalhe["aprovacao"]["motivo_recusa"] == "Margem baixa"
    # VEN-19: o texto da recusa vem pronto da API.
    assert detalhe["aprovacao"]["texto"] == (
        "Desconto de 8% recusado por Rodrigo: margem baixa. Dê até 5% ou peça uma nova aprovação."
    )


def test_apr_01_pedido_cancelado_pelo_vendedor(cenario):  # noqa: F811
    criada = _criada(cenario, "interessado", forma="a_vista")
    _post(cenario, criada["id"], "pedir-aprovacao", desconto_pct="6.00")
    aprovacoes_services.cancelar(_pedido(criada["id"]), cenario.pessoas["Bruna"])
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.aprovacao, venda.desconto_pct) == ("interessado", "cancelado", 0)
    assert venda.motivo_recusa == ""


def test_ven_02_edicao_acima_do_limite_e_em_aprovacao(cenario):  # noqa: F811
    criada = _criada(cenario, "enviar", forma="a_vista")
    acima = cenario.moto.api("Bruna").patch(
        f"{VENDAS}{criada['id']}/", {"desconto_pct": "6.00"}, format="json"
    )
    assert acima.status_code == 400
    _post(cenario, criada["id"], "pedir-aprovacao", desconto_pct="6.00")
    travada = cenario.moto.api("Bruna").patch(
        f"{VENDAS}{criada['id']}/", {"desconto_pct": "1.00"}, format="json"
    )
    assert travada.status_code == 409 and travada.json()["codigo"] == "APR-01"
    de_novo = _post(cenario, criada["id"], "pedir-aprovacao", desconto_pct="7.00")
    assert de_novo.status_code == 409 and de_novo.json()["codigo"] == "pedido_pendente"


def test_ven_02_pedir_ate_5_pct_e_recusado(cenario):  # noqa: F811
    criada = _criada(cenario, "enviar", forma="a_vista")
    resposta = _post(cenario, criada["id"], "pedir-aprovacao", desconto_pct="5.00")
    assert resposta.status_code == 400
    assert not PedidoAprovacao.objects.exists()


# --- Passagens (VEN-13, VEN-16) ---


def test_ven_13_resposta_leva_a_negociacao_e_reenvio_nao_muda(cenario, relogio, relogio_jwt):  # noqa: F811
    criada = _criada(cenario, "enviar", forma="a_vista")
    relogio.em("2026-10-08 09:00")
    resposta = _post(cenario, criada["id"], "resposta", nota="Quer pensar até sexta")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["status"] == "negociacao"
    venda = Venda.objects.get(pk=criada["id"])
    assert venda.entrou_negociacao_em == venda.ultimo_contato_em == relogio.agora
    evento = EventoAuditoria.objects.get(acao="venda.registrar_resposta")
    assert evento.motivo == "Quer pensar até sexta"
    relogio.em("2026-10-09 09:00")
    reenvio = _post(cenario, criada["id"], "enviar")
    assert reenvio.json()["venda"]["status"] == "negociacao"
    venda.refresh_from_db()
    assert venda.proposta_enviada_em == venda.ultimo_contato_em == relogio.agora
    assert (
        venda.entrou_proposta_em is not None and venda.entrou_proposta_em.day == 7
    )  # a primeira entrada não se reescreve
    # De negociação não se registra resposta outra vez.
    assert _post(cenario, criada["id"], "resposta").status_code == 409


def test_ven_13_resposta_no_interessado_e_recusada(cenario):  # noqa: F811
    criada = _criada(cenario, "interessado")
    resposta = _post(cenario, criada["id"], "resposta")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "transicao_venda"


def test_ven_13_perder_cancela_o_pedido_e_estorna_a_comissao(cenario):  # noqa: F811
    criada = _criada(cenario, "pedir_aprovacao", **VEN_0177)
    sem_motivo = _post(cenario, criada["id"], "perder", motivo=" ")
    assert sem_motivo.status_code == 400
    perdida = _post(cenario, criada["id"], "perder", motivo="Comprou em outra loja")
    assert perdida.status_code == 200, perdida.json()
    venda = Venda.objects.get(pk=criada["id"])
    assert (venda.status, venda.motivo_perda, venda.aprovacao) == (
        "perdida",
        "Comprou em outra loja",
        "cancelado",
    )
    assert venda.perdida_em is not None
    assert _pedido(venda.pk).status == "cancelado"
    assert _comissao(venda.pk).status == "estornada"
    assert perdida.json()["acoes"]["perder"] is False


def test_ven_13_vendedor_perde_so_as_dele_e_o_gerente_as_da_filial(cenario):  # noqa: F811
    do_rodrigo = _criada(cenario, "enviar", quem="Rodrigo", forma="a_vista")
    venda = Venda.objects.get(pk=do_rodrigo["id"])
    with pytest.raises(SemPermissao):
        services.perder(venda, "Desistiu", cenario.pessoas["Bruna"])
    assert _post(cenario, venda.pk, "perder", motivo="Desistiu").status_code == 404
    da_bruna = _criada(cenario, "enviar", veiculo=_cb(cenario, 1), forma="a_vista")
    resposta = _post(cenario, da_bruna["id"], "perder", quem="Rodrigo", motivo="Desistiu")
    assert resposta.status_code == 200, resposta.json()


def test_aut_19_proposta_vence_em_7_dias(cenario, relogio):  # noqa: F811
    proposta = _criada(cenario, "enviar", forma="a_vista")
    em_negociacao = _criada(cenario, "enviar", veiculo=_cb(cenario, 1), forma="a_vista")
    _post(cenario, em_negociacao["id"], "resposta")
    interessado = _criada(cenario, "interessado", veiculo=_cb(cenario, 2))
    relogio.em("2026-10-13 23:00")
    assert services.vencer_propostas() == 0
    relogio.em("2026-10-14 02:40")
    assert services.vencer_propostas() == 1
    assert services.vencer_propostas() == 0  # idempotente
    venda = Venda.objects.get(pk=proposta["id"])
    assert (venda.status, venda.motivo_perda) == ("perdida", "proposta vencida")
    assert services.situacao_texto(venda) == "Perdida · proposta vencida"  # VEN-19
    evento = EventoAuditoria.objects.get(acao="venda.vencer_proposta")
    assert (evento.ator_tipo, evento.regra) == ("sistema", "AUT-19")
    assert Venda.objects.get(pk=em_negociacao["id"]).status == "negociacao"
    assert Venda.objects.get(pk=interessado["id"]).status == "interessado"


def test_ven_16_ultimo_contato_a_cada_mudanca(cenario, relogio, relogio_jwt):  # noqa: F811
    criada = _criada(cenario, "interessado", forma="a_vista")
    relogio.em("2026-10-08 10:00")
    _api(cenario).patch(f"{VENDAS}{criada['id']}/", {"desconto_pct": "1.00"}, format="json")
    assert Venda.objects.get(pk=criada["id"]).ultimo_contato_em == relogio.agora
    relogio.em("2026-10-09 10:00")
    _post(cenario, criada["id"], "enviar")
    assert Venda.objects.get(pk=criada["id"]).ultimo_contato_em == relogio.agora


# --- Uma venda aberta por veículo (VEN-10) ---


def test_ven_10_uma_venda_aberta_por_veiculo(cenario):  # noqa: F811
    cb = _cb(cenario)
    primeira = _criada(cenario, "enviar", veiculo=cb, forma="a_vista")
    # O interessado não conta: entra; a segunda proposta, não.
    assert _criar(cenario, "interessado", veiculo=cb).status_code == 201
    segunda = _criar(cenario, "enviar", veiculo=cb, forma="a_vista")
    assert segunda.status_code == 409
    assert segunda.json()["codigo"] == "VEN-10"
    assert segunda.json()["mensagem"] == (
        f"Este veículo tem uma venda em andamento ({primeira['codigo']})."
    )


def test_ven_10_trava_do_estoque(cenario):  # noqa: F811
    cb = _cb(cenario)
    criada = _criada(cenario, "enviar", veiculo=cb, forma="a_vista")
    with pytest.raises(Conflito) as erro:
        veiculos_services.voltar_para_frota(cb)
    assert erro.value.codigo == "VEN-10"
    assert erro.value.detalhes == {"venda_id": criada["id"]}
    with pytest.raises(Conflito):
        veiculos_services.baixar(cb, "roubo", "")
    assert Veiculo.objects.get(pk=cb.pk).status == "a_venda"
    _post(cenario, criada["id"], "perder", motivo="Desistiu")
    veiculos_services.voltar_para_frota(cb)
    assert Veiculo.objects.get(pk=cb.pk).status in ("disponivel", "indisponivel")


# --- Juros da empresa (VEN-04) ---


def test_ven_04_juros_da_empresa_copiados_na_proposta(cenario):  # noqa: F811
    configuracao = ConfiguracaoEmpresa.objects.first() or ConfiguracaoEmpresa()
    configuracao.juros_venda_mes_pct = Decimal("1.00")
    configuracao.save()
    criada = _criada(
        cenario,
        "enviar",
        forma="entrada_parcelas",
        desconto_pct="5.00",
        entrada_centavos=500000,
        num_parcelas=12,
    )
    venda = Venda.objects.get(pk=criada["id"])
    assert venda.juros_pct == Decimal("1.00")
    assert criada["calculo"]["parcela_centavos"] == venda.parcela_centavos
    assert (
        venda.parcela_centavos is not None
        and venda.parcela_centavos > (venda.preco_final_centavos - 500000) // 12
    )


# --- Lista, quem pode e isolamento ---


def test_ven_13_lista_por_aba_e_quem_pode(cenario):  # noqa: F811
    _criada(cenario, "pedir_aprovacao", **VEN_0177)
    _criada(cenario, "enviar", veiculo=_cb(cenario, 1), forma="a_vista")
    api = cenario.moto.api("Rodrigo")
    aguardando = api.get(VENDAS, {"aba": "aguardando"}).json()["resultados"]
    assert [v["situacao_texto"] for v in aguardando] == ["Aguardando gerente"]
    abertas = api.get(VENDAS, {"aba": "abertas"}).json()["resultados"]
    assert len(abertas) == 2
    assert {v["forma_texto"] for v in abertas} == {"entrada + 12×", "Pix à vista"}
    # O financeiro lê e não cria; o vistoriador nem vê.
    assert cenario.moto.api("Lúcia").get(VENDAS).status_code == 200
    assert _criar(cenario, "interessado", quem="Lúcia").status_code == 403
    assert cenario.moto.api("João").get(VENDAS).status_code == 403


def test_ven_venda_da_empresa_a_nao_aparece_na_b(cenario):  # noqa: F811
    criada = _criada(cenario, "pedir_aprovacao", **VEN_0177)
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    try:
        assert not Venda.objects.exists()
        assert not Comissao.objects.exists()
        assert not PedidoAprovacao.objects.exists()
    finally:
        connection.set_tenant(cenario.moto.empresa)
    assert Venda.objects.filter(pk=criada["id"]).exists()


def test_vei_23_venda_aberta_leva_a_venda(cenario):  # noqa: F811
    """VEI-23: o 409 `VEN-10` do voltar para a frota e da baixa traz `detalhes.venda_id`, para o
    "Ver a venda" do diálogo."""
    cb = _cb(cenario)
    criada = _criada(cenario, "enviar", veiculo=cb, forma="a_vista")
    url = f"/api/veiculos/{cb.pk}/"
    voltar = _api(cenario, "Mariana").post(f"{url}voltar-para-frota/", {}, format="json")
    assert voltar.status_code == 409
    assert voltar.json() == {
        "codigo": "VEN-10",
        "mensagem": f"Este veículo tem uma venda em andamento ({criada['codigo']}).",
        "detalhes": {"venda_id": criada["id"]},
    }
    baixa = {"motivo": "roubo", "descricao": ""}
    baixar = _api(cenario, "Mariana").post(f"{url}baixar/", baixa, format="json")
    assert (baixar.status_code, baixar.json()["detalhes"]) == (409, {"venda_id": criada["id"]})
