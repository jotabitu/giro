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

## Implementado (T-081)

- `selectors.QUEM_DECIDE`: a tabela "Quem decide" do contrato. `APR-01` e `APR-02` também com as extras `aprovar_desconto` e `cancelar_contrato`; os outros, gerente e administrador.
- `selectors.decisor`: os tipos e as filiais de quem decide, uma vez por requisição. O administrador decide em todas as filiais, inclusive as desativadas.
- `GET /api/aprovacoes/`: os pedidos que a pessoa decide, no `X-Filial`, sem os que ela fez (`APR-09`). Com `?minhas=true`, os próprios. Mais antigo primeiro, com `contagens.pendente`.
- `aprovar`, `recusar` (motivo obrigatório, `APR-07`) e `cancelar` (só quem pediu):
  - fora do escopo, 404;
  - o próprio pedido, 403 `APR-09`;
  - já decidido, 409 `transicao_pedido`.
- Toda decisão grava quem e quando na mesma auditoria da mudança de status (`APR-10`) e publica `aprovacoes.pedido_decidido` na mesma transação. Se o efeito na origem falha, a decisão volta.
- O assinante do `APR-06` fica em `veiculos/eventos.py`.

## Falta

- O aviso ao gerente quando o pedido nasce, e a quem pediu quando é decidido (com `notificacoes`).
- A tela `Gerente` com 1 toque (`APR-07`) e o lembrete de 4 horas úteis (`APR-08`, `AUT-09`), na fase 2.
