# app `empresas`

**Schema:** empresa
**Escopo:** Dados da empresa, marca (cor, logo, nome), configurações gerais, assistente de implantação, integrações.
**Regras:** IMP (ver `docs/regras-de-negocio.md`)
**Telas:** Admin-Marca, Config, Integracoes, Onboarding-* (ver `docs/telas/README.md`)

## Estrutura esperada

```
empresas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/empresas.md` (escrito pelo arquiteto antes da implementação).
