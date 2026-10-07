# app `relatorios`

**Schema:** empresa
**Escopo:** Indicadores das telas iniciais, relatórios e DRE (só leitura, a partir dos outros apps).
**Regras:** FIN-13, relatórios (ver `docs/regras-de-negocio.md`)
**Telas:** Main, Dashboard, Pos-Dashboard, Relatorios, inícios por perfil (ver `docs/telas/README.md`)

## Estrutura esperada

```
relatorios/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/relatorios.md` (escrito pelo arquiteto antes da implementação).
