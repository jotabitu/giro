"""T-420 · Venda da quitação da locação com intenção de compra (`VEN-11`, `LOC-16`, ADR 0037;
`docs/qa/criterios/T-420.md`, CA-420-11, 12 e 16; `docs/api/vendas.md`).

Cenário da T-015: Moto Rápida, Filial Centro, 07 out 2026, 10:00. A locação é a LOC-2856 do Lucas
no SAK1D39, criada pela Bruna e `ativa`. A quitação (`locacoes.services.quitar_se_pago`) é da
parte de locações da T-420, em outra branch: aqui o evento `locacoes.locacao_quitada` é emitido
direto, com o payload da "Interface interna" de `locacoes.md`.
"""

from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.core.cache import cache
from django.db import connection, transaction

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import StatusUsuario, Usuario
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.financeiro.models import Comissao, ContaReceber
from apps.locacoes.models import Locacao
from apps.notificacoes.models import Notificacao
from apps.plataforma.models import Empresa
from apps.veiculos.models import HistoricoStatusVeiculo, Veiculo
from apps.vendas import selectors, services
from apps.vendas.models import Venda
from comum import eventos, leituras, relogio
from comum.auditoria import Ator, TipoAtor, usar_ator
from comum.erros import Conflito, TransicaoInvalida

from .test_t012_filiais import _filial
from .test_t015_locacoes import Cenario, cenario  # noqa: F401
from .test_t091_locacao_fim import _ativa

TRANSFERENCIA = "/api/locacoes/{}/transferencia/"
VENDAS = "/api/vendas/"


def _quitar(cenario: Cenario, locacao_id: int) -> None:  # noqa: F811
    """O que `locacoes` publica na quitação, dentro da transação (ADR 0037, item 4). Quem pagou
    a última parcela foi a Lúcia: a venda é do Sistema mesmo assim."""
    locacao = Locacao.objects.get(pk=locacao_id)
    lucia = cenario.pessoas["Lúcia"]
    with usar_ator(Ator(tipo=TipoAtor.USUARIO, nome=lucia.nome, id=lucia.pk)):
        eventos.publicar(
            "locacoes.locacao_quitada",
            locacao_id=locacao.pk,
            codigo=locacao.codigo,
            filial_id=locacao.filial_id,
            cliente_id=locacao.cliente_id,
            veiculo_id=locacao.veiculo_id,
            vendedor_id=cenario.pessoas["Bruna"].pk,
            quitada_em=relogio.agora(),
        )


@pytest.fixture
def quitada(cenario, django_capture_on_commit_callbacks) -> dict[str, Any]:  # noqa: F811
    locacao = _ativa(cenario)
    with django_capture_on_commit_callbacks(execute=True):
        _quitar(cenario, locacao["id"])
    return locacao


def _venda() -> Venda:
    return Venda.objects.get()


def test_ven_11_quitacao_cria_a_venda_de_zero(cenario, quitada):  # noqa: F811
    """CA-420-12: `vendida`, R$ 0,00, "Quitação da LOC-x", cliente, veículo, filial e vendedora
    da locação, sem contas a receber nem comissão."""
    venda = _venda()
    assert quitada["codigo"] == "LOC-2856"
    assert venda.codigo == "VEN-0001"
    assert (venda.status, venda.origem, venda.preco_final_centavos) == (
        "vendida",
        "quitacao_locacao",
        0,
    )
    assert venda.descricao == "Quitação da LOC-2856"
    assert venda.cliente.nome == "Lucas Ferreira"
    assert venda.veiculo.placa == "SAK1D39"
    assert venda.vendedor == cenario.pessoas["Bruna"]
    assert venda.locacao_id == quitada["id"]
    assert venda.vendida_em == relogio.agora()
    assert venda.forma == "" and venda.transferencia_feita_em is None
    assert not ContaReceber.objects.filter(origem_tipo="venda").exists()
    assert not Comissao.objects.filter(origem_tipo="venda").exists()


def test_ven_11_veiculo_vai_de_alugado_para_vendido(quitada):
    """CA-420-11: a moto sai da frota, com a origem na venda e o motivo da quitação."""
    venda = _venda()
    assert Veiculo.objects.get(pk=venda.veiculo_id).status == "vendido"
    linha = HistoricoStatusVeiculo.objects.filter(veiculo_id=venda.veiculo_id).last()
    assert linha is not None
    assert (linha.de, linha.para, linha.origem_tipo, linha.origem_codigo, linha.motivo) == (
        "alugado",
        "vendido",
        "venda",
        "VEN-0001",
        "Quitação da LOC-2856",
    )
    assert linha.por_id is None  # Sistema


