# app `automacoes`

**Schema:** empresa
**Escopo:** Tarefas Celery AUT-01 a AUT-15, agendadas por empresa no fuso America/Sao_Paulo.
**Regras:** AUT (ver `docs/regras-de-negocio.md`)
**Telas:** sem tela própria (ver `docs/telas/README.md`)

## Estrutura esperada

```
automacoes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/automacoes.md` (escrito pelo arquiteto antes da implementação).
