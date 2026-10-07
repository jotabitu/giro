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
