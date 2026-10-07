# app `auditoria`

**Schema:** empresa + public
**Escopo:** Eventos imutáveis, exportação de dados, anonimização LGPD, retenção após cancelamento.
**Regras:** AUD (ver `docs/regras-de-negocio.md`)
**Telas:** Admin-Auditoria, Plat-Auditoria, Admin-Exportar (ver `docs/telas/README.md`)

## Estrutura esperada

```
auditoria/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/auditoria.md` (escrito pelo arquiteto antes da implementação).
