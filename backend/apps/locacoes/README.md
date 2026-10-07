# app `locacoes`

**Schema:** empresa
**Escopo:** Planos especiais, locações, reservas, contratos e modelos de contrato, renovação, cancelamento.
**Regras:** LOC (ver `docs/regras-de-negocio.md`)
**Telas:** Locacao, Locacoes, Locacao-Detalhe, Contratos-Modelos (ver `docs/telas/README.md`)

## Estrutura esperada

```
locacoes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/locacoes.md` (escrito pelo arquiteto antes da implementação).