def test_ven_11_auditoria_do_sistema(quitada):
    venda = _venda()
    evento = EventoAuditoria.objects.get(acao="venda.criar_da_quitacao")
    assert (evento.ator_tipo, evento.regra, evento.objeto_id) == ("sistema", "VEN-11", venda.pk)
    vendido = EventoAuditoria.objects.get(acao="veiculo.vendido")
    assert vendido.ator_tipo == "sistema"


def test_ven_11_loc_16_aviso_aos_gerentes_e_administradores(cenario, quitada):  # noqa: F811
    """CA-420-11 e B-04 (decisão do dono, 12 nov 2026): o texto da `LOC-16`, no sino e por
    e-mail, para os gerentes da filial e os administradores da empresa."""
    venda = _venda()
    avisos = Notificacao.objects.filter(tipo="transferencia_quitacao").order_by("destinatario_id")
    assert {a.destinatario.nome for a in avisos} == {"Rodrigo", "Mariana"}
    assert len({a.titulo for a in avisos}) == 1
    aviso = avisos.get(destinatario=cenario.pessoas["Rodrigo"])
    assert aviso.titulo == (
        "Fazer a transferência no Detran: SAK-1D39 para Lucas Ferreira. "
        "LOC-2856 quitada em 07/10/2026."
    )
    assert (aviso.link, aviso.urgente) == (f"/locacoes/{quitada['id']}", False)
    assert aviso.chave == f"quitacao-transferencia-{venda.pk}"
    assert sorted(m.to[0] for m in mail.outbox if aviso.titulo in f"{m.subject} {m.body}") == [
        "mariana@motorapida.com.br",
        "rodrigo@motorapida.com.br",
    ]


def test_ven_11_loc_16_aviso_sem_gerente_na_filial(cenario):  # noqa: F811
    """B-04: numa filial sem gerente ativo, o aviso chega aos administradores ativos (sem
    repetir); administrador desativado e o gerente de outra filial (Rodrigo, do Centro) não
    recebem."""
    caucaia = Filial.objects.get(pk=cenario.moto.criar(_filial("Filial Caucaia")).json()["id"])
    Usuario.objects.create_user(
        "ana@motorapida.com.br",
        "senha-forte-123",
        nome="Ana",
        perfil="administrador",
        status=StatusUsuario.DESATIVADO,
    )
    paulo = Usuario.objects.create_user(
        "paulo@motorapida.com.br", "senha-forte-123", nome="Paulo", perfil="administrador"
    )
    assert services.destinatarios_da_transferencia(caucaia) == [
        cenario.pessoas["Mariana"].pk,
        paulo.pk,
    ]


def test_ven_11_idempotente_pela_locacao(cenario, quitada, django_capture_on_commit_callbacks):  # noqa: F811
    with django_capture_on_commit_callbacks(execute=True):
        _quitar(cenario, quitada["id"])
    assert Venda.objects.count() == 1
    assert HistoricoStatusVeiculo.objects.filter(para="vendido").count() == 1
    # Um aviso por pessoa (Rodrigo e Mariana), sem repetir na segunda quitação.
    assert Notificacao.objects.filter(tipo="transferencia_quitacao").count() == 2


def test_ven_11_falha_na_venda_desfaz_a_quitacao(cenario):  # noqa: F811
    """Mesma transação (ADR 0037, item 4): com o veículo fora de `alugado`, a venda falha e nada
    fica pela metade."""
    criada = cenario.confirmada()  # `reservado`, ainda não retirado
    with pytest.raises(TransicaoInvalida), transaction.atomic():
        _quitar(cenario, criada["id"])
    assert not Venda.objects.exists()
    assert Veiculo.objects.get(pk=criada["veiculo"]["id"]).status == "reservado"


def test_ven_11_nao_se_cancela(quitada):
    with pytest.raises(Conflito) as erro:
        services.cancelar(_venda(), "Desistência", None)
    assert (erro.value.codigo, erro.value.mensagem) == (
        "VEN-11",
        "A venda da quitação de uma locação não se cancela.",
    )


# --- Leituras para os outros apps (ADR 0015) ---


def test_ven_11_bloco_compra_venda_da_locacao(quitada):
    venda = _venda()
    locacao = Locacao.objects.get(pk=quitada["id"])
    assert leituras.bloco("locacoes.Locacao", "compra_venda", locacao) == {
        "id": venda.pk,
        "codigo": "VEN-0001",
        "transferencia": {"feita_em": None, "registrada_por": None, "pendente": True},
    }


def test_ven_11_bloco_vazio_sem_venda(cenario):  # noqa: F811
    locacao = Locacao.objects.get(pk=_ativa(cenario)["id"])
    assert selectors.venda_da_locacao(locacao.pk) is None
    assert not leituras.bloco("locacoes.Locacao", "compra_venda", locacao)


