# app `manutencao`

**Schema:** empresa
**Escopo:** Ordens de serviço, oficinas, preventivas por km e data.
**Regras:** MAN (ver `docs/regras-de-negocio.md`)
**Telas:** Manutencao (ver `docs/telas/README.md`)

## Estrutura esperada

```
manutencao/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/manutencao.md` (escrito pelo arquiteto antes da implementação).
