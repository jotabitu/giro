"""T-460 · Eventos de foto do veículo na auditoria (VEI-10, AUD-01; CA-437-13).

Os quatro eventos da galeria (`veiculo.foto_enviar`, `_trocar`, `_capa`, `_apagar`) levam a placa
como `objeto.codigo`, um `resumo` em português com a placa e um `detalhe` só com o nome do
arquivo, o número da foto e a capa (docs/api/auditoria.md). A galeria do QXA-4B21 é a do seed:
frente (capa), lateral e painel.
"""

from typing import Any

from apps.auditoria.models import EventoAuditoria
from apps.veiculos.models import Veiculo
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import registrar_evento

from .test_t012_filiais import MotoRapida
from .test_t414_fotos_veiculo import (  # noqa: F401 - fixtures
    _acao,
    _do_seed,
    _enviar,
    _jpg,
    _png,
    _trocar,
    frota,
    moto,
)

AUDITORIA = "/api/auditoria/eventos/"


def _linhas(empresa: MotoRapida, veiculo: Veiculo) -> list[dict[str, Any]]:
    """Os eventos de foto do veículo como a tela de Auditoria os recebe, do mais antigo ao mais
    novo."""
    resposta = empresa.api("Mariana").get(
        AUDITORIA, {"objeto_tipo": "veiculo", "objeto_id": veiculo.pk}
    )
    assert resposta.status_code == 200, resposta.json()
    linhas = [e for e in resposta.json()["resultados"] if e["acao"].startswith("veiculo.foto_")]
    return list(reversed(linhas))


def test_vei_10_foto_enviada_com_placa_detalhe_e_resumo_em_portugues(moto, frota) -> None:  # noqa: F811
    """CA-437-13: a `moto.png` enviada ao PNB-7C04 sem galeria vira capa; a segunda, não."""
    pnb = frota.veiculo("PNB7C04")
    assert _enviar(moto, pnb, _png("moto.png")).status_code == 201
    assert _enviar(moto, pnb, _jpg("lateral.jpg")).status_code == 201
    primeira, segunda = _linhas(moto, pnb)
    assert primeira["objeto"]["codigo"] == "PNB-7C04"
    assert primeira["resumo"] == "Enviou uma foto do veículo PNB-7C04"
    assert primeira["detalhe"] == "moto.png · foto 1 · virou a capa"
    assert primeira["regra"] == "VEI-10"
    assert segunda["detalhe"] == "lateral.jpg · foto 2 · não é a capa"
    assert EventoAuditoria.objects.get(pk=primeira["id"]).objeto_codigo == "PNB-7C04"


def test_vei_10_trocar_capa_e_apagar_com_placa_e_detalhe(moto, frota) -> None:  # noqa: F811
    qxa = frota.veiculo("QXA4B21")
    seed = _do_seed(qxa)
    assert _trocar(moto, qxa, seed["Lateral"], _png("lateral-nova.png")).status_code == 200
    assert _acao(moto, qxa, seed["Painel"], "capa").status_code == 200
    assert _acao(moto, qxa, seed["Painel"], "apagar").status_code == 200
    trocar, capa, apagar = _linhas(moto, qxa)
    assert {e["objeto"]["codigo"] for e in (trocar, capa, apagar)} == {"QXA-4B21"}
    assert (trocar["resumo"], trocar["detalhe"]) == (
        "Trocou uma foto do veículo QXA-4B21",
        "lateral-nova.png · foto 2 · não é a capa",
    )
    assert (capa["resumo"], capa["detalhe"]) == (
        "Mudou a capa do veículo QXA-4B21",
        "a foto 3 virou a capa",
    )
    assert (apagar["resumo"], apagar["detalhe"]) == (
        "Apagou uma foto do veículo QXA-4B21",
        "foto 1 · era a capa; a mais antiga virou a capa",
    )


def test_vei_10_detalhe_sem_imagem_nem_dado_pessoal(moto, frota) -> None:  # noqa: F811
    """AUD-01: o evento não leva a imagem, a URL nem o caminho no armazenamento; o nome do
    arquivo vem sem pasta."""
    pnb = frota.veiculo("PNB7C04")
    assert _enviar(moto, pnb, _png("C:\\fotos\\moto.png")).status_code == 201
    (linha,) = _linhas(moto, pnb)
    evento = EventoAuditoria.objects.get(pk=linha["id"])
    assert evento.depois["arquivo"] == "moto.png"
    assert set(evento.depois) == {"foto_id", "numero", "capa", "arquivo"}
    assert "http" not in str(evento.depois) and "/" not in str(evento.depois)


def test_vei_10_evento_antigo_sem_codigo_mostra_a_placa_do_veiculo(moto, frota) -> None:  # noqa: F811
    """Os eventos gravados antes da T-460 não têm código nem arquivo: o resumo lê a placa do
    veículo e o detalhe mostra o que o evento tem."""
    pnb = frota.veiculo("PNB7C04")
    # Como o serviço gravava antes: sem `codigo` (o veículo não tem) e sem o nome do arquivo.
    registrar_evento(
        "veiculo.foto_enviar",
        CategoriaAuditoria.OPERACAO,
        objeto=pnb,
        depois={"foto_id": 1, "numero": 1, "capa": True},
        regra="VEI-10",
    )
    (linha,) = _linhas(moto, pnb)
    assert linha["objeto"]["codigo"] is None
    assert linha["resumo"] == "Enviou uma foto do veículo PNB-7C04"
    assert linha["detalhe"] == "foto 1 · virou a capa"
