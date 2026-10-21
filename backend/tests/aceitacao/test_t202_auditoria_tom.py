"""T-202 · O `tom` das linhas da auditoria (`auditoria.md`, T-201), no cenário do CA-018-09 da
T-018."""

from .test_t018_auditoria import aud, moto  # noqa: F401 - fixtures


def test_aud_02_tom_das_linhas(aud):  # noqa: F811
    """CA-018-09 (cenário da T-018): suporte em alerta, login bloqueado em perigo, configurações
    e segurança em info, o resto sem tom."""
    api = aud.moto.api("Mariana")
    linhas = api.get("/api/auditoria/eventos/", {"periodo": "7d"}).json()["resultados"]
    tons = {(linha["acao"], linha["tom"]) for linha in linhas}
    assert ("usuario.bloqueado", "perigo") in tons
    assert ("usuario.convidar", "info") in tons
    assert ("categoria.definir_preco", "info") in tons
    assert ("movimento_caixa.sangria", None) in tons
    assert {linha["tom"] for linha in linhas if linha["suporte"]} == {"alerta"}
