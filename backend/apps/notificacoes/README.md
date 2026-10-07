# app `notificacoes`

**Schema:** empresa
**Escopo:** Envio por WhatsApp, e-mail e push com a marca da locadora; preferências por pessoa; sino.
**Regras:** AUT (canais) (ver `docs/regras-de-negocio.md`)
**Telas:** todas (sino e push) (ver `docs/telas/README.md`)

## Estrutura esperada

```
notificacoes/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/notificacoes.md` (escrito pelo arquiteto antes da implementação).
