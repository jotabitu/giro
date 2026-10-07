# app `financeiro`

**Schema:** empresa
**Escopo:** Contas a receber (parcelas), despesas, caixa do dia, movimentos, conciliação bancária, comissões, DRE.
**Regras:** FIN (ver `docs/regras-de-negocio.md`)
**Telas:** Receber, Caixa, Despesas, Comissoes, Conciliacao, Financeiro (ver `docs/telas/README.md`)

## Estrutura esperada

```
financeiro/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/financeiro.md` (escrito pelo arquiteto antes da implementação).
