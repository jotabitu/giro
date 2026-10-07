# app `plataforma`

**Schema:** public
**Escopo:** Planos, empresas (tenants), faturas da assinatura, usuários da plataforma, acesso de suporte, implantações e chamados.
**Regras:** PLT, IMP (ver `docs/regras-de-negocio.md`)
**Telas:** Plat-*, Plataforma, Compra-*, Admin-Assinatura, Admin-Cancelar (ver `docs/telas/README.md`)

## Estrutura esperada

```
plataforma/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/plataforma.md` (escrito pelo arquiteto antes da implementação).
