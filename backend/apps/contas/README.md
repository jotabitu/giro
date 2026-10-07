# app `contas`

**Schema:** empresa
**Escopo:** Usuários da empresa, perfis, permissões extras, filiais do usuário, convites, sessões, 2FA, login.
**Regras:** USR (ver `docs/regras-de-negocio.md`)
**Telas:** Login, Acesso-Senha, Convite, Admin-Usuarios (ver `docs/telas/README.md`)

## Estrutura esperada

```
contas/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/contas.md` (escrito pelo arquiteto antes da implementação).
