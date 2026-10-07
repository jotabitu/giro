# app `vendas`

**Schema:** empresa
**Escopo:** Propostas, funil, simulação de pagamento, troca, venda, recibo.
**Regras:** VEN (ver `docs/regras-de-negocio.md`)
**Telas:** Vendas, Venda, Vendedor (ver `docs/telas/README.md`)

## Estrutura esperada

```
vendas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/vendas.md` (escrito pelo arquiteto antes da implementação).
