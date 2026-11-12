"""T-464 · Placa nos eventos de cadastrar e editar o veículo na auditoria (VEI-01, AUD).

Como os eventos de foto da T-460: `veiculo.cadastrar` e `veiculo.editar` levam a placa como
`objeto.codigo` e um `resumo` em português com a placa. Os eventos de antes da T-464, sem código,
mostram a placa atual do veículo.
"""

from typing import Any

from apps.auditoria.models import EventoAuditoria
from apps.veiculos.models import Veiculo
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import registrar_evento

from .test_t012_filiais import MotoRapida
from .test_t013_veiculos import _cadastro, _url, frota, moto  # noqa: F401 - fixtures

AUDITORIA = "/api/auditoria/eventos/"


def _linhas(empresa: MotoRapida, veiculo: Veiculo, acao: str) -> list[dict[str, Any]]:
    """Os eventos `acao` do veículo como a tela de Auditoria os recebe."""
    resposta = empresa.api("Mariana").get(
        AUDITORIA, {"objeto_tipo": "veiculo", "objeto_id": veiculo.pk}
    )
    assert resposta.status_code == 200, resposta.json()
    return [e for e in resposta.json()["resultados"] if e["acao"] == acao]


def test_vei_01_cadastrar_com_placa_como_codigo_e_resumo(moto, frota) -> None:  # noqa: F811
    resposta = moto.api("Rodrigo").post("/api/veiculos/", _cadastro(frota), format="json")
    assert resposta.status_code == 201, resposta.json()
    veiculo = Veiculo.objects.get(placa="QAB1C23")
    (linha,) = _linhas(moto, veiculo, "veiculo.cadastrar")
    assert linha["objeto"]["codigo"] == "QAB-1C23"
    assert linha["resumo"] == "Cadastrou o veículo QAB-1C23"
    assert linha["regra"] == "VEI-01"
    assert EventoAuditoria.objects.get(pk=linha["id"]).objeto_codigo == "QAB-1C23"


def test_vei_01_editar_com_placa_como_codigo_e_resumo(moto, frota) -> None:  # noqa: F811
    pnb = frota.veiculo("PNB7C04")
    resposta = moto.api("Mariana").patch(_url(pnb), {"cor": "azul"}, format="json")
    assert resposta.status_code == 200, resposta.json()
    (linha,) = _linhas(moto, pnb, "veiculo.editar")
    assert linha["objeto"]["codigo"] == "PNB-7C04"
    assert linha["resumo"] == "Editou o veículo PNB-7C04"
    assert EventoAuditoria.objects.get(pk=linha["id"]).objeto_codigo == "PNB-7C04"


def test_vei_01_evento_antigo_sem_codigo_mostra_a_placa_do_veiculo(moto, frota) -> None:  # noqa: F811
    """Os eventos gravados antes da T-464 não têm código: o resumo lê a placa do veículo."""
    pnb = frota.veiculo("PNB7C04")
    # Como o serviço gravava antes: sem `codigo` (o veículo não tem).
    registrar_evento(
        "veiculo.editar",
        CategoriaAuditoria.OPERACAO,
        objeto=pnb,
        antes={"cor": "preta"},
        depois={"cor": "azul"},
    )
    (linha,) = _linhas(moto, pnb, "veiculo.editar")
    assert linha["objeto"]["codigo"] is None
    assert linha["resumo"] == "Editou o veículo PNB-7C04"
