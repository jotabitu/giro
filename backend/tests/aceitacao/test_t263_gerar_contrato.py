"""T-263 · Ação `gerar_contrato` na locação (`docs/api/locacoes.md`, `acoes.gerar_contrato`;
`docs/api/contratos.md`, recusas do `POST /api/locacoes/{id}/contrato/`).

A ação diz antes se o `POST` passa: quem cria locação, `aguardando_retirada`, sem desconto
pendente (`APR-01`), sem cancelamento em curso (`LOC-12`) e sem contrato vigente.
"""

import pytest

from apps.contratos import services as contratos
from apps.contratos.models import Contrato

from .test_t015_locacoes import LISTA
from .test_t090_contratos import _contrato, _gerar, moto  # noqa: F401 - fixture


def _acao(cenario, locacao_id: int, quem: str = "Bruna") -> bool:
    return bool(cenario.detalhe(locacao_id, quem)["acoes"]["gerar_contrato"])


@pytest.mark.parametrize(
    ("quem", "esperado"),
    [
        ("Mariana", True),
        ("Rodrigo", True),
        ("Bruna", True),
        ("João", False),
        ("Lúcia", False),
    ],
)
def test_loc_acoes_gerar_contrato_por_perfil(moto, quem, esperado):  # noqa: F811
    locacao = moto.confirmada()
    assert _acao(moto, locacao["id"], quem) is esperado


def test_loc_acoes_gerar_contrato(moto, django_capture_on_commit_callbacks):  # noqa: F811
    # Fora de `aguardando_retirada`: o rascunho.
    assert _acao(moto, moto.criar()["id"]) is False
    # Com o desconto pendente (APR-01).
    com_desconto = moto.confirmada(desconto_pct="7.00", veiculo=moto.veiculo("Urbana 110–125"))
    assert com_desconto["desconto"]["status"] == "pendente"
    assert _acao(moto, com_desconto["id"]) is False
    # Sem nada pendente: verdadeiro; o `POST` passa e o contrato `enviado` desliga a ação.
    locacao = moto.confirmada()
    assert _acao(moto, locacao["id"]) is True
    assert _gerar(moto, django_capture_on_commit_callbacks, locacao["id"]).status_code == 202
    assert _contrato(locacao["id"]).status == "enviado"
    detalhe = moto.detalhe(locacao["id"])
    assert detalhe["acoes"]["gerar_contrato"] is False
    assert detalhe["acoes"]["reenviar_contrato"] is True
    # Com o contrato cancelado, volta a valer.
    contratos.cancelar(_contrato(locacao["id"]), "Dados errados")
    assert _acao(moto, locacao["id"]) is True


def test_loc_gerar_contrato_com_cancelamento_em_curso(
    moto,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """LOC-12: com o cancelamento pedido, a ação é falsa e o `POST` responde 409."""
    locacao = moto.confirmada()
    pedido = moto.moto.api("Bruna").post(
        f"{LISTA}{locacao['id']}/cancelar/", {"motivo": "Cliente desistiu"}, format="json"
    )
    assert pedido.status_code in (200, 201, 202), pedido.json()
    detalhe = moto.detalhe(locacao["id"])
    assert detalhe["cancelamento"]["status"] == "pendente"
    assert detalhe["acoes"]["gerar_contrato"] is False
    resposta = _gerar(moto, django_capture_on_commit_callbacks, locacao["id"])
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "cancelamento_em_curso"
    assert resposta.json()["mensagem"] == "A locação tem um cancelamento em andamento."
    assert not Contrato.objects.filter(origem_id=locacao["id"]).exists()