def test_ven_11_transferencias_pendentes(quitada):
    filial = _venda().filial_id
    assert selectors.transferencias_pendentes([filial]) == [
        {
            "tipo": "transferencia_quitacao",
            "locacao_id": quitada["id"],
            "rotulo": "Transferência no Detran · SAK-1D39",
            "detalhe": "Lucas Ferreira · LOC-2856 quitada em 07/10/2026",
            "link": f"/locacoes/{quitada['id']}",
        }
    ]
    assert selectors.transferencias_pendentes([filial + 1000]) == []


# --- "Transferência feita" (CA-420-16) ---


def _registrar(cenario: Cenario, locacao_id: int, quem: str = "Rodrigo", **corpo: Any) -> Any:  # noqa: F811
    corpo = corpo or {"feita_em": relogio.hoje().isoformat()}
    return cenario.moto.api(quem).post(TRANSFERENCIA.format(locacao_id), corpo, format="json")


def test_ven_11_registrar_transferencia(cenario, quitada):  # noqa: F811
    """CA-420-16: o Rodrigo fecha a tarefa; ela sai das pendências, fica no histórico do veículo,
    e o veículo continua `vendido`."""
    resposta = _registrar(cenario, quitada["id"])
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["id"] == quitada["id"]  # o detalhe da locação
    venda = _venda()
    assert venda.transferencia_feita_em == relogio.hoje()
    assert venda.transferencia_registrada_por == cenario.pessoas["Rodrigo"]
    assert selectors.transferencias_pendentes([venda.filial_id]) == []
    assert Veiculo.objects.get(pk=venda.veiculo_id).status == "vendido"
    evento = EventoAuditoria.objects.get(acao="venda.registrar_transferencia")
    assert (evento.ator_id, evento.regra) == (cenario.pessoas["Rodrigo"].pk, "VEN-11")
    ficha = cenario.moto.api("Rodrigo").get(f"/api/veiculos/{venda.veiculo_id}/").json()
    [item] = ficha["vendas"]["itens"]
    assert item["codigo"] == "VEN-0001"
    assert item["transferencia"]["pendente"] is False
    assert item["transferencia_texto"] == "Transferência no Detran feita em 07/10/2026 · Rodrigo"
    bloco = leituras.bloco("locacoes.Locacao", "compra_venda", venda.locacao) or {}
    assert bloco["transferencia"] == {
        "feita_em": relogio.hoje(),
        "registrada_por": {"id": cenario.pessoas["Rodrigo"].pk, "nome": "Rodrigo"},
        "pendente": False,
    }


def test_ven_11_transferencia_duas_vezes(cenario, quitada):  # noqa: F811
    assert _registrar(cenario, quitada["id"]).status_code == 200
    resposta = _registrar(cenario, quitada["id"], quem="Mariana")
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "VEN-11"
    assert resposta.json()["mensagem"] == "A transferência desta venda já foi registrada."


@pytest.mark.parametrize(
    ("dias", "mensagem"),
    [(1, "A data não pode ser depois de hoje."), (-1, "A data não pode ser antes da quitação.")],
)
def test_ven_11_data_da_transferencia(cenario, quitada, dias, mensagem):  # noqa: F811
    feita_em = (relogio.hoje() + timedelta(days=dias)).isoformat()
    resposta = _registrar(cenario, quitada["id"], feita_em=feita_em)
    assert resposta.status_code == 400
    assert resposta.json()["campos"] == {"feita_em": [mensagem]}
    assert _venda().transferencia_feita_em is None


@pytest.mark.parametrize("quem", ["Bruna", "João", "Lúcia"])
def test_ven_11_transferencia_so_gerente_e_administrador(cenario, quitada, quem):  # noqa: F811
    assert _registrar(cenario, quitada["id"], quem=quem).status_code == 403
    assert _venda().transferencia_feita_em is None


def test_ven_11_transferencia_sem_venda_404(cenario):  # noqa: F811
    locacao = _ativa(cenario)
    assert _registrar(cenario, locacao["id"]).status_code == 404


# --- GET /api/vendas/ (CA-420-12) ---


def test_ven_11_lista_de_vendas(cenario, quitada):  # noqa: F811
    resposta = cenario.moto.api("Rodrigo").get(VENDAS)
    assert resposta.status_code == 200, resposta.json()
    [venda] = resposta.json()["resultados"]
    assert venda["codigo"] == "VEN-0001"
    assert (venda["origem"], venda["origem_rotulo"]) == ("quitacao_locacao", "Quitação de locação")
    assert venda["preco_final_centavos"] == 0
    assert venda["descricao"] == "Quitação da LOC-2856"
    assert venda["locacao"] == {"id": quitada["id"], "codigo": "LOC-2856"}
    assert venda["vendedor"]["nome"] == "Bruna"
    assert venda["veiculo"]["placa"] == "SAK1D39"
    assert venda["acoes"] == {"cancelar": False, "registrar_transferencia": True}
    detalhe = cenario.moto.api("Bruna").get(f"{VENDAS}{venda['id']}/")
    assert detalhe.status_code == 200
    assert detalhe.json()["acoes"]["registrar_transferencia"] is False
    pendentes = cenario.moto.api("Mariana").get(VENDAS, {"transferencia_pendente": "true"})
    assert len(pendentes.json()["resultados"]) == 1


