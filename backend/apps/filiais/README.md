# app `filiais`

**Schema:** empresa
**Escopo:** Filiais, matriz, horário de funcionamento.
**Regras:** PLT-03 (limite) (ver `docs/regras-de-negocio.md`)
**Telas:** Filiais, Filial, Onboarding-Filial (ver `docs/telas/README.md`)

## Estrutura esperada

```
filiais/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/filiais.md` (escrito pelo arquiteto antes da implementação).
