# app `vistorias`

**Schema:** empresa
**Escopo:** Vistoria de saída e de devolução, fotos, avarias, acerto da devolução e da caução.
**Regras:** VIS, DEV (ver `docs/regras-de-negocio.md`)
**Telas:** Vistoria, Devolucao, Vistoriador (ver `docs/telas/README.md`)

## Estrutura esperada

```
vistorias/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/vistorias.md` (escrito pelo arquiteto antes da implementação).
