"""T-202 · O que a T-201 pede do seed completo, como a T-019 e a T-204: desde a ADR 0043,
o seed sem o evento "Mudou a tabela de preço" da categoria (LOC-15), os números da tela
Aprovações em 07 out (`aprovacoes.md`, APR-12, CA-APR-01) e o `resumo` do pedido dos pneus
(CA-APR-11). O `tom` das linhas está em `test_t202_telas_resolvidas.py`, no cenário do
CA-018-09 da T-018."""

from typing import Any

from apps.aprovacoes.models import PedidoAprovacao
from apps.auditoria.models import EventoAuditoria

from .test_t019_seed_completo import _api
from .test_t019_seed_completo import seed as seed
from .test_t127_seed import _seed_do_modulo, semeado  # noqa: F401 - fixtures


def test_aud_02_seed_sem_evento_da_tabela_de_preco(seed: Any):
    """ADR 0043: sem categorias no seed, não há `categoria.definir_preco` (o "Mudou a tabela de
    preço" de 01 out sai do seed); o texto do evento antigo continua testado na T-018."""
    assert not EventoAuditoria.objects.filter(acao="categoria.definir_preco").exists()


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
    assert (celulas["Valor"], celulas["Vencimento"]) == ("R$ 1.200,00", "07 out")
    assert item["resumo"]["nota"] == (
        "Acima de R$ 500 precisa de aprovação. Aprovada, vai para o financeiro pagar."
    )
    assert "Fornecedor" not in celulas and "Forma" not in celulas
