# app `aprovacoes`

**Schema:** empresa
**Escopo:** Pedidos de aprovação (desconto, cancelamento, despesa, correção de km), prazos e lembretes.
**Regras:** APR (ver `docs/regras-de-negocio.md`)
**Telas:** Gerente, Venda, Despesas (ver `docs/telas/README.md`)

## Estrutura esperada

```
aprovacoes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/aprovacoes.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-013, ADR 0019)

- `models.py`: `PedidoAprovacao`, uma máquina de estados (`pendente` → `aprovado`, `recusado` ou `cancelado`).
  - Tem a origem genérica, a `filial`, os textos prontos `titulo` e `detalhe` e os `dados` por tipo.
  - No banco: `CHECK` "quem pede não aprova" (`APR-09`) e um só `pendente` por `(tipo, origem_tipo, origem_id)`.
- `services.pedir`: grava o pedido e a auditoria (`APR-10`). Um pedido igual pendente levanta `comum.aprovacoes.PedidoPendente` (409 `pedido_pendente`).
- `services.cancelar_pendentes`: cancela os pendentes e publica `aprovacoes.pedido_decidido`.
- `selectors.pendente`.
- O `ready()` registra as três funções em `comum.aprovacoes`. Os outros apps só abrem pedidos por ali (teste em `tests/test_limites_entre_apps.py`).

## Falta (T-081)

- A lista, as decisões de aprovar e recusar, o evento na decisão e o aviso ao gerente (com `notificacoes`).
