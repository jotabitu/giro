"""T-416 · Ver o comprovante da despesa paga (`FIN-05`, `AUD-05`).

A Lúcia (financeiro) paga por Pix o óleo de R$ 48,00 lançado pela Bruna em 07 out 2026, com o
comprovante. A despesa passa a devolver `comprovante` com a URL de 15 minutos, na resposta do
pagamento, no detalhe e na lista; o token de suporte recebe `null` (`AUD-09`, como o reembolso).
"""

from typing import Any

from .test_t015_locacoes import cenario  # noqa: F401 - fixture
from .test_t016_vistorias import _jpg
from .test_t017_financeiro import _despesa
from .test_t317_varredura_suporte import _suporte

DESPESAS = "/api/financeiro/despesas/"


def _expira_em_15_minutos(arquivo: dict[str, Any]) -> None:
    """10:00 em Fortaleza é 13:00 UTC; a URL vale até 13:15 (AUD-05)."""
    assert arquivo["url"]
    assert arquivo["url_expira_em"] == "2026-10-07T13:15:00Z"


def test_fin_05_aud_05_comprovante_da_despesa_paga(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    lancada = _despesa(cenario, "Bruna")
    assert lancada.status_code == 201, lancada.json()
    despesa = lancada.json()
    assert (despesa["status"], despesa["comprovante"]) == ("a_pagar", None)

    lucia = cenario.moto.api("Lúcia")
    paga = lucia.post(
        f"{DESPESAS}{despesa['id']}/pagar/",
        {"forma": "pix", "pago_em": "2026-10-07T13:00:00Z", "comprovante": _jpg("pix.jpg")},
        format="multipart",
    )
    assert paga.status_code == 200, paga.json()
    assert paga.json()["status"] == "paga"
    _expira_em_15_minutos(paga.json()["comprovante"])

    detalhe = lucia.get(f"{DESPESAS}{despesa['id']}/").json()
    _expira_em_15_minutos(detalhe["comprovante"])
    # Nova a cada leitura (AUD-05), separada da nota.
    assert detalhe["comprovante"]["url"] != detalhe["nota"]["url"]

    lista = lucia.get(DESPESAS, {"mes": "2026-10", "status": "paga"}).json()["resultados"]
    item = next(d for d in lista if d["id"] == despesa["id"])
    _expira_em_15_minutos(item["comprovante"])


def test_fin_05_despesa_paga_sem_comprovante(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    despesa = _despesa(cenario, "Bruna").json()
    paga = cenario.moto.api("Lúcia").post(
        f"{DESPESAS}{despesa['id']}/pagar/",
        {"forma": "transferencia", "pago_em": "2026-10-07T13:00:00Z"},
        format="multipart",
    )
    assert paga.status_code == 200, paga.json()
    assert paga.json()["comprovante"] is None


def test_aud_09_suporte_nao_recebe_o_comprovante_da_despesa(cenario, relogio_jwt):  # noqa: F811
    relogio_jwt.em("2026-10-07 10:00")
    despesa = _despesa(cenario, "Bruna").json()
    cenario.moto.api("Lúcia").post(
        f"{DESPESAS}{despesa['id']}/pagar/",
        {"forma": "pix", "pago_em": "2026-10-07T13:00:00Z", "comprovante": _jpg("pix.jpg")},
        format="multipart",
    )
    suporte = _suporte(cenario)
    detalhe = suporte.get(f"{DESPESAS}{despesa['id']}/")
    assert detalhe.status_code == 200, detalhe.json()
    assert detalhe.json()["comprovante"] is None
    lista = suporte.get(DESPESAS, {"mes": "2026-10"}).json()["resultados"]
    assert all(d["comprovante"] is None for d in lista)
