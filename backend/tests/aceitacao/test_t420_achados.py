"""T-420 · Achados da conferência do QA de 13 nov 2026 (`docs/qa/conferencia-13-nov-t420.md`).

- A2: o Início mostra a transferência no Detran pendente na hora da quitação e a tira na hora do
  registro, sem esperar o cache de 5 minutos (`LOC-16`, `VEN-11`).
- A3: o reembolso da sobra da caução na quitação tem a origem "Sobra da caução na quitação", e não
  "Locação cancelada antes da retirada" (`LOC-16`, `FIN-18`).
- A5: os eventos novos da T-420 têm resumo em português na auditoria, como os da T-460 e da T-464
  (`AUD`, `LOC-16`, `VEN-11`).
"""

from typing import Any

from apps.auditoria import textos as auditoria_textos
from apps.auditoria.models import EventoAuditoria
from apps.financeiro import services as financeiro
from apps.locacoes.models import Locacao, PlanoCompra
from comum import relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import registrar_evento

from .test_t015_locacoes import Cenario
from .test_t015_locacoes import cenario as cenario
from .test_t091_locacao_fim import _ativa
from .test_t420_locacao_com_compra import _confirmada, _criar_plano, _pagar, _retirada
from .test_t420_locacao_com_compra import compra as compra
from .test_t420_locacao_com_compra import plano as plano
from .test_t420_venda_da_quitacao import _quitar, _registrar
from .test_t420_venda_da_quitacao import quitada as quitada

INICIO = "/api/painel/inicio/"
REEMBOLSOS = "/api/financeiro/reembolsos/"


def _pendencias(cenario: Cenario, quem: str = "Rodrigo") -> dict[str, Any]:
    """O Início sem limpar o cache: o que a tela vê na hora."""
    resposta = cenario.moto.api(quem).get(INICIO)
    assert resposta.status_code == 200, resposta.json()
    return dict(resposta.json()["pendencias"])


# --- A2 ---


