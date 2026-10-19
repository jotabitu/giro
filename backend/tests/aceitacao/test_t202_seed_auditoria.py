"""T-202 · O evento "Mudou a tabela de preço" de 01 out no seed (`auditoria.md`, T-201; LOC-15).
Usa o seed completo, como a T-019 e a T-204. O `tom` das linhas está em
`test_t202_telas_resolvidas.py`, no cenário do CA-018-09 da T-018."""

from typing import Any

from apps.auditoria.models import EventoAuditoria

from .test_t019_seed_completo import _api, _sp
from .test_t019_seed_completo import seed as seed
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures


def test_aud_02_evento_da_tabela_de_preco(seed: Any):
    evento = EventoAuditoria.objects.exclude(antes={}).get(acao="categoria.definir_preco")
    assert _sp(evento.ocorrido_em) == "2026-10-01 17:42"
    assert evento.antes == {"semanal_centavos": 29940}
    assert evento.depois["semanal_centavos"] == 32900
    assert evento.depois["vigente_desde"] == "2026-10-01"

    linha = _api(seed).get(f"/api/auditoria/eventos/{evento.pk}/").json()
    assert linha["ator"]["nome"] == "Mariana Costa"
    assert (linha["categoria"], linha["regra"], linha["tom"]) == ("configuracoes", "LOC-15", "info")
    assert (linha["resumo"], linha["detalhe"]) == (
        "Mudou a tabela de preço",
        "Street 150–160 · semanal R$ 299,40 → R$ 329,00",
    )
    # A categoria nova, sem preço anterior: "Definiu a tabela de preço" com os valores.
    nova = EventoAuditoria.objects.filter(acao="categoria.definir_preco", antes={}).first()
    assert nova is not None
    definiu = _api(seed).get(f"/api/auditoria/eventos/{nova.pk}/").json()
    assert definiu["resumo"] == "Definiu a tabela de preço"
    assert definiu["detalhe"].count("R$") == 4  # diária, semanal, mensal e caução
