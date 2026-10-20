"""T-202 · O que a T-201 pede do seed completo, como a T-019 e a T-204: o evento "Mudou a
tabela de preço" de 01 out (`auditoria.md`, LOC-15), os números da tela Aprovações em 07 out
(`aprovacoes.md`, APR-12, CA-APR-01) e o `resumo` do pedido dos pneus (CA-APR-11). O `tom` das
linhas está em `test_t202_telas_resolvidas.py`, no cenário do CA-018-09 da T-018."""

from typing import Any

from apps.aprovacoes.models import PedidoAprovacao
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


def test_apr_12_numeros_do_seed(seed: Any):
    corpo = _api(seed, "Rodrigo").get("/api/aprovacoes/").json()
    indicadores = corpo["indicadores"]
    assert indicadores["esperando"]["quantidade"] == 2
    assert indicadores["aprovadas"]["quantidade"] == 2
    assert indicadores["aprovadas"]["tempo_medio_min"] == 90  # (40 + 140) / 2
    assert indicadores["aprovadas"]["contexto"] == "tempo médio de 1 h 30 min"
    assert indicadores["recusadas"]["quantidade"] == 0
    assert (indicadores["descontos"]["valor_centavos"], indicadores["descontos"]["contexto"]) == (
        0,
        "em 0 pedidos",
    )
    assert corpo["contagens"] == {
        "pendente": 2,
        "aprovado": 2,
        "recusado": 0,
        "minhas_pendentes": 0,
    }


def test_apr_03_resumo_da_despesa(seed: Any):
    pneus = PedidoAprovacao.objects.get(tipo="APR-03", status="pendente", valor_centavos=120000)
    corpo = _api(seed, "Rodrigo").get("/api/aprovacoes/").json()
    item = next(p for p in corpo["resultados"] if p["id"] == pneus.pk)
    celulas = {c["rotulo"]: c["valor"] for c in item["resumo"]["celulas"]}
    assert celulas["Categoria"] == "Manutenção"
    assert celulas["Descrição"] == "Pneus (2)"
    # A placa como os outros textos da API a mandam (sem hífen; o contrato mostra "PMZ-3E17").
    assert celulas["Veículo"] == "Honda Pop 110i · PMZ3E17"
    assert (celulas["Valor"], celulas["Vencimento"]) == ("R$ 1.200,00", "07 out")
    assert "Fornecedor" not in celulas and "Forma" not in celulas