def test_ven_11_lista_e_detalhe_pela_filial_escolhida(cenario, quitada):  # noqa: F811
    """B-03 (FIL-02, USR-07): a lista e o detalhe seguem o `X-Filial`, como as outras listas."""
    venda = _venda()
    caucaia = cenario.moto.criar(_filial("Filial Caucaia")).json()["id"]
    na_caucaia = cenario.moto.api("Mariana", HTTP_X_FILIAL=str(caucaia))
    assert na_caucaia.get(VENDAS).json()["resultados"] == []
    assert na_caucaia.get(f"{VENDAS}{venda.pk}/").status_code == 404
    no_centro = cenario.moto.api("Mariana", HTTP_X_FILIAL=str(venda.filial_id))
    assert [v["id"] for v in no_centro.get(VENDAS).json()["resultados"]] == [venda.pk]
    assert no_centro.get(f"{VENDAS}{venda.pk}/").status_code == 200
    todas = cenario.moto.api("Mariana", HTTP_X_FILIAL="todas")
    assert len(todas.get(VENDAS).json()["resultados"]) == 1


def test_ven_11_loc_16_pendencia_no_painel(cenario, quitada):  # noqa: F811
    """`painel.md`: a transferência que falta entra nas `pendencias.itens` do administrador,
    levando ao detalhe da locação, e sai quando a transferência é registrada."""
    painel = cenario.moto.api("Mariana").get("/api/painel/inicio/").json()
    assert painel["variante"] == "geral"
    item = {
        "texto": "Transferência no Detran · SAK-1D39 · Lucas Ferreira · LOC-2856 quitada em "
        "07/10/2026",
        "gravidade": "alerta",
        "destino": {"chave": "locacoes", "id": quitada["id"]},
    }
    assert item in painel["pendencias"]["itens"]
    assert _registrar(cenario, quitada["id"]).status_code == 200
    cache.clear()  # o início fica em cache por 5 minutos (`relatorios.api.views`)
    depois = cenario.moto.api("Mariana").get("/api/painel/inicio/").json()
    assert item not in depois["pendencias"]["itens"]


def test_ven_11_loc_16_pendencia_no_painel_do_gerente(cenario, quitada):  # noqa: F811
    """`painel.md`, variante `gerente`: as transferências pendentes só das filiais dele."""
    rodrigo = cenario.moto.api("Rodrigo").get("/api/painel/inicio/").json()
    assert rodrigo["variante"] == "gerente"
    assert rodrigo["pendencias"] == {
        "titulo": "1 transferência no Detran pendente",
        "itens": [
            {
                "texto": "Transferência no Detran · SAK-1D39 · Lucas Ferreira · LOC-2856 "
                "quitada em 07/10/2026",
                "gravidade": "alerta",
                "destino": {"chave": "locacoes", "id": quitada["id"]},
            }
        ],
    }
    caucaia = cenario.moto.criar(_filial("Filial Caucaia")).json()["id"]
    paula = Usuario.objects.create_user(
        "paula@motorapida.com.br", "senha-forte-123", nome="Paula", perfil="gerente"
    )
    filiais_services.definir_filiais_do_usuario(paula.pk, [caucaia])
    cenario.moto.pessoas["Paula"] = paula
    outra = cenario.moto.api("Paula").get("/api/painel/inicio/").json()
    assert outra["variante"] == "gerente"
    assert outra["pendencias"] == {
        "titulo": "Nenhuma transferência no Detran pendente",
        "itens": [],
    }


def test_ven_11_lista_vistoriador_403(cenario, quitada):  # noqa: F811
    assert cenario.moto.api("João").get(VENDAS).status_code == 403


def test_ven_11_sem_o_recurso_de_vendas(cenario, quitada, planos):  # noqa: F811
    """PLT-12: sem `vendas_comissoes`, `/api/vendas/` fecha, e a transferência segue pela
    locação (é do recurso `locacoes_vistoria`)."""
    empresa = cenario.moto.empresa
    empresa.plano = planos["Essencial"]
    empresa.save(update_fields=["plano"])
    resposta = cenario.moto.api("Rodrigo").get(VENDAS)
    assert resposta.status_code == 403 and resposta.json()["codigo"] == "PLT-12"
    assert _registrar(cenario, quitada["id"]).status_code == 200


def test_ven_11_isolamento_entre_empresas(quitada):
    assert Venda.objects.count() == 1
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    assert not Venda.objects.exists()
