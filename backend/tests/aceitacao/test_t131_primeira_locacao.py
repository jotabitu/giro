"""T-131 · A 1ª locação conclui a implantação (IMP-01).

Roda na `empresa_a` com as pessoas, a frota e os clientes da Moto Rápida (Filial Centro), sem a
carteira de outubro: nenhuma locação confirmada ainda. Relógio em 07 out 2026, 10:00, como a
T-015.
"""

from typing import Any

import pytest

from apps.auditoria.models import EventoAuditoria
from apps.contratos.models import ModeloContrato
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao
from apps.plataforma.models import UsoEmpresa
from apps.plataforma.services import concluir_implantacao

from .test_t015_locacoes import cenario  # noqa: F401 - fixture

EU = "/api/auth/eu/"
INICIO = "/api/painel/inicio/"


def _passos(cenario) -> dict[str, Any]:  # noqa: F811
    return dict(UsoEmpresa.objects.get(empresa=cenario.moto.empresa).passos_implantacao)


def _eventos() -> list[EventoAuditoria]:
    return list(EventoAuditoria.objects.filter(acao="implantacao.concluir"))


def _variantes(cenario) -> tuple[str, str]:  # noqa: F811
    """A variante de Mariana (administradora) no `eu` e no painel."""
    api = cenario.moto.api("Mariana")
    eu = api.get(EU).json()
    inicio = api.get(INICIO).json()
    return eu["navegacao"]["inicio"]["variante"], inicio["variante"]


def test_imp_01_primeira_locacao_conclui_a_implantacao(cenario):  # noqa: F811
    assert "primeira_locacao" not in _passos(cenario)
    # O painel em implantação fica no cache (5 min): a 1ª locação não espera ele vencer.
    assert _variantes(cenario) == ("implantacao", "implantacao")

    rascunho = cenario.criar()
    assert "primeira_locacao" not in _passos(cenario)  # rascunho não conta
    resposta = cenario.confirmar(rascunho["id"])
    assert resposta.status_code == 200, resposta.json()

    assert _passos(cenario)["primeira_locacao"] == "2026-10-07"
    [evento] = _eventos()
    assert (evento.categoria, evento.regra) == ("configuracoes", "IMP-01")
    assert (evento.objeto_tipo, evento.objeto_codigo) == ("locacao", "LOC-2856")
    assert evento.ator_nome.startswith("Bruna")
    assert _variantes(cenario) == ("geral", "geral")


def test_imp_01_segunda_locacao_nao_registra_de_novo(cenario):  # noqa: F811
    cenario.confirmada()
    assert _passos(cenario)["primeira_locacao"] == "2026-10-07"
    segunda = cenario.confirmada(
        cliente="Juliana", veiculo=cenario.veiculo("Street 150–160", exceto=("SAK1D39",))
    )
    assert segunda["codigo"] == "LOC-2857"
    assert _passos(cenario)["primeira_locacao"] == "2026-10-07"
    assert len(_eventos()) == 1
    # Chamada de novo (outra locação, outra venda): nada muda.
    assert concluir_implantacao(Locacao.objects.get(codigo="LOC-2857")) is False
    assert len(_eventos()) == 1


def test_imp_01_confirmacao_desfeita_nao_conclui(cenario, monkeypatch):  # noqa: F811
    """O passo grava na transação da confirmação: se ela desfaz, ele sai junto."""

    def falha(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("auditoria fora do ar")

    rascunho = Locacao.objects.get(pk=cenario.criar()["id"])
    monkeypatch.setattr("apps.plataforma.services.registrar_evento", falha)
    with pytest.raises(RuntimeError):
        locacoes_services.confirmar(rascunho, cenario.pessoas["Bruna"])

    rascunho.refresh_from_db()
    assert rascunho.status == "rascunho"
    assert "primeira_locacao" not in _passos(cenario)
    assert _eventos() == []


def test_imp_01_locacao_recusada_nao_conclui(cenario):  # noqa: F811
    ModeloContrato.objects.filter(pk=cenario.modelo.pk).update(arquivado=True)
    rascunho = cenario.criar()
    assert cenario.confirmar(rascunho["id"]).json()["codigo"] == "IMP-04"
    assert "primeira_locacao" not in _passos(cenario)
    assert _variantes(cenario) == ("implantacao", "implantacao")