def test_loc_16_ven_11_inicio_mostra_a_transferencia_na_hora(
    cenario: Cenario,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """O Rodrigo abre o Início antes da quitação (fica no cache), a LOC-2856 quita, e o Início
    seguinte já traz a transferência. Registrada a transferência, ela sai na hora."""
    locacao = _ativa(cenario)
    antes = _pendencias(cenario)
    assert antes["itens"] == []
    with django_capture_on_commit_callbacks(execute=True):
        _quitar(cenario, locacao["id"])
    depois = _pendencias(cenario)
    assert depois["titulo"] == "1 transferência no Detran pendente"
    assert [i["destino"] for i in depois["itens"]] == [{"chave": "locacoes", "id": locacao["id"]}]

    with django_capture_on_commit_callbacks(execute=True):
        assert _registrar(cenario, locacao["id"]).status_code == 200
    assert _pendencias(cenario)["itens"] == []


# --- A3 ---


def _linha_do_reembolso(cenario: Cenario, locacao: Locacao) -> dict[str, Any]:
    resposta = cenario.moto.api("Lúcia").get(REEMBOLSOS, {"busca": locacao.codigo})
    assert resposta.status_code == 200, resposta.json()
    [linha] = resposta.json()["resultados"]
    return dict(linha)


def test_loc_16_fin_18_reembolso_da_sobra_da_caucao_na_quitacao(compra: Cenario) -> None:
    """CA-420-14 pelo caminho real: 104 × R$ 199,00 com caução de R$ 300,00; paga a 103ª, quita,
    e os R$ 101,00 voltam com a origem da quitação."""
    plano = _criar_plano(
        compra,
        nome="Compra Street 104 semanas",
        periodicidade="semanal",
        parcelas=104,
        valor_parcela_centavos=19900,
    )
    locacao = _retirada(_confirmada(compra, plano["id"]))
    _pagar(locacao, *range(2, 104))
    locacao.refresh_from_db()
    assert locacao.quitada_em is not None
    linha = _linha_do_reembolso(compra, locacao)
    assert linha["valor_centavos"] == 10100
    assert linha["origem"]["tipo"] == "quitacao"
    assert linha["origem"]["id"] == locacao.pk
    assert linha["origem_rotulo"] == "Sobra da caução na quitação"
    assert linha["motivo"] == f"Sobra da caução na quitação da {locacao.codigo}"


def test_loc_12_reembolso_do_cancelamento_continua_igual(cenario: Cenario) -> None:
    """A locação sem quitação (o cancelamento antes da retirada) segue com o rótulo de antes."""
    locacao = Locacao.objects.get(pk=cenario.confirmada()["id"])
    financeiro.devolver_ao_cliente(
        financeiro.Origem("locacao", locacao.pk, locacao.codigo),
        filial_id=locacao.filial_id,
        cliente_id=locacao.cliente_id,
        valor_centavos=30000,
        forma="pix",
        motivo="Locação cancelada",
        regra="LOC-12",
    )
    linha = _linha_do_reembolso(cenario, locacao)
    assert (linha["origem"]["tipo"], linha["origem_rotulo"]) == (
        "cancelamento",
        "Locação cancelada antes da retirada",
    )


# --- A5 ---


def _texto(acao: str, **filtro: Any) -> tuple[str, str]:
    evento = EventoAuditoria.objects.filter(acao=acao, **filtro).latest("id")
    pronto = auditoria_textos.texto(evento, {})
    return pronto.resumo, pronto.detalhe


def test_aud_ven_11_venda_e_veiculo_vendido_em_portugues(
    cenario: Cenario,
    quitada: dict[str, Any],
) -> None:
    """A venda da quitação e o veículo vendido, pelo caminho real (o Sistema), e a transferência
    registrada pelo Rodrigo."""
    assert _texto("venda.criar_da_quitacao") == (
        "Criou a venda VEN-0001 da quitação",
        "Quitação da LOC-2856",
    )
    assert _texto("veiculo.vendido") == ("Vendeu o veículo SAK-1D39", "Quitação da LOC-2856")
    assert _registrar(cenario, quitada["id"]).status_code == 200
    hoje = relogio.hoje()
    assert _texto("venda.registrar_transferencia") == (
        "Registrou a transferência no Detran da VEN-0001",
        f"Feita em {hoje:%d/%m/%Y}",
    )


def test_aud_loc_16_quitar_e_encerrar_por_atraso_em_portugues(cenario: Cenario) -> None:
    """Como `locacoes` grava os dois eventos (o código da locação e o motivo)."""
    locacao = Locacao.objects.get(pk=_ativa(cenario)["id"])
    registrar_evento(
        "locacao.quitar",
        CategoriaAuditoria.OPERACAO,
        objeto=locacao,
        motivo="Todas as parcelas pagas",
        regra="LOC-16",
    )
    assert _texto("locacao.quitar") == ("Quitou a locação LOC-2856", "Todas as parcelas pagas")
    registrar_evento(
        "locacao.encerrar_por_atraso",
        CategoriaAuditoria.OPERACAO,
        objeto=locacao,
        motivo="Parcela 5 atrasada há 20 dias",
        regra="LOC-16",
    )
    assert _texto("locacao.encerrar_por_atraso") == (
        "Encerrou a locação LOC-2856 por atraso",
        "Parcela 5 atrasada há 20 dias",
    )


def test_aud_loc_16_plano_de_compra_em_portugues(compra: Cenario, plano: dict[str, Any]) -> None:
    """Criar, editar e desativar pela tela `Precos` (a Mariana)."""
    assert _texto("plano_compra.criar")[0] == "Criou o plano de compra Compra Street 24 meses"
    url = f"/api/planos-compra/{plano['id']}/"
    editado = compra.moto.api("Mariana").patch(url, {"nome": "Compra Street 2 anos"}, format="json")
    assert editado.status_code == 200, editado.json()
    assert _texto("plano_compra.editar")[0] == "Editou o plano de compra Compra Street 2 anos"
    # Evento sem o nome gravado: o nome de hoje do plano.
    registrar_evento(
        "plano_compra.desativar",
        CategoriaAuditoria.CONFIGURACOES,
        objeto=PlanoCompra.objects.get(pk=plano["id"]),
    )
    assert _texto("plano_compra.desativar")[0] == (
        "Desativou o plano de compra Compra Street 2 anos"
    )
