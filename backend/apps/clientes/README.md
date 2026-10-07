# app `clientes`

**Schema:** empresa
**Escopo:** Clientes PF/PJ, CNH, documentos, contatos, bloqueio, consentimento LGPD.
**Regras:** CLI, AUD-04, AUD-06 (ver `docs/regras-de-negocio.md`)
**Telas:** Clientes, Cliente (ver `docs/telas/README.md`)

## Estrutura esperada

```
clientes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/clientes.md` (escrito pelo arquiteto antes da implementação).
